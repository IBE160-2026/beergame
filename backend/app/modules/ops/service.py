"""Per-session error counts (Story 15.8, NFR-8, FR-29, NFR-9, AD-14): the one writer of
`error_events`.

`record_error` stores one row with ids and codes only, in a transaction of its own, and never
raises: a failure to count an error must not fail what was going on (the sweep, a job, an api
answer). The worker's job-failure hook and the api's 5xx hook live in `platform`, which imports no
module; `worker.py` and `main.py` hand them `record_job_failure` and `record_api_error`.
"""

import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

import structlog

from app.modules.games import service as games
from app.modules.ops.models import ERROR_SOURCES, error_events
from app.platform.db import get_sessionmaker

__all__ = [
    "API_ERROR",
    "CONSERVATION_CHECK",
    "JOB_FAILED",
    "GAME_CHECK_FAILED",
    "SOURCES",
    "record_api_error",
    "record_error",
    "record_game_check_failure",
    "record_job_failure",
]

log = structlog.get_logger(__name__)

CONSERVATION_CHECK, JOB_FAILED, API_ERROR = ERROR_SOURCES
SOURCES = ERROR_SOURCES

_CODE = re.compile(r"^[a-z0-9_.:-]{1,80}$")
REQUEST_ID_MAX = 64


def _as_uuid(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def record_error(
    source: str,
    code: str,
    class_session_id: uuid.UUID | str | None = None,
    request_id: str | None = None,
    *,
    at: datetime | None = None,
) -> bool:
    """Count one error of `source` (`conservation_check`, `job_failed`, `api_error`) with a fixed
    `code`, under its Class session when one is known. Returns whether the row was stored; any
    failure is logged with its type only and swallowed."""
    try:
        if source not in SOURCES:
            raise ValueError("unknown error source")
        if not _CODE.match(code):
            raise ValueError("code is not a fixed technical value")
        if request_id is not None and len(request_id) > REQUEST_ID_MAX:
            request_id = None
        async with get_sessionmaker().begin() as session:
            await session.execute(
                error_events.insert().values(
                    id=uuid.uuid7(),
                    source=source,
                    code=code,
                    class_session_id=_as_uuid(class_session_id),
                    request_id=request_id,
                    occurred_at=at or datetime.now(UTC),
                )
            )
    except Exception as exc:  # the type only: a message may hold personal data
        log.warning("error_record_failed", error_code=source, exc_type=type(exc).__name__)
        return False
    return True


async def _session_of_kwargs(kwargs: Mapping[str, object]) -> uuid.UUID | None:
    found = _as_uuid(kwargs.get("class_session_id"))
    if found is not None:
        return found
    game_id = _as_uuid(kwargs.get("game_id"))
    if game_id is None:
        return None
    return await games.class_session_of(game_id)


GAME_CHECK_FAILED = "game_check_failed"


async def record_game_check_failure(game_id: str, *, at: datetime | None = None) -> bool:
    """The sweep's finished-game check found a violation (FR-29): count it under the Game's
    Class session (a Class game, a played-out one or a Replay)."""
    try:
        session_id = await games.class_session_of(game_id)
    except Exception as exc:
        log.warning(
            "error_record_failed", error_code=CONSERVATION_CHECK, exc_type=type(exc).__name__
        )
        session_id = None
    return await record_error(CONSERVATION_CHECK, GAME_CHECK_FAILED, session_id, at=at)


async def record_job_failure(task_name: str, task_kwargs: Mapping[str, object], job_id: object):
    """The worker's hook (`platform.jobs.run_worker(on_failure=...)`): a job failed for good. The
    Class session comes from a `class_session_id` argument or the Game of a `game_id` argument."""
    try:
        session_id = await _session_of_kwargs(task_kwargs)
    except Exception as exc:
        log.warning("error_record_failed", error_code=JOB_FAILED, exc_type=type(exc).__name__)
        session_id = None
    code = task_name if _CODE.match(task_name or "") else "unknown_task"
    return await record_error(JOB_FAILED, code, session_id, None if job_id is None else str(job_id))


async def record_api_error(status: int, path_ids: Mapping[str, str], request_id: str | None):
    """The api's hook (`RequestLogMiddleware(on_server_error=...)`): an answer of 5xx, placed
    under the Class session its path names (`class_session_id` or `session_id`) or the Class
    session of the Game it names (`game_id`)."""
    ids = dict(path_ids)
    if "class_session_id" not in ids and "session_id" in ids:
        ids["class_session_id"] = ids["session_id"]
    try:
        session_id = await _session_of_kwargs(ids)
    except Exception as exc:
        log.warning("error_record_failed", error_code=API_ERROR, exc_type=type(exc).__name__)
        session_id = None
    return await record_error(API_ERROR, f"http_{status}", session_id, request_id)
