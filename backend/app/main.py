"""FastAPI app. Every route lives under /api (AD-11)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from app.platform import db
from app.platform.config import get_settings
from app.platform.logging import RequestLogMiddleware, configure_logging

log = structlog.get_logger("app.main")


def error_response(status: int, code: str, message: str, fields: dict | None = None):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "fields": fields or {}}},
    )


router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    try:
        await db.ping()
    except Exception as exc:
        log.error("health_db_unavailable", error_code="db_unavailable", exc_type=type(exc).__name__)
        return error_response(503, "db_unavailable", "The database cannot be reached.")
    return {"status": "ok"}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()  # refuses to start on a bad production config
    log.info("startup", app_env=settings.app_env)
    yield
    await db.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ØL-spillet API",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.include_router(router)
    app.add_middleware(RequestLogMiddleware)
    return app


# Configure at import so uvicorn's own startup lines are JSON too; this also
# runs the production guard before the server binds its port.
configure_logging(get_settings().log_level)
app = create_app()
