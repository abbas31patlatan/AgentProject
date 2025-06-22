import asyncio
from core.model_manager import ModelManager


class DummyBus:
    def publish_nowait(self, event, payload=None):
        pass


def test_echo_model():
    mm = ModelManager(event_bus=DummyBus())
    result = mm.infer('default', 'hello')
    assert 'hello' in result


def test_discover_and_load(tmp_path):
    model_file = tmp_path / 'sample.gguf'
    model_file.write_text('dummy')
    mm = ModelManager(models_dir=str(tmp_path), metadata_file=str(tmp_path / 'meta.json'), event_bus=DummyBus())
    mm.discover_models(update=True)
    assert 'sample' in mm.list_models()
    output = mm.infer('sample', 'hi there')
    assert 'hi there' in output
