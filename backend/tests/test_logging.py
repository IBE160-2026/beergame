import io
import json
import logging

import httpx
import pytest
import structlog

from app.main import create_app
from app.platform.logging import ALLOWED_FIELDS, configure_logging


@pytest.fixture
def log_stream():
    stream = io.StringIO()
    configure_logging("info", stream=stream)
    yield stream
    logging.getLogger().handlers[:] = []


def lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


async def test_one_json_line_per_request_with_request_id(log_stream, test_database):
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        response = await c.get("/api/health")
    request_lines = [line for line in lines(log_stream) if line["event"] == "request"]
    assert len(request_lines) == 1
    entry = request_lines[0]
    assert entry["request_id"] == response.headers["x-request-id"]
    assert entry["method"] == "GET"
    assert entry["path"] == "/api/health"
    assert entry["status"] == response.status_code


def test_allowlist_drops_unlisted_keys(log_stream):
    structlog.get_logger("t").info(
        "something", email="kari@example.no", name="Kari", text="free text", game_id="g1"
    )
    (entry,) = lines(log_stream)
    assert entry["event"] == "something"
    assert entry["game_id"] == "g1"
    for key in ("email", "name", "text"):
        assert key not in entry
    assert "kari@example.no" not in log_stream.getvalue()


def test_allowlist_has_no_personal_or_free_text_fields():
    forbidden = ("name", "email", "mail", "text", "message", "explanation", "answer", "body")
    for field in ALLOWED_FIELDS:
        assert not any(word in field for word in forbidden), field


def test_exception_traceback_is_kept(log_stream):
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        structlog.get_logger("t").exception("failed")
    (entry,) = lines(log_stream)
    assert "RuntimeError" in entry["exception"]
