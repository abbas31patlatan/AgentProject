# File: core/plugin_loader.py

import os
import sys
import json
import shutil
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional
from core.event_bus import EventBus
from plugin_market.registry_client import RegistryClient

class PluginSpec:
    def __init__(self, name: str, version: str, entrypoint: str, source: str):
        self.name = name
        self.version = version
        self.entrypoint = entrypoint  # "modulename:ClassName"
        self.source = source          # "local" veya registry url

class PluginLoader:
    """
    - plugins/ ve plugins/remote/ altında tüm eklentileri keşfeder
    - Uzak market/registry’den indirir
    - Dynamic import ile yükler, hot-reload/unload yapar
    - Her bir plugin’i izole path’te tutar, sandbox mantığı kurar
    - Olay tabanlı (event_bus) bildirimler
    """
    LOCAL_DIR = Path("plugins")
    REMOTE_DIR = Path("plugins/remote")

    def __init__(self, event_bus: EventBus, registry_url: Optional[str] = None):
        self.event_bus = event_bus
        self.registry = RegistryClient(registry_url) if registry_url else None
        self._specs: Dict[str, PluginSpec] = {}
        self._loaded: Dict[str, Any] = {}
        self.LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        self.REMOTE_DIR.mkdir(parents=True, exist_ok=True)

    def discover_local(self):
        """
        plugins/ klasöründe plugin.json olan klasörleri keşfeder.
        """
        for folder in self.LOCAL_DIR.iterdir():
            if not folder.is_dir():
                continue
            meta_path = folder / "plugin.json"
            if meta_path.exists():
                with meta_path.open(encoding="utf-8") as f:
                    meta = json.load(f)
                spec = PluginSpec(
                    name=meta["name"],
                    version=meta["version"],
                    entrypoint=meta["entrypoint"],
                    source="local"
                )
                self._specs[spec.name] = spec

    def discover_remote(self, force_refresh: bool = False):
        """
        Market/registry’den uzak plugin listesini alır.
        """
        if not self.registry:
            return
        index = self.registry.list_plugins(force=force_refresh)
        for entry in index:
            spec = PluginSpec(
                name=entry["name"],
                version=entry["version"],
                entrypoint=entry["entrypoint"],
                source=entry["url"]
            )
            self._specs[spec.name] = spec

    def install_remote(self, name: str, version: Optional[str] = None, overwrite: bool = False):
        """
        Marketten plugin’i indirip plugins/remote/ altına kurar.
        """
        if not self.registry or name not in self._specs:
            raise KeyError(f"Plugin '{name}' registryde yok")
        spec = self._specs[name]
        target = self.REMOTE_DIR / f"{name}-{spec.version}"
        if target.exists() and not overwrite:
            return
        if target.exists():
            shutil.rmtree(target)
        self.registry.download_plugin(name, version or spec.version, target)
        self.event_bus.publish_nowait("plugin.installed", {"name": name, "version": spec.version})

    def load_plugin(self, name: str):
        """
        Plugin’i (yerel veya uzak) yükler ve başlatır.
        """
        if name not in self._specs:
            raise KeyError(f"Plugin '{name}' keşfedilmedi")
        spec = self._specs[name]
        # Kök path’i bul
        if spec.source == "local":
            base = self.LOCAL_DIR / spec.name
        else:
            # Uzak ise remote dizininden bul
            base = next(self.REMOTE_DIR.glob(f"{spec.name}-*"), None)
        if not base or not base.exists():
            raise FileNotFoundError(f"Plugin '{name}' path bulunamadı")

        # sys.path’e ekle (import için)
        if str(base) not in sys.path:
            sys.path.insert(0, str(base))

        module_name, class_name = spec.entrypoint.split(":")
        # Plugin modülünü yükle
        spec_file = base / (module_name.replace(".", os.sep) + ".py")
        if spec_file.exists():
            spec_loader = importlib.util.spec_from_file_location(module_name, spec_file)
            module = importlib.util.module_from_spec(spec_loader)
            spec_loader.loader.exec_module(module)  # type: ignore
        else:
            module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        instance = cls(event_bus=self.event_bus)
        # Önceki instance varsa unload
        if name in self._loaded and hasattr(self._loaded[name], "teardown"):
            try:
                self._loaded[name].teardown()
            except Exception:
                pass
        self._loaded[name] = instance
        self.event_bus.publish_nowait("plugin.loaded", {"name": name, "version": spec.version})
        return instance

    def unload_plugin(self, name: str):
        """
        Plugin’i devreden çıkarır ve teardown çalıştırır.
        """
        instance = self._loaded.pop(name, None)
        if instance and hasattr(instance, "teardown"):
            try:
                instance.teardown()
            except Exception:
                pass
        self.event_bus.publish_nowait("plugin.unloaded", name)

    def load_all(self):
        """
        Tüm local ve remote plugin’leri keşfeder ve yükler.
        """
        self.discover_local()
        self.discover_remote()
        for name in list(self._specs):
            try:
                self.load_plugin(name)
            except Exception:
                continue

    def list_loaded(self) -> Dict[str, Any]:
        return dict(self._loaded)

    def list_specs(self) -> Dict[str, PluginSpec]:
        return dict(self._specs)

