"""Cover image endpoint. Images are stored in BLOB/BYTEA columns."""

import base64
import binascii
import hashlib
import zlib
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy import Connection

from app.db import get_conn
from app.deps import get_catalog, require_type
from app.repository import Catalog, get_cover

router = APIRouter()

_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def sniff(data: bytes) -> str | None:
    for prefix, mime in _SIGNATURES:
        if data.startswith(prefix):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def decode_image(data: bytes) -> tuple[bytes, str] | None:
    """Return image bytes and MIME type; stored images may be raw, base64 or qCompress-wrapped."""
    mime = sniff(data)
    if mime:
        return data, mime
    try:
        decoded = base64.b64decode(data, validate=False)
    except binascii.Error:
        decoded = b""
    mime = sniff(decoded)
    if mime:
        return decoded, mime
    # qCompress: 4-byte big-endian length followed by a zlib stream.
    for candidate in (data, decoded):
        try:
            inflated = zlib.decompress(candidate[4:])
        except zlib.error:
            continue
        mime = sniff(inflated)
        if mime:
            return inflated, mime
    return None


@router.get("/cover/{type_key}/{item_id}")
def cover(
    request: Request,
    type_key: str,
    item_id: int = Path(ge=0, le=2**63 - 1),
    side: Literal["front", "back"] = Query("front"),
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_catalog),
) -> Response:
    spec = require_type(type_key, catalog)
    raw = get_cover(conn, spec, item_id, side)
    decoded = decode_image(raw) if raw else None
    if decoded is None:
        raise HTTPException(status_code=404, detail="No cover")
    data, mime = decoded
    etag = f'"{hashlib.sha256(data).hexdigest()}"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=86400"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=data, media_type=mime, headers=headers)
