"""FastAPI app. Every route lives under /api (AD-11)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.modules.admin import routes as admin_routes
from app.modules.classes import routes as classes_routes
from app.modules.classes import seed as classes_seed
from app.modules.classes import service as classes_service
from app.modules.debrief import dev as debrief_dev
from app.modules.debrief import routes as debrief_routes
from app.modules.identity import routes as identity_routes
from app.modules.identity import seed as identity_seed
from app.modules.identity import service as identity_service
from app.modules.messaging import message_routes
from app.modules.messaging import routes as messaging_routes
from app.modules.messaging import webhooks as messaging_webhooks
from app.modules.ops import ai_routes as ops_ai_routes
from app.modules.ops import operations_routes as ops_operations_routes
from app.modules.ops import routes as ops_routes
from app.modules.ops import service as ops_service
from app.modules.replay import dev as replay_dev
from app.modules.replay import routes as replay_routes
from app.modules.reports import (
    class_report_jobs,  # noqa: F401  its finish hook (Story 14.1)
    class_report_routes,
)
from app.modules.reports import routes as reports_routes
from app.modules.reports import service as reports_service  # noqa: F401  registers Completion (Story 13.1)
from app.modules.sessions import dev as sessions_dev
from app.modules.sessions import routes as sessions_routes
from app.modules.tests import dev as tests_dev
from app.modules.tests import routes as tests_routes
from app.platform import audit, auth, authz, db, error_reporting, storage
from app.platform.auth import CsrfMiddleware
from app.platform.config import get_settings
from app.platform.errors import error_response
from app.platform.events import stream as event_stream
from app.platform.events.hub import hub as event_hub
from app.platform.logging import RequestLogMiddleware, configure_logging

log = structlog.get_logger("app.main")

router = APIRouter(prefix="/api")


@router.get("/health", dependencies=[Depends(authz.public)])
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
    error_reporting.log_start(settings)  # Story 15.11: the tracker, or that none is set yet
    from app.ai import seed

    await seed.ensure_zero_config_logged()  # AD-17: a default model config with zero keys
    await identity_seed.ensure_demo_users_logged()  # AD-17: local demo Admin and Lecturer
    await classes_seed.ensure_demo_class_logged()  # AD-17: the demo Lecturer's Class (Story 4.1)
    if settings.app_env == "production":
        # AD-17: the first Admin's Invitation, for each listed address with no account yet.
        await identity_service.ensure_bootstrap_invitations(auth.utcnow())
    # Story 15.9: the connections this process holds against the written budget, and the pooler
    # check (`DB_POOLER_SIZE`); a failed check is logged, it does not stop the start.
    await ops_service.report_connections("backend", settings)
    check = ops_service.check_connection_budget(settings)
    (log.warning if check.status == "failed" else log.info)(
        "db_pooler_check",
        status=check.status,
        pooler_size=check.pooler_size,
        pooler_required=check.required,
    )
    yield
    await event_hub.close()  # every open event stream ends (Story 6.4)
    await db.dispose()


async def _not_authenticated(_: Request, exc: authz.NotAuthenticated):
    if isinstance(exc, authz.SessionExpired):
        response = error_response(401, "session_expired", "The session has ended. Log in again.")
        # The dead cookie goes, so «Du er logget ut.» shows once and not on every later visit.
        auth.clear_session_cookie(response)
        return response
    return error_response(401, "not_authenticated", "No valid session.")


async def _forbidden(_: Request, __: authz.Forbidden):
    # The same answer for every refusal, so it never reveals whether an item exists (FR-5).
    return error_response(403, "forbidden", "Your roles do not allow this.")


async def _invalid_request(_: Request, exc: RequestValidationError):
    # The AD-19 envelope also for a body that fails validation; the field names only, never
    # the submitted values (a password could be among them).
    fields = {
        ".".join(str(part) for part in error["loc"][1:]) or "body": error["type"]
        for error in exc.errors()
    }
    return error_response(422, "invalid_request", "The request is not valid.", fields)


async def _class_archived(_: Request, __: Exception):
    # Story 4.10: the one answer to any change of an archived Class, for its Faglærere.
    return classes_routes.class_archived_response()


async def _control_test_class(_: Request, __: Exception):
    # Story 12.7: a Control test Class takes no other staff and no other Class session.
    return classes_routes.control_test_refused()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ØL-spillet API",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.include_router(router)
    app.include_router(event_stream.router)  # the live event stream (Story 6.4, AD-8)
    app.include_router(identity_routes.router)
    app.include_router(identity_routes.admin_router)
    app.include_router(identity_routes.me_router)  # a test student's consent (Story 12.8)
    app.include_router(admin_routes.router)
    app.include_router(classes_routes.router)
    app.include_router(sessions_routes.router)
    app.include_router(sessions_routes.admin_router)  # «Kontrolltest» (Story 12.7)
    app.include_router(tests_routes.router)  # the Starting task (Story 6.3)
    app.include_router(debrief_routes.router)  # the Debrief (Story 9.2)
    app.include_router(message_routes.router)  # Messages from staff (Story 7.9)
    app.include_router(replay_routes.router)  # the Student's Replay (Story 10.3)
    app.include_router(class_report_routes.router)  # the Klasserapport (Story 14.1)
    app.include_router(ops_routes.router)  # «Pseudonymisert eksport» (Story 15.4)
    app.include_router(ops_ai_routes.router)  # «KI-kostnad» (Story 15.5)
    app.include_router(ops_operations_routes.router)  # «Drift» per Class session (Story 15.8)
    app.include_router(reports_routes.router)  # the Studentside's record (Story 13.2)
    app.include_router(messaging_webhooks.router)  # the provider's events (Story 4.6), signed
    if get_settings().app_env != "production":
        app.include_router(messaging_routes.router)  # the dev mailbox (Story 3.6), local only
        app.include_router(sessions_dev.router)  # the dev lock (Story 6.15), local only
        app.include_router(debrief_dev.router)  # Group debrief back-dating (9.11), local only
        app.include_router(replay_dev.router)  # the dev quiz pass (10.5), local only
        app.include_router(tests_dev.router)  # the dev close of a test (12.4), local only
    if storage.uses_mock():
        app.include_router(storage.router)  # the storage mock's downloads (13.7), never in prod
    authz.register_principal_loader(identity_service.load_user)
    # The audit page shows names, read at request time from the module that owns them (AD-14).
    audit.register_labels("user_id", identity_service.user_labels)
    audit.register_labels("invitation_id", identity_service.invitation_labels)
    audit.register_labels("institution_id", identity_service.institution_labels)
    audit.register_labels("access_request_id", identity_service.access_request_labels)
    audit.register_labels("class_session_id", ops_routes.evaluation.class_session_labels)
    audit.register_labels("model_config_id", ops_ai_routes.ai_models.config_labels)
    app.add_exception_handler(authz.NotAuthenticated, _not_authenticated)
    app.add_exception_handler(authz.Forbidden, _forbidden)
    app.add_exception_handler(RequestValidationError, _invalid_request)
    app.add_exception_handler(classes_service.ClassArchived, _class_archived)
    app.add_exception_handler(classes_service.ControlTestClass, _control_test_class)
    app.add_middleware(CsrfMiddleware)
    # Outermost: refused requests are logged too, and each 5xx answer is counted under its Class
    # session through `ops.service` (Story 15.8, NFR-8).
    app.add_middleware(RequestLogMiddleware, on_server_error=ops_service.record_api_error)
    return app


# Configure at import so uvicorn's own startup lines are JSON too; this also
# runs the production guard before the server binds its port.
configure_logging(get_settings().log_level)
app = create_app()
