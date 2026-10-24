"""Read-only queries. Identifiers come from the item type registry; values are bound."""

import logging
import re
from dataclasses import dataclass, field

from natsort import natsort_keygen, ns
from sqlalchemy import Connection, text

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


@dataclass(frozen=True)
class Catalog:
    types: dict[str, ItemType]
    has_borrowers: bool


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
    fields: list[tuple[str, str]] = field(default_factory=list)
    text: str = ""
    headers: list[str] = field(default_factory=list)
    groups: list[tuple[str | None, list[list[str]]]] = field(default_factory=list)


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


def _columns_by_table(conn: Connection, schema: str) -> dict[str, set[str]]:
    columns: dict[str, set[str]] = {}
    if conn.dialect.name == "sqlite":
        # SQLite has no schemas; only the tables the app can use are inspected.
        for table in (
            [s.table for s in ITEM_TYPES]
            + [t for s in ITEM_TYPES for t in related_tables(s)]
            + ["item_borrower"]
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
    return Catalog(types=types, has_borrowers="item_borrower" in columns)


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


def _where_sql(spec: ItemType, n_terms: int) -> str:
    if not n_terms:
        return ""
    # Every term must match at least one searchable column.
    cols = spec.search_columns or (spec.title,)
    clauses = [
        "(" + " OR ".join(f"lower({_text(c)}) LIKE lower(:t{i}) ESCAPE '\\'" for c in cols) + ")"
        for i in range(n_terms)
    ]
    return " WHERE " + " AND ".join(clauses)


def _select_sql(spec: ItemType, n_terms: int) -> str:
    return (
        f"SELECT '{spec.key}' AS type, {quote(spec.pk)} AS id, {_text(spec.title)} AS title, "
        f"{_text(spec.creator)} AS creator, {_text(spec.identifier)} AS identifier, "
        f"{_flag(spec.front_cover)} AS has_cover "
        f"FROM {quote(spec.table)}" + _where_sql(spec, n_terms)
    )


def _keys_sql(spec: ItemType, n_terms: int) -> str:
    return (
        f"SELECT '{spec.key}' AS type, {quote(spec.pk)} AS id, {_text(spec.title)} AS title "
        f"FROM {quote(spec.table)}" + _where_sql(spec, n_terms)
    )


def title_sort_key(numbers: str):
    """Natural, case-insensitive sort key; digit runs are integers or decimals."""
    keygen = natsort_keygen(alg=ns.IGNORECASE | (ns.FLOAT if numbers == "decimal" else ns.INT))
    return lambda title: keygen(title or "")


def _natural_page(
    conn: Connection,
    specs: list[ItemType],
    terms: list[str],
    params: dict[str, object],
    page: int,
    page_size: int,
    numbers: str,
) -> Page:
    # Sorting happens here because the database has no portable natural collation.
    union = " UNION ALL ".join(_keys_sql(s, len(terms)) for s in specs)
    key = title_sort_key(numbers)
    keys = sorted(
        conn.execute(text(union), params).all(),
        key=lambda r: (key(r.title), r.type, r.id),
    )
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
        found.update({(r["type"], r["id"]): dict(r) for r in rows})
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
) -> Page:
    """Search the given types (all available if empty). An empty query lists everything.

    `natural` is "integer" or "decimal" to order titles naturally in Python;
    None orders in SQL by lowercased title.
    """
    specs = [catalog.types[k] for k in type_keys if k in catalog.types] or list(
        catalog.types.values()
    )
    if not specs:
        return Page([], 0, 1, page_size)
    terms = parse_terms(query)
    params: dict[str, object] = {f"t{i}": _like_pattern(t) for i, t in enumerate(terms)}
    if natural:
        return _natural_page(conn, specs, terms, params, page, page_size, natural)
    union = " UNION ALL ".join(_select_sql(s, len(terms)) for s in specs)

    total = conn.execute(text(f"SELECT count(*) FROM ({union}) u"), params).scalar_one()
    page = max(1, min(page, max(1, -(-total // page_size))))
    rows = conn.execute(
        text(
            f"SELECT * FROM ({union}) u ORDER BY lower(title), type, id LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    ).mappings()
    items = [dict(r) for r in rows]
    conn.rollback()
    return Page(items, total, page, page_size)


def recent(conn: Connection, spec: ItemType, limit: int) -> list[dict]:
    """Most recently added rows of one type (highest primary key first)."""
    rows = conn.execute(
        text(f"{_select_sql(spec, 0)} ORDER BY {quote(spec.pk)} DESC LIMIT :limit"),
        {"limit": limit},
    ).mappings()
    items = [dict(r) for r in rows]
    conn.rollback()
    return items


def _clean(value: object | None) -> str:
    return str(value).strip() if value is not None else ""


def _own_value(value: object | None) -> str:
    # "N/A" is a placeholder in BiblioteQ data, not content.
    cleaned = _clean(value)
    return "" if cleaned == "N/A" else cleaned


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
    return {c: _own_value(row[f"c{i}"]) for i, c in enumerate(names)}


def _table_section(conn: Connection, section: TableSection, item_id: int) -> Section | None:
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

    index = {c: i for i, c in enumerate(names)}
    groups: list[tuple[str | None, list[list[str]]]] = []
    for row in rows:
        heading = None
        if section.group_by:
            heading = f"{section.group_label} {_clean(row[index[section.group_by]])}".strip()
        if not groups or groups[-1][0] != heading:
            groups.append((heading, []))
        groups[-1][1].append([_clean(row[index[c]]) for c, _ in section.columns])
    return Section("table", section.label, headers=[h for _, h in section.columns], groups=groups)


def _load_sections(conn: Connection, spec: ItemType, tab: TabSpec, item_id: int) -> list[Section]:
    values = _own_values(conn, spec, tab, item_id)
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
                pairs.append((label, value))
            if pairs:
                sections.append(Section("fields", "", fields=pairs))
        elif isinstance(s, TextSection):
            if values.get(s.column):
                sections.append(Section("text", s.label, text=values[s.column]))
        elif built := _table_section(conn, s, item_id):
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
    cols = [
        f"{_text(spec.title)} AS title",
        f"{_flag(spec.front_cover)} AS has_front",
        f"{_flag(spec.back_cover)} AS has_back",
        f"{qty} AS quantity",
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
    )
    for tab in spec.tabs:
        loaded = not tab.lazy or tab.key == load
        sections = _load_sections(conn, spec, tab, item_id) if loaded else None
        if sections == [] and not tab.lazy:
            continue  # nothing to show for this item
        item.tabs.append(Tab(tab.key, tab.label, tab.template, sections))
    if spec.quantity and row["quantity"] is not None:
        item.availability = _availability(conn, catalog, spec, item_id, int(row["quantity"]))
    conn.rollback()
    return item


def get_tab(conn: Connection, spec: ItemType, item_id: int, tab_key: str) -> Tab | None:
    """One tab's content; None if the tab or the item does not exist."""
    tab = next((t for t in spec.tabs if t.key == tab_key), None)
    if tab is None:
        return None
    exists = conn.execute(
        text(f"SELECT 1 FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"), {"id": item_id}
    ).first()
    result = None
    if exists:
        result = Tab(tab.key, tab.label, tab.template, _load_sections(conn, spec, tab, item_id))
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
