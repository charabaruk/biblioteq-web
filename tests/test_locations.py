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


BOOKS = """
DELETE FROM book;
INSERT INTO book (title, quantity, location) VALUES
 ('At home', 1, 'home'), ('At Home', 1, 'Home'), ('At HOME', 1, 'HOME'),
 ('Shelf', 1, 'Shelf A'), ('Spaced', 1, 'Shelf A '), ('Nowhere', 1, NULL),
 ('Sentinel', 1, 'UNKNOWN'), ('Orphan', 1, 'Basement'), ('Manual', 1, 'Unknown'),
 ('Shelf guide', 1, 'Shelf A');
"""


@pytest.fixture
def books(make_conn):
    with make_conn(BOOKS) as conn:
        yield conn, repository.load_catalog(conn, "public")


def _titles(page):
    return sorted(i["title"] for i in page.items)


@pytest.mark.parametrize("natural", [None, "integer"])
@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("home", ["At home"]),
        ("Home", ["At Home"]),
        ("Shelf A", ["Shelf", "Shelf guide"]),
        ("Shelf A ", ["Spaced"]),
        ("Basement", ["Orphan"]),
        ("Unknown", ["Manual"]),
        ("UNKNOWN", ["Nowhere", "Sentinel"]),
        ("Elsewhere", []),
    ],
)
def test_location_filter_is_exact(books, natural, location, expected):
    conn, catalog = books
    page = repository.search(conn, catalog, "", [], 1, 50, natural, location)
    assert _titles(page) == expected
    assert page.total == len(expected)


def test_types_without_a_location_column_never_match(books):
    conn, catalog = books
    assert catalog.types["journal"].location is None
    for location in ("Shelf A", "UNKNOWN"):
        page = repository.search(conn, catalog, "", [], 1, 50, None, location)
        assert {i["type"] for i in page.items} == {"book"}


@pytest.mark.parametrize("natural", [None, "integer"])
def test_location_combines_with_search_terms(books, natural):
    conn, catalog = books
    page = repository.search(conn, catalog, "guide", [], 1, 50, natural, "Shelf A")
    assert _titles(page) == ["Shelf guide"]
    assert repository.search(conn, catalog, "guide", [], 1, 50, natural, "home").total == 0


def test_recent_honours_the_location(books):
    conn, catalog = books
    book = catalog.types["book"]
    assert [i["title"] for i in repository.recent(conn, book, 5, "UNKNOWN")] == [
        "Sentinel",
        "Nowhere",
    ]
    assert len(repository.recent(conn, book, 50)) == 10


REGISTERED = """
CREATE TABLE dvd (myoid INTEGER PRIMARY KEY, title TEXT NOT NULL, location TEXT);
INSERT INTO dvd (title, location) VALUES ('Film', 'Shelf A'), ('Lost film', NULL);
INSERT INTO locations (location, type) VALUES
 ('Shelf A', 'Book'), ('Shelf A', 'DVD'), ('home', 'Book'), ('Home', 'CD'),
 ('Annex', 'Journal'), ('Basement ', 'Book');
"""


@pytest.fixture
def registered(make_conn):
    with make_conn(BOOKS + REGISTERED) as conn:
        yield conn, repository.load_catalog(conn, "public")


def test_options_list_distinct_locations_of_served_types(registered):
    conn, catalog = registered
    # "Home" is only registered for CD, which this database has no table for.
    assert repository.location_options(conn, catalog) == ["Basement ", "home", "Shelf A"]


def test_types_for_a_name_follow_registry_order(registered):
    conn, catalog = registered
    assert [s.key for s in repository.location_types(conn, catalog, "Shelf A")] == ["book", "dvd"]
    assert [s.key for s in repository.location_types(conn, catalog, "home")] == ["book"]


@pytest.mark.parametrize("name", ["shelf a", "Shelf A ", "Home", "Annex", "UNKNOWN", ""])
def test_unregistered_or_unservable_names_have_no_types(registered, name):
    conn, catalog = registered
    assert repository.location_types(conn, catalog, name) == []


def test_registration_is_checked_per_type(registered):
    conn, catalog = registered
    book, dvd = catalog.types["book"], catalog.types["dvd"]
    assert repository.location_registered(conn, catalog, book, "home")
    assert not repository.location_registered(conn, catalog, dvd, "home")
    assert not repository.location_registered(conn, catalog, book, "Basement")


def test_types_without_location_lists_types_with_such_items(registered):
    conn, catalog = registered
    assert [s.key for s in repository.types_without_location(conn, catalog)] == ["book", "dvd"]


def test_lookups_are_empty_without_the_locations_table(make_conn):
    with make_conn(BOOKS + "DROP TABLE locations;") as conn:
        catalog = repository.load_catalog(conn, "public")
        book = catalog.types["book"]
        assert repository.location_options(conn, catalog) == []
        assert repository.location_types(conn, catalog, "Shelf A") == []
        assert not repository.location_registered(conn, catalog, book, "Shelf A")
