"""Liveness and readiness probes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection, text

from app.db import get_conn

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(conn: Connection = Depends(get_conn)) -> dict[str, str]:
    try:
        conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}
