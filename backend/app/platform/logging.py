"""structlog JSON logging with a field allowlist.

Every line is one JSON object. An allowlist processor drops any key not
listed below, so names, emails and free text cannot reach the logs even
if a caller passes them (spine: Logging convention, AD-14).
"""

import asyncio
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import IO, Any

import structlog
from structlog.types import EventDict, WrappedLogger

# Only ids, codes, numbers and fixed technical values. Never add a name,
# email or free-text field here.
ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "event",
        "exception",
        "level",
        "timestamp",
        "logger",
        "request_id",
        "method",
        "path",
        "status",
        "duration_ms",
        "error_code",
        "exc_type",
        "app_env",
        "revision",
        "game_id",
        "seat_id",
        "user_id",
        "week",
        "job_id",
        "check_id",
        "violation_count",
        # The mail pipeline (Story 3.5): ids, kinds and counts only, never an address.
        "delivery_id",
        "notice_id",
        "kind",
        "notice_count",
        "provider_ref",
        "action",
        # The connection budget at a process's start (Story 15.9): a service name and counts.
        "process",
        "sqlalchemy_pool",
        "procrastinate_pool",
        "db_listen",
        "db_total",
        "db_budget",
        "within_budget",
        "pooler_size",
        "pooler_required",
    }
)


def allowlist(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    return {k: v for k, v in event_dict.items() if k in ALLOWED_FIELDS}


def configure_logging(level: str = "info", stream: IO[str] | None = None) -> None:
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            allowlist,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers[:] = []
        lg.propagate = True
    # One line per request comes from RequestLogMiddleware instead.
    logging.getLogger("uvicorn.access").disabled = True


ServerErrorHook = Callable[[int, dict[str, str], str], Awaitable[object]]
"""`(status, the matched route's id path parameters, request id)`: told of each 5xx answer."""

PATH_IDS = ("class_session_id", "session_id", "game_id")
"""The path parameters a 5xx is placed by: a Class session's id (named either way) or a Game's."""

HOOK_TIMEOUT_S = 2.0
"""The longest a 5xx answer's hook may hold the request: an outage must not grow by it."""


def _path_ids(scope: dict) -> dict[str, str]:
    """The matched route's `PATH_IDS` that are UUIDs, as strings."""
    found = {}
    for name in PATH_IDS:
        value = (scope.get("path_params") or {}).get(name)
        try:
            if value is not None:
                found[name] = str(uuid.UUID(str(value)))
        except ValueError:
            continue
    return found


class RequestLogMiddleware:
    """Pure ASGI middleware: binds request_id and writes one line per request. With
    `on_server_error` it also tells that hook of each answer of 5xx, an unhandled exception
    included (Story 15.8); a failing hook is logged by type and changes nothing. `platform`
    imports no module, so `main.py` passes the hook."""

    def __init__(self, app: Any, on_server_error: ServerErrorHook | None = None) -> None:
        self.app = app
        self.on_server_error = on_server_error
        self.log = structlog.get_logger("app.request")

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid7())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        status = 500
        cancelled = False

        async def send_wrapper(message: dict) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except asyncio.CancelledError:
            cancelled = True  # a dropped connection or shutdown: no answer, so no 5xx
            raise
        finally:
            self.log.info(
                "request",
                method=scope["method"],
                path=scope["path"],
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
            )
            if status >= 500 and not cancelled and self.on_server_error is not None:
                try:
                    await asyncio.wait_for(
                        self.on_server_error(status, _path_ids(scope), request_id), HOOK_TIMEOUT_S
                    )
                except Exception as exc:
                    self.log.warning("server_error_hook_failed", exc_type=type(exc).__name__)
            structlog.contextvars.clear_contextvars()
