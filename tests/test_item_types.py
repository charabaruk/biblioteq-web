from dataclasses import replace
from gettext import NullTranslations

import pytest

from app.item_types import (
    ITEM_TYPES,
    FieldsSection,
    Message,
    TableSection,
    TabSpec,
    TextSection,
    localize_labels,
    quote,
    related_tables,
    resolve,
)


def test_quote_accepts_plain_names():
    assert quote("front_cover") == '"front_cover"'


@pytest.mark.parametrize("bad", ['a"b', "a b", "1abc", "a;drop", ""])
def test_quote_rejects_unsafe_names(bad):
    with pytest.raises(ValueError):
        quote(bad)


def test_registry_keeps_prose_out_of_detail_fields():
    for spec in ITEM_TYPES:
        assert not {c for c, _ in spec.detail_fields} & {c for c, _ in spec.text_fields}


def test_localize_labels_translates_nested_values_without_mutating_registry():
    class FrenchTranslations(NullTranslations):
        def gettext(self, message):
            return {"Description": "Description traduite"}.get(message, message)

        def pgettext(self, context, message):
            return {
                ("item-type", "Book"): "Livre",
                ("tab-book", "Main"): "Principal",
            }.get((context, message), self.gettext(message))

    book = next(spec for spec in ITEM_TYPES if spec.key == "book")
    localized = localize_labels(book, FrenchTranslations())

    assert localized.label == "Livre"
    assert localized.tabs[0].label == "Principal"
    assert localized.tabs[0].sections[0].label == "Description traduite"
    assert book.label == Message("Book", "item-type")
    assert localized.table == book.table == "book"


def _section_columns(spec):
    """Every column the type's declared tabs read, from its own table or related ones."""
    cols = set()
    for tab in spec.tabs:
        for s in tab.sections:
            if isinstance(s, FieldsSection):
                cols |= {c for c, _ in s.fields}
            elif isinstance(s, TextSection):
                cols.add(s.column)
            else:
                cols |= {c for c, _ in s.columns} | {s.fk, *s.order_by}
    return cols


def test_registry_never_references_marc_tags():
    for spec in ITEM_TYPES:
        cols = {spec.title, spec.creator, spec.identifier, spec.quantity, spec.front_cover}
        cols |= set(spec.search_columns) | {c for c, _ in spec.detail_fields}
        cols |= {c for c, _ in spec.text_fields} | _section_columns(spec)
        assert "marc_tags" not in cols


def test_book_tab_columns_are_valid_and_unique():
    book = next(t for t in ITEM_TYPES if t.key == "book")
    assert [t.key for t in book.tabs] == ["main", "holdings", "details"]
    columns = [
        c
        for tab in book.tabs
        for s in tab.sections
        for c in (
            [s.column]
            if isinstance(s, TextSection)
            else [c for c, _ in s.fields]
            if isinstance(s, FieldsSection)
            else []
        )
    ]
    assert len(columns) == len(set(columns))
    for c in columns:
        quote(c)


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


def test_default_main_tab_puts_text_before_fields():
    book = replace(
        next(t for t in ITEM_TYPES if t.key == "book"),
        tabs=(),
        detail_fields=(("author", "Authors"),),
        text_fields=(("description", "Description"),),
    )
    resolved = resolve(book, {"myoid", "title", "author", "description"})
    assert resolved is not None
    (main,) = resolved.tabs
    assert main.key == "main"
    assert main.sections == (
        TextSection("description", "Description"),
        FieldsSection((("author", "Authors"),)),
    )


def test_resolve_drops_missing_text_fields():
    book = replace(
        next(t for t in ITEM_TYPES if t.key == "book"),
        tabs=(),
        detail_fields=(("author", "Authors"),),
        text_fields=(("description", "Description"),),
    )
    resolved = resolve(book, {"myoid", "title", "author"})
    assert resolved is not None
    assert resolved.text_fields == ()
    (main,) = resolved.tabs
    assert main.sections == (FieldsSection((("author", "Authors"),)),)


NOTES = TableSection(
    label="Notes",
    table="note",
    fk="item_oid",
    columns=(("seq", "No."), ("note", "Note")),
    order_by=("grp", "seq"),
    group_by="grp",
)


def _with_notes(lazy=False):
    book = next(t for t in ITEM_TYPES if t.key == "book")
    return replace(book, tabs=(TabSpec("notes", "Notes", (NOTES,), lazy=lazy),))


def test_resolve_keeps_available_table_section():
    tables = {"note": {"item_oid", "seq", "note", "grp"}}
    resolved = resolve(_with_notes(), {"myoid", "title"}, tables)
    assert resolved is not None
    assert resolved.tabs[0].sections == (NOTES,)


def test_resolve_trims_table_section_columns():
    tables = {"note": {"item_oid", "seq", "note"}}
    resolved = resolve(_with_notes(), {"myoid", "title"}, tables)
    assert resolved is not None
    (section,) = resolved.tabs[0].sections
    assert section.order_by == ("seq",)
    assert section.group_by is None


@pytest.mark.parametrize(
    "tables",
    [None, {}, {"note": {"seq", "note"}}, {"note": {"item_oid", "other"}}],
    ids=["no tables", "table missing", "fk missing", "no shown columns"],
)
def test_resolve_drops_unusable_table_section_and_empty_tab(tables):
    resolved = resolve(_with_notes(), {"myoid", "title"}, tables)
    assert resolved is not None
    assert resolved.tabs == ()


def test_related_tables_lists_section_tables():
    assert list(related_tables(_with_notes())) == ["note"]
    assert list(related_tables(next(t for t in ITEM_TYPES if t.key == "book"))) == [
        "book_copy_info"
    ]
