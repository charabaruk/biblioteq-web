"""Bounded cache for derived, read-only application data."""

import hashlib
import json
import logging
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from typing import Protocol

from redis.exceptions import RedisError
from sqlalchemy.engine import make_url

from app.config import Settings

logger = logging.getLogger(__name__)

_CACHE_FORMAT_VERSION = 1
_DEFAULT_LEASE_SECONDS = 30
_DEFAULT_POLL_INTERVAL_SECONDS = 0.01
_DEFAULT_RETRY_BACKOFF_SECONDS = 5
DEFAULT_CACHE_LOCAL_MAX_BYTES = 16 * 1024 * 1024
_DEFAULT_CACHE_WAIT_TIMEOUT_SECONDS = 1.0
_DEFAULT_REDIS_TIMEOUT_SECONDS = 1.0

_PUBLISH_SCRIPT = """
if redis.call('GET', KEYS[2]) == ARGV[1] then
    redis.call('SET', KEYS[1], ARGV[2], 'PX', ARGV[3])
    redis.call('DEL', KEYS[2])
    return 1
end
return 0
"""

_RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    if tonumber(ARGV[2]) > 0 then
        redis.call('PEXPIRE', KEYS[1], ARGV[2])
    else
        redis.call('DEL', KEYS[1])
    end
    return 1
