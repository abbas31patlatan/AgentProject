# File: core/di.py

import threading
from enum import Enum, auto
from typing import Any, Callable, Dict, Type

class Scope(Enum):
    SINGLETON = auto()
    TRANSIENT = auto()

class DIContainer:
    """
    Tip güvenli, thread-safe, otomatik injection destekli bir Dependency Injection container.
    """
    def __init__(self):
        """Initialize internal storage for bindings and singletons."""

        self._bindings: Dict[Type, Dict[str, Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.RLock()

    def bind(self, abstract: Type, factory: Callable, scope: Scope = Scope.SINGLETON):
        """Bind a type to a factory with the given scope."""

        with self._lock:
            self._bindings[abstract] = {"factory": factory, "scope": scope}
            if abstract in self._singletons:
                del self._singletons[abstract]

    def get(self, abstract: Type) -> Any:
        """Retrieve an instance for the specified type."""

        with self._lock:
            if abstract not in self._bindings:
                raise KeyError(f"No binding for {abstract}")
            binding = self._bindings[abstract]
            if binding["scope"] == Scope.SINGLETON:
                if abstract not in self._singletons:
                    self._singletons[abstract] = binding["factory"]()
                return self._singletons[abstract]
            else:
                return binding["factory"]()

    def clear(self):
        """Remove all bindings and cached singletons."""

        with self._lock:
            self._singletons.clear()
            self._bindings.clear()
