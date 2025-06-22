# File: core/model_manager.py

"""Simple model manager and dummy models for AgentProject."""

from __future__ import annotations

from typing import Dict, Protocol


class BaseModel(Protocol):
    """Interface for all models."""

    def infer(self, prompt: str, **kwargs) -> str:
        """Return model response for a given prompt."""


class EchoModel:
    """A trivial model used as the default implementation."""

    def infer(self, prompt: str, **_: object) -> str:
        return f"ECHO: {prompt}"


class ModelManager:
    """Manage available models and perform inference."""

    def __init__(self) -> None:
        self._models: Dict[str, BaseModel] = {"default": EchoModel()}

    def register_model(self, name: str, model: BaseModel) -> None:
        """Register a new model instance."""

        self._models[name] = model

    def infer(self, name: str, prompt: str, **kwargs) -> str:
        """Run inference using the specified model."""

        if name not in self._models:
            raise KeyError(f"Model '{name}' is not registered")
        return self._models[name].infer(prompt, **kwargs)

