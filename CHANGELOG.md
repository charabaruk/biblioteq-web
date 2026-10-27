# Changelog

## [0.2.0] - 2026-10-26

### Changed

- Match item field labels and order to BiblioteQ, and use explicit collection plural names ([`112d06c`](https://github.com/charabaruk/biblioteq-web/commit/112d06c), [`262da45`](https://github.com/charabaruk/biblioteq-web/commit/262da45))
- Display periodical issue numbers consistently and hide unset issue and volume values ([`89c4de6`](https://github.com/charabaruk/biblioteq-web/commit/89c4de6))
- Use square cover images on music CD cards ([`6388d60`](https://github.com/charabaruk/biblioteq-web/commit/6388d60))

### Added

- Organize item details into tabs and sections, with lazy loading and in-page tab switching ([`f56f0b2`](https://github.com/charabaruk/biblioteq-web/commit/f56f0b2), [`eb4582a`](https://github.com/charabaruk/biblioteq-web/commit/eb4582a), [`7fcec8a`](https://github.com/charabaruk/biblioteq-web/commit/7fcec8a))
- Show track listings for music CDs ([`81e85ca`](https://github.com/charabaruk/biblioteq-web/commit/81e85ca))
- Sort search and browse titles naturally, with configurable numeric sorting ([`1c6eea1`](https://github.com/charabaruk/biblioteq-web/commit/1c6eea1), [`b8b04bb`](https://github.com/charabaruk/biblioteq-web/commit/b8b04bb))
- Add favicon and Apple touch icon support ([`d3a36cf`](https://github.com/charabaruk/biblioteq-web/commit/d3a36cf))

### Fixed

- Treat BiblioteQ's `N/A` field values as empty ([`78dd020`](https://github.com/charabaruk/biblioteq-web/commit/78dd020))
- Avoid duplicate accession-number fields for photograph collections ([`df02173`](https://github.com/charabaruk/biblioteq-web/commit/df02173), [`8c8d94e`](https://github.com/charabaruk/biblioteq-web/commit/8c8d94e))

## [0.1.0] - 2026-10-18

_Initial release._

### Added

- Search and browse BiblioteQ collections, with item details, covers, and availability counts ([`7470553`](https://github.com/charabaruk/biblioteq-web/commit/7470553), [`2ca5413`](https://github.com/charabaruk/biblioteq-web/commit/2ca5413), [`385e582`](https://github.com/charabaruk/biblioteq-web/commit/385e582))
- Connect to PostgreSQL or SQLite databases using read-only access ([`54422b3`](https://github.com/charabaruk/biblioteq-web/commit/54422b3))
- Provide Docker, systemd, and nginx deployment examples ([`fc11b31`](https://github.com/charabaruk/biblioteq-web/commit/fc11b31), [`0852ab7`](https://github.com/charabaruk/biblioteq-web/commit/0852ab7))

### Fixed

- Decode base64-encoded cover images ([`b18483c`](https://github.com/charabaruk/biblioteq-web/commit/b18483c))
- Match photograph collection fields to the database schema ([`cb8165a`](https://github.com/charabaruk/biblioteq-web/commit/cb8165a))

[0.2.0]: https://github.com/charabaruk/biblioteq-web/releases/tag/v0.2.0
[0.1.0]: https://github.com/charabaruk/biblioteq-web/releases/tag/v0.1.0
