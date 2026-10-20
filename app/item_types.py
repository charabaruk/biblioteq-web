"""Registry of BiblioteQ item types.

This is the only place table and column names are defined. SQL is built from these
names (never from user input); values are always bound parameters. The `marc_tags`
column is deliberately absent (see ADR-0003).

To add a type, append an `ItemType` to `ITEM_TYPES`. Columns that do not exist in the
connected database are dropped at startup by `resolve()`, so differences between
BiblioteQ versions degrade gracefully.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, replace

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class FieldsSection:
    """Short label/value pairs from the item's own table, rendered as a definition list."""

    fields: tuple[tuple[str, str], ...]  # (column, label)


@dataclass(frozen=True)
class TextSection:
    """One prose column from the item's own table."""

    column: str
    label: str


@dataclass(frozen=True)
class TableSection:
    """Rows of a related table whose `fk` column holds the item's primary key."""

    label: str
    table: str
    fk: str
    columns: tuple[tuple[str, str], ...]  # (column, header)
    order_by: tuple[str, ...] = ()  # must start with group_by when grouping
    group_by: str | None = None
    group_label: str = ""  # prefix for group headings, e.g. "Disc"
    limit: int = 500


SectionSpec = FieldsSection | TextSection | TableSection


@dataclass(frozen=True)
class TabSpec:
    key: str  # used in URLs and fragments
    label: str
    sections: tuple[SectionSpec, ...]
    lazy: bool = False  # content is fetched on demand, not rendered with the item page
    template: str | None = None  # optional template overriding the default tab body


@dataclass(frozen=True)
class ItemType:
    key: str  # URL slug
    label: str  # singular display name
    label_plural: str  # plural display name
    table: str
    title: str
    creator: str | None = None
    identifier: str | None = None  # primary identifier shown on cards (ISBN, ISSN, ...)
    identifier_label: str | None = None  # display label for primary identifier
    search_columns: tuple[str, ...] = ()
    detail_fields: tuple[tuple[str, str], ...] = ()  # (column, label)
    text_fields: tuple[tuple[str, str], ...] = ()  # prose columns, shown above detail_fields
    tabs: tuple[TabSpec, ...] = ()  # empty: a Main tab is built from the fields above
    quantity: str | None = None
    borrower_type: str | None = None  # value of item_borrower.type for this table
    front_cover: str | None = None
    back_cover: str | None = None
    pk: str = "myoid"


