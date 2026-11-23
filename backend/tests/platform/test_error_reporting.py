"""The error-reporting adapter (Story 15.11, AD-17, AD-14): one interface, a DSN from the
environment, a recording mock without one outside production, and reports built from the error's
class, stack and allowlisted ids only. No test reaches a tracker: the DSN reporter is given a fake
transport that keeps the bytes it would send."""

import json
import threading

import pytest
from structlog.testing import capture_logs

from app.platform import error_reporting
from app.platform.config import ConfigError, Settings, load_settings, parse_dsn
from app.platform.error_reporting import (
    DsnReporter,
    LogOnlyReporter,
    RecordingReporter,
    build_report,
    capture,
    envelope,
    get_reporter,
    use_reporter,
)

DSN = "https://publickey123@tracker.example.eu/42"

NAME = "Kari Nordmann"
EMAIL = "kari.nordmann@example.com"
EXPLANATION = "Jeg bestilte for mye fordi etterspørselen steg brått i uke fem"
PERSONAL = (NAME, "Nordmann", EMAIL, "kari.nordmann", "Jeg bestilte", "etterspørselen", "brått")


class FakeTransport:
    """Keeps what the DSN reporter would post."""

    def __init__(self, status: int = 200, fail: bool = False) -> None:
        self.sent: list[tuple[str, dict[str, str], bytes]] = []
        self.status = status
        self.fail = fail
        self.release = threading.Event()
        self.release.set()

    def __call__(self, url: str, headers: dict[str, str], body: bytes) -> int:
        self.release.wait(5)
        self.sent.append((url, headers, body))
        if self.fail:
            raise ConnectionError(f"tracker down for {EMAIL}")
        return self.status


def assert_no_personal_data(raw: bytes) -> None:
    # JSON escapes `ø` and `å`; both spellings are checked.
    text = raw.decode()
    escaped = json.dumps(text)
    for term in PERSONAL:
        assert term not in text and json.dumps(term)[1:-1] not in escaped, term


def _raise_with_personal_data() -> None:
    name, email, explanation = NAME, EMAIL, EXPLANATION  # noqa: F841 - locals in scope
    try:
        raise KeyError(email)
    except KeyError as inner:
        raise ValueError(f"{name} <{email}> wrote: {explanation}") from inner


def _caught() -> BaseException:
    try:
        _raise_with_personal_data()
    except ValueError as exc:
        return exc
    raise AssertionError("no error")


def test_a_report_holds_the_class_the_chain_the_frames_and_the_allowlisted_ids_only():
    report = build_report(
        _caught(),
        {
            "request_id": "0195f3c4-aaaa-7bbb-8ccc-0123456789ab",
            "game_id": "0195f3c4-aaaa-7bbb-8ccc-0123456789ac",
            "status": 500,
            "user_id": "0195f3c4-aaaa-7bbb-8ccc-0123456789ad",  # not an allowed id
            "email": EMAIL,  # not an allowed id
            "task": "a task with spaces",  # not an id value
        },
    )
    assert [part.type for part in report.chain] == ["KeyError", "ValueError"]
    assert report.error_type == "builtins.ValueError"
    assert dict(report.ids) == {
        "request_id": "0195f3c4-aaaa-7bbb-8ccc-0123456789ab",
        "game_id": "0195f3c4-aaaa-7bbb-8ccc-0123456789ac",
        "status": "500",
    }
    frames = report.chain[-1].frames
    assert [f.function for f in frames] == ["_caught", "_raise_with_personal_data"]
    assert frames[0].filename == "tests/platform/test_error_reporting.py"
    assert frames[0].module == "tests.platform.test_error_reporting" and not frames[0].in_app
    assert report.app_env == "test" and len(report.event_id) == 32
    assert_no_personal_data(envelope(report))


