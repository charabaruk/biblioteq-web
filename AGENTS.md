# Instructions for AI coding agents

This is a read-only FastAPI web browser for BiblioteQ PostgreSQL and SQLite databases.

## Rules

- Python 3.11+, FastAPI, SQLAlchemy 2.0 with psycopg 3, Jinja2.
- Never add database write paths. Assume a read-only role.
- Use parameterized SQL only. Table and column names come only from the item type registry.
- The `marc_tags` column is out of scope: never select, display or expose it.
- Never select borrower personal data; availability uses counts only.
- The database schema is configurable (default `public`, PostgreSQL only); never hard-code it in SQL.
- Keep SQL dialect-neutral (PostgreSQL and SQLite); branch on the dialect only in `app/db.py` and catalog inspection.
- Prefer clarity over cleverness. Comments are one short line and only state what the code cannot show.

## Workflow

- Commit per rational unit of change using Conventional Commits.
- Record architectural decisions as ADRs in `docs/arch/decisions/`; architecture docs go in `docs/arch/`.
- Run `ruff check .` and `pytest` before committing.
