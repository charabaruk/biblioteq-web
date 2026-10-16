# biblioteq-web

A read-only web browser for [BiblioteQ](https://github.com/textbrowser/biblioteq) library collections.

It connects to an existing BiblioteQ PostgreSQL database using a dedicated read-only role and lets users
search and browse books, DVDs, CDs, journals, magazines, video games, grey literature and photograph
collections, view item details and availability, and see cover images.

It is intended for anything from a home media server to a small or medium organizational library, and is
designed to run behind a reverse proxy such as nginx.

## Status

In development. Not yet usable.

## Planned stack

Python 3.11+, FastAPI, SQLAlchemy and psycopg 3, Jinja2, Uvicorn/Gunicorn.

## Scope

- Read-only: the application never writes to the database.
- Borrower personal data is never displayed.

## License

[MIT](LICENSE)
