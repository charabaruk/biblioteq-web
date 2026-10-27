import pytest

from app.config import ConfigError, load_settings


def test_requires_db_url(monkeypatch):
    monkeypatch.delenv("BIBLIOTEQ_DB_URL", raising=False)
    with pytest.raises(ConfigError):
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
