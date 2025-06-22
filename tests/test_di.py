import pytest
from core.di import DIContainer, Scope


class Dummy:
    pass

def test_singleton_scope():
    c = DIContainer()
    c.bind(Dummy, Dummy, scope=Scope.SINGLETON)
    assert c.get(Dummy) is c.get(Dummy)

def test_transient_scope():
    c = DIContainer()
    c.bind(Dummy, Dummy, scope=Scope.TRANSIENT)
    assert c.get(Dummy) is not c.get(Dummy)
