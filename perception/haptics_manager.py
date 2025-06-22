# File: perception/haptics_manager.py

"""Manage haptic feedback devices."""

from __future__ import annotations


class HapticsManager:
    """Simple abstraction for vibration capable devices."""

    def vibrate(self, intensity: float, duration: float) -> None:
        """Trigger a vibration with given intensity (0..1) and duration in seconds."""

        # Real implementation would communicate with device driver
        pass

