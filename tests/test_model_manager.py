from core.model_manager import ModelManager, EchoModel


def test_echo_model():
    mm = ModelManager()
    result = mm.infer('default', 'hello')
    assert 'hello' in result
