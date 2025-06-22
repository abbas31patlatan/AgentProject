# File: media/scene_synthesizer.py

"""Compose simple scenes using generated images and text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class SceneElement:
    """A positioned piece of text or image."""

    content: str
    x: int
    y: int


class SceneSynthesizer:
    """Combine elements into a textual scene description."""

    def synthesize(self, elements: List[SceneElement]) -> str:
        """Return a naive textual representation of the scene."""

        lines = [f"{el.content}@({el.x},{el.y})" for el in elements]
        return " | ".join(lines)

