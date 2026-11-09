"""Read-only queries. Identifiers come from the item type registry; values are bound."""

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from functools import cmp_to_key
from urllib.parse import quote as url_quote
from urllib.parse import urlencode

from natsort import natsort_keygen, ns
from sqlalchemy import Connection, text

from app.item_titles import PUBLICATION_DATE_FORMATS, TitleValues, normalize_issue
from app.item_types import (
    ITEM_TYPES,
    FieldsSection,
    ItemType,
    TableSection,
    TabSpec,
    TextSection,
    quote,
    related_tables,
    resolve,
)

log = logging.getLogger(__name__)

MAX_TERMS = 8
MAX_QUERY_LENGTH = 200
UNKNOWN_LOCATION = "UNKNOWN"  # BiblioteQ's stand-in for no location


@dataclass(frozen=True)
class Catalog:
    types: dict[str, ItemType]
    has_borrowers: bool
    has_locations: bool = False


@dataclass(frozen=True)
class Page:
    items: list[dict]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


@dataclass(frozen=True)
class Availability:
    total: int
    borrowed: int | None  # None when borrower data cannot be counted

    @property
    def available(self) -> int | None:
        if self.borrowed is None:
            return None
        return max(self.total - self.borrowed, 0)


@dataclass
class Section:
    kind: str  # "fields", "text" or "table"; selects the sections/ partial
    label: str
    fields: list[tuple[str, str, str | None]] = field(default_factory=list)  # label, value, URL
    text: str = ""
    headers: list[str] = field(default_factory=list)
    # Table cells are (value, URL).
    groups: list[tuple[str | None, list[list[tuple[str, str | None]]]]] = field(
        default_factory=list
    )


@dataclass
class Tab:
    key: str
    label: str
    template: str | None
    sections: list[Section]


@dataclass
class Item:
    spec: ItemType
    id: int
    title: str
    tabs: list[Tab] = field(default_factory=list)
    has_front: bool = False
    has_back: bool = False
    availability: Availability | None = None
    title_values: TitleValues = field(default_factory=TitleValues)


def _columns_by_table(conn: Connection, schema: str) -> dict[str, set[str]]:
    columns: dict[str, set[str]] = {}
    if conn.dialect.name == "sqlite":
        # SQLite has no schemas; only the tables the app can use are inspected.
        for table in (
            [s.table for s in ITEM_TYPES]
            + [t for s in ITEM_TYPES for t in related_tables(s)]
            + ["item_borrower", "locations"]
        ):
            names = conn.execute(
                text("SELECT name FROM pragma_table_info(:table)"), {"table": table}
            ).scalars()
            found = set(names)
            if found:
                columns[table] = found
        return columns
    # information_schema only lists columns the role has privileges on.
    rows = conn.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = :schema"
        ),
        {"schema": schema},
    ).all()
    for table, column in rows:
        columns.setdefault(table, set()).add(column)
    return columns


def load_catalog(conn: Connection, schema: str) -> Catalog:
    """Inspect the database and keep only the item types it can serve."""
    columns = _columns_by_table(conn, schema)

    types: dict[str, ItemType] = {}
    for spec in ITEM_TYPES:
        resolved = resolve(spec, columns.get(spec.table, set()), columns)
        if resolved is None:
            log.warning("Item type %r disabled: %r missing or incomplete", spec.key, spec.table)
            continue
        types[spec.key] = resolved
    conn.rollback()
    return Catalog(
        types=types,
        has_borrowers="item_borrower" in columns,
        has_locations={"location", "type"} <= columns.get("locations", set()),
    )


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def parse_terms(query: str) -> list[str]:
    return [t for t in re.split(r"\s+", query.strip()[:MAX_QUERY_LENGTH]) if t][:MAX_TERMS]


def _text(column: str | None) -> str:
    return f"CAST({quote(column)} AS TEXT)" if column else "CAST(NULL AS TEXT)"


def _flag(column: str | None) -> str:
    # 1/0 rather than booleans: SQLite has no boolean type and UNION needs matching types.
    if not column:
        return "0"
    return f"CASE WHEN {quote(column)} IS NOT NULL THEN 1 ELSE 0 END"


