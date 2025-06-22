import json
from pathlib import Path
from core.plugin_loader import PluginLoader


class DummyBus:
    def __init__(self):
        self.events = []

    def publish_nowait(self, event, payload=None):
        self.events.append((event, payload))


def test_local_plugin_loading(tmp_path):
    plugin_dir = tmp_path / "TestPlugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "name": "TestPlugin",
        "version": "0.1",
        "entrypoint": "myplugin:Plugin"
    }))
    (plugin_dir / "myplugin.py").write_text(
        "class Plugin:\n" 
        "    def __init__(self, event_bus=None):\n" 
        "        event_bus.publish_nowait('plugin.init', self.__class__.__name__)\n"
    )

    bus = DummyBus()
    loader = PluginLoader(event_bus=bus)
    loader.LOCAL_DIR = Path(tmp_path)
    loader.discover_local()
    loader.load_plugin("TestPlugin")

    assert "TestPlugin" in loader.list_loaded()
    assert any(evt[0] == "plugin.loaded" and evt[1]["name"] == "TestPlugin" for evt in bus.events)
