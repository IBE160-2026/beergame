"""Static checks of the proxy routing (AD-11). The live check is `docker compose up`
and curl through :8080; Playwright against compose arrives with a later story."""

import re
from pathlib import Path

CADDYFILE = Path(__file__).resolve().parents[2] / "proxy" / "Caddyfile"


def handle_blocks() -> dict[str, str]:
    text = re.sub(r"#.*", "", CADDYFILE.read_text(encoding="utf-8"))
    blocks: dict[str, str] = {}
    for match in re.finditer(r"handle(\s+\S+)?\s*\{", text):
        start, depth, i = match.end(), 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        blocks[(match.group(1) or "").strip() or "*"] = text[start : i - 1]
    return blocks


def matchers() -> dict[str, list[str]]:
    text = CADDYFILE.read_text(encoding="utf-8")
    return {m[1]: m[2].split() for m in re.finditer(r"^\s*(@\w+)\s+path\s+(.+)$", text, re.M)}


def test_matchers_cover_bare_and_nested_paths():
    m = matchers()
    assert m["@api"] == ["/api", "/api/*"]
    assert m["@print"] == ["/print", "/print/*"]


def test_api_goes_to_backend_with_immediate_flush():
    body = handle_blocks()["@api"]
    assert re.search(r"reverse_proxy\s+\{\$API_UPSTREAM:backend:8000\}", body)
    assert re.search(r"flush_interval\s+-1", body)


def test_print_answers_404_at_the_proxy():
    body = handle_blocks()["@print"]
    assert re.search(r"respond\s+404", body)
    assert "reverse_proxy" not in body


def test_everything_else_goes_to_frontend():
    body = handle_blocks()["*"]
    assert re.search(r"reverse_proxy\s+\{\$WEB_UPSTREAM:frontend:3000\}", body)


def test_no_auth_rules_yet():
    text = CADDYFILE.read_text(encoding="utf-8")
    for directive in ("basic_auth", "basicauth", "forward_auth"):
        assert directive not in text


def test_the_client_address_is_read_only_from_trusted_hops():
    # Story 3.14: Railway's edge overwrites X-Real-IP; Caddy believes it only from these peers.
    text = re.sub(r"#.*", "", CADDYFILE.read_text(encoding="utf-8"))
    servers = re.search(r"servers\s*\{([^}]*)\}", text)
    assert servers
    assert re.search(
        r"trusted_proxies\s+static\s+private_ranges\s+100\.0\.0\.0/8\s*$", servers[1], re.M
    )
    assert re.search(r"client_ip_headers\s+X-Real-IP\s*$", servers[1], re.M)


def test_the_api_gets_exactly_the_resolved_client_address():
    body = handle_blocks()["@api"]
    assert re.search(r"header_up\s+X-Forwarded-For\s+\{client_ip\}", body)
    assert re.search(r"header_up\s+-X-Real-IP", body)
