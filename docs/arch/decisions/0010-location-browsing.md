# ADR-0010: Location browsing

- Status: Accepted
- Date: 2026-10-29

## Context

Every item table has a `location` column (`TEXT NOT NULL`, except nullable on `grey_literature`).
BiblioteQ uses the `locations` table (`location`, `type`) only to fill drop-down lists, one row per
location and item type. The column and the table can disagree: an administrator can remove a row
from `locations` without updating items, or edit items directly. BiblioteQ stores `UNKNOWN` in the
column where there is no location, and never lists it in `locations`. BiblioteQ does no
normalization, so `home`, `Home` and `HOME` are distinct locations, and the schema belongs to
BiblioteQ ([ADR-0005](0005-support-sqlite-and-postgresql.md)).

## Decision

- A location is the exact `location` string. Comparisons are case- and whitespace-sensitive.
  Normalizing values is the job of BiblioteQ users or upstream, not this app.
- The same string on different item types is one location. `locations` says which types are
  registered for it; each registry entry names its `locations.type` value (`location_type`).
- **Location page** `/location/{name}`: shows recent items, in sections like the home page, for
  each registered type that has items there. A name with no `locations` rows redirects to `/`.
- **Filter** `?location=` on search and browse matches the item column exactly, so orphaned values
  (in the column but not in `locations`) are still browsable. A value that matches nothing gives
  zero results rather than a redirect.
- **`UNKNOWN`** is special on both the page and the filter. It matches items whose column is
  `NULL` or `UNKNOWN`. Orphans are not unknown; they are found under their own name. A location
  a user names "Unknown" is an ordinary location.
- Item pages hide the location when it is `NULL` or `UNKNOWN`. Otherwise they link to the location
  page if that exact name is registered for the item's type, and to the browse filter if not.
- `locations` is read only for the filter options, page lookup and link check. If the table is
  missing, location features are turned off.
- No index page of locations, no hierarchy, and no copy-level locations (the copy tables have no
  `location` column).

## Consequences

- No schema change, and the SQL stays dialect-neutral with bound parameters.
- Exact equality can use an index on `location`, where one exists.
- Spelling variants of one place appear as separate locations until fixed in the data.
- `UNKNOWN` is a stand-in for "no location" and cannot also name a real location.

## Alternatives considered

- **Case-insensitive, trimmed matching:** conflicts with BiblioteQ, where such variants are
  deliberately distinct, and behaves differently in SQLite and PostgreSQL for non-ASCII text.
- **Treating orphans as unknown:** hides a known value behind a vague label, and they are already
  browsable by name.
- **A locations index page:** deferred; the filter's options list covers discovery for now.
