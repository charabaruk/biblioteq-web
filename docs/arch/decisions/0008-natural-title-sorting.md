# ADR-0008: Natural title sorting

- Status: Accepted
- Date: 2026-10-23

## Context

Title-ordered results sort lexically, so `Volume 10` precedes `Volume 2`. A fix in the database
would need a schema change (a sort-key column) or a server extension (a natural collation), and
neither is available: the schema belongs to BiblioteQ, and the app must work on SQLite and
PostgreSQL with a read-only role ([ADR-0001](0001-read-only-fastapi-stack.md),
[ADR-0005](0005-support-sqlite-and-postgresql.md)).

## Decision

- Natural ordering runs in the application with the `natsort` library, case-insensitively.
- `search()` (used by search and browse) fetches `(type, id, title)` for all matches, sorts them in
  Python with ties broken by type and id, slices the requested page, then loads the full rows of
  that page only. The total is the length of the sorted list.
- `BIBLIOTEQ_NATURAL_SORT` (default `true`) turns it on or off. When off, the original SQL
  `ORDER BY lower(title), type, id` path with `LIMIT`/`OFFSET` is used.
- `BIBLIOTEQ_NATURAL_SORT_NUMBERS` chooses how digit runs are read: `integer` (default) or
  `decimal`. Integer keeps `v2.9` before `v2.10`; decimal reads `2.10` as 2.1 so it precedes `2.9`.
  Integer is the default because version-like and numbered titles are more common than decimals.
- Signs are not interpreted, so hyphens in titles are not read as negative numbers. Leading
  articles ("The", "A") get no special treatment.
- The home page's recent items and table-section ordering are unchanged.

## Consequences

- No schema change, no extension, and the SQL stays dialect-neutral.
- Each request reads the id and title of every match, so cost grows with the number of matches.
  Large catalogs can turn the feature off; a cache can be added later if needed.
- Ordering can differ from the database's own collation for non-ASCII titles.
- `natsort` is a new pure-Python dependency.

## Alternatives considered

- **Sort-key column or generated column:** needs schema changes outside this project.
- **Database collation or extension (for example ICU numeric collation):** not portable across
  SQLite and PostgreSQL and not guaranteed to be installed.
- **Regex-based `ORDER BY` expressions in SQL:** not dialect-neutral and fragile.
- **A hand-written sort key:** `natsort` already handles mixed digit and text runs and decimals.
