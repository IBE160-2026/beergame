"""structlog JSON logging with a field allowlist.

Every line is one JSON object. An allowlist processor drops any key not
listed below, so names, emails and free text cannot reach the logs even
if a caller passes them (spine: Logging convention, AD-14).
"""

import logging
import sys
import time
import uuid
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


class RequestLogMiddleware:
    """Pure ASGI middleware: binds request_id and writes one line per request."""

    def __init__(self, app: Any) -> None:
        self.app = app
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
        finally:
            self.log.info(
                "request",
                method=scope["method"],
                path=scope["path"],
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
            )
            structlog.contextvars.clear_contextvars()
