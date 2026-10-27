import gettext
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALES_DIR = BASE_DIR / "app" / "locales"

DEFAULT_LANG = get_settings().default_lang


def get_translations(lang: str):
    try:
        return gettext.translation(
            "messages",
            localedir=LOCALES_DIR,
            languages=[lang],
            fallback=True,
        )
    except FileNotFoundError:
        return gettext.translation(
            "messages",
            localedir=LOCALES_DIR,
            languages=[DEFAULT_LANG],
            fallback=True,
        )


class LanguageMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, templates: Jinja2Templates):
        super().__init__(app)
        self.templates = templates

    async def dispatch(self, request: Request, call_next):
        # Prefer session, cookie, query, or Accept-Language
        lang = (
            request.query_params.get("lang")
            or request.headers.get("Accept-Language", DEFAULT_LANG).split(",")[0][:2]
            or DEFAULT_LANG
        )
        translations = get_translations(lang)
        # Make _ / gettext available in all templates for this request
        self.templates.env.globals["_"] = translations.gettext
        self.templates.env.globals["gettext"] = translations.gettext
        self.templates.env.globals["ngettext"] = translations.ngettext
        # optional: store on request.state for Python code
        request.state.lang = lang
        request.state.translations = translations

        response = await call_next(request)
        return response
