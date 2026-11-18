"""`scripts/smoke` against a stub proxy in this process (Story 3.14). CI runs the script itself
against `docker compose`."""

import importlib.machinery
import importlib.util
import io
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke"

HEALTHY = {
    "/api/health": (200, '{"status":"ok"}'),
    "/print/smoke": (404, ""),
    "/": (200, '<!DOCTYPE html><html><script src="/_next/static/a.js"></script></html>'),
}


def load_smoke():
    loader = importlib.machinery.SourceFileLoader("smoke", str(SCRIPT))
    spec = importlib.util.spec_from_loader("smoke", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


smoke = load_smoke()


@pytest.fixture
def stub() -> Iterator[tuple[str, dict[str, tuple[int, str]]]]:
    routes = dict(HEALTHY)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server's name)
            status, body = routes.get(self.path, (500, "no route"))
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", routes
    server.shutdown()
    server.server_close()


def run(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    code = smoke.main(argv, out=out, sleep=lambda _: None)
    return code, out.getvalue()


def test_a_healthy_stack_passes(stub):
    base, _ = stub
    code, out = run([base + "/"])
    assert code == 0
    assert "FAIL" not in out
    assert "smoke ok: 0 of 3 requests failed" in out


@pytest.mark.parametrize(
    "path,answer,expected",
    [
        ("/print/smoke", (200, "<html>print</html>"), "/print/smoke answered 200, expected 404"),
        ("/print/smoke", (404, '<html><a href="/_next/x">'), "404 from the frontend"),
        ("/api/health", (503, '{"error":"db"}'), "/api/health answered 503"),
        ("/api/health", (200, "ok"), '/api/health did not answer {"status": "ok"}'),
        ("/", (200, "<html>plain</html>"), "/ is not a page served by the frontend"),
        ("/", (502, ""), "/ answered 502"),
    ],
)
def test_each_broken_rule_is_reported_and_fails(stub, path, answer, expected):
    base, routes = stub
    routes[path] = answer
    code, out = run([base])
    assert code == 1
    [line] = [line for line in out.splitlines() if " FAIL " in line]
    assert expected in line
    assert line[:4].isdigit() and line[19] == "Z"  # a UTC time comes first


def test_watch_reports_every_failed_request_as_it_happens(stub):
    base, routes = stub
    ticks = iter([0.0, 0.0, 1.0, 5.0])  # deadline at 3: three rounds
    rounds = []

    def sleep(_):
        rounds.append(1)
        if len(rounds) == 1:
            routes["/print/smoke"] = (200, "")  # breaks between round 1 and 2
        else:
            routes["/print/smoke"] = HEALTHY["/print/smoke"]

    out = io.StringIO()
    code = smoke.main([base, "--watch", "3"], out=out, sleep=sleep, clock=lambda: next(ticks))
    assert code == 1
    assert out.getvalue().count(" FAIL ") == 1
    assert "1 of 9 requests failed" in out.getvalue()


def test_a_proxy_that_hangs_up_fails_every_check():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()

    def hang_up():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            conn.close()

    threading.Thread(target=hang_up, daemon=True).start()
    try:
        code, out = run([f"http://127.0.0.1:{server.getsockname()[1]}"])
    finally:
        server.close()
    assert code == 1
    assert out.count(" FAIL ") == 3
    assert "health: request failed" in out


def test_a_malformed_answer_is_reported_not_raised():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()

    def garbage():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            conn.recv(1024)
            conn.sendall(b"NOT-HTTP\r\n\r\n")
            conn.close()

    threading.Thread(target=garbage, daemon=True).start()
    try:
        code, out = run([f"http://127.0.0.1:{server.getsockname()[1]}"])
    finally:
        server.close()
    assert code == 1
    assert out.count(" FAIL ") == 3


def test_a_base_url_without_a_scheme_fails_with_a_line_per_check():
    code, out = run(["olspillet.example"])
    assert code == 1
    assert out.count(" FAIL ") == 3
