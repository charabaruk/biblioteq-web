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