def test_the_envelope_is_a_sentry_event_without_message_request_user_or_vars():
    raw = envelope(build_report(_caught(), {"request_id": "r-1"}))
    header, item, event_line, end = raw.split(b"\n")
    assert end == b""
    assert json.loads(item) == {"type": "event", "length": len(event_line)}
    event = json.loads(event_line)
    assert json.loads(header)["event_id"] == event["event_id"]
    assert set(event) == {
        "event_id",
        "timestamp",
        "platform",
        "level",
        "logger",
        "environment",
        "tags",
        "exception",
        "sdk",
    }
    assert event["tags"] == {"request_id": "r-1"}
    last = event["exception"]["values"][-1]
    assert set(last) == {"type", "module", "mechanism", "stacktrace"}  # no `value`
    assert set(last["stacktrace"]["frames"][0]) == {
        "filename",
        "module",
        "function",
        "lineno",
        "in_app",
    }


def test_app_frames_are_shown_from_the_app_directory_and_marked_in_app():
    from app.platform import config

    try:
        config.parse_dsn("not a dsn")
    except ValueError as exc:
        frames = build_report(exc, {}).chain[-1].frames
    assert frames[-1].filename == "app/platform/config.py"
    assert frames[-1].module == "app.platform.config" and frames[-1].in_app


def test_the_dsn_reporter_posts_one_envelope_to_the_trackers_endpoint():
    transport = FakeTransport()
    reporter = DsnReporter(DSN, transport)
    with use_reporter(reporter):
        capture(
            _caught(), request_id="r-2", class_session_id="0195f3c4-aaaa-7bbb-8ccc-0123456789ae"
        )
    assert reporter.flush(5)
    [(url, headers, body)] = transport.sent
    assert url == "https://tracker.example.eu/api/42/envelope/"
    assert headers["X-Sentry-Auth"] == (
        "Sentry sentry_version=7, sentry_key=publickey123, sentry_client=olspillet/1"
    )
    assert_no_personal_data(body)
    assert b'"class_session_id":"0195f3c4-aaaa-7bbb-8ccc-0123456789ae"' in body


def test_a_dsn_with_a_port_and_a_path_prefix_keeps_both():
    dsn = parse_dsn("http://k@localhost:8000/errors/7")
    assert dsn.envelope_url == "http://localhost:8000/errors/api/7/envelope/"


def test_a_tracker_that_fails_or_refuses_is_logged_by_type_and_never_reaches_the_caller():
    for transport, expected in (
        (FakeTransport(fail=True), {"exc_type": "ConnectionError"}),
        (FakeTransport(status=429), {"status": 429}),
    ):
        reporter = DsnReporter(DSN, transport)
        with capture_logs() as logs, use_reporter(reporter):
            capture(_caught())  # returns at once and raises nothing
            assert reporter.flush(5)
        [failed] = [e for e in logs if e["event"] == "error_report_failed"]
        assert {k: failed[k] for k in expected} == expected
        assert EMAIL not in str(logs)


def test_a_full_queue_drops_the_report_and_says_so():
    transport = FakeTransport()
    transport.release.clear()  # the sender is stuck on the first report
    reporter = DsnReporter(DSN, transport)
    with capture_logs() as logs, use_reporter(reporter):
        for _ in range(error_reporting.QUEUE_SIZE + 3):
            capture(_caught())
    dropped = [e for e in logs if e["event"] == "error_report_dropped"]
    assert 1 <= len(dropped) <= 3
    transport.release.set()
    assert reporter.flush(10)


