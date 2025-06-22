# File: action/robotics.py

"""Minimal robotics abstraction layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class RobotState:
    """Simple position and orientation container."""

    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float]


class RobotController:
    """Provides basic movement commands for a robot."""

    def __init__(self) -> None:
        self.state = RobotState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    def move_to(self, x: float, y: float, z: float) -> None:
        """Move robot to the given coordinates."""

        self.state.position = (x, y, z)

    def rotate_to(self, yaw: float, pitch: float, roll: float) -> None:
        """Rotate robot to the given orientation."""

        self.state.orientation = (yaw, pitch, roll)

    def get_state(self) -> RobotState:
        """Return current state of the robot."""

        return self.state

