# Candidate Features

This checklist follows the version goals in the [roadmap](roadmap.md). Items listed as additional candidates are not committed release scope.

## v0.2: More Useful Item Pages

- [x] **Music CD track listings:** Show tracks ordered by disc and track number.
- [x] **Square Music CD browse images:** Use square images for Music CDs on browse pages while retaining the current aspect ratio for other item types.
- [x] **Natural title sorting:** Sort titles naturally in browse and other title-ordered results, so, for example, `Volume 2` precedes `Volume 10`.

## v0.3: Localization and Holdings Information

- [ ] **Initial localization support:** Replace bare strings in templates with translatable strings and generate translation catalogs.
- [ ] **Item copy info:** Show information about individual item copies under each item page.
- [x] **Locations:** Pages for item locations, and browsing items at them.

## v0.4: Related Catalog Records

- [ ] **Book series pages:** Group books with a non-empty series title and show their volume strings. A null or empty series title means the book is standalone; BiblioteQ does not link books into a series.
- [ ] **Journal and magazine publication pages:** Group issues by ISSN and show all issues for the serial publication.
- [ ] **Category browsing:** List item categories and browse items in them.
- [ ] **Author browsing:** List authors / artists and browse items by them.
- [ ] **Call/Dewey Number search:** Find related items by call number or Dewey class.

## v0.5: Photograph Galleries

- [ ] **Photograph collection galleries:** Show the photographs belonging to a collection on its detail page. This is distinct from using one photograph as the collection's browse thumbnail.
- [ ] **Attached-file listings:** List files attached to supported item types. Do not retrieve or serve file contents; file access is deferred.
- [ ] **Attached-file access:** Consider downloads separately from file listings, after deciding access policy, content handling, and large-file behavior.

## v0.6: Reassess and Extend

- [ ] **Caching support:** Reduce bandwidth use by checking `ETag` headers before sending files or cover images.

## Other Candidates

- [x] **Favicon:** Include the BiblioteQ icon for identifying pages.
