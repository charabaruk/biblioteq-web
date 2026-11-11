import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app import repository
from app.repository import title_sort_key

SCHEMA = Path(__file__).parent / "schema_sqlite.sql"
PERIODICAL_ROWS = [
    (5, "A Periodical", 1, 1, 1, "2024-01-01"),
    (10, "Same Periodical", 2, 1, 2, "2023-01-01"),
    (11, "Same Periodical", 1, 1, 10, "2022-01-01"),
    (12, "Same Periodical", 1, 2, 1, "2020-01-01"),
    (13, "Same Periodical", 1, 1, 2, "2024-01-01"),
    (14, "Same Periodical", 1, 1, 2, "12/31/2023"),
]


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
        db.execute("DELETE FROM journal")
        db.execute("DELETE FROM magazine")
        db.executemany(
            "INSERT INTO book (title, quantity) VALUES (?, 1)",
            [("Vol 10",), ("Vol 2",), ("Vol 1",), ("vol 3",)],
        )
        for table in ("journal", "magazine"):
            db.executemany(
                f"INSERT INTO {table} "
                "(myoid, title, issuevolume, issueno, display_number, pdate) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                PERIODICAL_ROWS,
            )
    engine = create_engine(f"sqlite:///{path}")
    with engine.connect() as conn:
        yield conn, repository.load_catalog(conn, "public")
    engine.dispose()


def _titles(page):
    return [i["title"] for i in page.items]


@pytest.mark.parametrize("type_key", ["journal", "magazine"])
@pytest.mark.parametrize("natural", [None, "integer"])
@pytest.mark.parametrize(
    ("direction", "expected_ids"),
    [
        ("asc", [5, 14, 13, 11, 12, 10]),
        ("desc", [5, 10, 12, 11, 13, 14]),
    ],
)
def test_periodical_ordering(conn_and_catalog, type_key, natural, direction, expected_ids):
    conn, catalog = conn_and_catalog
    page = repository.search(
        conn,
        catalog,
        "",
        [type_key],
        1,
        10,
        natural,
        issue_direction=direction,
    )
    assert [item["id"] for item in page.items] == expected_ids


def test_periodical_pagination_follows_issue_order(conn_and_catalog):
    conn, catalog = conn_and_catalog
    first = repository.search(conn, catalog, "", ["journal"], 1, 3, issue_direction="asc")
    second = repository.search(conn, catalog, "", ["journal"], 2, 3, issue_direction="asc")
    assert [item["id"] for item in first.items] == [5, 14, 13]
    assert [item["id"] for item in second.items] == [11, 12, 10]


@pytest.mark.parametrize("type_key", ["journal", "magazine"])
@pytest.mark.parametrize("natural", [None, "integer"])
def test_periodical_series_group_before_pagination(conn_and_catalog, type_key, natural):
    conn, catalog = conn_and_catalog
    conn.execute(text(f"DELETE FROM {type_key}"))
    conn.execute(
        text(
            f"INSERT INTO {type_key} (myoid, title, id, issuevolume, issueno, display_number) "
            "VALUES (:oid, :title, :identifier, :volume, :issue, :display)"
        ),
        [
            {
                "oid": 1,
                "title": "Z Old",
                "identifier": "Shared",
                "volume": 1,
                "issue": 1,
                "display": 1,
            },
            {
                "oid": 2,
                "title": "A New",
                "identifier": "Shared",
                "volume": 2,
                "issue": 1,
                "display": 1,
            },
            {
                "oid": 3,
                "title": "Shared",
                "identifier": None,
                "volume": 1,
                "issue": 1,
                "display": 1,
            },
            {"oid": 4, "title": "Shared", "identifier": " ", "volume": 1, "issue": 2, "display": 2},
            {
                "oid": 5,
                "title": "Shared",
                "identifier": "Other",
                "volume": 1,
                "issue": 1,
                "display": 1,
            },
        ],
    )
    conn.commit()
    spec = catalog.types[type_key]
    first = repository.browse_periodical_series(conn, spec, 1, 2, natural)
    second = repository.browse_periodical_series(conn, spec, 2, 2, natural)

    assert first.total == second.total == 3
    assert [item["id"] for item in first.items + second.items] == [2, 5, 4]
    assert second.items[0]["series_url"].endswith("/by-title/Shared")
    assert repository.browse_periodical_series(conn, spec, 99, 2, natural).page == 2


def test_periodical_search_filters_exact_identifier_and_paginates(conn_and_catalog):
    conn, catalog = conn_and_catalog
    conn.execute(
        text("UPDATE journal SET id = :identifier WHERE myoid IN (10, 11, 12)"),
        {"identifier": "SERIES-A"},
    )
    conn.execute(
        text("UPDATE journal SET id = :identifier WHERE myoid = 13"),
        {"identifier": "SERIES-AB"},
    )
    conn.commit()

    first = repository.search(
        conn,
        catalog,
        "",
        ["journal"],
        1,
        2,
        issue_direction="asc",
        identifier_filter="SERIES-A",
    )
    second = repository.search(
        conn,
        catalog,
        "",
        ["journal"],
        2,
        2,
        issue_direction="asc",
        identifier_filter="SERIES-A",
    )

    assert first.total == 3
    assert [item["id"] for item in first.items] == [11, 12]
    assert [item["id"] for item in second.items] == [10]


@pytest.mark.parametrize(
    ("direction", "expected_ids"),
    [
        ("asc", [5, 13, 14, 11, 12, 10]),
        ("desc", [5, 10, 12, 11, 14, 13]),
    ],
)
def test_periodical_null_date_order_uses_database_default(
    conn_and_catalog, direction, expected_ids
):
    conn, catalog = conn_and_catalog
    conn.execute(text("UPDATE journal SET pdate = NULL WHERE myoid = 13"))
    page = repository.search(conn, catalog, "", ["journal"], 1, 10, issue_direction=direction)
    assert [item["id"] for item in page.items] == expected_ids


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
