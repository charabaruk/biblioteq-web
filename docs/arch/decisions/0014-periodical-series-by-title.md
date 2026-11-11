# ADR-0014: Browse periodical series by title

- Status: Accepted
- Date: 2026-11-11
- Issue: [#13](https://github.com/charabaruk/biblioteq-web/issues/13)

## Context

Journal and magazine issues are grouped by their ISSN, stored in the `id` column. Some issues
have a NULL ISSN, so their series cannot be reached through the identifier-based series page.
Matching a title can also find issues belonging to different ISSNs, or a mixture of identified and
unidentified issues. Choosing a series from one page of results could miss other matches.

## Decision

Provide a separate `/series/{type_key}/by-title/{title}` route for journals and magazines.
Match the raw stored title exactly, including case and whitespace. The route captures the rest of
the path as the title and takes precedence over the identifier-based route. Encode titles in links,
sorting forms and pagination URLs.

Inspect all matching issues before sorting or pagination:

1. If there are no matches, return 404.
2. If any match has a NULL ISSN, show only the matches with a NULL ISSN in the series page.
3. If all matches have the same non-NULL ISSN, redirect to its identifier-based series page.
4. Otherwise, show a selection page with the title and ISSN for each distinct non-NULL ISSN.

An empty string and other non-NULL values are identifiers, not NULL placeholders. The existing
identifier route accepts empty and slash-containing identifiers, except those beginning with
`by-title/`, which is reserved for title lookup. Such values are not valid ISSNs: BiblioteQ accepts
ISSNs matching `\d{4}-\d{3}[0-9X]`. This application does not add ISSN validation on read. If the
identifier column is unavailable, the title route returns 404 because it cannot determine which
issues lack an ISSN.

Periodical item pages link to the title-based route when the item's ISSN is NULL. Existing ISSN
links remain unchanged. The issue ordering and pagination of the existing series page also apply
to a series identified by title. Book series are outside this decision.

## Consequences

- Issues without an ISSN can be browsed together without mixing them with identified issues.
- Identical titles do not imply that different ISSNs identify the same series.
- Case or whitespace differences in stored titles produce separate title-based series.
- Series resolution must examine all matching identifiers before paginating the issues.
- Intermediaries that normalize path segments or reject encoded slashes may prevent some titles
  from round-tripping.
- Queries remain read-only and dialect-neutral, with values bound as parameters and identifiers
  supplied by the item type registry.

## Alternatives considered

- **Always group by title:** merges issues from distinct identified series.
- **Always show every ISSN alongside NULL:** leaves ambiguous whether unidentified issues belong
  to one of the identified series.
- **Use a separate route with a title query parameter:** avoids path normalization and route
  conflicts, but does not place title lookup under the series URL.
- **Validate every stored ISSN on read:** changes how existing non-NULL values are handled and is
  unnecessary to reserve `by-title/` for title lookup.
- **Fuzzy or case-insensitive title matching:** can combine distinct titles and obscures which
  stored value determines the series.
