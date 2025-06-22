import os
from core.memory import MemoryManager


def test_store_and_retrieve(tmp_path):
    db = tmp_path / 'mem.db'
    mm = MemoryManager(db_path=str(db))
    mm.store_interaction('hi', 'hello')
    ctx = mm.retrieve_context()
    assert 'hi' in ctx and 'hello' in ctx

    # token-limited retrieval should return empty if limit is too strict
    short = mm.retrieve_context(limit_tokens=1)
    assert short == ''
    mm.close()
