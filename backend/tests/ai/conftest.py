from pathlib import Path

import pytest

from app.ai import config


@pytest.fixture(autouse=True)
def prompts(tmp_path, monkeypatch) -> Path:
    """A prompts directory holding `player_order/v1.md` and `recognition_probe/v1.md` (the
    versions the shipped configs reference), so no test depends on the shipped prompt text."""
    for purpose in ("player_order", "recognition_probe"):
        (tmp_path / purpose).mkdir()
        (tmp_path / purpose / "v1.md").write_text("prompt", encoding="utf-8")
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path)
    return tmp_path
