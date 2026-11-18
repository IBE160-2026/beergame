"""`backend/docker-entrypoint.sh` (AD-24, Story 3.14): locally it migrates before the command;
with APP_ENV=production only `RUN_MIGRATIONS=true` makes it migrate, so on Railway only the
backend's pre-deploy command does. A stub `alembic` on PATH records whether it was called."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "docker-entrypoint.sh"
SH = shutil.which("sh")

pytestmark = pytest.mark.skipif(SH is None, reason="no POSIX sh on this machine")


def migrated(tmp_path: Path, **env: str) -> bool:
    calls = tmp_path / "calls"
    stub = tmp_path / "alembic"
    stub.write_text(f'#!/bin/sh\necho "$@" >> "{calls.as_posix()}"\n', newline="\n")
    stub.chmod(0o755)
    environ = {k: v for k, v in os.environ.items() if k not in ("APP_ENV", "RUN_MIGRATIONS")}
    environ["PATH"] = f"{tmp_path}{os.pathsep}{environ.get('PATH', '')}"
    environ.update(env)
    script = ENTRYPOINT.read_text(encoding="utf-8")
    result = subprocess.run(
        [SH, "-c", script, "docker-entrypoint.sh", "echo", "started"],
        env=environ,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("started")
    return calls.exists() and calls.read_text().strip() == "upgrade head"


def test_locally_it_migrates_before_the_command(tmp_path):
    assert migrated(tmp_path)


def test_in_production_it_does_not_migrate(tmp_path):
    assert not migrated(tmp_path, APP_ENV="production")


def test_in_production_run_migrations_true_still_migrates(tmp_path):
    assert migrated(tmp_path, APP_ENV="production", RUN_MIGRATIONS="true")


def test_run_migrations_false_skips_locally(tmp_path):
    assert not migrated(tmp_path, RUN_MIGRATIONS="false")
