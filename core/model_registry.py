# File: core/model_registry.py

import os
import json
import hashlib
from typing import Dict, Any, Optional, List

class ModelSpec:
    def __init__(self, name: str, framework: str, url: str, sha256: Optional[str] = None):
        self.name = name
        self.framework = framework
        self.url = url
        self.sha256 = sha256

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            name=self.name,
            framework=self.framework,
            url=self.url,
            sha256=self.sha256,
        )

class ModelRegistry:
    """
    Uzak/yerel model metadata yönetimi.
    - Model listesi indirir, json’da saklar
    - SHA256 ile güvenlik kontrolü
    - Model indirici
    """
    def __init__(self, registry_url: str = "https://huggingface.co/api/agentproject/models.json", cache_file: str = "models/metadata.json"):
        self.registry_url = registry_url
        self.cache_file = cache_file
        self._specs: Dict[str, ModelSpec] = {}
        self.refresh_registry(force=True)

    def refresh_registry(self, force: bool = False):
        """Model metadata’sını günceller."""
        if not force and os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                self._specs[entry["name"]] = ModelSpec(**entry)
        else:
            import requests

            resp = requests.get(self.registry_url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            for entry in data:
                self._specs[entry["name"]] = ModelSpec(**entry)

    def list_models(self) -> List[str]:
        return list(self._specs.keys())

    def get_spec(self, name: str) -> Optional[ModelSpec]:
        return self._specs.get(name)

    def download_model(self, name: str, overwrite: bool = False) -> str:
        """
        Modeli indirir ve doğrular, varsa önbellekten döner.
        """
        spec = self.get_spec(name)
        if not spec:
            raise KeyError(f"Model {name} bulunamadı.")
        models_dir = "models"
        os.makedirs(models_dir, exist_ok=True)
        filename = os.path.join(models_dir, f"{name}.{spec.framework.lower()}")
        if os.path.exists(filename) and not overwrite:
            return filename
        # indir
        import requests

        resp = requests.get(spec.url, stream=True, timeout=300)
        with open(filename, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        # SHA256 kontrolü
        if spec.sha256:
            with open(filename, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            if file_hash != spec.sha256:
                os.remove(filename)
                raise RuntimeError("Model dosyası hash eşleşmiyor!")
        return filename

    def auto_download_all(self):
        for name in self._specs:
            try:
                self.download_model(name)
            except Exception:
                continue
