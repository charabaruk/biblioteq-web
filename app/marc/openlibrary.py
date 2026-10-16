"""OpenLibrary JSON to MARC conversion. Stub only; not used by the MVP."""

from typing import Any

from pymarc import Record


def openlibrary_to_marc(edition: dict[str, Any]) -> Record:
    """Map an OpenLibrary edition JSON document to a MARC record."""
    raise NotImplementedError("OpenLibrary to MARC mapping is not implemented yet")
