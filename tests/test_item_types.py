import pytest

from app.item_types import ITEM_TYPES, quote, resolve


def test_quote_accepts_plain_names():
    assert quote("front_cover") == '"front_cover"'


@pytest.mark.parametrize("bad", ['a"b', "a b", "1abc", "a;drop", ""])
def test_quote_rejects_unsafe_names(bad):
    with pytest.raises(ValueError):
        quote(bad)


def test_registry_never_references_marc_tags():
    for spec in ITEM_TYPES:
        cols = {spec.title, spec.creator, spec.identifier, spec.quantity, spec.front_cover}
        cols |= set(spec.search_columns) | {c for c, _ in spec.detail_fields}
        assert "marc_tags" not in cols


def test_registry_identifiers_are_valid():
    for spec in ITEM_TYPES:
        quote(spec.table)
        for c in (spec.title, spec.creator, spec.identifier, spec.quantity, *spec.search_columns):
            if c:
                quote(c)


def test_resolve_drops_missing_columns():
    book = next(t for t in ITEM_TYPES if t.key == "book")
    resolved = resolve(book, {"myoid", "title", "author"})
    assert resolved is not None
    assert resolved.creator == "author"
    assert resolved.identifier is None
    assert resolved.search_columns == ("title", "author")


def test_resolve_disables_type_without_required_columns():
    book = next(t for t in ITEM_TYPES if t.key == "book")
    assert resolve(book, {"title"}) is None
    assert resolve(book, set()) is None


def test_photograph_collection_uses_collection_columns():
    photo = next(t for t in ITEM_TYPES if t.key == "photograph")
    resolved = resolve(
        photo,
        {"myoid", "title", "id", "accession_number", "location", "about", "notes", "image_scaled"},
    )

    assert resolved is not None
    assert resolved.creator is None
    assert resolved.search_columns == ("title", "id", "accession_number", "about", "notes")
    assert resolved.detail_fields == (
        ("id", "ID"),
        ("accession_number", "Accession Number"),
        ("location", "Location"),
        ("about", "About"),
        ("notes", "Notes"),
    )
