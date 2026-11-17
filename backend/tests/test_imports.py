"""Story 2.1 import check (AD-2, AD-5, AD-6): `players` reaches game state only through
`games.service` and `games.commands`, and `modules/games` has no LLM or provider import."""

import ast
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
    allowed = ("app.modules.games.service", "app.modules.games.commands")
    for path, line, name in imports(APP / "modules" / "players"):
        if name.startswith("app.modules.") and not name.startswith("app.modules.players"):
            assert name in allowed, f"{path.name}:{line} imports {name}"
        assert not name.startswith(LLM_IMPORTS), f"{path.name}:{line} imports {name}"


def test_games_has_no_llm_or_provider_import():
    for path, line, name in imports(APP / "modules" / "games"):
        assert not name.startswith(LLM_IMPORTS), f"{path.name}:{line} imports {name}"
        if name.startswith("app.modules.") and not name.startswith("app.modules.games"):
            # The order source, called when a Week opens; nothing else of another module.
            assert name == "app.modules.players.service", f"{path.name}:{line} imports {name}"


def test_the_check_sees_imports_inside_functions():
    names = {name for _, _, name in imports(APP / "modules" / "games")}
    assert "app.modules.players.service" in names
