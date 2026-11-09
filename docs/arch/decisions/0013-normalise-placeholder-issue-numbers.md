# ADR-0013: Normalise placeholder volume and issue numbers

- Status: Accepted
- Date: 2026-11-06

## Context

`issuevolume` and `issueno` are `NOT NULL` columns defaulting to 0, and `display_number` is a
nullable integer where -1 means unset. Some BiblioteQ records use the volume column as a
placeholder: a volume of 0 with an issue number that repeats the display number, or a volume of 0
with only an issue number and no display number. Shown as stored, these read "Foo 42 (no. 42)" and
"Foo no. 42", which is noise ([ADR-0012](0012-display-titles.md)); the upstream BiblioteQ project
tracks the underlying data issue.

## Decision

Magazines and journals read their display number, volume and issue through one normalisation
step, in this order. Empty means `display_number` of -1 or NULL, and a volume or issue of 0.

1. **Issue only:** with an empty volume, a set issue number and an empty display number, the issue
   number becomes the display number.
2. **Repeated number:** with an empty volume and an issue number equal to the display number, the
   volume and issue are treated as unset.

The result is that a volume of 0 with an issue equal to, or standing in for, the display number
leaves only the display number. Any other combination is left as stored; in particular, a set
volume is never altered.

The normalised values are used everywhere these fields are shown:

- the page title, display title and subtitle of [ADR-0012](0012-display-titles.md);
- the Issue Number, Volume and Issue fields on the Main tab;
- the issue line on browse, search and home cards.

The stored data is never changed; this is a read-only view of it.

## Consequences

- One function owns the rule, so titles, fields and cards cannot disagree.
- Card queries return the raw columns and are normalised in Python after the fetch, keeping the SQL
  dialect-neutral.
- A record whose issue number deliberately equals its display number with a volume of 0 loses the
  duplicate; nothing else about it is hidden.
- The Main tab can show an Issue Number the database holds only in the issue column.

## Alternatives considered

- **Normalise in the titles only:** the Main tab and cards would still show "Volume 0"-derived
  noise and contradict the title.
- **Normalise in SQL with `CASE`:** repeats the rule per query and per dialect.
- **Fix the data:** the application is read-only ([ADR-0001](0001-read-only-fastapi-stack.md)).
