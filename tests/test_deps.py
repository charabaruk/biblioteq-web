from gettext import NullTranslations
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app import deps
from app.item_types import ITEM_TYPES
from app.repository import Catalog


def test_get_cache_returns_application_cache():
    cache = object()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(cache=cache)))

    assert deps.get_cache(request) is cache


def test_get_catalog_loads_once_with_configured_schema(monkeypatch):
    catalog = Catalog(types={}, has_borrowers=False)
    connection = object()
    loader = Mock(return_value=catalog)
    monkeypatch.setattr(deps, "_catalog", None)
    monkeypatch.setattr(deps, "load_catalog", loader)
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(db_schema="archive"))

    assert deps.get_catalog(conn=connection) is catalog
    assert deps.get_catalog(conn=connection) is catalog
    loader.assert_called_once_with(connection, "archive")


def test_get_localized_catalog_returns_localized_registry():
    spec = ITEM_TYPES[0]
    catalog = Catalog(types={spec.key: spec}, has_borrowers=True, has_locations=True)
    request = SimpleNamespace(state=SimpleNamespace(translations=NullTranslations()))

    localized = deps.get_localized_catalog(request, catalog)

    assert localized is not catalog
    assert localized.types[spec.key].label == "Book"
    assert localized.types[spec.key].label_plural == "Books"
    assert catalog.types[spec.key] is spec
    assert localized.types is not catalog.types
    assert localized.has_borrowers is True
    assert localized.has_locations is True


def test_require_type_returns_registered_item_type():
    spec = ITEM_TYPES[0]
    catalog = Catalog(types={spec.key: spec}, has_borrowers=False)

    assert deps.require_type(spec.key, catalog) is spec


def test_require_type_rejects_unknown_item_type():
    catalog = Catalog(types={}, has_borrowers=False)

    with pytest.raises(HTTPException) as error:
        deps.require_type("unknown", catalog)

    assert error.value.status_code == 404
