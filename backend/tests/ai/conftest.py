from pathlib import Path

import pytest

from app.ai import config


@pytest.fixture(autouse=True)
def prompts(tmp_path, monkeypatch) -> Path:
    """A prompts directory holding `player_order/v1.md` only, so no test depends on the
    prompt files a later story ships."""
    (tmp_path / "player_order").mkdir()
    (tmp_path / "player_order" / "v1.md").write_text("prompt", encoding="utf-8")
    monkeypatch.setattr(config, "PROMPTS_DIR", tmp_path)
    return tmp_path
