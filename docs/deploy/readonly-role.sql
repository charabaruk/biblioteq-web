-- Read-only role for biblioteq-web. Run as a database administrator.
-- Adjust the schema name and password. Item tables that do not exist in your database are skipped by the app,
-- but GRANT fails on missing tables, so remove those lines first.

CREATE ROLE biblioteq_web LOGIN PASSWORD 'change-me' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER ROLE biblioteq_web SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE biblioteq TO biblioteq_web;
GRANT USAGE ON SCHEMA public TO biblioteq_web;

GRANT SELECT ON
  book, dvd, cd, journal, magazine, videogame, grey_literature, photograph_collection
  TO biblioteq_web;

-- Availability only counts checkouts; borrower identities are not granted.
GRANT SELECT (item_oid, type) ON item_borrower TO biblioteq_web;

-- Optional: keep MARC data out of reach entirely (the app never reads it).
-- REVOKE SELECT ON book FROM biblioteq_web;
-- GRANT SELECT (<every column except marc_tags>) ON book TO biblioteq_web;
