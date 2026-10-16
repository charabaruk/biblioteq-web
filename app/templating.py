"""Jinja2 environment shared by page routes."""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent


def _context(request: Request) -> dict:
    return {
        "site_title": get_settings().site_title,
        "base": request.scope.get("root_path", ""),
    }


templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates", context_processors=[_context])
