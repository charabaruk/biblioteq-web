"""Registry of BiblioteQ item types.

This is the only place table and column names are defined. SQL is built from these
names (never from user input); values are always bound parameters. The `marc_tags`
column is deliberately absent (see ADR-0003).

To add a type, append an `ItemType` to `ITEM_TYPES`. Columns that do not exist in the
connected database are dropped at startup by `resolve()`, so differences between
BiblioteQ versions degrade gracefully.
"""

import gettext
import re
from collections.abc import Iterator
from dataclasses import dataclass, fields, is_dataclass, replace
from typing import TypeVar

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Message:
    msgid: str
    context: str | None = None


def _(msgid: str) -> Message:
    return Message(msgid)


def pgettext(context: str, msgid: str) -> Message:
    return Message(msgid, context)


DisplayText = str | Message
T = TypeVar("T")


def localize_labels(value: T, translations: gettext.NullTranslations) -> T:
    if isinstance(value, Message):
        if value.context is None:
            return translations.gettext(value.msgid)  # type: ignore[return-value]
        return translations.pgettext(value.context, value.msgid)  # type: ignore[return-value]
    if isinstance(value, tuple):
        return tuple(localize_labels(item, translations) for item in value)  # type: ignore[return-value]
    if is_dataclass(value) and not isinstance(value, type):
        localized = {
            field.name: localize_labels(getattr(value, field.name), translations)
            for field in fields(value)
        }
        return replace(value, **localized)
    return value


@dataclass(frozen=True)
class FieldsSection:
    """Short label/value pairs from the item's own table, rendered as a definition list."""

    fields: tuple[tuple[str, DisplayText], ...]  # (column, label)


@dataclass(frozen=True)
class TextSection:
    """One prose column from the item's own table."""

    column: str
    label: DisplayText | None


@dataclass(frozen=True)
class TableSection:
    """Rows of a related table whose `fk` column holds the item's primary key."""

    label: DisplayText | None
    table: str
    fk: str
    columns: tuple[tuple[str, DisplayText], ...]  # (column, header)
    order_by: tuple[str, ...] = ()  # must start with group_by when grouping
    group_by: str | None = None
    group_label: DisplayText = ""  # prefix for group headings, e.g. "Disc"
    limit: int = 500


SectionSpec = FieldsSection | TextSection | TableSection


@dataclass(frozen=True)
class TabSpec:
    key: str  # used in URLs and fragments
    label: DisplayText
    sections: tuple[SectionSpec, ...]
    lazy: bool = False  # content is fetched on demand, not rendered with the item page
    template: str | None = None  # optional template overriding the default tab body


@dataclass(frozen=True)
class ItemType:
    key: str  # URL slug
    label: DisplayText  # singular display name
    label_plural: DisplayText  # plural display name
    table: str
    title: str
    creator: str | None = None
    identifier: str | None = None  # primary identifier shown on cards (ISBN, ISSN, ...)
    identifier_label: DisplayText | None = None  # display label for primary identifier
    search_columns: tuple[str, ...] = ()
    detail_fields: tuple[tuple[str, DisplayText], ...] = ()  # (column, label)
    text_fields: tuple[tuple[str, DisplayText], ...] = ()  # prose fields
    tabs: tuple[TabSpec, ...] = ()  # empty: a Main tab is built from the fields above
    quantity: str | None = None
    borrower_type: str | None = None  # value of item_borrower.type for this table
    front_cover: str | None = None
    back_cover: str | None = None
    pk: str = "myoid"


