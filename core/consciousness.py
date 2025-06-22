# File: core/consciousness.py

import asyncio
import logging
from typing import Any, Dict, Optional

from core.event_bus import EventBus

logger = logging.getLogger(__name__)

class ConsciousnessEngine:
    """
    AgentProject’in merkez “beyni”. 
    Hafıza, model, API, karar alma ve kendi kendini optimize etme döngülerini yönetir.
    """

    def __init__(
        self,
        memory: Any,
        model_manager: Any,
        api_manager: Any,
        event_bus: Optional[EventBus] = None,
    ):
        self.memory = memory
        self.model_manager = model_manager
        self.api_manager = api_manager
        self.event_bus = event_bus or EventBus()
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def initialize(self):
        logger.info("Consciousness: başlatılıyor")
        # Event abonelikleri
        await self.event_bus.subscribe("consciousness.request", self._on_request, priority=10)
        # Döngüsel görevler
        self._tasks = [
            asyncio.create_task(self._decision_loop(), name="decision_loop"),
            asyncio.create_task(self._self_optimize_loop(), name="optimize_loop"),
            asyncio.create_task(self._memory_maintenance_loop(), name="memory_loop"),
        ]
        self.event_bus.publish_nowait("consciousness.initialized", None)
        logger.info("Consciousness: başlatıldı")

    async def shutdown(self):
        logger.info("Consciousness: kapatılıyor")
        self._stop_event.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self.event_bus.publish_nowait("consciousness.shutdown", None)
        logger.info("Consciousness: kapatıldı")

    async def request(
        self,
        prompt: str,
        model: str = "default",
        timeout: float = 30.0,
    ) -> Any:
        """
        Dışarıdan API: prompt gönder, cevap dön.
        """
        correlation_id = id(prompt) ^ int(asyncio.get_event_loop().time() * 1e6)
        payload = {"prompt": prompt, "model": model, "cid": correlation_id}
        fut = asyncio.create_task(
            self.event_bus.wait_for(
                "consciousness.response",
                lambda res: isinstance(res, dict) and res.get("cid") == correlation_id,
                timeout=timeout
            )
        )
        self.event_bus.publish_nowait("consciousness.request", payload)
        try:
            response = await fut
        except asyncio.TimeoutError:
            raise TimeoutError("ConsciousnessEngine.request timed out")
        return response.get("result")

    async def _on_request(self, payload: Dict[str, Any]):
        """
        'consciousness.request' eventini işler: 
        Hafızadan bağlamı alır, modele prompt iletir, sonucu saklar ve 'consciousness.response' yayar.
        """
        prompt = payload.get("prompt", "")
        model_name = payload.get("model", "default")
        cid = payload.get("cid")

        logger.debug(f"Request: cid={cid}, prompt={prompt!r}")
        context = self.memory.retrieve_context(limit_tokens=1024)
        full_prompt = f"{context}\nUser: {prompt}\nAI:"
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.model_manager.infer(model_name, prompt=full_prompt)
            )
        except Exception as e:
            logger.error(f"Inference error cid={cid}: {e}")
            self.event_bus.publish_nowait("consciousness.error", {"cid": cid, "error": str(e)})
            return

        try:
            self.memory.store_interaction(prompt=prompt, response=result)
        except Exception as e:
            logger.warning(f"Memory store failed cid={cid}: {e}")

        self.event_bus.publish_nowait("consciousness.response", {"cid": cid, "result": result})

    async def _decision_loop(self):
        """
        Düzenli olarak bellek ve çevreyi analiz eder, tetiklenmesi gereken görevleri işler.
        """
        while not self._stop_event.is_set():
            try:
                pending = self.memory.get_pending_tasks()
                for task in pending:
                    self.event_bus.publish_nowait("consciousness.task", task)
                await asyncio.sleep(3600)  # 1 saatte bir
                self.event_bus.publish_nowait("consciousness.check_calendar", None)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Decision loop error: {e}")

    async def _self_optimize_loop(self):
        """
        Periyodik olarak kendi kendini optimize etme ve refactor event’i tetikler.
        """
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(300)  # 5 dakikada bir
                logger.debug("Self-optimization event tetiklendi")
                self.event_bus.publish_nowait("consciousness.optimize", None)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Optimize loop error: {e}")

    async def _memory_maintenance_loop(self):
        """
        Hafızayı özetleyip, gereksiz verileri temizler.
        """
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(600)  # 10 dakikada bir
                logger.debug("Memory prune")
                self.memory.prune(max_age_seconds=86400)
                self.event_bus.publish_nowait("consciousness.memory_pruned", None)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory maintenance error: {e}")
