"""Application entrypoint: `uvicorn app.main:app`."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.config import get_settings
from app.locale import LanguageMiddleware
from app.routes import covers, health, pages
from app.templating import BASE_DIR, templates


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app = FastAPI(
        title="biblioteq-web",
        root_path=settings.root_path,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.include_router(health.router)
    app.include_router(pages.router)
    app.include_router(covers.router)
    app.add_middleware(LanguageMiddleware, templates=templates)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"types": [], "status": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )

    return app


app = create_app()