ITEM_TYPES: tuple[ItemType, ...] = (
    ItemType(
        key="book",
        label=pgettext("item-type", "Book"),
        label_plural=pgettext("item-type", "Books"),
        table="book",
        title="title",
        creator="author",
        identifier="isbn13",
        identifier_label=_("ISBN-13"),
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
                label=pgettext("tab-book", "Main"),
                sections=(
                    TextSection("description", _("Description")),
                    FieldsSection(
                        (
                            ("series_title", _("Series Title")),
                            ("volume_number", _("Volume Number")),
                            ("author", _("Authors")),
                            ("publisher", _("Publisher")),
                            ("pdate", _("Publication Date")),
                            ("place", _("Place of Publication")),
                            ("edition", _("Edition")),
                            ("category", _("Categories")),
                            ("language", _("Language")),
                            ("target_audience", _("Target Audience")),
                            ("id", _("ISBN-10")),
                            ("isbn13", _("ISBN-13")),
                            ("binding_type", _("Book Binding Type")),
                            ("location", _("Location")),
                            ("callnumber", _("Call Number")),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-book", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("lccontrolnumber", _("LC Control Number")),
                            ("deweynumber", _("Dewey Class Number")),
                            ("originality", _("Originality")),
                            ("condition", _("Condition")),
                            ("accession_number", _("Accession Number")),
                            ("origin", _("Origin")),
                            ("date_of_reform", _("Reform Date")),
                            ("purchase_date", _("Purchase Date")),
                            ("price", _("Price")),
                            ("monetary_units", _("Monetary Units")),
                            ("keyword", _("Keywords")),
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
        label=pgettext("item-type", "DVD"),
        label_plural=pgettext("item-type", "DVDs"),
        table="dvd",
        title="title",
        creator="dvddirector",
        identifier="id",
        identifier_label=_("UPC"),
        search_columns=("title", "id", "dvdactor", "dvddirector", "studio", "category", "keyword"),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-dvd", "Main"),
                sections=(
                    TextSection("description", _("Description")),
                    FieldsSection(
                        (
                            ("dvdformat", _("Format")),
                            ("studio", _("Studio")),
                            ("rdate", _("Release Date")),
                            ("dvddiskcount", _("Number of Discs")),
                            ("dvdrunning", _("Runtime")),
                            ("category", _("Categories")),
                            ("language", _("Language")),
                            ("location", _("Location")),
                            ("dvdrating", _("Rating")),
                            ("dvdregion", _("Region")),
                            ("dvdaspectratio", _("Aspect Ratio")),
                            ("dvddirector", _("Director")),
                            ("dvdactor", _("Actors")),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-dvd", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("id", _("UPC")),
                            ("price", _("Price")),
                            ("monetary_units", _("Monetary Units")),
                            ("accession_number", _("Accession Number")),
                            ("keyword", _("Keywords")),
                        )
                    ),
                ),
            ),
        ),
        quantity="quantity",
        borrower_type="DVD",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="cd",
        label=pgettext("item-type", "Music CD"),
        label_plural=pgettext("item-type", "Music CDs"),
        table="cd",
        title="title",
        creator="artist",
        identifier="id",
        identifier_label=_("Catalogue Number"),
        search_columns=("title", "artist", "id", "recording_label", "category"),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-cd", "Main"),
                sections=(
                    TextSection("description", _("Description")),
                    TableSection(
                        label=_("Track Listing"),
                        table="cd_songs",
                        fk="item_oid",
                        columns=(
                            ("songnum", "#"),
                            ("songtitle", _("Title")),
                            ("runtime", _("Length")),
                            ("composer", _("Composer")),
                        ),
                        order_by=("albumnum", "songnum"),
                        group_by="albumnum",
                        group_label=_("Disc"),
                    ),
                    FieldsSection(
                        (
                            ("artist", _("Artist")),
                            ("cdformat", _("Format")),
                            ("recording_label", _("Recording Label")),
                            ("rdate", _("Release Date")),
                            ("cddiskcount", _("Number of Discs")),
                            ("cdruntime", _("Runtime")),
                            ("category", _("Categories")),
                            ("language", _("Language")),
                            ("id", _("Catalogue Number")),
                            ("location", _("Location")),
                            ("cdaudio", _("Audio")),
                        ),
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-cd", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("price", _("Price")),
                            ("monetary_units", _("Monetary Units")),
                            ("accession_number", _("Accession Number")),
                            ("keyword", _("Keywords")),
                        )
                    ),
                ),
            ),
        ),
        quantity="quantity",
        borrower_type="CD",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="journal",
        label=pgettext("item-type", "Journal"),
        label_plural=pgettext("item-type", "Journals"),
        table="journal",
        title="title",
        creator="publisher",
        identifier="id",
        identifier_label=_("ISSN"),
        search_columns=("title", "id", "publisher", "category", "keyword"),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-journal", "Main"),
                sections=(
                    TextSection("description", _("Description")),
                    FieldsSection(
                        (
                            ("publisher", _("Publisher")),
                            ("pdate", _("Publication Date")),
                            ("place", _("Place of Publication")),
                            ("display_number", _("Issue Number")),
                            ("issuevolume", _("Volume")),
                            ("issueno", _("Issue")),
                            ("category", _("Categories")),
                            ("language", _("Language")),
                            ("id", _("ISSN")),
                            ("location", _("Location")),
                            ("callnumber", _("Call Number")),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-journal", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("lccontrolnumber", _("LC Control Number")),
                            ("price", _("Price")),
                            ("monetary_units", _("Monetary Units")),
                            ("deweynumber", _("Dewey Number")),
                            ("accession_number", _("Accession Number")),
                            ("keyword", _("Keywords")),
                        )
                    ),
                ),
            ),
        ),
        quantity="quantity",
        borrower_type="Journal",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="magazine",
        label=pgettext("item-type", "Magazine"),
        label_plural=pgettext("item-type", "Magazines"),
        table="magazine",
        title="title",
        creator="publisher",
        identifier="id",
        identifier_label=_("ISSN"),
        search_columns=("title", "id", "publisher", "category", "keyword"),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-magazine", "Main"),
                sections=(
                    TextSection("description", _("Description")),
                    FieldsSection(
                        (
                            ("publisher", _("Publisher")),
                            ("pdate", _("Publication Date")),
                            ("place", _("Place of Publication")),
                            ("display_number", _("Issue Number")),
                            ("issuevolume", _("Volume")),
                            ("issueno", _("Issue")),
                            ("category", _("Categories")),
                            ("language", _("Language")),
                            ("id", _("ISSN")),
                            ("location", _("Location")),
                            ("callnumber", _("Call Number")),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-magazine", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("price", _("Price")),
                            ("monetary_units", _("Monetary Units")),
                            ("lccontrolnumber", _("LC Control Number")),
                            ("deweynumber", _("Dewey Number")),
                            ("accession_number", _("Accession Number")),
                            ("keyword", _("Keywords")),
                        )
                    ),
                ),
            ),
        ),
        quantity="quantity",
        borrower_type="Magazine",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="videogame",
        label=pgettext("item-type", "Video Game"),
        label_plural=pgettext("item-type", "Video Games"),
        table="videogame",
        title="title",
        creator="publisher",
        identifier="id",
        identifier_label=_("UPC"),
        search_columns=("title", "id", "publisher", "genre", "vgplatform", "keyword"),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-videogame", "Main"),
                sections=(
                    TextSection("description", _("Description")),
                    FieldsSection(
                        (
                            ("vgrating", _("Game Rating")),
                            ("vgplatform", _("Platform")),
                            ("vgmode", _("Mode")),
                            ("publisher", _("Publisher")),
                            ("rdate", _("Release Date")),
                            ("place", _("Place of Publication")),
                            ("genre", _("Genres")),
                            ("language", _("Language")),
                            ("location", _("Location")),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-videogame", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("id", _("UPC")),
                            ("price", _("Price")),
                            ("monetary_units", _("Monetary Units")),
                            ("accession_number", _("Accession Number")),
                            ("keyword", _("Keywords")),
                        )
                    ),
                ),
            ),
        ),
        quantity="quantity",
        borrower_type="Video Game",
        front_cover="front_cover",
        back_cover="back_cover",
    ),
    ItemType(
        key="greyliterature",
        label=pgettext("item-type", "Grey Literature"),
        label_plural=pgettext("item-type", "Grey Literature"),
        table="grey_literature",
        title="document_title",
        creator="author",
        identifier="document_id",
        identifier_label=_("Document ID"),
        search_columns=("document_title", "author", "document_id", "client", "job_number", "notes"),
        detail_fields=(),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-greyliterature", "Main"),
                sections=(
                    FieldsSection(
                        (
                            ("author", _("Authors")),
                            ("client", _("Clients")),
                            ("document_date", _("Document Date")),
                            ("document_id", _("Document ID")),
                            ("document_type", _("Document Type")),
                            ("job_number", _("Job Number")),
                            ("location", _("Location")),
                            # File count (computed field)
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-greyliterature", "Details"),
                sections=(
                    FieldsSection(
                        (
                            ("document_code_a", _("Document code A")),
                            ("document_code_b", _("Document code B")),
                            ("document_status", _("Document Status")),
                        )
                    ),
                ),
            ),
            TabSpec(
                key="notes",
                label=pgettext("tab-greyliterature", "Notes"),
                sections=(TextSection("notes", None),),
            ),
        ),
        front_cover="front_cover",
    ),
    ItemType(
        key="photograph",
        label=pgettext("item-type", "Photograph Collection"),
        label_plural=pgettext("item-type", "Photograph Collections"),
        table="photograph_collection",
        title="title",
        identifier="id",
        identifier_label=_("ID"),
        search_columns=("title", "id", "accession_number", "about", "notes"),
        detail_fields=(),
        text_fields=(("about", _("About")), ("notes", _("Notes"))),
        tabs=(
            TabSpec(
                key="main",
                label=pgettext("tab-photograph", "Main"),
                sections=(
                    TextSection("about", _("About")),
                    FieldsSection(
                        (
                            ("id", _("ID")),
                            ("location", _("Location")),
                            # Photograph count (computed field)
                        )
                    ),
                ),
            ),
            TabSpec(
                key="details",
                label=pgettext("tab-photograph", "Details"),
                sections=(FieldsSection((("accession_number", _("Accession Number")),)),),
            ),
            TabSpec(
                key="notes",
                label=pgettext("tab-photograph", "Notes"),
                sections=(TextSection("notes", None),),
            ),
        ),
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
            label=pgettext("tab-default", "Main"),
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
