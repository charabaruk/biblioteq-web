# ADR-0011: Copy-level locations

- Status: Accepted
- Date: 2026-10-31

## Context

[ADR-0010](0010-location-browsing.md) ruled out copy-level locations because the copy tables had no
`location` column. The `*_copy_info` tables now have one (`TEXT NOT NULL`), so a copy can sit in a
different place from its item. BiblioteQ writes `UNKNOWN` to a copy's column when none is given,
as it does for items, and the copy then belongs wherever the item does.

## Decision

- A copy location is the exact `location` string, with the same case- and whitespace-sensitive
  semantics as an item location ([ADR-0010](0010-location-browsing.md)).
- A copy at `UNKNOWN` inherits the location of its item, whatever the number of copies.
- **Matching:** a named location matches an item when the item's own column or any of its copies,
  other than those inheriting, equals it. This applies to the location page and to the `?location=`
  filter on search and browse. It is an `EXISTS` test on the copy table, so an item is listed once.
- **`UNKNOWN`** stays item-only: it matches items whose own column is `NULL` or `UNKNOWN`. A copy
  at `UNKNOWN` adds nothing, because it takes its item's location.
- **Holdings tables** show the copy location as a link, built as for items: to the location page if
  the name is registered for the item's type, otherwise to the browse filter. A copy at `UNKNOWN`
  shows its item's location, and is blank if that is also `NULL` or `UNKNOWN`.
- `locations` stays the only registry; copies have no registration of their own, and the filter
  options list is unchanged.
- A database whose copy table has no `location` column behaves as before.
- This supersedes only the "no copy-level locations" bullet of ADR-0010. The rest of it stands.

## Consequences

- An item can appear on a location page though its own column names another location.
- No schema change; the SQL stays dialect-neutral with bound parameters, and identifiers come only
  from the item type registry.
- Copy lookups use an index on the copy location and item key where the database has one.
- A copy at `UNKNOWN` cannot be told apart from one deliberately left at the item's location.

## Alternatives considered

- **Links only, with unchanged matching:** a linked location would lead to a page that omits the
  item that led there.
- **A JOIN or UNION over copies:** lists an item once per matching copy and needs deduplication.
- **Inheritance only for single-copy items:** leaves an item's other copies at `UNKNOWN` with
  nothing to show, and makes the result depend on the copy count.
- **Treating `UNKNOWN` copies as unknown:** would list items under `UNKNOWN` that have a known
  location, and shows the user a vaguer value than the data supports.
