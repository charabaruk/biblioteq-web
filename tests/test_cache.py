import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from app.cache import (
    Cache,
    CacheUnavailable,
    LocalCacheBackend,
    RedisCacheBackend,
    create_cache,
    make_cache_namespace,
)
from app.config import Settings


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


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.fail_on = set()
        self.closed = False

    def _check(self, operation):
        if operation in self.fail_on:
            raise RedisError(f"{operation} failed")

    def get(self, key):
        self._check("get")
        return self.values.get(key)

    def set(self, key, value, *, nx, px):
        self._check("set")
        value = value.encode() if isinstance(value, str) else value
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    def delete(self, *keys):
        self._check("delete")
        for key in keys:
            self.values.pop(key, None)

    def eval(self, script, number_of_keys, *args):
        self._check("eval")
        if "PEXPIRE" in script:
            key, owner, retry_ms = args
            owner = owner.encode() if isinstance(owner, str) else owner
            if self.values.get(key) != owner:
                return 0
            if int(retry_ms) > 0:
                return 1
            self.values.pop(key, None)
            return 1

        data_key, lease_key, owner, value, _ttl = args
        owner = owner.encode() if isinstance(owner, str) else owner
        if self.values.get(lease_key) != owner:
            return 0
        self.values[data_key] = value
        self.values.pop(lease_key, None)
        return 1

    def close(self):
        self.closed = True


def encoded_entry(value, loaded_at=100.0):
    return json.dumps({"version": 1, "loaded_at": loaded_at, "value": value}).encode()


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


def test_local_cache_does_not_store_oversized_or_unowned_entries():
    backend = LocalCacheBackend(max_bytes=8)

    assert backend.acquire("a", "owner", 30)
    assert not backend.publish("a", "other", b"x", 30)
    assert not backend.publish("a", "owner", b"x" * 8, 30)
    assert backend.get("a") is None
    backend.release("a", "other")
    assert not backend.acquire("a", "other", 30)


def test_local_cache_requires_positive_capacity():
    with pytest.raises(ValueError, match="max_bytes"):
        LocalCacheBackend(max_bytes=0)


def test_local_cache_remember_keeps_newest_and_rejects_oversized_values():
    backend = LocalCacheBackend(max_bytes=100)
    newest = encoded_entry("new", loaded_at=101)
    older = encoded_entry("old", loaded_at=100)

    backend.remember("key", newest)
    backend.remember("key", older)

    assert backend.get("key") == newest
    backend.remember("too-large", encoded_entry("x" * 200))
    assert backend.get("too-large") is None


def test_local_cache_remember_evicts_oldest_entry_to_stay_bounded():
    backend = LocalCacheBackend(max_bytes=120)
    first = encoded_entry("a" * 10, loaded_at=100)
    second = encoded_entry("b" * 10, loaded_at=101)

    backend.remember("first", first)
    backend.remember("second", second)

    assert backend.get("first") is None
    assert backend.get("second") == second


def test_local_cache_replaces_malformed_fallback_entry():
    backend = LocalCacheBackend(max_bytes=1024)
    assert backend.acquire("key", "owner", 30)
    assert backend.publish("key", "owner", b"not json", 30)
    backend.release("key", "owner")
    replacement = encoded_entry("recovered")

    backend.remember("key", replacement)

    assert backend.get("key") == replacement


@pytest.mark.parametrize("raw", [b"[]", b"invalid json", b'{}', b'{"version":1,"loaded_at":"bad"}'])
def test_local_fallback_ignores_malformed_entries(raw):
    backend = LocalCacheBackend(max_bytes=1024)

    backend.remember("bad", raw)

    assert backend.get("bad") is None


def test_local_cache_replaces_expired_lease(monkeypatch):
    monotonic = [100.0]
    monkeypatch.setattr("app.cache.time.monotonic", lambda: monotonic[0])
    backend = LocalCacheBackend(max_bytes=100)

    assert backend.acquire("key", "first", 5)
    monotonic[0] += 6
    assert backend.acquire("key", "second", 5)
    assert not backend.publish("key", "first", b"expired", 30)
    assert backend.publish("key", "second", b"current", 30)


@pytest.mark.parametrize(
    ("namespace", "freshness", "max_stale", "wait", "lease", "backoff"),
    [
        ("", 1, 1, 1, 1, 1),
        ("test", 0, 1, 1, 1, 1),
        ("test", 2, 1, 1, 1, 1),
        ("test", 1, 1, 0, 1, 1),
        ("test", 1, 1, 1, 0, 1),
        ("test", 1, 1, 1, 1, 0),
    ],
)
def test_cache_rejects_invalid_policy(namespace, freshness, max_stale, wait, lease, backoff):
    with pytest.raises(ValueError):
        Cache(
            LocalCacheBackend(max_bytes=100),
            namespace=namespace,
            freshness_seconds=freshness,
            max_stale_seconds=max_stale,
            wait_timeout_seconds=wait,
            lease_seconds=lease,
            retry_backoff_seconds=backoff,
        )


