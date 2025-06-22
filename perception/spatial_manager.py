# File: perception/spatial_manager.py

"""Track spatial positions of entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Entity:
    """Represents an object in 3D space."""

    name: str
    position: Tuple[float, float, float]


class SpatialManager:
    """Very small in-memory spatial registry."""

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}

    def update(self, name: str, position: Tuple[float, float, float]) -> None:
        """Create or update an entity position."""

        self._entities[name] = Entity(name, position)

    def get(self, name: str) -> Entity | None:
        """Return entity by name if it exists."""

        return self._entities.get(name)

