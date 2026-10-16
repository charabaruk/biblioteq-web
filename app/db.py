"""Database engine and connection dependency. Every connection is read-only."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
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


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency yielding a connection that is rolled back on exit."""
    with get_engine().connect() as conn:
        yield conn
