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


GATEWAY_USERS = ("llm", "jobs")
"""`players/llm.py` builds the request and `players/jobs.py` (the `ai-orders` job) makes the
call; no other file of `players` may import the gateway."""
AI_NON_LLM = ("app.ai.config", "app.ai.budget")
"""What `games` may use of `app/ai`: model configs and budgets, which load no LLM library."""


def test_players_imports_only_the_games_service_and_commands():
    """`players` may reach the LLM only through the gateway (Stories 2.4, 2.5, AD-6), and only
    from `players/llm.py` and `players/jobs.py`: the order source that `games` imports loads no
    provider library."""
    allowed = ("app.modules.games.service", "app.modules.games.commands")
    for path, line, name in imports(APP / "modules" / "players"):
        if name.startswith("app.modules.") and not name.startswith("app.modules.players"):
            assert name in allowed, f"{path.name}:{line} imports {name}"
        if path.stem in GATEWAY_USERS and name == "app.ai.gateway":
            continue
        assert not name.startswith(LLM_IMPORTS), f"{path.name}:{line} imports {name}"
        # `players.llm` and `players.jobs` load pydantic-ai; only the job may import them.
        if path.stem != "jobs":
            for loaded in ("app.modules.players.llm", "app.modules.players.jobs"):
                assert not name.startswith(loaded), f"{path.name}:{line} imports {name}"


def test_games_has_no_llm_or_provider_import():
    for path, line, name in imports(APP / "modules" / "games"):
        if name.startswith(AI_NON_LLM):
            continue
        assert not name.startswith(LLM_IMPORTS), f"{path.name}:{line} imports {name}"
        if name.startswith("app.modules.") and not name.startswith("app.modules.games"):
            # The order source, called when a Week opens, and `progress`, where `finish` records
            # the Class game step (Story 6.18, AD-16); nothing else of another module.
            assert name in ("app.modules.players.service", "app.modules.progress.service"), (
                f"{path.name}:{line} imports {name}"
            )


def test_progress_imports_no_feature_module():
    """AD-16: any module records and reads steps through `progress`, so `progress` imports no
    other module (Story 6.1)."""
    for path, line, name in imports(APP / "modules" / "progress"):
        if name.startswith("app.modules."):
            assert name.startswith("app.modules.progress"), f"{path.name}:{line} imports {name}"


def test_content_imports_no_feature_module():
    """AD-23: every module reads its pinned content through `content.service`, so `content`
    imports no other module (Story 6.3)."""
    for path, line, name in imports(APP / "modules" / "content"):
        if name.startswith("app.modules."):
            assert name.startswith("app.modules.content"), f"{path.name}:{line} imports {name}"


def test_analysis_is_pure():
    """AD-1: `app/analysis` (the Play guard, the Starting task's scoring) imports only the
    stdlib, pydantic and `app.engine`: no module, no platform, no database, no LLM."""
    for path, line, name in imports(APP / "analysis"):
        assert not name.startswith(
            ("app.modules", "app.platform", "app.ai", "sqlalchemy", "httpx", *LLM_IMPORTS)
        ), f"{path.name}:{line} imports {name}"


def test_the_platform_imports_no_module_and_no_llm_library():
    """`app/platform` (jobs included) names task modules by string only (Story 2.5)."""
    for path, line, name in imports(APP / "platform"):
        assert not name.startswith(("app.modules", *LLM_IMPORTS)), f"{path.name}:{line} {name}"


AI_PUBLIC = (
    "app.ai.config",
    "app.ai.budget",
    "app.ai.gateway",
    "app.ai.endpoint",
    # Reads of the call rows for reports (`sim report`, Story 2.11, AD-22).
    "app.ai.calls",
    # The zero-config seed the api, the workers and `app.sim` run at start (Story 2.12, AD-17).
    "app.ai.seed",
)
AI_TABLES = re.compile(
    r"\b(ai_model_configs|ai_budgets|llm_call|effort_measurements|ai_default_pins)\b"
)
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


def test_only_ops_imports_messaging_and_nothing_imports_ops():
    """Story 3.5 (AD-9): modules tell people through `platform/notify`, never by importing
    `messaging`; only the sweep (`ops`) and `classes` (delivery state, Story 4.6) call
    `messaging.service`, and only the worker entry point imports `ops`. The app factory mounts
    the local dev mailbox, `messaging.routes` (Story 3.6), and the provider's webhook,
    `messaging.webhooks` (Story 4.6)."""
    for path, line, name in imports(APP):
        inside = {
            folder: (APP / "modules" / folder) in path.parents
            for folder in ("messaging", "ops", "classes")
        }
        if name.startswith("app.modules.messaging") and not inside["messaging"]:
            mounts_routes = path == APP / "main.py" and name in (
                "app.modules.messaging.routes",
                "app.modules.messaging.webhooks",
            )
            assert mounts_routes or (
                (inside["ops"] or inside["classes"])
                and name.startswith("app.modules.messaging.service")
            ), f"{path.name}:{line} imports {name}"
        if name.startswith("app.modules.ops") and not inside["ops"]:
            assert path == APP / "worker.py", f"{path.name}:{line} imports {name}"


def test_messaging_reaches_other_modules_only_through_their_service():
    for path, line, name in imports(APP / "modules" / "messaging"):
        if name.startswith("app.modules.") and not name.startswith("app.modules.messaging"):
            assert name.split(".")[3] == "service", f"{path.name}:{line} imports {name}"


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


def test_classes_reaches_identity_only_through_its_service_and_identity_never_imports_classes():
    """AD-14 (Story 4.1): Roster addresses and Users live in `identity`, which `classes` reaches
    only through `identity.service`; `identity` learns of Classes only through its registries."""
    for path, line, name in imports(APP / "modules" / "classes"):
        if name.startswith("app.modules.") and not name.startswith("app.modules.classes"):
            # Delivery state of the Invitations' mails comes from `messaging` (Story 4.6).
            assert name in (
                "app.modules.identity.service",
                "app.modules.messaging.service",
            ), f"{path.name}:{line} imports {name}"
    for path, line, name in imports(APP / "modules" / "identity"):
        assert not name.startswith("app.modules.classes"), f"{path.name}:{line} imports {name}"
    for path, line, name in imports(APP / "platform"):
        assert not name.startswith("app.modules"), f"{path.name}:{line} imports {name}"
