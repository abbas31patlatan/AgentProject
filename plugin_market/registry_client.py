# File: plugin_market/registry_client.py

"""Minimal client for a remote plugin registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List



class RegistryClient:
    """Fetch plugin metadata from a registry URL."""

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def list_plugins(self, force: bool = False) -> List[Dict[str, Any]]:
        """Return plugin metadata list."""

        import requests

        resp = requests.get(self.url + "/index.json", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def download_plugin(self, name: str, version: str, target_dir: Path) -> None:
        """Download and extract a plugin archive into *target_dir*."""

        target_dir.mkdir(parents=True, exist_ok=True)
        import requests

        resp = requests.get(f"{self.url}/{name}-{version}.zip", stream=True, timeout=30)
        resp.raise_for_status()
        tmp = target_dir / "plugin.zip"
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        import zipfile

        with zipfile.ZipFile(tmp) as zf:
            zf.extractall(target_dir)
        tmp.unlink()

