"""Error reporting to an external tracker behind one interface (Story 15.11, AD-17, AD-14, NFR-4).

A report is built from structure, never scrubbed from text: the error's class, its chain, and per
stack frame the file, module, function and line number, plus allowlisted ids. The exception's
message and arguments, frame locals, source lines, request headers and bodies are never read, so
no name, e-mail or free text can leave the process however it got into the error.

Reporters:

- `DsnReporter` sends each report as a Sentry envelope to the tracker named by
  `ERROR_TRACKER_DSN` (Sentry, GlitchTip and Bugsink accept it; the tool is the founder's open
  decision, issue #28). It sends from one daemon thread through a bounded queue, so a slow or
  down tracker never holds a request or a job; a full queue drops the report.
- `RecordingReporter` keeps reports in memory and logs `[errors:mock]` with ids only: the
  reporter when the DSN is empty and `APP_ENV` is local, test or ci.
- `LogOnlyReporter` logs that a report was not sent: production with no DSN yet.

`capture(exc, **ids)` never raises. The api's request log middleware and the worker's failure
middleware call it for unhandled exceptions and jobs that fail for good, beside the per-session
count of errors (Story 15.8), which does not depend on the tracker.
"""

import atexit
import json
import queue
import re
import sys
import threading
import traceback
import urllib.error
import urllib.request
import uuid
from collections import deque
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Protocol

import structlog

from app.platform.config import ConfigError, Dsn, Settings, get_settings, parse_dsn

__all__ = [
    "ErrorReport",
    "DsnReporter",
    "LogOnlyReporter",
    "RecordingReporter",
    "Reporter",
    "build_report",
    "capture",
    "envelope",
    "get_reporter",
    "log_start",
    "use_reporter",
]

log = structlog.get_logger(__name__)

ID_KEYS = ("request_id", "class_session_id", "game_id", "job_id", "task", "status")
"""The only ids a report carries. No `user_id`: the tracker is a sub-processor, and a request id
joins a report to the logs and to the per-session error count."""
_ID_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
_TYPE_NAME = re.compile(r"^[A-Za-z0-9_.<>]{1,200}$")
MAX_FRAMES = 50
MAX_CHAIN = 5
QUEUE_SIZE = 50
SEND_TIMEOUT_S = 5
CLIENT = "olspillet/1"

_APP_ROOT = Path(__file__).resolve().parents[2]
"""The backend directory: frames under it are shown as `app/...`."""


@dataclass(frozen=True)
class Frame:
    filename: str
    module: str
    function: str
    lineno: int
    in_app: bool


@dataclass(frozen=True)
class ErrorPart:
    """One exception of the chain: its class and stack, never its message."""

    type: str
    module: str
    frames: tuple[Frame, ...]


@dataclass(frozen=True)
class ErrorReport:
    event_id: str
    occurred_at: datetime
    app_env: str
    release: str | None
    ids: Mapping[str, str]
    chain: tuple[ErrorPart, ...]
    """Oldest first, as trackers expect: the reported exception is the last one."""

    @property
    def error_type(self) -> str:
        last = self.chain[-1]
        return f"{last.module}.{last.type}" if last.module else last.type


def _safe_name(value: object, fallback: str) -> str:
    text = str(value) if isinstance(value, str) else ""
    return text if _TYPE_NAME.match(text) else fallback


def _relative(filename: str) -> tuple[str, bool]:
    """The frame's file without the machine's directories, and whether it is our code."""
    path = filename.replace("\\", "/")
    root = str(_APP_ROOT).replace("\\", "/").rstrip("/") + "/"
    if path.startswith(root):
        rel = path[len(root) :]
        return rel, rel.startswith("app/")
    if "site-packages/" in path:
        return path.rsplit("site-packages/", 1)[1], False
    return path.rsplit("/", 1)[-1], False


def _module_of(rel: str) -> str:
    if not rel.endswith(".py"):
        return ""
    return rel[: -len(".py")].replace("/", ".").removesuffix(".__init__")


def _frames(tb: TracebackType | None) -> tuple[Frame, ...]:
    found = []
    # `walk_tb` yields frame and line only: no locals, no source text is looked up.
    for frame, lineno in traceback.walk_tb(tb):
        code = frame.f_code
        rel, in_app = _relative(code.co_filename)
        found.append(
            Frame(
                filename=_safe_path(rel),
                module=_safe_name(_module_of(rel), ""),
                function=_safe_name(code.co_name, "<unknown>"),
                lineno=int(lineno or 0),
                in_app=in_app,
            )
        )
    return tuple(found[-MAX_FRAMES:])


