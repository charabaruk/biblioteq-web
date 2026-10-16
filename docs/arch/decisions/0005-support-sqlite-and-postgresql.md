# ADR-0005: Support SQLite and PostgreSQL

- Status: Accepted
- Date: 2026-10-16

## Context

BiblioteQ stores its data in either PostgreSQL or SQLite. Many users, especially on home servers, run the
desktop application against a SQLite file. The web app should serve both equally.

## Decision

- The backend is chosen from the scheme of `BIBLIOTEQ_DB_URL` (`postgresql+psycopg://` or `sqlite:///`).
  Other backends are rejected at startup.
- SQL stays in one code path and is dialect-neutral: `CAST(x AS TEXT)`, `lower(x) LIKE lower(:p)` with
  an escape character instead of `ILIKE`, and 1/0 flags instead of booleans.
- Only two places branch on the dialect: engine setup in `app/db.py` and column inspection in
  `app/repository.py` (`information_schema` for PostgreSQL, `pragma_table_info` for SQLite).
- SQLite files are opened with `mode=ro` (the file is never created or written) plus
  `PRAGMA query_only=ON`; `BIBLIOTEQ_DB_STATEMENT_TIMEOUT_MS` becomes the SQLite busy timeout.
- `BIBLIOTEQ_DB_SCHEMA` applies to PostgreSQL only.
- This supersedes the PostgreSQL-only parts of ADR-0001.

## Consequences

- SQLite has no roles, so borrower identities cannot be hidden by a column grant as on PostgreSQL
  (ADR-0004). Not reading them rests on the code alone; availability still uses `COUNT` only.
- SQLite `lower()` and `LIKE` fold only ASCII case, so searches for accented capitals are case-sensitive.
- The desktop application may hold locks on the file; reads can occasionally wait for the busy timeout.
- Integration tests run on both backends; SQLite always, PostgreSQL when `BIBLIOTEQ_TEST_DB_URL` is set.
