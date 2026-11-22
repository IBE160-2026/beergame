"""Story 2.3: prompt files and their hash lock (AD-6)."""

import json
from pathlib import Path

from app.ai import config, prompt_files
from app.ai.cli import main
from tests.ai.helpers import CONFIGS, mock_config

REAL_PROMPTS = Path(config.__file__).parent / "prompts"


def test_the_repository_prompts_match_their_lock(monkeypatch):
    """The CI check: no locked version was changed or removed, every file is locked, and every
    version the shipped example configs reference exists and is locked."""
    monkeypatch.setattr(config, "PROMPTS_DIR", REAL_PROMPTS)
    references = []
    for path in sorted(CONFIGS.glob("*.json")):
        prompts = json.loads(path.read_text(encoding="utf-8"))["prompts"]
        references += list(prompts.items())
    assert prompt_files.check(references) == []
    assert all(name in prompt_files.read_lock() for name in (f"{p}/v{v}" for p, v in references))


def test_lock_records_new_files_and_check_finds_every_breach(prompts):
    unlocked = [
        "debrief_follow_up",
        "debrief_narration",
        "player_order",
        "quiz_explanation",
        "recognition_probe",
        "replay_walkthrough",
    ]
    assert prompt_files.check([("player_order", 1)]) == [
        f"prompt_unlocked {name}/v1: run `python -m app.ai.cli prompts lock`" for name in unlocked
    ]
    assert prompt_files.lock() == [f"{name}/v1" for name in unlocked]
    assert prompt_files.lock() == []
    assert prompt_files.check([("player_order", 1)]) == []

    # CRLF line endings hash like LF ones (a Windows checkout).
    (prompts / "player_order" / "v2.md").write_bytes(b"a\r\nb\r\n")
    prompt_files.lock()
    (prompts / "player_order" / "v2.md").write_bytes(b"a\nb\n")
    assert prompt_files.check() == []

    (prompts / "player_order" / "v1.md").write_text("changed", encoding="utf-8")
    (prompts / "player_order" / "v2.md").unlink()
    assert prompt_files.check([("player_order", 3)]) == [
        "prompt_changed player_order/v1: the file no longer matches its locked hash",
        "prompt_removed player_order/v2: locked but the file is gone",
        "prompt_missing player_order/v3: a stored config references it",
    ]
    # Locking again never overwrites an entry; `v01.md` is not a version.
    (prompts / "player_order" / "v01.md").write_text("x", encoding="utf-8")
    assert prompt_files.lock() == []
    assert prompt_files.check() != []
    assert "player_order/v1" in prompt_files.read_lock()


def test_prompts_check_runs_over_stored_configs(ai_db, prompts, capsys, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(mock_config(prompts={"player_order": 1})), encoding="utf-8")
    assert main(["config", "add", str(path)]) == 0
    capsys.readouterr()
    assert main(["prompts", "lock"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "locked debrief_follow_up/v1",
        "locked debrief_narration/v1",
        "locked player_order/v1",
        "locked quiz_explanation/v1",
        "locked recognition_probe/v1",
        "locked replay_walkthrough/v1",
    ]
    assert main(["prompts", "check"]) == 0
    assert capsys.readouterr().out.splitlines() == ["prompts ok: 6 locked, 1 referenced"]

    (prompts / "player_order" / "v1.md").unlink()
    assert main(["prompts", "lock"]) == 1  # locking reports what it cannot fix
    capsys.readouterr()
    assert main(["prompts", "check"]) == 1
    err = capsys.readouterr().err.splitlines()
    assert err == [
        "error prompt_removed player_order/v1: locked but the file is gone",
    ]


def test_latest_is_the_newest_version_with_a_file(prompts):
    """Story 2.4: `sim prompt` without a config renders the newest version."""
    assert prompt_files.latest("player_order") == 1
    (prompts / "player_order" / "v10.md").write_text("x", encoding="utf-8")
    (prompts / "player_order" / "v02.md").write_text("x", encoding="utf-8")
    assert prompt_files.latest("player_order") == 10
    assert prompt_files.latest("player") is None
