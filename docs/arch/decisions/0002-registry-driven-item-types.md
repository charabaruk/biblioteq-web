# ADR-0002: Registry-driven item types

- Status: Accepted
- Date: 2026-10-16

## Context

BiblioteQ stores each media type in its own table with different columns, and column sets differ between
BiblioteQ versions. The web app must support several types, be easy to extend, and must never build SQL
from user input.

## Decision

- `app/item_types.py` holds an `ItemType` record per media type: table, title/creator/identifier columns,
  searchable columns, detail fields, quantity, cover columns and the `item_borrower.type` value.
- All table and column names in SQL come from this registry and are quoted by `quote()`, which rejects
  anything but plain identifiers. Values are bound parameters.
- At startup the repository reads `information_schema.columns` for the configured schema and calls
  `resolve()`, which drops columns that do not exist and disables types whose table or required
  columns (`myoid`, title) are missing. Disabled types are logged.
- The `marc_tags` column is not in the registry and is never selected.
- Borrower data: availability uses `COUNT(*)` on `item_borrower` only; no borrower rows or member
  identifiers are ever selected.

## Consequences

- Adding a type or fixing a column name is a registry edit.
- A wrong guess about a column in one type cannot break search for the others.
- Column names for types other than books are based on the BiblioteQ schema and may need adjustment.
