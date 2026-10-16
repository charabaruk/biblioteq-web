"""Database engine and connection dependency. Every connection is read-only."""

from collections.abc import Iterator
from functools import lru_cache
from urllib.parse import quote

from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.engine import URL, make_url

from app.config import ConfigError, Settings, get_settings


def _postgresql_engine(s: Settings) -> Engine:
    # Server-side options are a second guard on top of the read-only role.
    options = (
        "-c default_transaction_read_only=on "
        f"-c statement_timeout={s.db_statement_timeout_ms} "
        f"-c search_path={s.db_schema}"
    )
    return create_engine(
        s.db_url,
        pool_size=s.db_pool_size,
        max_overflow=s.db_max_overflow,
        pool_pre_ping=True,
        connect_args={"options": options},
    )


def _sqlite_engine(s: Settings) -> Engine:
    path = make_url(s.db_url).database
    if not path or path == ":memory:":
        raise ConfigError("BIBLIOTEQ_DB_URL must point to a SQLite database file")
    # mode=ro makes SQLite refuse to write or create the file.
    url = URL.create(
        "sqlite", database=f"file:{quote(path, safe='/:')}?mode=ro", query={"uri": "true"}
    )
    engine = create_engine(
        url, pool_size=s.db_pool_size, max_overflow=s.db_max_overflow, pool_pre_ping=True
    )

    @event.listens_for(engine, "connect")
    def _guard(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA query_only = ON")
        dbapi_connection.execute(f"PRAGMA busy_timeout = {int(s.db_statement_timeout_ms)}")

    return engine


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    backend = make_url(s.db_url).get_backend_name()
    if backend == "postgresql":
        return _postgresql_engine(s)
    if backend == "sqlite":
        return _sqlite_engine(s)
    raise ConfigError(f"Unsupported database backend {backend!r}; use postgresql or sqlite")


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency yielding a connection that is rolled back on exit."""
    with get_engine().connect() as conn:
        yield conn
