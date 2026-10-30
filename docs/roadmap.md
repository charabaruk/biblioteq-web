# Roadmap

This roadmap is directional and has no date commitments. It groups candidate work into release themes; scope can change as the project and its users provide more information. See the [candidate feature checklist](candidate-features.md) for ideas not yet assigned to a release.

## v0.2: More Useful Item Pages

The initial v0.2 scope is:

- Show Music CD tracks ordered by disc and track number. *(done)*
- Use square images for Music CDs on browse pages; retain the existing aspect ratio for other item types. *(done)*
- Sort titles naturally in browse and other title-ordered results (application-side), so for example `Volume 2` precedes `Volume 10`. *(done)*

## v0.3: Localization and Holdings Information

Proposed focus:

- Initial localization support: replace bare strings in templates with translatable strings and generate translation catalogs.
- Show information about individual item copies on item pages. *(done)*
- Add pages for item locations and browsing items at them.

## v0.4: Related Catalog Records

Proposed focus:

- Add book series pages (grouping books that share a non-empty series title and showing volume strings).
- Add publication-level detail pages for journals and magazines, grouping issues by ISSN.
- Add category browsing and author/artist browsing.
- Improve search with call-number and Dewey-class lookup.

## v0.5: Photograph Galleries and Attached Files

Proposed focus:

- Add a gallery of a collection’s photographs on its detail page.
- List files attached to supported item types and, after deciding access policy, content handling, and large-file behavior, consider making those files available for download.

## v0.6: Reassess and Extend

Use feedback from the preceding releases to choose the next user-facing priority. Caching support (ETag checks for covers and any future file responses) is a candidate for reducing bandwidth use. If higher-priority browsing or reliability work emerges, prefer that instead.
