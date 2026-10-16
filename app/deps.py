"""Shared FastAPI dependencies."""

from threading import Lock

from fastapi import Depends, HTTPException
from sqlalchemy import Connection

from app.config import get_settings
from app.db import get_conn
from app.item_types import ItemType
from app.repository import Catalog, load_catalog

_catalog: Catalog | None = None
_lock = Lock()


def get_catalog(conn: Connection = Depends(get_conn)) -> Catalog:
    """Schema inspection runs once, on first request."""
    global _catalog
    with _lock:
        if _catalog is None:
            _catalog = load_catalog(conn, get_settings().db_schema)
        return _catalog


def require_type(key: str, catalog: Catalog) -> ItemType:
    spec = catalog.types.get(key)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown item type")
    return spec