end
return 0
"""


class CacheUnavailable(RuntimeError):
    """Raised when no fresh or permitted stale cache value is available."""


class CacheBackend(Protocol):
    """Storage and per-key coordination contract implemented by each backend."""

    def get(self, key: str) -> bytes | None: ...

    def delete(self, key: str) -> None: ...

    def acquire(self, key: str, owner: str, lease_seconds: int) -> bool: ...

    def publish(self, key: str, owner: str, value: bytes, ttl_seconds: int) -> bool: ...

    def release(self, key: str, owner: str, retry_after_seconds: int = 0) -> None: ...

    def close(self) -> None: ...


class LocalCacheBackend:
    """Thread-safe, byte-bounded LRU storage local to one worker."""

    def __init__(self, max_bytes: int):
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self._max_bytes = max_bytes
        self._entries: OrderedDict[str, bytes] = OrderedDict()
        self._entry_bytes = 0
        self._leases: dict[str, tuple[str, float]] = {}
        self._lock = Lock()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            value = self._entries.get(key)
            if value is not None:
                self._entries.move_to_end(key)
            return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._remove(key)

    def acquire(self, key: str, owner: str, lease_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            current = self._leases.get(key)
            if current is not None and current[1] > now:
                return False
            self._leases[key] = (owner, now + lease_seconds)
            return True

    def publish(self, key: str, owner: str, value: bytes, ttl_seconds: int) -> bool:
        del ttl_seconds
        key_size = len(key.encode("utf-8"))
        entry_size = key_size + len(value)
        if entry_size > self._max_bytes:
            return False

        with self._lock:
            if not self._owns_lease(key, owner):
                return False
            self._remove(key)
            while self._entries and self._entry_bytes + entry_size > self._max_bytes:
                oldest = next(iter(self._entries))
                self._remove(oldest)
            self._entries[key] = value
            self._entry_bytes += entry_size
            return True

    def remember(self, key: str, value: bytes) -> None:
        """Keep the newest shared snapshot as a bounded local fallback."""
        loaded_at = _loaded_at(value)
        if loaded_at is None:
            return
        key_size = len(key.encode("utf-8"))
        entry_size = key_size + len(value)
        if entry_size > self._max_bytes:
            return

        with self._lock:
            current = self._entries.get(key)
            if current is not None:
                current_loaded_at = _loaded_at(current)
                if current_loaded_at is not None and current_loaded_at >= loaded_at:
                    self._entries.move_to_end(key)
                    return
            self._remove(key)
            while self._entries and self._entry_bytes + entry_size > self._max_bytes:
                oldest = next(iter(self._entries))
                self._remove(oldest)
            self._entries[key] = value
            self._entry_bytes += entry_size

    def release(self, key: str, owner: str, retry_after_seconds: int = 0) -> None:
        with self._lock:
            if self._owns_lease(key, owner):
                if retry_after_seconds:
                    self._leases[key] = (owner, time.monotonic() + retry_after_seconds)
                else:
                    del self._leases[key]

    def close(self) -> None:
        return None

    def _owns_lease(self, key: str, owner: str) -> bool:
        current = self._leases.get(key)
        if current is None or current[0] != owner or current[1] <= time.monotonic():
            return False
        return True

    def _remove(self, key: str) -> None:
        value = self._entries.pop(key, None)
        if value is not None:
            self._entry_bytes -= len(key.encode("utf-8")) + len(value)


class Cache:
    """Load and cache JSON-compatible snapshots using a pluggable backend."""

    def __init__(
        self,
        backend: CacheBackend,
        *,
        namespace: str,
        freshness_seconds: int,
        max_stale_seconds: int,
        wait_timeout_seconds: float,
        clock: Callable[[], float] = time.time,
        lease_seconds: int = _DEFAULT_LEASE_SECONDS,
        retry_backoff_seconds: int = _DEFAULT_RETRY_BACKOFF_SECONDS,
    ):
        if not namespace:
            raise ValueError("namespace must not be empty")
        if freshness_seconds < 1 or max_stale_seconds < freshness_seconds:
            raise ValueError("cache timeouts must be positive and max stale >= freshness")
        if wait_timeout_seconds <= 0 or lease_seconds < 1 or retry_backoff_seconds < 1:
            raise ValueError("cache coordination timeouts must be positive")
        self._backend = backend
        self._namespace = namespace
        self._freshness_seconds = freshness_seconds
        self._max_stale_seconds = max_stale_seconds
        self._wait_timeout_seconds = wait_timeout_seconds
        self._clock = clock
        self._lease_seconds = lease_seconds
        self._retry_backoff_seconds = retry_backoff_seconds

    def get_or_load(self, key: str, loader: Callable[[], object]):
        """Return a fresh value, refresh a stale one, or load a cold key once."""
        if not key:
            raise ValueError("cache key must not be empty")
        storage_key = f"{self._namespace}:{key}"
        deadline = time.monotonic() + self._wait_timeout_seconds

        while True:
            entry = self._read(storage_key)
            now = self._clock()
            if entry is not None:
                value, loaded_at = entry
                age = now - loaded_at
                if 0 <= age < self._freshness_seconds:
                    return value
                has_stale_value = 0 <= age <= self._max_stale_seconds
            else:
                value = None
                has_stale_value = False

            owner = uuid.uuid4().hex
            if self._backend.acquire(storage_key, owner, self._lease_seconds):
                return self._refresh(storage_key, owner, loader, value, has_stale_value)

            if has_stale_value:
                return value
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CacheUnavailable("cache load did not complete before timeout")
            time.sleep(min(_DEFAULT_POLL_INTERVAL_SECONDS, remaining))

    def close(self) -> None:
        """Close backend resources owned by this cache instance."""
        self._backend.close()

    def _refresh(self, key, owner, loader, stale_value, has_stale_value):
        try:
            value = loader()
            payload = self._encode(value, self._clock())
            self._backend.publish(key, owner, payload, self._max_stale_seconds)
        except Exception as exc:
            self._backend.release(key, owner, self._retry_backoff_seconds)
            logger.warning(
                "Cache refresh failed for key %s (%s)",
                _cache_key_for_log(key),
                type(exc).__name__,
            )
            if has_stale_value:
                return stale_value
            raise CacheUnavailable("cache value is unavailable") from exc
        self._backend.release(key, owner)
        return json.loads(json.dumps(value, allow_nan=False))

    def _read(self, key: str) -> tuple[object, float] | None:
        raw = self._backend.get(key)
        if raw is None:
            return None
        try:
            entry = json.loads(raw)
            if (
                not isinstance(entry, dict)
                or entry.get("version") != _CACHE_FORMAT_VERSION
                or not isinstance(entry.get("loaded_at"), (int, float))
                or "value" not in entry
            ):
                raise ValueError("invalid cache entry")
            value = json.loads(json.dumps(entry["value"], allow_nan=False))
            return value, float(entry["loaded_at"])
        except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._backend.delete(key)
            return None

    @staticmethod
    def _encode(value: object, loaded_at: float) -> bytes:
        return json.dumps(
            {"version": _CACHE_FORMAT_VERSION, "loaded_at": loaded_at, "value": value},
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


class RedisCacheBackend:
    """Redis-protocol storage with bounded worker-local last-known-good values."""

    def __init__(self, client, *, key_prefix: str, fallback: LocalCacheBackend):
        if not key_prefix:
            raise ValueError("key_prefix must not be empty")
        self._client = client
        self._key_prefix = key_prefix.rstrip(":")
        self._fallback = fallback

    def get(self, key: str) -> bytes | None:
        data_key, _ = self._keys(key)
        try:
            value = self._client.get(data_key)
        except RedisError as exc:
            logger.warning("Redis cache read failed (%s)", type(exc).__name__)
            return self._fallback.get(key)
        if value is None:
            return self._fallback.get(key)
        self._fallback.remember(key, value)
        return value

    def delete(self, key: str) -> None:
        data_key, _ = self._keys(key)
        try:
            self._client.delete(data_key)
        except RedisError as exc:
            logger.warning("Redis cache delete failed (%s)", type(exc).__name__)

    def acquire(self, key: str, owner: str, lease_seconds: int) -> bool:
        _, lock_key = self._keys(key)
        try:
            return bool(self._client.set(lock_key, owner, nx=True, px=lease_seconds * 1000))
        except RedisError as exc:
            logger.warning("Redis cache lease failed (%s)", type(exc).__name__)
            return False

    def publish(self, key: str, owner: str, value: bytes, ttl_seconds: int) -> bool:
        data_key, lock_key = self._keys(key)
        try:
            published = bool(
                self._client.eval(
                    _PUBLISH_SCRIPT,
                    2,
                    data_key,
                    lock_key,
                    owner,
                    value,
                    ttl_seconds * 1000,
                )
            )
        except RedisError as exc:
            logger.warning("Redis cache publish failed (%s)", type(exc).__name__)
            self._fallback.remember(key, value)
            return False
        if published:
            self._fallback.remember(key, value)
        return published

    def release(self, key: str, owner: str, retry_after_seconds: int = 0) -> None:
        _, lock_key = self._keys(key)
        try:
            self._client.eval(
                _RELEASE_SCRIPT,
                1,
                lock_key,
                owner,
                retry_after_seconds * 1000,
            )
        except RedisError as exc:
            logger.warning("Redis cache lease release failed (%s)", type(exc).__name__)

    def close(self) -> None:
        self._client.close()

    def _keys(self, key: str) -> tuple[str, str]:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        base = f"{self._key_prefix}:{digest}"
        return f"{base}:data", f"{base}:lease"


def _loaded_at(value: bytes) -> float | None:
    try:
        entry = json.loads(value)
        if not isinstance(entry, dict):
            return None
        loaded_at = entry.get("loaded_at")
        if entry.get("version") == _CACHE_FORMAT_VERSION and isinstance(loaded_at, (int, float)):
            return float(loaded_at)
    except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return None


def _cache_key_for_log(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def make_cache_namespace(db_url: str, schema: str, deployment: str) -> str:
    """Return a stable, credential-free namespace for one deployment and database."""
    url = make_url(db_url).set(username=None, password=None, query={})
    database_identity = url.render_as_string(hide_password=True)
    database_hash = hashlib.sha256(database_identity.encode("utf-8")).hexdigest()[:20]
    safe_deployment = hashlib.sha256(deployment.encode("utf-8")).hexdigest()[:12]
    safe_schema = hashlib.sha256(schema.encode("utf-8")).hexdigest()[:12]
    return f"biblioteq:v{_CACHE_FORMAT_VERSION}:{safe_deployment}:{safe_schema}:{database_hash}"


def create_cache(settings: Settings) -> Cache:
    """Create the configured per-worker cache without requiring Redis at startup."""
    namespace = make_cache_namespace(settings.db_url, settings.db_schema, settings.cache_namespace)
    if settings.cache_redis_url:
        from redis import Redis

        client = Redis.from_url(
            settings.cache_redis_url,
            decode_responses=False,
            socket_timeout=_DEFAULT_REDIS_TIMEOUT_SECONDS,
            socket_connect_timeout=_DEFAULT_REDIS_TIMEOUT_SECONDS,
        )
        backend = RedisCacheBackend(
            client,
            key_prefix=namespace,
            fallback=LocalCacheBackend(DEFAULT_CACHE_LOCAL_MAX_BYTES),
        )
    else:
        backend = LocalCacheBackend(DEFAULT_CACHE_LOCAL_MAX_BYTES)
    return Cache(
        backend,
        namespace=namespace,
        freshness_seconds=settings.cache_freshness_seconds,
        max_stale_seconds=settings.cache_max_stale_seconds,
        wait_timeout_seconds=_DEFAULT_CACHE_WAIT_TIMEOUT_SECONDS,
    )
