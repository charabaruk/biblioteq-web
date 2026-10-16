"""Registry of BiblioteQ item types.

This is the only place table and column names are defined. SQL is built from these
names (never from user input); values are always bound parameters. The `marc_tags`
column is deliberately absent (see ADR-0003).

To add a type, append an `ItemType` to `ITEM_TYPES`. Columns that do not exist in the
connected database are dropped at startup by `resolve()`, so differences between
BiblioteQ versions degrade gracefully.
"""

import re
from dataclasses import dataclass, replace

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class ItemType:
    key: str  # URL slug
    label: str  # singular display name
    table: str
    title: str
    creator: str | None = None
    identifier: str | None = None  # primary identifier shown on cards (ISBN, ISSN, ...)
    search_columns: tuple[str, ...] = ()
    detail_fields: tuple[tuple[str, str], ...] = ()  # (column, label)
    quantity: str | None = None
    borrower_type: str | None = None  # value of item_borrower.type for this table
    front_cover: str | None = None
    back_cover: str | None = None
    pk: str = "myoid"


ITEM_TYPES: tuple[ItemType, ...] = (
    ItemType(
        key="book",
        label="Book",
        table="book",
        title="title",
        creator="author",
        identifier="isbn13",
        search_columns=("title", "author", "id", "isbn13", "publisher", "category", "keyword"),
        detail_fields=(
            ("author", "Author"),
            ("publisher", "Publisher"),
            ("pdate", "Publication date"),
            ("place", "Place"),
            ("edition", "Edition"),
            ("id", "ISBN-10"),
            ("isbn13", "ISBN-13"),
            ("lccontrolnumber", "LC control number"),
            ("callnumber", "Call number"),
            ("deweynumber", "Dewey number"),
            ("category", "Category"),
            ("language", "Language"),
            ("binding_type", "Binding"),
            ("location", "Location"),
            ("keyword", "Keywords"),
            ("description", "Description"),
        ),
        quantity="quantity",
        borrower_type="Book",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="dvd",
        label="DVD",
        table="dvd",
        title="title",
        creator="dvddirector",
        identifier="id",
        search_columns=("title", "id", "dvdactor", "dvddirector", "studio", "category"),
        detail_fields=(
            ("dvddirector", "Director"),
            ("dvdactor", "Actors"),
            ("studio", "Studio"),
            ("rdate", "Release date"),
            ("dvdformat", "Format"),
            ("dvdrunning", "Running time"),
            ("dvdrating", "Rating"),
            ("dvdregion", "Region"),
            ("category", "Category"),
            ("language", "Language"),
            ("location", "Location"),
            ("description", "Description"),
        ),
        quantity="quantity",
        borrower_type="DVD",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="cd",
        label="Music CD",
        table="cd",
        title="title",
        creator="artist",
        identifier="id",
        search_columns=("title", "artist", "id", "recording_label", "category"),
        detail_fields=(
            ("artist", "Artist"),
            ("recording_label", "Label"),
            ("rdate", "Release date"),
            ("cdformat", "Format"),
            ("cddiskcount", "Discs"),
            ("cdruntime", "Running time"),
            ("category", "Category"),
            ("language", "Language"),
            ("location", "Location"),
            ("description", "Description"),
        ),
        quantity="quantity",
        borrower_type="CD",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="journal",
        label="Journal",
        table="journal",
        title="title",
        creator="publisher",
        identifier="id",
        search_columns=("title", "id", "publisher", "category", "keyword"),
        detail_fields=(
            ("publisher", "Publisher"),
            ("pdate", "Publication date"),
            ("place", "Place"),
            ("issuevolume", "Volume"),
            ("issueno", "Issue"),
            ("lccontrolnumber", "LC control number"),
            ("category", "Category"),
            ("language", "Language"),
            ("location", "Location"),
            ("description", "Description"),
        ),
        quantity="quantity",
        borrower_type="Journal",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="magazine",
        label="Magazine",
        table="magazine",
        title="title",
        creator="publisher",
        identifier="id",
        search_columns=("title", "id", "publisher", "category", "keyword"),
        detail_fields=(
            ("publisher", "Publisher"),
            ("pdate", "Publication date"),
            ("place", "Place"),
            ("issuevolume", "Volume"),
            ("issueno", "Issue"),
            ("lccontrolnumber", "LC control number"),
            ("category", "Category"),
            ("language", "Language"),
            ("location", "Location"),
            ("description", "Description"),
        ),
        quantity="quantity",
        borrower_type="Magazine",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="videogame",
        label="Video game",
        table="videogame",
        title="title",
        creator="publisher",
        identifier="id",
        search_columns=("title", "id", "publisher", "genre", "vgplatform"),
        detail_fields=(
            ("publisher", "Publisher"),
            ("rdate", "Release date"),
            ("vgplatform", "Platform"),
            ("genre", "Genre"),
            ("vgrating", "Rating"),
            ("vgmode", "Mode"),
            ("language", "Language"),
            ("location", "Location"),
            ("description", "Description"),
        ),
        quantity="quantity",
        borrower_type="Video Game",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="greyliterature",
        label="Grey literature",
        table="grey_literature",
        title="document_title",
        creator="author",
        identifier="document_id",
        search_columns=("document_title", "author", "document_id", "client", "job_number"),
        detail_fields=(
            ("author", "Author"),
            ("client", "Client"),
            ("document_date", "Document date"),
            ("document_type", "Document type"),
            ("document_status", "Status"),
            ("job_number", "Job number"),
            ("location", "Location"),
            ("notes", "Notes"),
        ),
    ),
    ItemType(
        key="photograph",
        label="Photograph collection",
        table="photograph_collection",
        title="title",
        creator="creators",
        identifier="id",
        search_columns=("title", "id", "creators", "about"),
        detail_fields=(
            ("creators", "Creators"),
            ("pdate", "Date"),
            ("location", "Location"),
            ("about", "About"),
            ("notes", "Notes"),
        ),
        front_cover="image_scaled",
    ),
)

def quote(name: str) -> str:
    """Quote a registry identifier for SQL; rejects anything that is not a plain name."""
    if not _IDENTIFIER.match(name):
        raise ValueError(f"invalid SQL identifier: {name!r}")
    return f'"{name}"'


def resolve(spec: ItemType, columns: set[str]) -> ItemType | None:
    """Drop columns missing from the database; None if the type is unusable."""
    if spec.pk not in columns or spec.title not in columns:
        return None

    def keep(col: str | None) -> str | None:
        return col if col in columns else None

    return replace(
        spec,
        creator=keep(spec.creator),
        identifier=keep(spec.identifier),
        search_columns=tuple(c for c in spec.search_columns if c in columns),
        detail_fields=tuple(f for f in spec.detail_fields if f[0] in columns),
        quantity=keep(spec.quantity),
        front_cover=keep(spec.front_cover),
        back_cover=keep(spec.back_cover),
    )