def _location_clause(spec: ItemType, location: str) -> str:
    # A type without a location column cannot match any location.
    if not spec.location:
        return "0 = 1"
    column = f"{quote(spec.table)}.{quote(spec.location)}"
    if location == UNKNOWN_LOCATION:
        return f"({column} IS NULL OR {column} = :loc)"
    copies = spec.copy_location()
    if copies is None:
        return f"{column} = :loc"
    # A copy at UNKNOWN inherits its item's location, so only named copy locations match here.
    table = quote(copies.table)
    return (
        f"({column} = :loc OR EXISTS (SELECT 1 FROM {table} "
        f"WHERE {table}.{quote(copies.fk)} = {quote(spec.table)}.{quote(spec.pk)} "
        f"AND {table}.{quote('location')} = :loc))"
    )


def _where_sql(spec: ItemType, n_terms: int, location: str | None = None) -> str:
    # Every term must match at least one searchable column.
    cols = spec.search_columns or (spec.title,)
    clauses = [
        "(" + " OR ".join(f"lower({_text(c)}) LIKE lower(:t{i}) ESCAPE '\\'" for c in cols) + ")"
        for i in range(n_terms)
    ]
    if location is not None:
        clauses.append(_location_clause(spec, location))
    return " WHERE " + " AND ".join(clauses) if clauses else ""


def _select_sql(spec: ItemType, n_terms: int, location: str | None = None) -> str:
    return (
        f"SELECT '{spec.key}' AS type, {quote(spec.pk)} AS id, {_text(spec.title)} AS title, "
        f"{_text(spec.creator)} AS creator, {_text(spec.identifier)} AS identifier, "
        f"{_text(spec.issue[0] if spec.issue else None)} AS issue_display, "
        f"{_text(spec.issue[1] if spec.issue else None)} AS issue_volume, "
        f"{_text(spec.issue[2] if spec.issue else None)} AS issue_number, "
        f"{_flag(spec.front_cover)} AS has_cover "
        f"FROM {quote(spec.table)}" + _where_sql(spec, n_terms, location)
    )


def _card(row: Mapping[str, object]) -> dict:
    """A card row with the issue numbers normalised (ADR-0013)."""
    card = dict(row)
    card["issue_display"], card["issue_volume"], card["issue_number"] = normalize_issue(
        card["issue_display"], card["issue_volume"], card["issue_number"]
    )
    return card


def _keys_sql(
    spec: ItemType,
    n_terms: int,
    location: str | None = None,
    sort_columns: tuple[str, ...] = (),
) -> str:
    sort_keys = ""
    if sort_columns:
        sort_keys = ", lower(" + _text(spec.title) + ") AS title_order, " + ", ".join(
            f"{_text(column)} AS sort_{index}" for index, column in enumerate(sort_columns)
        )
    return (
        f"SELECT '{spec.key}' AS type, {quote(spec.pk)} AS id, {_text(spec.title)} AS title"
        f"{sort_keys} "
        f"FROM {quote(spec.table)}" + _where_sql(spec, n_terms, location)
    )


def title_sort_key(numbers: str):
    """Natural, case-insensitive sort key; digit runs are integers or decimals."""
    keygen = natsort_keygen(alg=ns.IGNORECASE | (ns.FLOAT if numbers == "decimal" else ns.INT))
    return lambda title: keygen(title or "")


def _periodical_sort_columns(spec: ItemType) -> tuple[str, ...]:
    if not spec.issue:
        return ()
    display_number, volume, issue_number = spec.issue
    return tuple(
        column for column in (volume, issue_number, display_number, spec.published) if column
    )


def _periodical_sort_value(column: str, value: str | None, spec: ItemType):
    if value is None:
        return None
    if column == spec.published:
        for date_format in PUBLICATION_DATE_FORMATS:
            try:
                return ("date", datetime.strptime(value, date_format))
            except ValueError:
                continue
        return ("text", value.casefold())
    return int(value)


def _compare_periodical_values(left, right, direction: str, nulls_first: bool) -> int:
    if left is None or right is None:
        if left is None and right is None:
            return 0
        if left is None:
            return -1 if nulls_first else 1
        return 1 if nulls_first else -1
    comparison = (left > right) - (left < right)
    return comparison if direction == "asc" else -comparison


