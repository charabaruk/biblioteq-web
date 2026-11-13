"""Bounded cache for derived, read-only application data."""

import json
import logging
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from typing import Protocol

logger = logging.getLogger(__name__)

_CACHE_FORMAT_VERSION = 1
_DEFAULT_LEASE_SECONDS = 30
_DEFAULT_POLL_INTERVAL_SECONDS = 0.01
_DEFAULT_RETRY_BACKOFF_SECONDS = 5


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
            logger.warning("Cache refresh failed for key %s (%s)", key, type(exc).__name__)
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
