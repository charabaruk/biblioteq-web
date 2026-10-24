"""HTML pages: home, search, browse and item detail."""

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import Connection

from app import repository
from app.config import get_settings
from app.db import get_conn
from app.deps import get_catalog, require_type
from app.repository import Catalog
from app.templating import templates

router = APIRouter()

ItemId = Annotated[int, Path(ge=0, le=2**63 - 1)]
PageNo = Annotated[int, Query(ge=1, le=100000)]
HOME_RECENT = 6


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_catalog),
):
    sections = [
        (spec, repository.recent(conn, spec, HOME_RECENT)) for spec in catalog.types.values()
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"types": catalog.types.values(), "sections": [s for s in sections if s[1]]},
    )


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: Annotated[str, Query(max_length=200)] = "",
    type: Annotated[str, Query(max_length=40)] = "",
    page: PageNo = 1,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_catalog),
):
    selected = [type] if type in catalog.types else []
    settings = get_settings()
    result = repository.search(
        conn, catalog, q, selected, page, settings.page_size, settings.title_sort
    )
    pager = "/search?" + urlencode({"q": q, "type": type})
    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "types": catalog.types.values(),
            "q": q,
            "selected_type": type,
            "result": result,
            "pager": pager,
            "type_labels": {k: v.label for k, v in catalog.types.items()},
        },
    )


@router.get("/browse/{type_key}", response_class=HTMLResponse)
def browse(
    request: Request,
    type_key: str,
    page: PageNo = 1,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_catalog),
):
    spec = require_type(type_key, catalog)
    settings = get_settings()
    result = repository.search(
        conn, catalog, "", [spec.key], page, settings.page_size, settings.title_sort
    )
    return templates.TemplateResponse(
        request,
        "browse.html",
        {
            "types": catalog.types.values(),
            "spec": spec,
            "result": result,
            "pager": f"/browse/{spec.key}?",
            "type_labels": {k: v.label for k, v in catalog.types.items()},
        },
    )


@router.get("/item/{type_key}/{item_id}", response_class=HTMLResponse)
def item_detail(
    request: Request,
    type_key: str,
    item_id: ItemId,
    conn: Connection = Depends(get_conn),
    catalog: Catalog = Depends(get_catalog),
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
    catalog: Catalog = Depends(get_catalog),
):
    """One tab: a fragment for the tab script, the whole item page for everyone else."""
    spec = require_type(type_key, catalog)
    if not any(t.key == tab_key for t in spec.tabs):
        raise HTTPException(status_code=404, detail="Unknown tab")
    if request.headers.get("x-requested-with") == "fetch":
        tab = repository.get_tab(conn, spec, item_id, tab_key)
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
