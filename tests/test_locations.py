import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app import repository
from app.item_types import Message

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
DELETE FROM locations;
DELETE FROM journal;
DELETE FROM magazine;
CREATE TABLE videogame (myoid INTEGER PRIMARY KEY, title TEXT NOT NULL);
INSERT INTO videogame (title) VALUES ('Pong');
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
    assert catalog.types["videogame"].location is None
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


COPIES = """
INSERT INTO book_copy_info (item_oid, copyid, location)
SELECT myoid, 'n1', 'Annex' FROM book WHERE title = 'Nowhere';
INSERT INTO book_copy_info (item_oid, copyid, location)
SELECT myoid, 's1', 'Shelf A' FROM book WHERE title = 'Shelf';
INSERT INTO book_copy_info (item_oid, copyid, location)
SELECT myoid, 's2', 'Annex' FROM book WHERE title = 'Shelf';
INSERT INTO book_copy_info (item_oid, copyid, location)
SELECT myoid, 'o1', 'UNKNOWN' FROM book WHERE title = 'Orphan';
"""


@pytest.fixture
def copies(make_conn):
    with make_conn(BOOKS + COPIES) as conn:
        yield conn, repository.load_catalog(conn, "public")


@pytest.mark.parametrize("natural", [None, "integer"])
@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Annex", ["Nowhere", "Shelf"]),
        ("Shelf A", ["Shelf", "Shelf guide"]),  # Shelf matches twice but is listed once
        ("Basement", ["Orphan"]),
        ("UNKNOWN", ["Nowhere", "Sentinel"]),  # copy locations never widen UNKNOWN
        ("annex", []),
    ],
)
def test_location_filter_matches_item_or_copy_location(copies, natural, location, expected):
    conn, catalog = copies
    page = repository.search(conn, catalog, "", [], 1, 50, natural, location)
    assert _titles(page) == expected
    assert page.total == len(expected)


def test_recent_includes_items_matched_by_copy_location(copies):
    conn, catalog = copies
    titles = [i["title"] for i in repository.recent(conn, catalog.types["book"], 5, "Annex")]
    assert sorted(titles) == ["Nowhere", "Shelf"]


NO_COPY_LOCATION = """
DROP TABLE book_copy_info;
CREATE TABLE book_copy_info (
  copy_number INTEGER NOT NULL DEFAULT 1, copyid TEXT NOT NULL, item_oid INTEGER NOT NULL,
  myoid INTEGER UNIQUE, notes TEXT, status TEXT, PRIMARY KEY (copyid, item_oid)
);
"""


def test_filter_ignores_copies_without_a_location_column(make_conn):
    with make_conn(BOOKS + NO_COPY_LOCATION) as conn:
        catalog = repository.load_catalog(conn, "public")
        assert catalog.types["book"].copy_location() is None
        page = repository.search(conn, catalog, "", [], 1, 50, None, "Shelf A")
        assert _titles(page) == ["Shelf", "Shelf guide"]


REGISTERED = """
CREATE TABLE dvd (myoid INTEGER PRIMARY KEY, title TEXT NOT NULL, location TEXT);
INSERT INTO dvd (title, location) VALUES ('Film', 'Shelf A'), ('Lost film', NULL);
INSERT INTO locations (location, type) VALUES
 ('Shelf A', 'Book'), ('Shelf A', 'DVD'), ('home', 'Book'), ('Home', 'CD'),
 ('Annex', 'Video Game'), ('Basement ', 'Book');
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


def _item(conn, catalog, title):
    book = catalog.types["book"]
    item_id = conn.execute(
        text("SELECT myoid FROM book WHERE title = :t"), {"t": title}
    ).scalar_one()
    return repository.get_item(conn, catalog, book, item_id)


def _location_field(item):
    fields = [f for tab in item.tabs for s in tab.sections for f in s.fields]
    found = next((f for f in fields if f[0] == Message("Location")), None)
    return found[1:] if found else None


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Shelf", ("Shelf A", "/location/Shelf%20A")),
        ("Spaced", ("Shelf A ", "/browse/book?location=Shelf+A+")),
        ("Orphan", ("Basement", "/browse/book?location=Basement")),
        ("Manual", ("Unknown", "/browse/book?location=Unknown")),
        ("Sentinel", None),
        ("Nowhere", None),
    ],
)
def test_item_location_is_exact_linked_and_hidden_when_unknown(registered, title, expected):
    conn, catalog = registered
    assert _location_field(_item(conn, catalog, title)) == expected


def test_item_location_is_hidden_when_blank(make_conn):
    with make_conn(BOOKS + "UPDATE book SET location = '  ' WHERE title = 'Nowhere';") as conn:
        catalog = repository.load_catalog(conn, "public")
        assert _location_field(_item(conn, catalog, "Nowhere")) is None


def test_item_location_links_to_browse_without_the_locations_table(make_conn):
    with make_conn(BOOKS + "DROP TABLE locations;") as conn:
        catalog = repository.load_catalog(conn, "public")
        field = _location_field(_item(conn, catalog, "Shelf"))
        assert field[1] == "/browse/book?location=Shelf+A"


def _holdings(item):
    sections = [s for tab in item.tabs for s in tab.sections if s.kind == "table"]
    assert len(sections) == 1
    column = sections[0].headers.index(Message("Location"))
    return [row[column] for _, rows in sections[0].groups for row in rows]


@pytest.fixture
def held(make_conn):
    extra = """
    INSERT INTO book_copy_info (item_oid, copyid, location)
    SELECT myoid, 'h2', 'Basement ' FROM book WHERE title = 'Sentinel';
    INSERT INTO book_copy_info (item_oid, copyid)
    SELECT myoid, 'h1' FROM book WHERE title IN ('Sentinel', 'Shelf guide', 'Manual');
    """
    with make_conn(BOOKS + REGISTERED + COPIES + extra) as conn:
        yield conn, repository.load_catalog(conn, "public")


def test_copy_locations_link_like_item_locations(held):
    conn, catalog = held
    assert _holdings(_item(conn, catalog, "Shelf")) == [
        ("Shelf A", "/location/Shelf%20A"),
        ("Annex", "/browse/book?location=Annex"),
    ]


def test_copy_at_unknown_takes_its_items_location(held):
    conn, catalog = held
    assert _holdings(_item(conn, catalog, "Shelf guide")) == [("Shelf A", "/location/Shelf%20A")]
    assert _holdings(_item(conn, catalog, "Orphan")) == [
        ("Basement", "/browse/book?location=Basement")
    ]


def test_copy_at_unknown_of_an_item_at_unknown_is_blank(held):
    conn, catalog = held
    assert _holdings(_item(conn, catalog, "Sentinel")) == [
        ("", None),
        ("Basement ", "/location/Basement%20"),
    ]