_PATH = re.compile(r"^[A-Za-z0-9_./<>-]{1,300}$")


def _safe_path(rel: str) -> str:
    return rel if _PATH.match(rel) else "<file>"


def _chain(exc: BaseException) -> tuple[ErrorPart, ...]:
    parts: list[ErrorPart] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(parts) < MAX_CHAIN:
        seen.add(id(current))
        cls = type(current)
        parts.append(
            ErrorPart(
                type=_safe_name(cls.__qualname__, "UnknownError"),
                module=_safe_name(cls.__module__, ""),
                frames=_frames(current.__traceback__),
            )
        )
        if current.__cause__ is not None:
            current = current.__cause__
        elif current.__suppress_context__:
            current = None
        else:
            current = current.__context__
    return tuple(reversed(parts))


def _ids(ids: Mapping[str, object]) -> dict[str, str]:
    kept = {}
    for key in ID_KEYS:
        value = ids.get(key)
        if value is None:
            continue
        text = str(value) if isinstance(value, (str, int, uuid.UUID)) else ""
        if _ID_VALUE.match(text):
            kept[key] = text
    return kept


def build_report(
    exc: BaseException, ids: Mapping[str, object], settings: Settings | None = None
) -> ErrorReport:
    """The report of `exc`: its class, chain and frames, and the allowlisted `ids`. Reads no
    message, argument, local variable or source line."""
    settings = settings or get_settings()
    release = settings.railway_git_commit_sha.strip()
    return ErrorReport(
        event_id=uuid.uuid4().hex,
        occurred_at=datetime.now(UTC),
        app_env=settings.app_env,
        release=release if _ID_VALUE.match(release) else None,
        ids=_ids(ids),
        chain=_chain(exc),
    )


def event_payload(report: ErrorReport) -> dict:
    """The report as a Sentry event: no `value` (message), `request`, `user`, `extra` or vars."""
    event: dict = {
        "event_id": report.event_id,
        "timestamp": report.occurred_at.isoformat(),
        "platform": "python",
        "level": "error",
        "logger": "olspillet",
        "environment": report.app_env,
        "tags": dict(report.ids),
        "exception": {
            "values": [
                {
                    "type": part.type,
                    "module": part.module,
                    "mechanism": {"type": "olspillet", "handled": False},
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": frame.filename,
                                "module": frame.module,
                                "function": frame.function,
                                "lineno": frame.lineno,
                                "in_app": frame.in_app,
                            }
                            for frame in part.frames
                        ]
                    },
                }
                for part in report.chain
            ]
        },
        "sdk": {"name": "olspillet.error_reporting", "version": "1"},
    }
    if report.release:
        event["release"] = report.release
    return event


def envelope(report: ErrorReport) -> bytes:
    """The Sentry envelope of one event: header, item header, item; one JSON line each."""
    event = json.dumps(event_payload(report), separators=(",", ":")).encode()
    lines = [
        json.dumps({"event_id": report.event_id, "sent_at": report.occurred_at.isoformat()}),
        json.dumps({"type": "event", "length": len(event)}),
    ]
    return "\n".join(lines).encode() + b"\n" + event + b"\n"


class Reporter(Protocol):
    def send(self, report: ErrorReport) -> None:
        """Hand `report` on; must not block the caller for long and must not raise."""
        ...


class RecordingReporter:
    """The mock (AD-17): keeps every report in memory, logs ids only."""

    def __init__(self, keep: int = 1000) -> None:
        self.reports: deque[ErrorReport] = deque(maxlen=keep)  # a long local run stays bounded

    def send(self, report: ErrorReport) -> None:
        self.reports.append(report)
        log.info(
            "[errors:mock]",
            exc_type=report.chain[-1].type,
            request_id=report.ids.get("request_id"),
            job_id=report.ids.get("job_id"),
            game_id=report.ids.get("game_id"),
        )


class LogOnlyReporter:
    """Production before the founder has chosen a tracker: the error is in the logs and in
    the per-session error count, and this line says the tracker did not get it."""

    def send(self, report: ErrorReport) -> None:
        log.warning(
            "error_report_not_sent",
            exc_type=report.chain[-1].type,
            request_id=report.ids.get("request_id"),
            job_id=report.ids.get("job_id"),
        )


