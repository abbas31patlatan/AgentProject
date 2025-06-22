# File: perception/bci_adapter.py

"""Brain-computer interface abstraction."""

from __future__ import annotations

from typing import Callable


class BCIAdapter:
    """Stub adapter emitting synthetic brain wave events."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[[str], None]] = []

    def on_signal(self, callback: Callable[[str], None]) -> None:
        """Register a callback for brain signals."""

        self._callbacks.append(callback)

    def emit(self, signal: str) -> None:
        """Emit a synthetic signal to all subscribers."""

        for cb in self._callbacks:
            cb(signal)

