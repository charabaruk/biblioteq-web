"""HTML pages: home, search, browse and item detail."""

from typing import Annotated
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Connection

from app import repository
from app.config import get_settings
from app.db import get_conn
from app.deps import get_localized_catalog, require_type
from app.locale import LANGUAGE_COOKIE, available_languages
from app.repository import Catalog
from app.templating import templates

router = APIRouter()

ItemId = Annotated[int, Path(ge=0, le=2**63 - 1)]
PageNo = Annotated[int, Query(ge=1, le=100000)]
LocationFilter = Annotated[str, Query(max_length=500)]
HOME_RECENT = 6


def _local_redirect_target(target: str, root_path: str) -> str:
    parsed = urlsplit(target)
    if (
        not target.startswith("/")
        or target.startswith("//")
        or "\\" in target
        or parsed.scheme
        or parsed.netloc
    ):
        return f"{root_path}/"
    if root_path and target != root_path and not target.startswith(f"{root_path}/"):
        return f"{root_path}/"
    return target


@router.get("/language")
def select_language(
    request: Request,
    lang: Annotated[str, Query(max_length=32)],
    next_path: Annotated[str, Query(alias="next", max_length=2048)] = "/",
) -> RedirectResponse:
    if lang not in {option.code for option in available_languages()}:
        raise HTTPException(status_code=400, detail="Unsupported language")
    root_path = request.scope.get("root_path", "")
    response = RedirectResponse(_local_redirect_target(next_path, root_path), status_code=303)
    response.set_cookie(
        LANGUAGE_COOKIE,
        lang,
        max_age=31536000,
        path=root_path or "/",
        secure=request.url.scheme == "https",
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_localized_catalog),
):
    sections = [
        (spec, repository.recent(conn, spec, HOME_RECENT)) for spec in catalog.types.values()
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"types": catalog.types.values(), "sections": [s for s in sections if s[1]]},
    )


@router.get("/location/{name:path}", response_class=HTMLResponse)
def location(
    request: Request,
    name: Annotated[str, Path(max_length=500)],
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_localized_catalog),
):
    unknown = name == repository.UNKNOWN_LOCATION
    specs = (
        repository.types_without_location(conn, catalog)
        if unknown
        else repository.location_types(conn, catalog, name)
    )
    if not specs and not unknown:
        return RedirectResponse(f"{request.scope.get('root_path', '')}/")
    sections = [(spec, repository.recent(conn, spec, HOME_RECENT, name)) for spec in specs]
    return templates.TemplateResponse(
        request,
        "location.html",
        {
            "types": catalog.types.values(),
            "location": name,
            "unknown": unknown,
            "sections": [s for s in sections if s[1]],
        },
    )


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: Annotated[str, Query(max_length=200)] = "",
    type: Annotated[str, Query(max_length=40)] = "",
    location: LocationFilter = "",
    page: PageNo = 1,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_localized_catalog),
):
    selected = [type] if type in catalog.types else []
    settings = get_settings()
    result = repository.search(
        conn,
        catalog,
        q,
        selected,
        page,
        settings.page_size,
        settings.title_sort,
        location or None,
    )
    pager = "/search?" + urlencode(
        {"q": q, "type": type, **({"location": location} if location else {})}
    )
    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "types": catalog.types.values(),
            "q": q,
            "selected_type": type,
            "location": location,
            "locations": repository.location_options(conn, catalog),
            "result": result,
            "pager": pager,
            "type_labels": {k: v.label for k, v in catalog.types.items()},
        },
    )


@router.get("/browse/{type_key}", response_class=HTMLResponse)
def browse(
    request: Request,
    type_key: str,
    location: LocationFilter = "",
    page: PageNo = 1,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_localized_catalog),
):
    spec = require_type(type_key, catalog)
    settings = get_settings()
    result = repository.search(
        conn,
        catalog,
        "",
        [spec.key],
        page,
        settings.page_size,
        settings.title_sort,
        location or None,
    )
    return templates.TemplateResponse(
        request,
        "browse.html",
        {
            "types": catalog.types.values(),
            "spec": spec,
            "location": location,
            "result": result,
            "pager": f"/browse/{spec.key}?"
            + (urlencode({"location": location}) if location else ""),
            "type_labels": {k: v.label for k, v in catalog.types.items()},
        },
    )


@router.get("/item/{type_key}/{item_id}", response_class=HTMLResponse)
def item_detail(
    request: Request,
    type_key: str,
    item_id: ItemId,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_localized_catalog),
):
    spec = require_type(type_key, catalog)
    item = repository.get_item(conn, catalog, spec, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse(
        request, "item.html", {"types": catalog.types.values(), "item": item, "spec": spec}
    )


@router.get("/item/{type_key}/{item_id}/{tab_key}", response_class=HTMLResponse)
def item_tab(
    request: Request,
    type_key: str,
    item_id: ItemId,
    tab_key: str,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_localized_catalog),
):
    """One tab: a fragment for the tab script, the whole item page for everyone else."""
    spec = require_type(type_key, catalog)
    if not any(t.key == tab_key for t in spec.tabs):
        raise HTTPException(status_code=404, detail="Unknown tab")
    if request.headers.get("x-requested-with") == "fetch":
        tab = repository.get_tab(conn, catalog, spec, item_id, tab_key)
        if tab is None:
            raise HTTPException(status_code=404, detail="Item not found")
        response = templates.TemplateResponse(
            request, "item/fragment.html", {"spec": spec, "tab": tab}
        )
    else:
        item = repository.get_item(conn, catalog, spec, item_id, load=tab_key)
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")
        response = templates.TemplateResponse(
            request, "item.html", {"types": catalog.types.values(), "item": item, "spec": spec}
        )
    response.headers["Vary"] = "X-Requested-With"
    return response
