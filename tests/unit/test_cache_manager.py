from __future__ import annotations

from cache_manager import SimpleCache, cached, invalidate_cache, _cache


def test_cache_pattern_invalidation_uses_visible_prefix():
    _cache.invalidate()
    calls = 0

    @cached(ttl=60, key_prefix="mpfm_metadata")
    def load_metadata():
        nonlocal calls
        calls += 1
        return {"calls": calls}

    assert load_metadata() == {"calls": 1}
    assert load_metadata() == {"calls": 1}
    assert invalidate_cache("mpfm_metadata") == 1
    assert load_metadata() == {"calls": 2}


def test_simple_cache_can_still_clear_all_entries():
    cache = SimpleCache()
    cache.set("one", 1)
    cache.set("two", 2)
    assert cache.invalidate() == 2
    assert cache.get_stats()["cached_items"] == 0