Transport = Callable[[str, dict[str, str], bytes], int]
"""`(url, headers, body) -> status`: one blocking POST."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is an answer, not a new place to send the key and the report (it could be a
    downgrade to http)."""

    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_post(url: str, headers: dict[str, str], body: bytes) -> int:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _OPENER.open(request, timeout=SEND_TIMEOUT_S) as response:
            return response.status
    except urllib.error.HTTPError as exc:  # a 3xx too: it counts as a failed send
        return exc.code


class DsnReporter:
    """Sends envelopes to the tracker the DSN names, from one daemon thread."""

    def __init__(self, dsn: Dsn | str, transport: Transport | None = None) -> None:
        self.dsn = parse_dsn(dsn) if isinstance(dsn, str) else dsn
        self.transport = transport or urllib_post
        self._queue: queue.Queue[ErrorReport] = queue.Queue(maxsize=QUEUE_SIZE)
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        # A report queued just before the process ends (a worker stopping on its last failure,
        # a deploy) is still tried, for at most two seconds.
        atexit.register(self.flush, 2.0)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/x-sentry-envelope",
            "X-Sentry-Auth": (
                f"Sentry sentry_version=7, sentry_key={self.dsn.public_key}, sentry_client={CLIENT}"
            ),
        }

    def send(self, report: ErrorReport) -> None:
        try:
            self._queue.put_nowait(report)
        except queue.Full:
            log.warning("error_report_dropped", exc_type=report.chain[-1].type)
            return
        self._ensure_thread()

    def _ensure_thread(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="error-reporting", daemon=True
                )
                self._thread.start()

    def _run(self) -> None:
        while True:
            report = self._queue.get()
            try:
                self.deliver(report)
            finally:
                self._queue.task_done()

    def deliver(self, report: ErrorReport) -> bool:
        """Post one report now; logs a failure by type and status only."""
        try:
            status = self.transport(self.dsn.envelope_url, self.headers, envelope(report))
        except Exception as exc:
            log.warning("error_report_failed", exc_type=type(exc).__name__)
            return False
        if not 200 <= status < 300:
            log.warning("error_report_failed", status=status)
            return False
        return True

    def flush(self, timeout: float = 5.0) -> bool:
        """Wait until every queued report was tried; False when `timeout` passed first."""
        done = threading.Event()

        def wait() -> None:
            self._queue.join()
            done.set()

        threading.Thread(target=wait, daemon=True).start()
        return done.wait(timeout)


_made: list[tuple[Settings, Reporter]] = []
_override: list[Reporter] = []


def reporter_for(settings: Settings) -> Reporter:
    kind = reporter_for_kind(settings)
    if kind == "dsn":
        return DsnReporter(settings.error_tracker_dsn)
    return LogOnlyReporter() if kind == "log_only" else RecordingReporter()


def get_reporter() -> Reporter:
    """The reporter of this process, made once from the settings (`use_reporter` in tests)."""
    if _override:
        return _override[-1]
    settings = get_settings()
    if not _made or _made[0][0] is not settings:  # settings loaded again (tests): made again
        _made[:] = [(settings, reporter_for(settings))]
    return _made[0][1]


def log_start(settings: Settings) -> None:
    """At a process's start: which reporter it uses. In production with no DSN this is the
    warning that reports are not sent (the tool is open, issue #28)."""
    reporter = reporter_for_kind(settings)
    if reporter == "log_only":
        log.warning("error_tracker_not_configured", app_env=settings.app_env)
    else:
        log.info("error_tracker", kind=reporter, app_env=settings.app_env)


def reporter_for_kind(settings: Settings) -> str:
    if settings.error_tracker_dsn:
        return "dsn"
    return "log_only" if settings.app_env == "production" else "mock"


@contextmanager
def use_reporter(reporter: Reporter) -> Iterator[Reporter]:
    _override.append(reporter)
    try:
        yield reporter
    finally:
        _override.remove(reporter)


def capture(exc: BaseException, **ids: object) -> None:
    """Report `exc` with the allowlisted `ids`. Never raises; a failure is logged by type."""
    try:
        get_reporter().send(build_report(exc, ids))
    except (Exception, ConfigError) as failure:  # the type only, never the error's text
        try:
            log.warning("error_report_failed", exc_type=type(failure).__name__)
        except Exception:
            print("error_report_failed", file=sys.stderr)
