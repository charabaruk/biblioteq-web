"""SRU endpoint (`/sru`) returning MARCXML. Not implemented and not mounted yet.

Planned: map registry item rows to `pymarc.Record` objects and serialize with
`pymarc.record_to_xml`. Must not read the `marc_tags` column (see ADR-0003).
"""

from fastapi import APIRouter

router = APIRouter()

# TODO: implement explain, searchRetrieve (CQL subset) and MARCXML record packing.
