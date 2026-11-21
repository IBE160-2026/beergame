from pathlib import Path

import pytest

from app.ai import config


@pytest.fixture(autouse=True)
def prompts(tmp_path, monkeypatch) -> Path:
    """A prompts directory holding `v1.md` of every purpose the shipped configs reference
    (`player_order`, `recognition_probe`, and the Debrief's since Stories 9.14 and 9.15), so no test
    depends on the shipped prompt text."""
    for purpose in (
        "player_order",
        "recognition_probe",
        "debrief_narration",
        "quiz_explanation",
        "debrief_follow_up",
    ):
        (tmp_path / purpose).mkdir()
        (tmp_path / purpose / "v1.md").write_text("prompt", encoding="utf-8")
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path)
    return tmp_path
