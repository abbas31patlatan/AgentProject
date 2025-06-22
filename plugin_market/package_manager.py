# File: plugin_market/package_manager.py

"""Install and uninstall plugin packages."""

from __future__ import annotations

import shutil
from pathlib import Path


class PackageManager:
    """Very small local package manager for plugins."""

    def __init__(self, plugins_dir: Path) -> None:
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def install(self, source: Path) -> Path:
        """Install a plugin from *source* directory."""

        target = self.plugins_dir / source.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        return target

    def uninstall(self, name: str) -> None:
        """Remove a previously installed plugin."""

        target = self.plugins_dir / name
        if target.exists():
            shutil.rmtree(target)

