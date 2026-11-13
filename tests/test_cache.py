from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.cache import Cache, CacheUnavailable, LocalCacheBackend


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def make_cache(clock, *, freshness=10, max_stale=30, max_bytes=1024):
    return Cache(
        LocalCacheBackend(max_bytes=max_bytes),
        namespace="test",
        freshness_seconds=freshness,
        max_stale_seconds=max_stale,
        wait_timeout_seconds=1,
        clock=clock,
    )


def test_local_cache_returns_isolated_fresh_values():
    cache = make_cache(Clock())
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return {"items": ["book"]}

    first = cache.get_or_load("items", load)
    first["items"].append("mutation")

    assert cache.get_or_load("items", load) == {"items": ["book"]}
    assert calls == 1


def test_local_cache_refresh_failure_serves_only_within_stale_window():
    clock = Clock()
    cache = make_cache(clock)
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("source unavailable")
        return ["snapshot"]

    assert cache.get_or_load("items", load) == ["snapshot"]
    clock.now += 11
    assert cache.get_or_load("items", load) == ["snapshot"]

    clock.now += 20
    with pytest.raises(CacheUnavailable):
        cache.get_or_load("items", load)


def test_local_cache_backs_off_after_refresh_failure(monkeypatch):
    clock = Clock()
    monotonic = [100.0]
    monkeypatch.setattr("app.cache.time.monotonic", lambda: monotonic[0])
    cache = make_cache(clock)
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("source unavailable")
        return ["snapshot"]

    assert cache.get_or_load("items", load) == ["snapshot"]
    clock.now += 11
    assert cache.get_or_load("items", load) == ["snapshot"]
    assert cache.get_or_load("items", load) == ["snapshot"]
    assert calls == 2

    monotonic[0] += 6
    assert cache.get_or_load("items", load) == ["snapshot"]
    assert calls == 3


def test_local_cache_coalesces_concurrent_cold_loads():
    cache = make_cache(Clock())
    started = Event()
    release = Event()
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        started.set()
        assert release.wait(timeout=2)
        return ["snapshot"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get_or_load, "items", load)
        assert started.wait(timeout=2)
        second = pool.submit(cache.get_or_load, "items", load)
        release.set()

        assert first.result(timeout=2) == ["snapshot"]
        assert second.result(timeout=2) == ["snapshot"]

    assert calls == 1


def test_local_cache_evicts_entries_to_respect_byte_limit():
    cache = make_cache(Clock(), max_bytes=110)
    calls = {"first": 0, "second": 0}

    def load_first():
        calls["first"] += 1
        return "a" * 30

    def load_second():
        calls["second"] += 1
        return "b" * 30

    cache.get_or_load("first", load_first)
    cache.get_or_load("second", load_second)
    cache.get_or_load("first", load_first)

    assert calls["first"] == 2
    assert calls["second"] == 1