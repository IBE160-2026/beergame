"""The per-service Railway config in `railway/` (AD-11, AD-24, Story 3.14)."""

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ("proxy", "frontend", "backend", "worker-ai", "worker-batch")
PYTHON = ("backend", "worker-ai", "worker-batch")
EU_WEST = "europe-west4-drams3a"
"""Railway's EU West region (Amsterdam), SETUP-GUIDE §2."""

START = {
    "proxy": "caddy run --config /etc/caddy/Caddyfile --adapter caddyfile",
    "frontend": "node server.js",
    "backend": "uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log",
    "worker-ai": "python -m app.worker --queues ai-orders",
    "worker-batch": (
        "python -m app.worker --queues llm-batch,mail,reports-bulk,reports-single --sweeper"
    ),
}
HEALTH = {"proxy": "/api/health", "frontend": "/", "backend": "/api/health"}


def config(service: str) -> dict:
    return tomllib.loads((ROOT / "railway" / service / "railway.toml").read_text(encoding="utf-8"))


def test_one_config_per_service_and_nothing_else():
    found = sorted(p.parent.name for p in (ROOT / "railway").glob("*/railway.toml"))
    assert found == sorted(SERVICES)


@pytest.mark.parametrize("service", SERVICES)
def test_each_service_is_pinned_to_eu_west_with_one_replica(service):
    assert config(service)["deploy"]["multiRegionConfig"] == {EU_WEST: {"numReplicas": 1}}


@pytest.mark.parametrize("service", SERVICES)
def test_start_command_health_check_and_deploy_overlap(service):
    deploy = config(service)["deploy"]
    assert deploy["startCommand"] == START[service]
    assert deploy.get("healthcheckPath") == HEALTH.get(service)
    assert deploy["overlapSeconds"] > 0
    assert deploy["drainingSeconds"] > 0
    assert deploy["restartPolicyType"] == "ON_FAILURE"


def test_the_python_services_build_one_image_and_only_backend_migrates():
    for service in PYTHON:
        build = config(service)["build"]
        assert (build["builder"], build["dockerfilePath"]) == ("DOCKERFILE", "backend/Dockerfile")
    assert config("backend")["deploy"]["preDeployCommand"] == ["alembic upgrade head"]
    for service in ("proxy", "frontend", "worker-ai", "worker-batch"):
        assert "preDeployCommand" not in config(service)["deploy"]


@pytest.mark.parametrize("service", SERVICES)
def test_watch_patterns_cover_the_image_source_and_the_config(service):
    build = config(service)["build"]
    source = build["dockerfilePath"].split("/")[0]
    assert (ROOT / build["dockerfilePath"]).is_file()
    assert set(build["watchPatterns"]) == {
        "/.dockerignore",
        f"/{source}/**",
        f"/railway/{service}/**",
    }


def test_the_worker_commands_match_compose():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("worker-ai", "worker-batch"):
        block = compose.split(f"\n  {service}:\n")[1]
        command = re.search(r"^\s+command: \[(.+)\]$", block, re.M)
        assert command, service
        assert " ".join(re.findall(r'"([^"]*)"', command.group(1))) == START[service]


def test_no_secret_value_is_in_the_config():
    for service in SERVICES:
        text = (ROOT / "railway" / service / "railway.toml").read_text(encoding="utf-8")
        assert not re.search(r"^\s*\w*(KEY|SECRET|PASSWORD|URL)\w*\s*=", text, re.M | re.I)
