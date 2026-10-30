import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app import repository

SCHEMA = Path(__file__).parent / "schema_sqlite.sql"


@pytest.fixture
def make_conn(tmp_path):
    engines = []

    def make(setup: str = ""):
        path = tmp_path / f"library{len(engines)}.db"
        with sqlite3.connect(path) as db:
            db.executescript(SCHEMA.read_text())
            db.executescript(setup)
        engine = create_engine(f"sqlite:///{path}")
        engines.append(engine)
        return engine.connect()

    yield make
    for engine in engines:
        engine.dispose()


def test_catalog_reports_the_locations_table(make_conn):
    with make_conn() as conn:
        assert repository.load_catalog(conn, "public").has_locations


def test_catalog_without_locations_table(make_conn):
    with make_conn("DROP TABLE locations;") as conn:
        assert not repository.load_catalog(conn, "public").has_locations
