"""Prompt files and their hash lock (AD-6).

Prompts live at `prompts/<purpose>/v<N>.md`. `prompts/hashes.json` records the hash of every
version once (`prompts lock`); a deploy may add versions but never change or remove one, so a
model config that references a version always gets the text it was measured with. `check`
lists every breach; a test runs it over the repository and `prompts check` over stored configs.
"""

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from app.ai import config

LOCK_NAME = "hashes.json"


def _dir() -> Path:
    return config.PROMPTS_DIR  # read at call time: tests point it elsewhere


def key(purpose: str, version: int) -> str:
    return f"{purpose}/v{version}"


def load(purpose: str, version: int) -> str | None:
    path = config.prompt_path(purpose, version)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def digest(text: str) -> str:
    """sha256 of the text with `\\r\\n` as `\\n`, so a Windows checkout hashes the same."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def read_lock() -> dict[str, str]:
    path = _dir() / LOCK_NAME
    if not path.is_file():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")))


def files() -> dict[str, str]:
    """Every prompt file under the directory, as `{key: digest}`."""
    found: dict[str, str] = {}
    for path in sorted(_dir().glob("*/v*.md")):
        version = path.stem[1:]
        if version.isdigit() and str(int(version)) == version:  # `v01.md` is not a version
            found[key(path.parent.name, int(version))] = digest(path.read_text(encoding="utf-8"))
    return found


def check(references: Iterable[tuple[str, int]] = ()) -> list[str]:
    """Problems with the prompt files: a locked version changed or removed, a file with no lock
    entry, and for each `(purpose, version)` referenced by a config, a missing or unlocked file."""
    lock = read_lock()
    present = files()
    problems: list[str] = []
    for name, expected in sorted(lock.items()):
        if name not in present:
            problems.append(f"prompt_removed {name}: locked but the file is gone")
        elif present[name] != expected:
            problems.append(f"prompt_changed {name}: the file no longer matches its locked hash")
    for name in sorted(present.keys() - lock.keys()):
        problems.append(f"prompt_unlocked {name}: run `python -m app.ai.cli prompts lock`")
    for purpose, version in sorted(set(references)):
        name = key(purpose, version)
        if name not in present and name not in lock:
            problems.append(f"prompt_missing {name}: a stored config references it")
    return problems


def lock() -> list[str]:
    """Record the hash of every file that has none yet; never change an existing entry.
    Returns the keys added."""
    current = read_lock()
    present = files()
    added = sorted(present.keys() - current.keys())
    if added:
        merged = {**current, **{name: present[name] for name in added}}
        (_dir() / LOCK_NAME).write_text(
            json.dumps(dict(sorted(merged.items())), indent=2) + "\n", encoding="utf-8"
        )
    return added
