# File: core/utils/telemetry.py

"""Collect simple runtime metrics."""

from __future__ import annotations

import time


class Telemetry:
    """Record timestamps for basic events."""

    def __init__(self) -> None:
        self.events: list[float] = []

    def ping(self) -> None:
        """Record a timestamp."""

        self.events.append(time.time())