def _periodical_nulls_first(
    conn: Connection,
    spec: ItemType,
    terms: list[str],
    params: dict[str, object],
    location: str | None,
    column: str,
    direction: str,
) -> bool:
    sql = (
        f"SELECT {quote(column)} FROM {quote(spec.table)}"
        + _where_sql(spec, len(terms), location)
        + f" ORDER BY {quote(column)} {direction.upper()} LIMIT 1"
    )
    return conn.execute(text(sql), params).scalar() is None


def _natural_page(
    conn: Connection,
    specs: list[ItemType],
    terms: list[str],
    params: dict[str, object],
    page: int,
    page_size: int,
    numbers: str | None,
    location: str | None = None,
    issue_direction: str | None = None,
    sort_columns: tuple[str, ...] = (),
) -> Page:
    # Sorting happens here because the database has no portable natural collation.
    union = " UNION ALL ".join(
        _keys_sql(s, len(terms), location, sort_columns if issue_direction else ())
        for s in specs
    )
    title_key = title_sort_key(numbers) if numbers else lambda title: (title or "").lower()
    rows = conn.execute(text(union), params).all()
    if issue_direction:
        spec = specs[0]
        nulls_first = {}
        for index, column in enumerate(sort_columns):
            values = [row._mapping[f"sort_{index}"] for row in rows]
            if any(value is None for value in values) and any(
                value is not None for value in values
            ):
                nulls_first[index] = _periodical_nulls_first(
                    conn, spec, terms, params, location, column, issue_direction
                )
            else:
                nulls_first[index] = False

        def compare_rows(left, right):
            left_title_key = (
                left._mapping["title_order"] if numbers is None else title_key(left.title)
            )
            right_title_key = (
                right._mapping["title_order"] if numbers is None else title_key(right.title)
            )
            title_comparison = (left_title_key > right_title_key) - (
                left_title_key < right_title_key
            )
            if title_comparison:
                return title_comparison
            for index, column in enumerate(sort_columns):
                left_value = _periodical_sort_value(
                    column, left._mapping[f"sort_{index}"], spec
                )
                right_value = _periodical_sort_value(
                    column, right._mapping[f"sort_{index}"], spec
                )
                comparison = _compare_periodical_values(
                    left_value, right_value, issue_direction, nulls_first[index]
                )
                if comparison:
                    return comparison
            return (left.id > right.id) - (left.id < right.id)

        keys = sorted(rows, key=cmp_to_key(compare_rows))
    else:
        keys = sorted(rows, key=lambda row: (title_key(row.title), row.type, row.id))
    total = len(keys)
    page = max(1, min(page, max(1, -(-total // page_size))))
    window = keys[(page - 1) * page_size : page * page_size]

    by_type: dict[str, list[int]] = {}
    for row in window:
        by_type.setdefault(row.type, []).append(row.id)
    found: dict[tuple[str, int], dict] = {}
    for spec in specs:
        ids = by_type.get(spec.key)
        if not ids:
            continue
        marks = ", ".join(f":i{n}" for n in range(len(ids)))
        sql = f"{_select_sql(spec, 0)} WHERE {quote(spec.pk)} IN ({marks})"
        rows = conn.execute(text(sql), {f"i{n}": v for n, v in enumerate(ids)}).mappings()
        found.update({(r["type"], r["id"]): _card(r) for r in rows})
    conn.rollback()
    items = [found[(r.type, r.id)] for r in window if (r.type, r.id) in found]
    return Page(items, total, page, page_size)


def search(
    conn: Connection,
    catalog: Catalog,
    query: str,
    type_keys: list[str],
    page: int,
    page_size: int,
    natural: str | None = None,
    location: str | None = None,
    issue_direction: str | None = None,
) -> Page:
    """Search the given types (all available if empty). An empty query lists everything.

    `natural` is "integer" or "decimal" to order titles naturally in Python;
    None orders in SQL by lowercased title. `location` keeps items at exactly that
    location; "UNKNOWN" also keeps items with none. `issue_direction` enables the
    registered issue ordering for a periodical browse page.
    """
    specs = [catalog.types[k] for k in type_keys if k in catalog.types] or list(
        catalog.types.values()
    )
    if not specs:
        return Page([], 0, 1, page_size)
    terms = parse_terms(query)
    params: dict[str, object] = {f"t{i}": _like_pattern(t) for i, t in enumerate(terms)}
    if location is not None:
        params["loc"] = location
    if issue_direction is not None and issue_direction not in ("asc", "desc"):
        raise ValueError("issue_direction must be 'asc' or 'desc'")
    sort_columns = _periodical_sort_columns(specs[0]) if len(specs) == 1 else ()
    if issue_direction and sort_columns:
        return _natural_page(
            conn,
            specs,
            terms,
            params,
            page,
            page_size,
            natural,
            location,
            issue_direction,
            sort_columns,
        )
    if natural:
        return _natural_page(conn, specs, terms, params, page, page_size, natural, location)
    union = " UNION ALL ".join(_select_sql(s, len(terms), location) for s in specs)

    total = conn.execute(text(f"SELECT count(*) FROM ({union}) u"), params).scalar_one()
    page = max(1, min(page, max(1, -(-total // page_size))))
    rows = conn.execute(
        text(
            f"SELECT * FROM ({union}) u ORDER BY lower(title), type, id LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    ).mappings()
    items = [_card(r) for r in rows]
    conn.rollback()
    return Page(items, total, page, page_size)


def recent(conn: Connection, spec: ItemType, limit: int, location: str | None = None) -> list[dict]:
    """Most recently added rows of one type (highest primary key first)."""
    params: dict[str, object] = {"limit": limit}
    if location is not None:
        params["loc"] = location
    rows = conn.execute(
        text(f"{_select_sql(spec, 0, location)} ORDER BY {quote(spec.pk)} DESC LIMIT :limit"),
        params,
    ).mappings()
    items = [_card(r) for r in rows]
    conn.rollback()
    return items


def _registered_specs(catalog: Catalog) -> list[ItemType]:
    return [s for s in catalog.types.values() if s.location and s.location_type]


def location_options(conn: Connection, catalog: Catalog) -> list[str]:
    """Distinct locations registered for any type the catalog serves, for the filter list."""
    specs = _registered_specs(catalog)
    if not catalog.has_locations or not specs:
        return []
    marks = ", ".join(f":t{n}" for n in range(len(specs)))
    names = conn.execute(
        text(f"SELECT DISTINCT location FROM locations WHERE type IN ({marks})"),
        {f"t{n}": s.location_type for n, s in enumerate(specs)},
    ).scalars()
    options = list(names)
    conn.rollback()
    return sorted(options, key=lambda name: (name.casefold(), name))


def location_types(conn: Connection, catalog: Catalog, name: str) -> list[ItemType]:
    """Catalog types registered for exactly this location, in registry order."""
    if not catalog.has_locations:
        return []
    registered = set(
        conn.execute(
            text("SELECT type FROM locations WHERE location = :name"), {"name": name}
        ).scalars()
    )
    conn.rollback()
    return [s for s in _registered_specs(catalog) if s.location_type in registered]


def location_registered(conn: Connection, catalog: Catalog, spec: ItemType, name: str) -> bool:
    """Whether `locations` lists exactly this name for the item's own type."""
    if not catalog.has_locations or not spec.location_type:
        return False
    found = conn.execute(
        text("SELECT 1 FROM locations WHERE location = :name AND type = :type"),
        {"name": name, "type": spec.location_type},
    ).first()
    conn.rollback()
    return found is not None


def types_without_location(conn: Connection, catalog: Catalog) -> list[ItemType]:
    """Catalog types with at least one item that has no location (NULL or UNKNOWN)."""
    found = []
    for spec in catalog.types.values():
        if not spec.location:
            continue
        sql = f"SELECT 1 FROM {quote(spec.table)} WHERE {_location_clause(spec, UNKNOWN_LOCATION)}"
        if conn.execute(text(sql + " LIMIT 1"), {"loc": UNKNOWN_LOCATION}).first():
            found.append(spec)
    conn.rollback()
    return found


def _clean(value: object | None) -> str:
    return str(value).strip() if value is not None else ""


def _own_value(value: object | None) -> str:
    # "N/A" is a placeholder in BiblioteQ data, not content.
    cleaned = _clean(value)
    return "" if cleaned == "N/A" else cleaned


def _location_value(value: object | None) -> str:
    # Kept as stored: locations compare exactly, so the link must carry the same string.
    raw = "" if value is None else str(value)
    return "" if raw == UNKNOWN_LOCATION or not raw.strip() else raw


def _table_value(section: TableSection, column: str, value: object | None) -> str:
    if (
        section.table.endswith("_copy_info")
        and column in {"status", "condition", "originality"}
        and value == "UNKNOWN"
    ):
        return ""
    return _clean(value)


def _own_values(conn: Connection, spec: ItemType, tab: TabSpec, item_id: int) -> dict[str, str]:
    """Values of every column the tab's own-table sections read, in one query."""
    names: list[str] = []
    for section in tab.sections:
        if isinstance(section, FieldsSection):
            names += [c for c, _ in section.fields]
        elif isinstance(section, TextSection):
            names.append(section.column)
    names = list(dict.fromkeys(names))
    if not names:
        return {}
    cols = ", ".join(f"{_text(c)} AS c{i}" for i, c in enumerate(names))
    row = (
        conn.execute(
            text(f"SELECT {cols} FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"),
            {"id": item_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        return {}
    return {
        c: (_location_value if c == spec.location else _own_value)(row[f"c{i}"])
        for i, c in enumerate(names)
    }


def _item_location(conn: Connection, spec: ItemType, item_id: int) -> str:
    if not spec.location:
        return ""
    value = conn.execute(
        text(
            f"SELECT {_text(spec.location)} FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"
        ),
        {"id": item_id},
    ).scalar()
    return _location_value(value)


def _table_section(
    conn: Connection,
    catalog: Catalog,
    spec: ItemType,
    section: TableSection,
    item_id: int,
) -> Section | None:
    names = [c for c, _ in section.columns]
    if section.group_by and section.group_by not in names:
        names.append(section.group_by)
    cols = ", ".join(f"{_text(c)} AS c{i}" for i, c in enumerate(names))
    sql = f"SELECT {cols} FROM {quote(section.table)} WHERE {quote(section.fk)} = :id"
    if section.order_by:
        sql += " ORDER BY " + ", ".join(quote(c) for c in section.order_by)
    rows = conn.execute(text(sql + " LIMIT :limit"), {"id": item_id, "limit": section.limit}).all()
    if not rows:
        return None

    copies = spec.copy_location()
    locating = copies is not None and copies.table == section.table
    item_location = _item_location(conn, spec, item_id) if locating else ""
    urls: dict[str, str] = {}

    def cell(column: str, raw: object | None) -> tuple[str, str | None]:
        if not (locating and column == "location"):
            return _table_value(section, column, raw), None
        # A copy at UNKNOWN is wherever its item is.
        name = _location_value(raw) or item_location
        if not name or not spec.location:
            return name, None
        if name not in urls:
            urls[name] = _location_url(conn, catalog, spec, name)
        return name, urls[name]

    index = {c: i for i, c in enumerate(names)}
    groups: list[tuple[str | None, list[list[tuple[str, str | None]]]]] = []
    for row in rows:
        heading = None
        if section.group_by:
            heading = f"{section.group_label} {_clean(row[index[section.group_by]])}".strip()
        if not groups or groups[-1][0] != heading:
            groups.append((heading, []))
        groups[-1][1].append([cell(c, row[index[c]]) for c, _ in section.columns])
    return Section("table", section.label, headers=[h for _, h in section.columns], groups=groups)


def _location_url(conn: Connection, catalog: Catalog, spec: ItemType, name: str) -> str:
    # The location page only shows types registered for the name; others fall back to browse.
    if location_registered(conn, catalog, spec, name):
        return f"/location/{url_quote(name, safe='/')}"
    return f"/browse/{spec.key}?{urlencode({'location': name})}"


def _load_sections(
    conn: Connection, catalog: Catalog, spec: ItemType, tab: TabSpec, item_id: int
) -> list[Section]:
    values = _own_values(conn, spec, tab, item_id)
    if spec.issue and all(column in values for column in spec.issue):
        numbers = normalize_issue(*(values[column] for column in spec.issue))
        values.update(zip(spec.issue, (number or "" for number in numbers), strict=True))
    sections: list[Section] = []
    for s in tab.sections:
        if isinstance(s, FieldsSection):
            pairs = []
            for column, label in s.fields:
                value = values.get(column, "")
                if not value or (column == "display_number" and value == "-1"):
                    continue
                if column in {"issueno", "issuevolume"} and value == "0":
                    continue
                url = _location_url(conn, catalog, spec, value) if column == spec.location else None
                pairs.append((label, value, url))
            if pairs:
                sections.append(Section("fields", "", fields=pairs))
        elif isinstance(s, TextSection):
            if values.get(s.column):
                sections.append(Section("text", s.label, text=values[s.column]))
        elif built := _table_section(conn, catalog, spec, s, item_id):
            sections.append(built)
    return sections


def get_item(
    conn: Connection,
    catalog: Catalog,
    spec: ItemType,
    item_id: int,
    load: str | None = None,
) -> Item | None:
    """Load an item; lazy tabs stay unloaded unless named by `load`."""
    qty = quote(spec.quantity) if spec.quantity else "NULL"
    display_number, volume, issue = spec.issue or (None, None, None)
    series_title, volume_number = spec.series or (None, None)
    cols = [
        f"{_text(spec.title)} AS title",
        f"{_flag(spec.front_cover)} AS has_front",
        f"{_flag(spec.back_cover)} AS has_back",
        f"{qty} AS quantity",
        f"{_text(display_number)} AS display_number",
        f"{_text(volume)} AS volume",
        f"{_text(issue)} AS issue",
        f"{_text(spec.published)} AS published",
        f"{_text(series_title)} AS series_title",
        f"{_text(volume_number)} AS volume_number",
    ]
    row = (
        conn.execute(
            text(f"SELECT {', '.join(cols)} FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"),
            {"id": item_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        conn.rollback()
        return None

    item = Item(
        spec=spec,
        id=item_id,
        title=row["title"] or "(untitled)",
        has_front=bool(row["has_front"]),
        has_back=bool(row["has_back"]),
        title_values=TitleValues(
            display_number=row["display_number"],
            volume=row["volume"],
            issue=row["issue"],
            published=row["published"],
            series_title=row["series_title"],
            volume_number=row["volume_number"],
        ),
    )
    for tab in spec.tabs:
        loaded = not tab.lazy or tab.key == load
        sections = _load_sections(conn, catalog, spec, tab, item_id) if loaded else None
        if sections == [] and not tab.lazy:
            continue  # nothing to show for this item
        item.tabs.append(Tab(tab.key, tab.label, tab.template, sections))
    if spec.quantity and row["quantity"] is not None:
        item.availability = _availability(conn, catalog, spec, item_id, int(row["quantity"]))
    conn.rollback()
    return item


def get_tab(
    conn: Connection, catalog: Catalog, spec: ItemType, item_id: int, tab_key: str
) -> Tab | None:
    """One tab's content; None if the tab or the item does not exist."""
    tab = next((t for t in spec.tabs if t.key == tab_key), None)
    if tab is None:
        return None
    exists = conn.execute(
        text(f"SELECT 1 FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"), {"id": item_id}
    ).first()
    result = None
    if exists:
        result = Tab(
            tab.key, tab.label, tab.template, _load_sections(conn, catalog, spec, tab, item_id)
        )
    conn.rollback()
    return result


def _availability(
    conn: Connection, catalog: Catalog, spec: ItemType, item_id: int, quantity: int
) -> Availability:
    if not (catalog.has_borrowers and spec.borrower_type):
        return Availability(quantity, None)
    # COUNT only: borrower identities are never read.
    borrowed = conn.execute(
        text("SELECT count(*) FROM item_borrower WHERE item_oid = :id AND type = :type"),
        {"id": item_id, "type": spec.borrower_type},
    ).scalar_one()
    return Availability(quantity, borrowed)


def get_cover(conn: Connection, spec: ItemType, item_id: int, side: str) -> bytes | None:
    column = spec.back_cover if side == "back" else spec.front_cover
    if not column:
        return None
    data = conn.execute(
        text(f"SELECT {quote(column)} FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"),
        {"id": item_id},
    ).scalar()
    conn.rollback()
    return bytes(data) if data is not None else None