ITEM_TYPES: tuple[ItemType, ...] = (
    ItemType(
        key="book",
        label="Book",
        label_plural="Books",
        table="book",
        title="title",
        creator="author",
        identifier="isbn13",
        identifier_label="ISBN-13",
        search_columns=(
            "title",
            "series_title",
            "author",
            "id",
            "isbn13",
            "publisher",
            "category",
            "keyword",
        ),
        tabs=(
            TabSpec(
                key="main",
                label="Main",
                sections=(
                    TextSection("description", "Description"),
                    FieldsSection(
                        (
                            ("series_title", "Series Title"),
                            ("volume_number", "Volume Number"),
                            ("author", "Authors"),
                            ("publisher", "Publisher"),
                            ("pdate", "Publication Date"),
                            ("place", "Place of Publication"),
                            ("edition", "Edition"),
                            ("category", "Categories"),
                            ("language", "Language"),
                            ("target_audience", "Target Audience"),
                            ("id", "ISBN-10"),
                            ("isbn13", "ISBN-13"),
                            ("binding_type", "Book Binding Type"),
                            ("location", "Location"),
                            ("callnumber", "Call Number"),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label="Details",
                sections=(
                    FieldsSection(
                        (
                            ("lccontrolnumber", "LC Control Number"),
                            ("deweynumber", "Dewey Class Number"),
                            ("originality", "Originality"),
                            ("condition", "Condition"),
                            ("accession_number", "Accession Number"),
                            ("origin", "Origin"),
                            ("date_of_reform", "Reform Date"),
                            ("purchase_date", "Purchase Date"),
                            ("price", "Price"),
                            ("monetary_units", "Monetary Units"),
                            ("keyword", "Keywords"),
                        )
                    ),
                ),
            ),
        ),
        quantity="quantity",
        borrower_type="Book",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="dvd",
        label="DVD",
        label_plural="DVDs",
        table="dvd",
        title="title",
        creator="dvddirector",
        identifier="id",
        identifier_label="UPC",
        search_columns=("title", "id", "dvdactor", "dvddirector", "studio", "category", "keyword"),
        detail_fields=(
            ("dvdformat", "Format"),
            ("studio", "Studio"),
            ("rdate", "Release Date"),
            ("dvddiskcount", "Number of Discs"),
            ("dvdrunning", "Runtime"),
            ("category", "Categories"),
            ("language", "Language"),
            ("id", "UPC"),
            ("price", "Price"),
            ("monetary_units", "Monetary Units"),
            ("location", "Location"),
            ("dvdrating", "Rating"),
            ("dvdregion", "Region"),
            ("dvdaspectratio", "Aspect Ratio"),
            ("accession_number", "Accession Number"),
            ("dvddirector", "Director"),
            ("dvdactor", "Actors"),
            ("keyword", "Keywords"),
        ),
        text_fields=(("description", "Description"),),
        quantity="quantity",
        borrower_type="DVD",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="cd",
        label="Music CD",
        label_plural="Music CDs",
        table="cd",
        title="title",
        creator="artist",
        identifier="id",
        identifier_label="Catalogue Number",
        search_columns=("title", "artist", "id", "recording_label", "category"),
        detail_fields=(
            ("artist", "Artist"),
            ("cdformat", "Format"),
            ("recording_label", "Recording Label"),
            ("rdate", "Release Date"),
            ("cddiskcount", "Number of Discs"),
            ("cdruntime", "Runtime"),
            ("category", "Categories"),
            ("language", "Language"),
            ("id", "Catalogue Number"),
            ("price", "Price"),
            ("monetary_units", "Monetary Units"),
            ("location", "Location"),
            ("cdaudio", "Audio"),
            ("accession_number", "Accession Number"),
            ("keyword", "Keywords"),
        ),
        text_fields=(("description", "Description"),),
        quantity="quantity",
        borrower_type="CD",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="journal",
        label="Journal",
        label_plural="Journals",
        table="journal",
        title="title",
        creator="publisher",
        identifier="id",
        identifier_label="ISSN",
        search_columns=("title", "id", "publisher", "category", "keyword"),
        detail_fields=(
            ("publisher", "Publisher"),
            ("pdate", "Publication Date"),
            ("place", "Place of Publication"),
            ("issuevolume", "Volume"),
            ("issueno", "Issue"),
            ("category", "Categories"),
            ("lccontrolnumber", "LC Control Number"),
            ("language", "Language"),
            ("id", "ISSN"),
            ("price", "Price"),
            ("monetary_units", "Monetary Units"),
            ("location", "Location"),
            ("callnumber", "Call Number"),
            ("deweynumber", "Dewey Number"),
            ("accession_number", "Accession Number"),
            ("keyword", "Keywords"),
        ),
        text_fields=(("description", "Description"),),
        quantity="quantity",
        borrower_type="Journal",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="magazine",
        label="Magazine",
        label_plural="Magazines",
        table="magazine",
        title="title",
        creator="publisher",
        identifier="id",
        identifier_label="ISSN",
        search_columns=("title", "id", "publisher", "category", "keyword"),
        detail_fields=(
            ("publisher", "Publisher"),
            ("pdate", "Publication Date"),
            ("place", "Place of Publication"),
            ("issuevolume", "Volume"),
            ("issueno", "Issue"),
            ("category", "Categories"),
            ("language", "Language"),
            ("id", "ISSN"),
            ("price", "Price"),
            ("monetary_units", "Monetary Units"),
            ("location", "Location"),
            ("lccontrolnumber", "LC Control Number"),
            ("callnumber", "Call Number"),
            ("deweynumber", "Dewey Number"),
            ("accession_number", "Accession Number"),
            ("keyword", "Keywords"),
        ),
        text_fields=(("description", "Description"),),
        quantity="quantity",
        borrower_type="Magazine",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="videogame",
        label="Video Game",
        label_plural="Video Games",
        table="videogame",
        title="title",
        creator="publisher",
        identifier="id",
        identifier_label="UPC",
        search_columns=("title", "id", "publisher", "genre", "vgplatform", "keyword"),
        detail_fields=(
            ("vgrating", "Game Rating"),
            ("vgplatform", "Platform"),
            ("vgmode", "Mode"),
            ("publisher", "Publisher"),
            ("rdate", "Release Date"),
            ("place", "Place of Publication"),
            ("genre", "Genres"),
            ("language", "Language"),
            ("id", "UPC"),
            ("price", "Price"),
            ("monetary_units", "Monetary Units"),
            ("location", "Location"),
            ("accession_number", "Accession Number"),
            ("keyword", "Keywords"),
        ),
        text_fields=(("description", "Description"),),
        quantity="quantity",
        borrower_type="Video Game",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="greyliterature",
        label="Grey Literature",
        label_plural="Grey Literature",
        table="grey_literature",
        title="document_title",
        creator="author",
        identifier="document_id",
        identifier_label="Document ID",
        search_columns=("document_title", "author", "document_id", "client", "job_number", "notes"),
        detail_fields=(
            ("author", "Authors"),
            ("client", "Clients"),
            ("document_code_a", "Document code A"),
            ("document_code_b", "Document code B"),
            ("document_date", "Document Date"),
            ("document_id", "Document ID"),
            ("document_status", "Document Status"),
            ("document_type", "Document Type"),
            ("job_number", "Job Number"),
            ("location", "Location"),
            # File count (computed field)
        ),
        text_fields=(("notes", "Notes"),),
        front_cover="front_cover",
    ),
    ItemType(
        key="photograph",
        label="Photograph Collection",
        label_plural="Photograph Collections",
        table="photograph_collection",
        title="title",
        identifier="id",
        identifier_label="ID",
        search_columns=("title", "id", "accession_number", "about", "notes"),
        detail_fields=(
            ("id", "ID"),
            ("location", "Location"),
            # Photograph count (computed field)
            ("accession_number", "Accession Number"),
        ),
        text_fields=(("about", "About"), ("notes", "Notes")),
        front_cover="image_scaled",
    ),
)


def quote(name: str) -> str:
    """Quote a registry identifier for SQL; rejects anything that is not a plain name."""
    if not _IDENTIFIER.match(name):
        raise ValueError(f"invalid SQL identifier: {name!r}")
    return f'"{name}"'


def related_tables(spec: ItemType) -> Iterator[str]:
    """Names of tables, other than the item's own, that its tab sections read."""
    for tab in spec.tabs:
        for section in tab.sections:
            if isinstance(section, TableSection):
                yield section.table


def _resolve_section(
    section: SectionSpec, columns: set[str], tables: dict[str, set[str]]
) -> SectionSpec | None:
    if isinstance(section, FieldsSection):
        fields = tuple(f for f in section.fields if f[0] in columns)
        return replace(section, fields=fields) if fields else None
    if isinstance(section, TextSection):
        return section if section.column in columns else None
    available = tables.get(section.table, set())
    shown = tuple(c for c in section.columns if c[0] in available)
    if section.fk not in available or not shown:
        return None
    return replace(
        section,
        columns=shown,
        order_by=tuple(c for c in section.order_by if c in available),
        group_by=section.group_by if section.group_by in available else None,
    )


def resolve(
    spec: ItemType, columns: set[str], tables: dict[str, set[str]] | None = None
) -> ItemType | None:
    """Drop columns, sections and tabs the database cannot serve; None if the type is unusable.

    `tables` maps table name to column names, for sections that read related tables.
    """
    if spec.pk not in columns or spec.title not in columns:
        return None

    def keep(col: str | None) -> str | None:
        return col if col in columns else None

    declared = spec.tabs or (
        TabSpec(
            key="main",
            label="Main",
            sections=(
                *(TextSection(c, label) for c, label in spec.text_fields),
                FieldsSection(spec.detail_fields),
            ),
        ),
    )
    tabs = []
    for tab in declared:
        sections = tuple(
            s for s in (_resolve_section(s, columns, tables or {}) for s in tab.sections) if s
        )
        if sections:
            tabs.append(replace(tab, sections=sections))

    return replace(
        spec,
        creator=keep(spec.creator),
        identifier=keep(spec.identifier),
        search_columns=tuple(c for c in spec.search_columns if c in columns),
        detail_fields=tuple(f for f in spec.detail_fields if f[0] in columns),
        text_fields=tuple(f for f in spec.text_fields if f[0] in columns),
        tabs=tuple(tabs),
        quantity=keep(spec.quantity),
        front_cover=keep(spec.front_cover),
        back_cover=keep(spec.back_cover),
    )