def test_a_failure_to_build_a_report_never_raises(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError(EMAIL)

    monkeypatch.setattr(error_reporting, "build_report", broken)
    with capture_logs() as logs:
        capture(_caught())
    assert [(e["event"], e["exc_type"]) for e in logs] == [("error_report_failed", "RuntimeError")]


@pytest.mark.parametrize(
    ("env", "dsn", "kind"),
    [
        ("test", "", RecordingReporter),
        ("local", "", RecordingReporter),
        ("ci", "", RecordingReporter),
        ("production", "", LogOnlyReporter),
        ("test", DSN, DsnReporter),
    ],
)
def test_the_reporter_follows_the_dsn_and_the_environment(monkeypatch, env, dsn, kind):
    from app.platform.config import get_settings

    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("ERROR_TRACKER_DSN", dsn)
    monkeypatch.setattr(Settings, "production_problems", lambda self: [])
    get_settings.cache_clear()
    assert type(get_reporter()) is kind
    assert get_reporter() is get_reporter()  # one per process
    with capture_logs() as logs:
        error_reporting.log_start(get_settings())
    if kind is LogOnlyReporter:
        assert [e["event"] for e in logs] == ["error_tracker_not_configured"]
        with capture_logs() as logs:
            capture(_caught(), request_id="r-3")
        assert [(e["event"], e["request_id"]) for e in logs] == [("error_report_not_sent", "r-3")]
    get_settings.cache_clear()


def test_the_mock_keeps_the_report_and_logs_ids_only():
    with use_reporter(RecordingReporter()) as mock, capture_logs() as logs:
        capture(_caught(), request_id="r-4")
    [report] = mock.reports
    assert report.ids == {"request_id": "r-4"}
    assert [(e["event"], e["exc_type"], e["request_id"]) for e in logs] == [
        ("[errors:mock]", "ValueError", "r-4")
    ]


@pytest.mark.parametrize(
    "dsn",
    [
        "not-a-dsn",
        "https://tracker.example.eu/42",  # no key
        "https://key@tracker.example.eu/",  # no project
        "ftp://key@tracker.example.eu/42",
        "https://key@tracker.example.eu:port/42",
        "https://key@tracker.example.eu/42?x=1",
    ],
)
def test_a_malformed_dsn_refuses_at_load_naming_the_variable_not_its_value(monkeypatch, dsn):
    monkeypatch.setenv("ERROR_TRACKER_DSN", dsn)
    with pytest.raises(ConfigError) as refused:
        load_settings()
    assert "ERROR_TRACKER_DSN" in str(refused.value) and "key@" not in str(refused.value)


def test_production_refuses_a_dsn_without_tls_and_starts_without_one():
    assert (
        "error_tracker_dsn"
        in Settings(
            app_env="production", error_tracker_dsn="http://key@tracker.example.eu/42"
        ).production_problems()
    )
    for dsn in ("", DSN):
        assert (
            "error_tracker_dsn"
            not in Settings(app_env="production", error_tracker_dsn=dsn).production_problems()
        )


def test_an_ipv6_dsn_keeps_its_brackets():
    assert parse_dsn("https://k@[2001:db8::1]:8443/1").envelope_url == (
        "https://[2001:db8::1]:8443/api/1/envelope/"
    )


def test_a_redirect_is_a_failed_send_and_is_not_followed():
    import http.server

    followed = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - the stdlib's name
            if self.path.startswith("/moved"):
                followed.append(self.path)
            self.send_response(307)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/moved")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/1/envelope/"
        assert error_reporting.urllib_post(url, {"X-Sentry-Auth": "k"}, b"{}") == 307
    finally:
        server.shutdown()
        server.server_close()
    assert followed == []  # the key never went to the redirect's target


def test_a_config_error_while_reporting_never_raises(monkeypatch):
    def refused(*args, **kwargs):
        raise ConfigError("Invalid configuration: ERROR_TRACKER_DSN")

    monkeypatch.setattr(error_reporting, "build_report", refused)
    with capture_logs() as logs:
        capture(_caught())
    assert [(e["event"], e["exc_type"]) for e in logs] == [("error_report_failed", "ConfigError")]


def test_the_mock_keeps_a_bounded_number_of_reports():
    mock = RecordingReporter(keep=2)
    with use_reporter(mock), capture_logs():
        for _ in range(3):
            capture(_caught())
    assert len(mock.reports) == 2
