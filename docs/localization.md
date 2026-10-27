# Localization and Internationalization

The interface uses gettext catalogs. English source strings and their translation contexts are defined in `app/item_types.py` and the Jinja templates. `babel.cfg` configures Babel to extract strings from both Python and templates.

## Language Selection

The supported language names and codes are listed in `LANGUAGES` in `app/locale.py`. English (`en`) is the source-text fallback. The configured default is always available, even without a compiled catalog; other non-default languages are offered when their compiled catalog is available at:

```text
app/locales/<language>/LC_MESSAGES/messages.mo
```

For each request, the application selects a language in this order:

1. A supported `?lang=<code>` query parameter, which overrides other preferences for that request.
2. The `biblioteq_lang` cookie, set by the language selector.
3. The best supported match in the `Accept-Language` request header.
4. The `DEFAULT_LANG` environment setting, falling back to English if it is unsupported.

Regional language tags such as `fr-CA` match the base language (`fr`) when it is supported. The chosen catalog's translations are applied to a request-local copy of the item type registry; the registry remains the source of truth for message IDs, contexts, and database identifiers.

To add a language, add its locale code and native display name to `LANGUAGES` in `app/locale.py`, create and translate its `.po` catalog as described below, then compile it. The compiled `.mo` file must be included in the deployed application for that language to appear in the selector.

## Catalog Workflow

Babel is included in the development requirements. Install or refresh the project environment with:

```sh
.venv/bin/pip install -r requirements.txt
```

After changing translatable strings, regenerate the template. The project version should match `pyproject.toml`:

```sh
.venv/bin/pybabel extract -F babel.cfg \
  --project=biblioteq-web \
  --version=0.2.0 \
  --copyright-holder='Chris Charabaruk' \
  --msgid-bugs-address=https://github.com/charabaruk/biblioteq-web/issues \
  -o app/locales/messages.pot .
```

Initialize a language catalog once, replacing `fr` with the target locale code. Edit the resulting `.po` file to provide translations:

```sh
.venv/bin/pybabel init -i app/locales/messages.pot -d app/locales -l fr
```

When the template changes later, update existing catalogs rather than reinitializing them, then compile:

```sh
.venv/bin/pybabel update -i app/locales/messages.pot -d app/locales
.venv/bin/pybabel compile -d app/locales
```

Compilation creates `app/locales/fr/LC_MESSAGES/messages.mo`. Keep the `.pot` and translated `.po` files as source; deploy the compiled `.mo` files with the application because gettext loads those at runtime.
