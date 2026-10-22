# Releases

This project uses [Semantic Versioning](https://semver.org/) and records user-visible changes in
[CHANGELOG.md](../CHANGELOG.md), following the [Common Changelog](https://common-changelog.org/).

## Versioning

- Increment the patch version for compatible bug fixes and other compatible corrections.
- Increment the minor version for backward-compatible features.
- Increment the major version for incompatible changes.
- While the version is `0.y.z`, minor releases may include breaking changes.

Keep the version in `pyproject.toml` aligned with the release. Tag each release as `vX.Y.Z`.

## Preparing a release

1. Review changes since the previous release and include user-visible features, fixes, and other UX
   changes in `CHANGELOG.md`. Do not add an "Unreleased" section.
2. Write concise, imperative entries under the Common Changelog categories `Changed`, `Added`,
   `Removed`, or `Fixed`. Explain user impact, mark breaking changes, and link relevant commits,
   issues, or pull requests.
3. Order release entries newest first. Use the version without a `v` prefix and the release date in
   `YYYY-MM-DD` format in the heading.
4. Update the version in `pyproject.toml` and commit the changelog and version together before
   creating the matching `vX.Y.Z` tag.
5. Run `ruff check .` and `pytest`, then create the tag and publish the release notes.