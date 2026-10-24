import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app import repository
from app.repository import title_sort_key

SCHEMA = Path(__file__).parent / "schema_sqlite.sql"


def _ordered(titles, numbers):
    return sorted(titles, key=title_sort_key(numbers))


def test_integer_runs_sort_numerically():
    assert _ordered(["Volume 10", "Volume 2", "Volume 1"], "integer") == [
        "Volume 1",
        "Volume 2",
        "Volume 10",
    ]


def test_sort_ignores_case():
    assert _ordered(["b", "A", "c"], "integer") == ["A", "b", "c"]


def test_missing_title_sorts_first():
    assert _ordered(["Volume 1", None, ""], "integer")[-1] == "Volume 1"


def test_integer_mode_keeps_version_order():
    assert _ordered(["v2.10", "v2.9"], "integer") == ["v2.9", "v2.10"]


def test_decimal_mode_reads_fractions():
    assert _ordered(["v2.9", "v2.10"], "decimal") == ["v2.10", "v2.9"]


@pytest.fixture
def conn_and_catalog(tmp_path):
    path = tmp_path / "library.db"
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA.read_text())
        db.execute("DELETE FROM book")
        db.executemany(
            "INSERT INTO book (title, quantity) VALUES (?, 1)",
            [("Vol 10",), ("Vol 2",), ("Vol 1",), ("vol 3",)],
        )
    engine = create_engine(f"sqlite:///{path}")
    with engine.connect() as conn:
        yield conn, repository.load_catalog(conn, "public")
    engine.dispose()


def _titles(page):
    return [i["title"] for i in page.items]


def test_search_orders_naturally(conn_and_catalog):
    conn, catalog = conn_and_catalog
    page = repository.search(conn, catalog, "", ["book"], 1, 10, "integer")
    assert _titles(page) == ["Vol 1", "Vol 2", "vol 3", "Vol 10"]
    assert page.total == 4
    assert {"creator", "identifier", "has_cover"} <= page.items[0].keys()


def test_search_without_natural_orders_in_sql(conn_and_catalog):
    conn, catalog = conn_and_catalog
    page = repository.search(conn, catalog, "", ["book"], 1, 10)
    assert _titles(page) == ["Vol 1", "Vol 10", "Vol 2", "vol 3"]


def test_natural_pagination_follows_order(conn_and_catalog):
    conn, catalog = conn_and_catalog
    first = repository.search(conn, catalog, "", ["book"], 1, 3, "integer")
    second = repository.search(conn, catalog, "", ["book"], 2, 3, "integer")
    assert _titles(first) == ["Vol 1", "Vol 2", "vol 3"]
    assert _titles(second) == ["Vol 10"]
    assert second.total == 4
    clamped = repository.search(conn, catalog, "", ["book"], 99, 3, "integer")
    assert clamped.page == 2


def test_natural_search_filters_by_terms(conn_and_catalog):
    conn, catalog = conn_and_catalog
    page = repository.search(conn, catalog, "vol 1", ["book"], 1, 10, "integer")
    assert _titles(page) == ["Vol 1", "Vol 10"]
