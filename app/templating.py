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


def tab_templates(spec_key: str, tab) -> list[str]:
    """Template candidates for a tab body, most specific first."""
    names = [f"item/{spec_key}/{tab.key}.html", f"item/{tab.key}.html", "item/tab.html"]
    return [tab.template, *names] if tab.template else names


templates.env.globals["tab_templates"] = tab_templates
