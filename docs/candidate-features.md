# Candidate Features

This checklist follows the version goals in the [roadmap](roadmap.md). Items listed as additional candidates are not committed release scope.

## v0.2: More Useful Item Pages

- [ ] **Photograph collection thumbnails:** Use the first photograph in a collection as its browse thumbnail. Choose a deterministic ordering for identifying the first photograph.
- [ ] **Attached-file listings:** List files attached to supported item types. Do not retrieve or serve file contents; file access is deferred.
- [ ] **Music CD track listings:** Show tracks ordered by disc and track number.
- [ ] **Square Music CD browse images:** Use square images for Music CDs on browse pages while retaining the current aspect ratio for other item types.

## v0.3: Related Catalog Records

- [ ] **Book series pages:** Group books with a non-empty series title and show their volume strings. A null or empty series title means the book is standalone; BiblioteQ does not link books into a series.
- [ ] **Journal and magazine publication pages:** Group issues by ISSN and show all issues for the serial publication.

## v0.4: Photograph Galleries

- [ ] **Photograph collection galleries:** Show the photographs belonging to a collection on its detail page. This is distinct from using one photograph as the collection's browse thumbnail.

## v0.5: Reassess and Extend

- [ ] **Attached-file access:** Consider downloads separately from file listings, after deciding access policy, content handling, and large-file behavior.

## Other Candidates

- [ ] **Back images on item details:** Show an item's back image when one is available.
- [ ] **Natural title sorting:** Sort titles naturally in browse and other title-ordered results, so, for example, `Volume 2` precedes `Volume 10`.
