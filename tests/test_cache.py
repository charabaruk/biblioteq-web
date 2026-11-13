import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest

from app.cache import Cache, CacheUnavailable, LocalCacheBackend, make_cache_namespace


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


def test_local_fallback_ignores_malformed_entries():
    backend = LocalCacheBackend(max_bytes=1024)

    backend.remember("bad", b"[]")

    assert backend.get("bad") is None


def test_cache_namespace_excludes_credentials_and_separates_deployments():
    first = make_cache_namespace(
        "postgresql+psycopg://reader:secret-one@db/library", "public", "shelf-a"
    )
    same_database = make_cache_namespace(
        "postgresql+psycopg://reader:secret-two@db/library", "public", "shelf-a"
    )
    other_deployment = make_cache_namespace(
        "postgresql+psycopg://reader:secret-one@db/library", "public", "shelf-b"
    )

    assert first == same_database
    assert first != other_deployment
    assert "secret" not in first


def test_app_lifespan_exposes_and_closes_cache(configured, monkeypatch):
    from unittest.mock import Mock

    from fastapi.testclient import TestClient

    from app import main

    cache = Mock()
    monkeypatch.setattr(main, "create_cache", lambda settings: cache, raising=False)
    app = main.create_app()

    with TestClient(app) as client:
        assert client.app.state.cache is cache

    cache.close.assert_called_once_with()


@pytest.mark.redis
def test_redis_cache_shares_values_and_coordinates_loads():
    redis_url = os.environ.get("BIBLIOTEQ_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("BIBLIOTEQ_TEST_REDIS_URL is not set")

    from redis import Redis

    from app.cache import RedisCacheBackend

    prefix = f"test-cache:{uuid4().hex}"
    first_client = Redis.from_url(redis_url, decode_responses=False)
    second_client = Redis.from_url(redis_url, decode_responses=False)
    first_backend = RedisCacheBackend(
        first_client, key_prefix=prefix, fallback=LocalCacheBackend(max_bytes=4096)
    )
    second_backend = RedisCacheBackend(
        second_client, key_prefix=prefix, fallback=LocalCacheBackend(max_bytes=4096)
    )
    clock = Clock()
    first = Cache(
        first_backend,
        namespace="shared",
        freshness_seconds=30,
        max_stale_seconds=60,
        wait_timeout_seconds=1,
        clock=clock,
    )
    second = Cache(
        second_backend,
        namespace="shared",
        freshness_seconds=30,
        max_stale_seconds=60,
        wait_timeout_seconds=1,
        clock=clock,
    )
    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return {"snapshot": ["shared"]}

    try:
        assert first.get_or_load("items", load) == {"snapshot": ["shared"]}
        assert second.get_or_load("items", load) == {"snapshot": ["shared"]}
        assert calls == 1

        assert first_backend.acquire("lease", "owner-one", 30)
        assert not second_backend.acquire("lease", "owner-two", 30)
        assert not second_backend.publish("lease", "owner-two", b"bad", 60)
        first_backend.delete("lease")
        assert not second_backend.acquire("lease", "owner-two", 30)

        from redis.exceptions import ConnectionError as RedisConnectionError

        class OfflineClient:
            def get(self, key):
                raise RedisConnectionError("offline")

            def set(self, *args, **kwargs):
                raise RedisConnectionError("offline")

            def eval(self, *args):
                raise RedisConnectionError("offline")

            def close(self):
                return None

        first_client.close()
        first_backend._client = OfflineClient()
        clock.now += 31
        assert first.get_or_load("items", load) == {"snapshot": ["shared"]}
        assert calls == 1

        unavailable = Cache(
            RedisCacheBackend(
                OfflineClient(),
                key_prefix=prefix,
                fallback=LocalCacheBackend(max_bytes=4096),
            ),
            namespace="shared",
            freshness_seconds=30,
            max_stale_seconds=60,
            wait_timeout_seconds=0.02,
        )
        try:
            with pytest.raises(CacheUnavailable):
                unavailable.get_or_load("cold", load)
        finally:
            unavailable.close()
        assert calls == 1
    finally:
        first.close()
        second.close()
        for key in second_client.scan_iter(match=f"{prefix}:*"):
            second_client.delete(key)
        second_client.close()
