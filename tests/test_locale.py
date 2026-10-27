from gettext import NullTranslations
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import locale
from app.main import app


def _install_languages(monkeypatch, tmp_path):
    monkeypatch.setattr(locale, "LOCALES_DIR", tmp_path)
    french_catalog = tmp_path / "fr" / "LC_MESSAGES" / "messages.mo"
    french_catalog.parent.mkdir(parents=True)
    french_catalog.touch()
    monkeypatch.setattr(locale, "get_settings", lambda: SimpleNamespace(default_lang="en"))


def test_available_languages_include_default_and_compiled_catalogs(monkeypatch, tmp_path):
    monkeypatch.setattr(locale, "LOCALES_DIR", tmp_path)
    monkeypatch.setattr(locale, "get_settings", lambda: SimpleNamespace(default_lang="en"))
    assert [(option.code, option.name) for option in locale.available_languages()] == [
        ("en", "English")
    ]

    _install_languages(monkeypatch, tmp_path)
    assert [(option.code, option.name) for option in locale.available_languages()] == [
        ("en", "English"),
        ("fr", "Français"),
    ]


def test_english_source_fallback_is_available_with_french_default(monkeypatch, tmp_path):
    monkeypatch.setattr(locale, "LOCALES_DIR", tmp_path)
    monkeypatch.setattr(locale, "get_settings", lambda: SimpleNamespace(default_lang="fr"))

    assert [option.code for option in locale.available_languages()] == ["fr", "en"]
    assert locale.resolve_language("en", None, None) == "en"


def test_resolve_language_obeys_override_cookie_and_weighted_header(monkeypatch, tmp_path):
    _install_languages(monkeypatch, tmp_path)

    assert locale.resolve_language("fr", "en", "en") == "fr"
    assert locale.resolve_language(None, "fr", "en") == "fr"
    assert locale.resolve_language(None, None, "de, fr-CA;q=0.8, en;q=0.5") == "fr"
    assert locale.resolve_language(None, None, "fr;q=0, en;q=0.5") == "en"
    assert locale.resolve_language("unsupported", None, None) == "en"


def test_get_translations_uses_source_text_when_catalog_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(locale, "LOCALES_DIR", tmp_path)
    monkeypatch.setattr(locale, "get_settings", lambda: SimpleNamespace(default_lang="en"))

    translations = locale.get_translations("fr")

    assert isinstance(translations, NullTranslations)
    assert translations.gettext("Book") == "Book"
    assert translations.pgettext("item-type", "Book") == "Book"


def test_language_selection_persists_cookie_and_translates_page(configured, monkeypatch, tmp_path):
    _install_languages(monkeypatch, tmp_path)

    class FrenchTranslations(NullTranslations):
        def gettext(self, message):
            return {"Books": "Livres"}.get(message, message)

        def pgettext(self, context, message):
            return {
                ("item-type", "Books"): "Livres",
                ("item-type", "Book"): "Livre",
            }.get((context, message), self.gettext(message))

    monkeypatch.setattr(
        locale,
        "get_translations",
        lambda lang: FrenchTranslations() if lang == "fr" else NullTranslations(),
    )

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/language", params={"lang": "fr", "next": "/"})
        assert response.status_code == 303
        assert response.headers["location"] == "/"
        assert "biblioteq_lang=fr" in response.headers["set-cookie"]

        page = client.get("/")
        assert page.status_code == 200
        assert '<html lang="fr">' in page.text
        assert ">Livres</a>" in page.text
        assert 'name="lang"' in page.text


def test_language_selection_rejects_unsupported_and_external_redirects(
    configured, monkeypatch, tmp_path
):
    _install_languages(monkeypatch, tmp_path)
    monkeypatch.setattr(locale, "get_translations", lambda lang: NullTranslations())
    with TestClient(app, follow_redirects=False) as client:
        unsupported = client.get("/language", params={"lang": "es"})
        assert unsupported.status_code == 400

        external = client.get("/language", params={"lang": "fr", "next": "//example.com/"})
        assert external.status_code == 303
        assert external.headers["location"] == "/"
