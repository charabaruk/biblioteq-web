# ADR-0003: Defer MARC, SRU and the `marc_tags` column

- Status: Accepted
- Date: 2026-10-16

## Context

BiblioteQ stores raw MARC data for some items in the `marc_tags` column. Displaying it would require
converting between OpenLibrary JSON, UNIMARC and MARCXML. That conversion is not needed for a read-only
browser MVP.

## Decision

- The `marc_tags` column is out of scope: it is never selected, displayed or exposed, and is not in the
  item type registry. A test asserts this.
- `pymarc` is a dependency so MARCXML generation can be added cleanly later.
- Placeholders exist for the future work and are not wired into the app: `app/routes/sru.py` (an SRU
  `/sru` endpoint returning MARCXML) and `app/marc/openlibrary.py` (OpenLibrary JSON to MARC mapper).
- MARC output, when added, will be generated from structured columns first; any use of `marc_tags`
  requires a new ADR covering UNIMARC/MARCXML conversion.

## Consequences

- The MVP stays small and has no MARC conversion code to maintain.
- SRU and MARC export can be added without restructuring the app.
