import asyncio
from core.model_manager import ModelManager


class DummyBus:
    def __init__(self):
        self.events = []

    def publish_nowait(self, event, payload=None):
        self.events.append((event, payload))


def test_echo_model():
    mm = ModelManager(event_bus=DummyBus())
    result = mm.infer('default', 'hello')
    assert 'hello' in result


def test_discover_and_load(tmp_path):
    model_file = tmp_path / 'sample.gguf'
    model_file.write_text('dummy')
    bus = DummyBus()
    mm = ModelManager(models_dir=str(tmp_path), metadata_file=str(tmp_path / 'meta.json'), event_bus=bus)
    mm.discover_models(update=True)
    assert 'sample' in mm.list_models()
    output = mm.infer('sample', 'hi there')
    assert 'hi there' in output
    assert any(evt[0] == 'model.loaded' and evt[1]['name'] == 'sample' for evt in bus.events)


def test_onnx_and_torch(tmp_path):
    (tmp_path / 'm.onnx').write_text('d')
    (tmp_path / 'n.pt').write_text('d')
    bus = DummyBus()
    mm = ModelManager(models_dir=str(tmp_path), metadata_file=str(tmp_path / 'meta.json'), event_bus=bus)
    mm.discover_models(update=True)
    assert 'm' in mm.list_models() and 'n' in mm.list_models()
    assert 'ONNX_DUMMY' in mm.infer('m', 'hi')
    assert 'TORCH_DUMMY' in mm.infer('n', 'hi')


def test_hot_swap(tmp_path):
    (tmp_path / 'a.gguf').write_text('a')
    (tmp_path / 'b.gguf').write_text('b')
    bus = DummyBus()
    mm = ModelManager(models_dir=str(tmp_path), metadata_file=str(tmp_path / 'meta.json'), event_bus=bus)
    mm.discover_models(update=True)
    mm.load_model('a')
    mm.hot_swap('a', 'b')
    assert 'demo' in mm.infer('b', 'demo')
    assert any(evt[0] == 'model.unloaded' and evt[1] == 'a' for evt in bus.events)


def test_get_and_remove(tmp_path):
    path = tmp_path / 'x.gguf'
    path.write_text('x')
    bus = DummyBus()
    mm = ModelManager(models_dir=str(tmp_path), metadata_file=str(tmp_path / 'm.json'), event_bus=bus)
    mm.discover_models(update=True)
    mm.load_model('x')
    assert mm.get_model('x')
    mm.remove_model('x')
    assert 'x' not in mm.list_models()
    assert any(evt[0] == 'model.removed' and evt[1] == 'x' for evt in bus.events)

