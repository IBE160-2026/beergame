"""The real start commands refuse to start in production with one secret removed (AD-17,
Story 3.14). Each process is started as Railway starts it (`railway/<service>/railway.toml`), in
a subprocess, with a full valid production set minus one variable. The three run at once, so
the test costs one interpreter start."""

import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from tests.test_config import PRODUCTION_ENV

BACKEND = Path(__file__).resolve().parents[1]
RAILWAY = BACKEND.parent / "railway"

REMOVED = {
    "backend": "JWT_SECRET",
    "worker-ai": "RESEND_API_KEY",
    "worker-batch": "SUPABASE_SERVICE_ROLE_KEY",
}
"""One required secret left out per process."""


def command(service: str) -> list[str]:
    """The service's Railway start command, run with this interpreter."""
    config = tomllib.loads((RAILWAY / service / "railway.toml").read_text(encoding="utf-8"))
    argv = shlex.split(config["deploy"]["startCommand"])
    if argv[0] == "python":
        return [sys.executable, *argv[1:]]
    return [sys.executable, "-m", *argv]  # uvicorn


def environment(removed: str) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in PRODUCTION_ENV and "RATE_LIMIT" not in name
    }
    env.update({name: value for name, value in PRODUCTION_ENV.items() if name != removed})
    return env


def test_each_process_refuses_to_start_naming_the_missing_secret():
    started = {
        service: subprocess.Popen(
            command(service),
            cwd=BACKEND,
            env=environment(removed),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        for service, removed in REMOVED.items()
    }
    try:
        outputs = {s: p.communicate(timeout=60) for s, p in started.items()}
    finally:
        for process in started.values():
            process.kill()
    for service, (out, err) in outputs.items():
        process = started[service]
        assert process.returncode != 0, f"{service} started without {REMOVED[service]}"
        assert "Refusing to start with APP_ENV=production" in err + out, service
        assert REMOVED[service] in err + out, service
        for name, value in PRODUCTION_ENV.items():
            if name in ("APP_ENV", "BCRYPT_ROUNDS"):
                continue
            assert value not in err + out, f"{service} printed the value of {name}"
