# File: core/refactor_engine.py

"""Simple automatic formatting engine triggered via the EventBus."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Optional

from .event_bus import EventBus


class RefactorEngine:
    """Listens for optimization events and formats the code base."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus or EventBus()

    async def initialize(self) -> None:
        """Start listening for optimization events."""

        await self.event_bus.subscribe("consciousness.optimize", self._on_optimize)

    async def _on_optimize(self, _payload: object) -> None:
        """Run autopep8 over the project to keep it clean."""

        proc = await asyncio.create_subprocess_exec(
            "autopep8", "--in-place", "--recursive", ".",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