@pytest.mark.parametrize(
    "raw",
    [
        b"invalid json",
        b"[]",
        b'{"version":2}',
        b'{"version":1,"loaded_at":"bad"}',
        b'{"version":1,"loaded_at":100,"value":NaN}',
    ],
)
def test_cache_discards_malformed_entries_and_reloads(raw):
    backend = LocalCacheBackend(max_bytes=1024)
    assert backend.acquire("test:key", "owner", 30)
    assert backend.publish("test:key", "owner", raw, 30)
    backend.release("test:key", "owner")
    cache = Cache(
        backend,
        namespace="test",
        freshness_seconds=10,
        max_stale_seconds=30,
        wait_timeout_seconds=0.1,
    )

    assert cache.get_or_load("key", lambda: {"valid": True}) == {"valid": True}


def test_cache_rejects_empty_key_and_non_json_values():
    cache = make_cache(Clock())
    with pytest.raises(ValueError, match="key"):
        cache.get_or_load("", lambda: None)
    with pytest.raises(CacheUnavailable):
        cache.get_or_load("bad", lambda: object())


def test_cache_reports_cold_miss_when_another_loader_holds_lease(monkeypatch):
    backend = LocalCacheBackend(max_bytes=1024)
    assert backend.acquire("test:key", "other-worker", 30)
    cache = Cache(
        backend,
        namespace="test",
        freshness_seconds=10,
        max_stale_seconds=30,
        wait_timeout_seconds=0.01,
    )
    monkeypatch.setattr("app.cache.time.sleep", lambda _duration: None)

    with pytest.raises(CacheUnavailable, match="timeout"):
        cache.get_or_load("key", lambda: None)


def test_redis_backend_reads_publishes_and_releases_leases():
    client = FakeRedis()
    fallback = LocalCacheBackend(max_bytes=1024)
    backend = RedisCacheBackend(client, key_prefix="test", fallback=fallback)
    payload = encoded_entry({"shared": True})

    assert backend.get("key") is None
    assert backend.acquire("key", "owner", 30)
    assert not backend.acquire("key", "other", 30)
    assert backend.publish("key", "owner", payload, 60)
    assert backend.get("key") == payload
    assert fallback.get("key") == payload

    assert backend.acquire("key", "owner", 30)
    backend.release("key", "owner", retry_after_seconds=5)
    assert not backend.acquire("key", "other", 30)
    backend.release("key", "owner")
    assert backend.acquire("key", "other", 30)
    backend.close()

    assert client.closed


def test_redis_backend_handles_errors_and_uses_local_fallback():
    client = FakeRedis()
    fallback = LocalCacheBackend(max_bytes=1024)
    backend = RedisCacheBackend(client, key_prefix="test", fallback=fallback)
    payload = encoded_entry({"stale": True})
    fallback.remember("key", payload)

    assert backend.get("key") == payload
    client.fail_on.update({"get", "set", "delete", "eval"})

    assert backend.get("key") == payload
    assert not backend.acquire("key", "owner", 30)
    assert not backend.publish("new", "owner", payload, 60)
    backend.release("key", "owner", retry_after_seconds=5)
    backend.delete("key")

    assert fallback.get("key") == payload


def test_redis_backend_rejects_publish_without_owned_lease():
    client = FakeRedis()
    backend = RedisCacheBackend(
        client, key_prefix="test", fallback=LocalCacheBackend(max_bytes=1024)
    )

    assert not backend.publish("key", "owner", encoded_entry("value"), 60)
    assert backend.get("key") is None


def test_redis_backend_requires_a_key_prefix():
    with pytest.raises(ValueError, match="key_prefix"):
        RedisCacheBackend(FakeRedis(), key_prefix="", fallback=LocalCacheBackend(max_bytes=10))


def test_create_cache_selects_local_backend_by_default():
    settings = Settings(db_url="sqlite:////tmp/library.sqlite")
    cache = create_cache(settings)

    assert cache.get_or_load("key", lambda: ["local"]) == ["local"]
    cache.close()


def test_create_cache_configures_redis_backend(monkeypatch):
    from unittest.mock import Mock

    from redis import Redis

    client = FakeRedis()
    from_url = Mock(return_value=client)
    monkeypatch.setattr(Redis, "from_url", from_url)
    settings = Settings(
        db_url="postgresql+psycopg://user:secret@db/library",
        cache_redis_url="redis://localhost:6379/15",
        cache_namespace="shelf-a",
    )
    cache = create_cache(settings)

    assert cache.get_or_load("key", lambda: ["redis"]) == ["redis"]
    assert from_url.call_args.args == ("redis://localhost:6379/15",)
    assert from_url.call_args.kwargs["decode_responses"] is False
    assert from_url.call_args.kwargs["socket_timeout"] > 0
    assert all("secret" not in key for key in client.values)
    cache.close()


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


def test_app_lifespan_exposes_and_closes_cache(monkeypatch):
    import asyncio
    from unittest.mock import Mock

    from app import main
    from app.config import Settings

    cache = Mock()
    settings = Settings(db_url="sqlite:////tmp/library.sqlite")
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "create_cache", lambda settings: cache, raising=False)
    app = main.create_app()

    async def verify_lifespan():
        async with app.router.lifespan_context(app):
            assert app.state.cache is cache

    asyncio.run(verify_lifespan())

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
