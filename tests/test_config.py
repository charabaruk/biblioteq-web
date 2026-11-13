import pytest

from app.config import ConfigError, load_settings


def test_requires_db_url(monkeypatch):
    monkeypatch.delenv("BIBLIOTEQ_DB_URL", raising=False)
    with pytest.raises(ConfigError):
        load_settings()


def test_sqlite_icu_path_defaults_to_none(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "sqlite:////tmp/library.db")
    monkeypatch.delenv("BIBLIOTEQ_SQLITE_EXT_ICU_PATH", raising=False)
    assert load_settings().sqlite_ext_icu_path is None


def test_sqlite_icu_path(monkeypatch, tmp_path):
    icu_path = tmp_path / "icu.so"
    icu_path.touch()
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "sqlite:////tmp/library.db")
    monkeypatch.setenv("BIBLIOTEQ_SQLITE_EXT_ICU_PATH", str(icu_path))
    assert load_settings().sqlite_ext_icu_path == str(icu_path)


def test_sqlite_icu_path_must_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "sqlite:////tmp/library.db")
    monkeypatch.setenv("BIBLIOTEQ_SQLITE_EXT_ICU_PATH", str(tmp_path / "missing.so"))
    with pytest.raises(ConfigError, match="BIBLIOTEQ_SQLITE_EXT_ICU_PATH"):
        load_settings()


def test_schema_defaults_to_public(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.delenv("BIBLIOTEQ_DB_SCHEMA", raising=False)
    assert load_settings().db_schema == "public"


def test_default_language_setting_normalizes_locale_separator(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("DEFAULT_LANG", "fr_CA")
    assert load_settings().default_lang == "fr-CA"


def test_schema_override(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_DB_SCHEMA", "library")
    assert load_settings().db_schema == "library"


@pytest.mark.parametrize("bad", ["a b", "a;b", 'x"y', "1abc", "a,b"])
def test_schema_must_be_identifier(monkeypatch, bad):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_DB_SCHEMA", bad)
    with pytest.raises(ConfigError):
        load_settings()


def test_page_size_is_capped(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_PAGE_SIZE", "5000")
    assert load_settings().page_size == 100


def test_natural_sort_defaults(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.delenv("BIBLIOTEQ_NATURAL_SORT", raising=False)
    monkeypatch.delenv("BIBLIOTEQ_NATURAL_SORT_NUMBERS", raising=False)
    settings = load_settings()
    assert settings.natural_sort is True
    assert settings.natural_sort_numbers == "integer"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("ON", True), ("1", True), ("false", False), ("No", False), ("0", False)],
)
def test_natural_sort_boolean(monkeypatch, raw, expected):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_NATURAL_SORT", raw)
    assert load_settings().natural_sort is expected


def test_natural_sort_boolean_invalid(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_NATURAL_SORT", "maybe")
    with pytest.raises(ConfigError):
        load_settings()


def test_natural_sort_numbers(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_NATURAL_SORT_NUMBERS", "Decimal")
    assert load_settings().natural_sort_numbers == "decimal"
    monkeypatch.setenv("BIBLIOTEQ_NATURAL_SORT_NUMBERS", "float")
    with pytest.raises(ConfigError):
        load_settings()


def test_cache_settings_defaults(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.delenv("BIBLIOTEQ_CACHE_REDIS_URL", raising=False)
    monkeypatch.delenv("BIBLIOTEQ_CACHE_NAMESPACE", raising=False)
    monkeypatch.delenv("BIBLIOTEQ_CACHE_FRESHNESS_SECONDS", raising=False)
    monkeypatch.delenv("BIBLIOTEQ_CACHE_MAX_STALE_SECONDS", raising=False)
    settings = load_settings()
    assert settings.cache_redis_url is None
    assert settings.cache_namespace == "biblioteq-web"
    assert settings.cache_freshness_seconds == 300
    assert settings.cache_max_stale_seconds == 3600


def test_cache_settings_from_environment(monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_CACHE_REDIS_URL", " redis://localhost:6379/15 ")
    monkeypatch.setenv("BIBLIOTEQ_CACHE_NAMESPACE", " shelf-a ")
    monkeypatch.setenv("BIBLIOTEQ_CACHE_FRESHNESS_SECONDS", "60")
    monkeypatch.setenv("BIBLIOTEQ_CACHE_MAX_STALE_SECONDS", "600")
    settings = load_settings()
    assert settings.cache_redis_url == "redis://localhost:6379/15"
    assert settings.cache_namespace == "shelf-a"
    assert settings.cache_freshness_seconds == 60
    assert settings.cache_max_stale_seconds == 600


@pytest.mark.parametrize(
    ("freshness", "max_stale"), [("0", "3600"), ("300", "0"), ("301", "300")]
)
def test_cache_timeouts_must_be_positive_and_consistent(monkeypatch, freshness, max_stale):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("BIBLIOTEQ_CACHE_FRESHNESS_SECONDS", freshness)
    monkeypatch.setenv("BIBLIOTEQ_CACHE_MAX_STALE_SECONDS", max_stale)
    with pytest.raises(ConfigError):
        load_settings()
