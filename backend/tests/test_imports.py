"""Story 2.1 import check (AD-2, AD-5, AD-6): `players` reaches game state only through
`games.service` and `games.commands`, and `modules/games` has no LLM or provider import."""

import ast
import re
from pathlib import Path

APP = Path(__file__).parents[1] / "app"

LLM_IMPORTS = ("app.ai", "pydantic_ai", "openai", "anthropic", "httpx", "litellm")


def imports(package: Path) -> list[tuple[Path, int, str]]:
    """Every module imported by the files under `package`, absolute (`from x import y` gives
    `x.y`), with its file and line, also those imported inside functions."""
    found = []
    for path in sorted(package.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found += [(path, node.lineno, alias.name) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                # A relative import would slip past the prefix checks; none is allowed.
                assert node.level == 0, f"{path.name}:{node.lineno} uses a relative import"
                found += [(path, node.lineno, f"{node.module}.{a.name}") for a in node.names]
    return found


def test_players_imports_only_the_games_service_and_commands():
    """`players` may reach the LLM only through the gateway (Story 2.4, AD-6), and only from
    `players/llm.py`: the order source that `games` imports loads no provider library."""
    allowed = ("app.modules.games.service", "app.modules.games.commands")
    for path, line, name in imports(APP / "modules" / "players"):
        if name.startswith("app.modules.") and not name.startswith("app.modules.players"):
            assert name in allowed, f"{path.name}:{line} imports {name}"
        if path.stem == "llm" and name == "app.ai.gateway":
            continue
        assert not name.startswith(LLM_IMPORTS), f"{path.name}:{line} imports {name}"
        # `players.llm` loads pydantic-ai; the order source that `games` imports never does.
        assert not name.startswith("app.modules.players.llm"), f"{path.name}:{line} imports {name}"


def test_games_has_no_llm_or_provider_import():
    for path, line, name in imports(APP / "modules" / "games"):
        assert not name.startswith(LLM_IMPORTS), f"{path.name}:{line} imports {name}"
        if name.startswith("app.modules.") and not name.startswith("app.modules.games"):
            # The order source, called when a Week opens; nothing else of another module.
            assert name == "app.modules.players.service", f"{path.name}:{line} imports {name}"
            assert not name.startswith("app.modules.players.llm")


AI_PUBLIC = ("app.ai.config", "app.ai.budget", "app.ai.gateway")
AI_TABLES = re.compile(r"\b(ai_model_configs|ai_budgets|llm_call)\b")
"""Whole words, so `llm_call_ids` (on the gateway's results) is not a table name."""


def test_only_app_ai_touches_the_model_config_and_budget_tables():
    """Stories 2.2 and 2.3 (AD-6): other packages use `ai.config`, `ai.budget` and
    `ai.gateway` only, and never name the tables; `app/ai` imports nothing from `app.modules`."""
    outside = [path for path in sorted(APP.rglob("*.py")) if (APP / "ai") not in path.parents]
    for path in outside:
        assert not AI_TABLES.search(path.read_text(encoding="utf-8")), path.name
    for path, line, name in imports(APP):  # every file, top-level modules included
        if (APP / "ai") not in path.parents and name.startswith("app.ai"):
            assert name.startswith(AI_PUBLIC), f"{path.name}:{line} imports {name}"
    for path, line, name in imports(APP / "ai"):
        assert not name.startswith("app.modules"), f"{path.name}:{line} imports {name}"


def test_the_check_sees_imports_inside_functions():
    names = {name for _, _, name in imports(APP / "modules" / "games")}
    assert "app.modules.players.service" in names


PROVIDER_SDKS = (
    "pydantic_ai",
    "openai",
    "anthropic",
    "google.genai",
    "google.generativeai",
    "mistralai",
    "cohere",
    "groq",
    "litellm",
    "ollama",
)
BANNED = "Fallback" + "Model"
"""pydantic-ai's provider fallback (FR-68), spelled so this file does not contain it."""
BACKEND = APP.parent


def test_only_app_ai_imports_pydantic_ai_or_a_provider_sdk():
    """Story 2.3 (AD-6, FR-68)."""
    for path, line, name in imports(APP):
        if (APP / "ai") not in path.parents:
            assert not name.startswith(PROVIDER_SDKS), f"{path.name}:{line} imports {name}"


def test_no_code_uses_the_provider_fallback_model():
    for folder in (APP, BACKEND / "migrations", BACKEND / "tests"):
        for path in sorted(folder.rglob("*.py")):
            assert BANNED not in path.read_text(encoding="utf-8"), path


def test_the_check_sees_pydantic_ai_in_app_ai():
    names = {name for _, _, name in imports(APP / "ai")}
    assert any(name.startswith("pydantic_ai") for name in names)
