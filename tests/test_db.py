import pytest

from app import config, db
from app.config import ConfigError, Settings


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


class _RecordingConnection:
    def __init__(self, fail_load=False):
        self.calls = []
        self.fail_load = fail_load

    def execute(self, statement):
        self.calls.append(("execute", statement))

    def enable_load_extension(self, enabled):
        self.calls.append(("enable", enabled))

    def load_extension(self, path):
        self.calls.append(("load", path))
        if self.fail_load:
            raise RuntimeError("extension load failed")


def _sqlite_connect_listener(monkeypatch, settings):
    listeners = []
    engine = object()

    def listen_for(_engine, event_name):
        assert _engine is engine
        assert event_name == "connect"
        return listeners.append

    monkeypatch.setattr(db.event, "listens_for", listen_for)
    monkeypatch.setattr(db, "create_engine", lambda *_args, **_kwargs: engine)
    assert db._sqlite_engine(settings) is engine
    return listeners[0]


def test_sqlite_connect_sets_read_only_pragmas(monkeypatch, tmp_path):
    database_path = tmp_path / "library.db"
    database_path.touch()
    settings = Settings(db_url=f"sqlite:///{database_path}", db_statement_timeout_ms=1234)
    listener = _sqlite_connect_listener(monkeypatch, settings)
    connection = _RecordingConnection()

    listener(connection, None)

    assert connection.calls == [
        ("execute", "PRAGMA query_only = ON"),
        ("execute", "PRAGMA busy_timeout = 1234"),
    ]


def test_sqlite_connect_loads_icu_extension(monkeypatch, tmp_path):
    database_path = tmp_path / "library.db"
    database_path.touch()
    icu_path = tmp_path / "icu.so"
    icu_path.touch()
    settings = Settings(
        db_url=f"sqlite:///{database_path}",
        sqlite_ext_icu_path=str(icu_path),
    )
    listener = _sqlite_connect_listener(monkeypatch, settings)
    connection = _RecordingConnection()

    listener(connection, None)

    assert connection.calls == [
        ("execute", "PRAGMA query_only = ON"),
        ("execute", "PRAGMA busy_timeout = 5000"),
        ("enable", True),
        ("load", str(icu_path)),
        ("enable", False),
    ]


def test_sqlite_connect_disables_extension_loading_when_load_fails(monkeypatch, tmp_path):
    database_path = tmp_path / "library.db"
    database_path.touch()
    icu_path = tmp_path / "icu.so"
    icu_path.touch()
    settings = Settings(
        db_url=f"sqlite:///{database_path}",
        sqlite_ext_icu_path=str(icu_path),
    )
    listener = _sqlite_connect_listener(monkeypatch, settings)
    connection = _RecordingConnection(fail_load=True)

    with pytest.raises(RuntimeError, match="extension load failed"):
        listener(connection, None)

    assert connection.calls[-1] == ("enable", False)
