"""Read-only queries. Identifiers come from the item type registry; values are bound."""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import Connection, text

from app.item_types import ITEM_TYPES, ItemType, quote, resolve

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
class Item:
    spec: ItemType
    id: int
    title: str
    fields: list[tuple[str, str]] = field(default_factory=list)
    has_front: bool = False
    has_back: bool = False
    availability: Availability | None = None


def load_catalog(conn: Connection, schema: str) -> Catalog:
    """Inspect the configured schema and keep only the item types it can serve."""
    rows = conn.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = :schema"
        ),
        {"schema": schema},
    ).all()
    columns: dict[str, set[str]] = {}
    for table, column in rows:
        columns.setdefault(table, set()).add(column)

    types: dict[str, ItemType] = {}
    for spec in ITEM_TYPES:
        resolved = resolve(spec, columns.get(spec.table, set()))
        if resolved is None:
            log.warning("Item type %r disabled: table %r missing or incomplete", spec.key, spec.table)
            continue
        types[spec.key] = resolved
    conn.rollback()
    return Catalog(types=types, has_borrowers="item_borrower" in columns)


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def parse_terms(query: str) -> list[str]:
    return [t for t in re.split(r"\s+", query.strip()[:MAX_QUERY_LENGTH]) if t][:MAX_TERMS]


def _select_sql(spec: ItemType, n_terms: int) -> str:
    creator = f"{quote(spec.creator)}::text" if spec.creator else "NULL::text"
    ident = f"{quote(spec.identifier)}::text" if spec.identifier else "NULL::text"
    cover = f"({quote(spec.front_cover)} IS NOT NULL)" if spec.front_cover else "false"
    sql = (
        f"SELECT '{spec.key}' AS type, {quote(spec.pk)} AS id, {quote(spec.title)}::text AS title, "
        f"{creator} AS creator, {ident} AS identifier, {cover} AS has_cover "
        f"FROM {quote(spec.table)}"
    )
    if n_terms:
        # Every term must match at least one searchable column.
        cols = spec.search_columns or (spec.title,)
        clauses = [
            "(" + " OR ".join(f"{quote(c)}::text ILIKE :t{i} ESCAPE '\\'" for c in cols) + ")"
            for i in range(n_terms)
        ]
        sql += " WHERE " + " AND ".join(clauses)
    return sql


def search(
    conn: Connection,
    catalog: Catalog,
    query: str,
    type_keys: list[str],
    page: int,
    page_size: int,
) -> Page:
    """Search the given types (all available if empty). An empty query lists everything."""
    specs = [catalog.types[k] for k in type_keys if k in catalog.types] or list(
        catalog.types.values()
    )
    if not specs:
        return Page([], 0, 1, page_size)
    terms = parse_terms(query)
    params: dict[str, object] = {f"t{i}": _like_pattern(t) for i, t in enumerate(terms)}
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


def get_item(conn: Connection, catalog: Catalog, spec: ItemType, item_id: int) -> Item | None:
    cols = [f"{quote(spec.title)}::text AS title"]
    cols += [f"{quote(c)}::text AS f{i}" for i, (c, _) in enumerate(spec.detail_fields)]
    cols.append(f"({quote(spec.front_cover)} IS NOT NULL) AS has_front" if spec.front_cover else "false AS has_front")
    cols.append(f"({quote(spec.back_cover)} IS NOT NULL) AS has_back" if spec.back_cover else "false AS has_back")
    cols.append(f"{quote(spec.quantity)} AS quantity" if spec.quantity else "NULL AS quantity")
    row = conn.execute(
        text(f"SELECT {', '.join(cols)} FROM {quote(spec.table)} WHERE {quote(spec.pk)} = :id"),
        {"id": item_id},
    ).mappings().first()
    if row is None:
        conn.rollback()
        return None

    item = Item(
        spec=spec,
        id=item_id,
        title=row["title"] or "(untitled)",
        fields=[
            (label, row[f"f{i}"].strip())
            for i, (_, label) in enumerate(spec.detail_fields)
            if row[f"f{i}"] and row[f"f{i}"].strip()
        ],
        has_front=bool(row["has_front"]),
        has_back=bool(row["has_back"]),
    )
    if spec.quantity and row["quantity"] is not None:
        item.availability = _availability(conn, catalog, spec, item_id, int(row["quantity"]))
    conn.rollback()
    return item


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
