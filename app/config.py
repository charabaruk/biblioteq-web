"""Application settings read from environment variables."""

import os
import re
from dataclasses import dataclass
from functools import lru_cache

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    db_url: str
    db_schema: str = "public"
    page_size: int = 24
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_statement_timeout_ms: int = 5000
    site_title: str = "Library Collection"
    log_level: str = "INFO"
    root_path: str = ""
    natural_sort: bool = True
    natural_sort_numbers: str = "integer"  # "integer" or "decimal"
    default_lang: str = "en"

    @property
    def title_sort(self) -> str | None:
        return self.natural_sort_numbers if self.natural_sort else None


_BOOLEANS = {"true": True, "1": True, "yes": True, "on": True}
_BOOLEANS |= {"false": False, "0": False, "no": False, "off": False}
_SORT_NUMBERS = ("integer", "decimal")


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw == "":
        return default
    if raw not in _BOOLEANS:
        raise ConfigError(f"{name} must be true or false")
    return _BOOLEANS[raw]


def _int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return value


def load_settings() -> Settings:
    db_url = os.environ.get("BIBLIOTEQ_DB_URL", "")
    if not db_url:
        raise ConfigError("BIBLIOTEQ_DB_URL is required")
    schema = os.environ.get("BIBLIOTEQ_DB_SCHEMA", "public")
    # The schema ends up in search_path, so it must be a plain identifier.
    if not _IDENTIFIER.match(schema):
        raise ConfigError("BIBLIOTEQ_DB_SCHEMA must be a plain SQL identifier")
    sort_numbers = os.environ.get("BIBLIOTEQ_NATURAL_SORT_NUMBERS", "").strip().lower() or "integer"
    if sort_numbers not in _SORT_NUMBERS:
        raise ConfigError("BIBLIOTEQ_NATURAL_SORT_NUMBERS must be integer or decimal")
    return Settings(
        db_url=db_url,
        db_schema=schema,
        page_size=min(_int("BIBLIOTEQ_PAGE_SIZE", 24), 100),
        db_pool_size=_int("BIBLIOTEQ_DB_POOL_SIZE", 5),
        db_max_overflow=_int("BIBLIOTEQ_DB_MAX_OVERFLOW", 5, minimum=0),
        db_statement_timeout_ms=_int("BIBLIOTEQ_DB_STATEMENT_TIMEOUT_MS", 5000),
        site_title=os.environ.get("BIBLIOTEQ_SITE_TITLE", "Library Collection"),
        log_level=os.environ.get("BIBLIOTEQ_LOG_LEVEL", "INFO").upper(),
        root_path=os.environ.get("BIBLIOTEQ_ROOT_PATH", "").rstrip("/"),
        natural_sort=_bool("BIBLIOTEQ_NATURAL_SORT", True),
        natural_sort_numbers=sort_numbers,
        default_lang=os.environ.get("DEFAULT_LANG", "en").strip().replace("_", "-"),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
