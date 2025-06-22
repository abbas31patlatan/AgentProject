# File: core/event_bus.py

import asyncio
import fnmatch
from typing import Any, Awaitable, Callable, List, Tuple

Handler = Callable[[Any], Awaitable[None]]

class EventBus:
    """
    Gelişmiş Asenkron Event Bus:
    - Wildcard (fnmatch) ile pattern tabanlı abonelik
    - Priority (yüksek öncelik önce)
    - Tek seferlik (once) handler
    - publish (await ile) ve publish_nowait (fire&forget)
    - wait_for ile belirli bir event’i ve şartı bekleyebilme
    """
    def __init__(self):
        self._handlers: List[Tuple[str, Handler, int, bool]] = []
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        pattern: str,
        handler: Handler,
        priority: int = 0,
        once: bool = False,
    ):
        async with self._lock:
            self._handlers.append((pattern, handler, priority, once))
            self._handlers.sort(key=lambda x: -x[2])  # priority high → low

    def publish_nowait(self, event: str, payload: Any = None):
        asyncio.create_task(self.publish(event, payload))

    async def publish(self, event: str, payload: Any = None):
        """
        Eşleşen tüm handler’ları çağırır.
        once=True ise handler sadece bir kere çalışır ve silinir.
        """
        to_remove = []
        async with self._lock:
            handlers = list(self._handlers)
        for pattern, handler, _, once in handlers:
            if fnmatch.fnmatch(event, pattern):
                try:
                    await handler(payload)
                except Exception:
                    # Hataları yut (isteğe bağlı log eklenebilir)
                    pass
                if once:
                    to_remove.append((pattern, handler))
        if to_remove:
            async with self._lock:
                self._handlers = [
                    h for h in self._handlers
                    if (h[0], h[1]) not in to_remove
                ]

    async def wait_for(
        self,
        event: str,
        condition: Callable[[Any], bool] = lambda _: True,
        timeout: float = None
    ) -> Any:
        """
        Belirli bir event (veya koşul) için bekler. Tek seferlik handler olarak eklenir.
        """
        fut = asyncio.get_event_loop().create_future()

        async def _checker(payload):
            if condition(payload) and not fut.done():
                fut.set_result(payload)

        await self.subscribe(event, _checker, once=True)
        return await asyncio.wait_for(fut, timeout)
