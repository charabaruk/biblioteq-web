import pytest

from app import config, db
from app.config import ConfigError


@pytest.fixture(autouse=True)
def _reset():
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()


@pytest.mark.parametrize("url", ["mysql://u:p@h/d", "sqlite://", "sqlite:///:memory:"])
def test_rejects_unsupported_or_non_file_urls(monkeypatch, url):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", url)
    with pytest.raises(ConfigError):
        db.get_engine()


def test_sqlite_does_not_create_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("BIBLIOTEQ_DB_URL", f"sqlite:///{tmp_path / 'missing.db'}")
    with pytest.raises(Exception, match="unable to open"):
        db.get_engine().connect()
    assert not (tmp_path / "missing.db").exists()
