import gettext
from dataclasses import dataclass
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALES_DIR = BASE_DIR / "app" / "locales"
LANGUAGE_COOKIE = "biblioteq_lang"
LANGUAGES = {"en": "English", "fr": "Français"}


@dataclass(frozen=True)
class LanguageOption:
    code: str
    name: str


def _normalize(value: str) -> str:
    return value.strip().replace("_", "-").lower()


def _default_language() -> str:
    configured = _normalize(get_settings().default_lang)
    base = configured.split("-", 1)[0]
    return configured if configured in LANGUAGES else base if base in LANGUAGES else "en"


def available_languages() -> tuple[LanguageOption, ...]:
    default = _default_language()
    options = [LanguageOption(default, LANGUAGES.get(default, default))]
    for code, name in LANGUAGES.items():
        catalog = LOCALES_DIR / code / "LC_MESSAGES" / "messages.mo"
        if code not in {default, "en"} and catalog.is_file():
            options.append(LanguageOption(code, name))
        elif code == "en" and code != default:
            options.append(LanguageOption(code, name))
    return tuple(options)


def _match_language(value: str, codes: set[str]) -> str | None:
    normalized = _normalize(value)
    if normalized in codes:
        return normalized
    base = normalized.split("-", 1)[0]
    return base if base in codes else None


def _accepted_languages(header: str) -> list[tuple[str, float, int]]:
    accepted = []
    for order, entry in enumerate(header.split(",")):
        parts = entry.strip().split(";")
        language = parts[0].strip()
        if not language:
            continue
        quality = 1.0
        for parameter in parts[1:]:
            key, separator, value = parameter.strip().partition("=")
            if separator and key.strip() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
                break
        if 0 < quality <= 1:
            accepted.append((language, quality, order))
    return sorted(accepted, key=lambda item: (-item[1], item[2]))


def resolve_language(
    query_language: str | None,
    cookie_language: str | None,
    accept_language: str | None,
) -> str:
    options = available_languages()
    codes = {option.code for option in options}
    default = _default_language()

    if query_language:
        return _match_language(query_language, codes) or default
    if cookie_language:
        match = _match_language(cookie_language, codes)
        if match:
            return match
    for language, _, _ in _accepted_languages(accept_language or ""):
        if language == "*":
            return default
        match = _match_language(language, codes)
        if match:
            return match
    return default


def get_translations(lang: str) -> gettext.NullTranslations:
    language = resolve_language(lang, None, None)
    return gettext.translation(
        "messages",
        localedir=LOCALES_DIR,
        languages=[language],
        fallback=True,
    )


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        lang = resolve_language(
            request.query_params.get("lang"),
            request.cookies.get(LANGUAGE_COOKIE),
            request.headers.get("Accept-Language"),
        )
        request.state.lang = lang
        request.state.translations = get_translations(lang)
        return await call_next(request)
