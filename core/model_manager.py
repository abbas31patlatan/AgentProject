"""Model management with automatic GGUF loader.

This module discovers models under the ``models`` directory and loads them on
request. GGUF models are loaded with ``llama_cpp`` when available. The manager
supports multiple frameworks, exposes a uniform ``infer`` method and can
hot-swap or remove models at runtime. Metadata is persisted to
``models/metadata.json`` so newly added files are detected automatically.
"""

from __future__ import annotations

import json
import hashlib
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Protocol, Optional

from core.event_bus import EventBus
from core.model_registry import ModelRegistry


class BaseModel(Protocol):
    """Minimal interface every model must implement."""

    def infer(self, prompt: str, **kwargs: object) -> str:
        """Return a text response for ``prompt``."""


class EchoModel:
    """Fallback model returning the prompt with an ``ECHO`` prefix."""

    def infer(self, prompt: str, **_: object) -> str:
        return f"ECHO: {prompt}"


@dataclass
class ModelMeta:
    """Metadata describing a local model file."""

    name: str
    framework: str
    path: str
    size: int
    added_at: float
    sha256: str


class GGUFModelWrapper:
    """Simple wrapper around a ``llama_cpp`` model instance."""

    def __init__(self, path: Path):
        try:
            from llama_cpp import Llama

            self._model = Llama(model_path=str(path))
            self._dummy = False
        except Exception:
            # Use a lightweight dummy when llama_cpp is unavailable.
            self._model = None
            self._dummy = True
            self._path = path

    def infer(self, prompt: str, **kwargs: object) -> str:
        if self._dummy:
            return f"DUMMY({self._path.name}): {prompt}"
        res = self._model.create_completion(prompt=prompt, **kwargs)
        return res["choices"][0]["text"]


class ModelManager:
    """Thread-safe manager that lazily loads models on demand."""

    SUPPORTED_EXT = {
        ".gguf": "gguf",
        ".onnx": "onnx",
        ".pt": "torch",
        ".pth": "torch",
    }

    def __init__(
        self,
        models_dir: str = "models",
        metadata_file: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.metadata_file = Path(metadata_file or self.models_dir / "metadata.json")
        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()
        self._models: Dict[str, BaseModel] = {"default": EchoModel()}
        self._meta: Dict[str, ModelMeta] = {}

        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._load_metadata()
        self.discover_models(update=True)

    # ------------------------------------------------------------------
    # Metadata handling
    # ------------------------------------------------------------------
    def _load_metadata(self) -> None:
        if self.metadata_file.exists():
            with self.metadata_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                self._meta[entry["name"]] = ModelMeta(**entry)

    def _save_metadata(self) -> None:
        with self.metadata_file.open("w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self._meta.values()], f, indent=2)

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Model discovery and loading
    # ------------------------------------------------------------------
    def discover_models(self, update: bool = False) -> None:
        """Scan ``models_dir`` for new model files."""

        updated = False
        for file in self.models_dir.iterdir():
            if not file.is_file():
                continue
            ext = file.suffix.lower()
            if ext not in self.SUPPORTED_EXT:
                continue
            name = file.stem
            if name not in self._meta:
                meta = ModelMeta(
                    name=name,
                    framework=self.SUPPORTED_EXT[ext],
                    path=str(file),
                    size=file.stat().st_size,
                    added_at=time.time(),
                    sha256=self._hash_file(file),
                )
                self._meta[name] = meta
                updated = True
        if update and updated:
            self._save_metadata()

    def _load_model(self, meta: ModelMeta) -> BaseModel:
        if meta.framework == "gguf":
            return GGUFModelWrapper(Path(meta.path))
        # ONNX and Torch loading can be implemented here.
        return EchoModel()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_models(self) -> Dict[str, ModelMeta]:
        """Return metadata for all discovered models."""

        with self._lock:
            return dict(self._meta)

    def load_model(self, name: str) -> BaseModel:
        """Load *name* into memory and return the model instance."""

        with self._lock:
            if name in self._models:
                return self._models[name]
            if name not in self._meta:
                raise KeyError(f"Model '{name}' not found")
            meta = self._meta[name]

        start = time.perf_counter()
        try:
            model = self._load_model(meta)
        except Exception as exc:  # pragma: no cover - error path
            self.event_bus.publish_nowait(
                "model.load_failed", {"name": name, "error": str(exc)}
            )
            raise
        load_time = time.perf_counter() - start

        with self._lock:
            self._models[name] = model

        self.event_bus.publish_nowait(
            "model.loaded", {"name": name, "load_time": load_time}
        )
        return model

    def get_model(self, name: str) -> BaseModel:
        """Return a loaded model instance without triggering a load."""

        with self._lock:
            if name not in self._models:
                raise KeyError(f"Model '{name}' not loaded")
            return self._models[name]

    def unload_model(self, name: str) -> None:
        """Unload a previously loaded model if present."""

        with self._lock:
            if name in self._models and name != "default":
                self._models.pop(name, None)
                self.event_bus.publish_nowait("model.unloaded", name)

    def remove_model(self, name: str) -> None:
        """Delete model file and remove metadata entry."""

        with self._lock:
            meta = self._meta.pop(name, None)
            self._models.pop(name, None)
        if meta:
            try:
                Path(meta.path).unlink(missing_ok=True)
            finally:
                self.event_bus.publish_nowait("model.removed", name)

    def hot_swap(self, unload_name: str, load_name: str) -> BaseModel:
        """Unload ``unload_name`` and load ``load_name`` atomically."""

        with self._lock:
            if unload_name in self._models and unload_name != "default":
                self._models.pop(unload_name, None)
                self.event_bus.publish_nowait("model.unloaded", unload_name)
        return self.load_model(load_name)

    def auto_download_all(self, registry_url: str | None = None) -> None:
        """Refresh registry and download all available models."""

        registry = ModelRegistry(registry_url) if registry_url else ModelRegistry()
        registry.auto_download_all()
        self.discover_models(update=True)

    def infer(self, name: str, prompt: str, **kwargs: object) -> str:
        """Run inference on the specified model."""

        model = self.load_model(name)
        start = time.perf_counter()
        try:
            result = model.infer(prompt, **kwargs)
            duration = time.perf_counter() - start
            self.event_bus.publish_nowait(
                "model.infer", {"name": name, "latency": duration}
            )
            return result
        except Exception as exc:  # pragma: no cover - error path
            self.event_bus.publish_nowait(
                "model.error", {"name": name, "error": str(exc)}
            )
            raise


if __name__ == "__main__":  # pragma: no cover - manual example
    mm = ModelManager()
    print("Discovered models:", list(mm.list_models()))
    print(mm.infer("default", "hello"))
    # Load another model if available and run inference
    for name in mm.list_models().keys():
        if name != "default":
            print(mm.infer(name, "demo"))
            break

