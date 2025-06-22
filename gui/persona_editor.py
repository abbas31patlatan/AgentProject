# File: gui/persona_editor.py

"""Simple data structure to hold persona information."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Persona:
    """Represents a user selectable persona."""

    name: str
    description: str


class PersonaEditor:
    """Manage available personas."""

    def __init__(self) -> None:
        self._personas: list[Persona] = []

    def add_persona(self, persona: Persona) -> None:
        """Add a new persona definition."""

        self._personas.append(persona)

    def list_personas(self) -> list[Persona]:
        """Return all personas."""

        return list(self._personas)

