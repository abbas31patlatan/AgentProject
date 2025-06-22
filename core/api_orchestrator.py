# File: core/api_orchestrator.py

import asyncio
import json
from typing import Any, Dict, Optional, Union
import httpx
import grpc
import websockets
from cachetools import TTLCache
from aiobreaker import CircuitBreaker
from core.event_bus import EventBus

class APIInfo:
    def __init__(self, name: str, type_: str, endpoint: str, spec: Optional[Dict] = None, auth: Optional[Dict] = None):
        self.name = name
        self.type = type_  # rest, graphql, grpc, websocket
        self.endpoint = endpoint
        self.spec = spec
        self.auth = auth

class APIOrchestrator:
    """
    API keşfi ve çağrı merkezidir:
    - Runtime’da yeni API register/unregister
    - REST/GraphQL/gRPC/WebSocket desteği
    - Retry, circuit breaker, cache
    - EventBus ile istek/cevap event’leri
    """

    DEFAULT_TIMEOUT = 10.0
    CACHE_TTL = 300  # sn

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus or EventBus()
        self._apis: Dict[str, APIInfo] = {}
        self._clients: Dict[str, Any] = {}  # httpx, grpc channel vs.
        self._cache = TTLCache(maxsize=1024, ttl=self.CACHE_TTL)
        self._cb = CircuitBreaker(fail_max=5, reset_timeout=30)

    def register_api(self, info: APIInfo):
        self._apis[info.name] = info
        self._event_bus.publish_nowait("api.registered", info)

    def unregister_api(self, name: str):
        if name in self._apis:
            del self._apis[name]
            self._clients.pop(name, None)
            self._event_bus.publish_nowait("api.unregistered", name)

    def _get_http_client(self, name: str) -> httpx.AsyncClient:
        client = self._clients.get(name)
        if client is None:
            client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
            self._clients[name] = client
        return client

    def _get_grpc_channel(self, info: APIInfo) -> grpc.Channel:
        channel = self._clients.get(info.name)
        if channel is None:
            channel = grpc.aio.insecure_channel(info.endpoint)
            self._clients[info.name] = channel
        return channel

    async def call_api(
        self,
        name: str,
        path: str = "",
        method: str = "GET",
        params: Dict[str, Any] = None,
        json_body: Any = None,
        headers: Dict[str, str] = None,
        use_cache: bool = True
    ) -> Any:
        """
        REST/GraphQL çağrısı.
        """
        if name not in self._apis:
            raise KeyError(f"API '{name}' kayıtlı değil")
        info = self._apis[name]

        cache_key = f"{name}:{path}:{method}:{json.dumps(params, sort_keys=True)}:{json.dumps(json_body, sort_keys=True)}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        url = info.endpoint.rstrip("/") + "/" + path.lstrip("/")
        client = self._get_http_client(name)

        @self._cb
        async def _do_request():
            resp = await client.request(method, url, params=params or {}, json=json_body, headers=headers or {})
            resp.raise_for_status()
            data = resp.json()
            self._event_bus.publish_nowait("api.response", {"api": name, "path": path, "status": resp.status_code, "response": data})
            return data

        result = await _do_request()
        if use_cache:
            self._cache[cache_key] = result
        return result

    async def call_grpc(self, name: str, stub_class: Any, method_name: str, request_obj: Any) -> Any:
        """
        gRPC çağrısı.
        """
        if name not in self._apis:
            raise KeyError(f"gRPC API '{name}' kayıtlı değil")
        info = self._apis[name]
        channel = self._get_grpc_channel(info)
        stub = stub_class(channel)
        method = getattr(stub, method_name)
        try:
            response = await method(request_obj, timeout=self.DEFAULT_TIMEOUT)
            self._event_bus.publish_nowait("api.grpc_response", {"api": name, "method": method_name, "response": response})
            return response
        except Exception as e:
            self._event_bus.publish_nowait("api.grpc_error", {"api": name, "method": method_name, "error": str(e)})
            raise

    async def connect_websocket(self, name: str, on_message):
        """
        WebSocket API ile bağlantı kurup gelen mesajları handler’a iletir.
        """
        if name not in self._apis:
            raise KeyError(f"WebSocket API '{name}' kayıtlı değil")
        info = self._apis[name]
        uri = info.endpoint
        async with websockets.connect(uri) as ws:
            self._event_bus.publish_nowait("api.ws_open", name)
            try:
                async for msg in ws:
                    await on_message(msg)
                    self._event_bus.publish_nowait("api.ws_message", {"api": name, "message": msg})
            except websockets.ConnectionClosed:
                self._event_bus.publish_nowait("api.ws_close", name)

    def list_apis(self) -> Dict[str, APIInfo]:
        return dict(self._apis)

    def clear_cache(self):
        self._cache.clear()

    def close(self):
        for client in self._clients.values():
            if isinstance(client, httpx.AsyncClient):
                asyncio.create_task(client.aclose())
            elif isinstance(client, grpc.Channel):
                asyncio.create_task(client.close())
        self._clients.clear()
        self.clear_cache()
        self._event_bus.publish_nowait("api.closed", None)

