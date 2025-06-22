# File: core/utils/metrics.py

"""Expose very lightweight in-process counters."""

from __future__ import annotations


class Counter:
    """Simple integer counter."""

    def __init__(self) -> None:
        self.value = 0

    def inc(self, amount: int = 1) -> None:
        """Increase counter by *amount*."""

        self.value += amount

    def get(self) -> int:
        """Return current value."""

        return self.value

