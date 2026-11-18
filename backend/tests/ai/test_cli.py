"""Story 2.2: `python -m app.ai.cli`."""

import json
import re
import uuid

import pytest

from app.ai.cli import main
from tests.ai.helpers import CONFIGS, MOCK, mock_config, query

ID = r"[0-9a-f-]{36}"


def run(capsys, *argv: str) -> tuple[int, list[str], str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out.splitlines(), captured.err


def write(tmp_path, data: object, name: str = "config.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def added_id(lines: list[str]) -> str:
    match = re.fullmatch(rf"config ({ID})", lines[0])
    assert match, lines
    return match[1]


def test_config_add_list_show_and_edit(ai_db, capsys, tmp_path, prompts):
    code, lines, err = run(capsys, "config", "add", str(CONFIGS / "openrouter-deepseek.json"))
    assert code == 0, err
    first = added_id(lines)
    assert "placeholder values" in err
    code, lines, _ = run(capsys, "config", "add", write(tmp_path, MOCK))
    second = added_id(lines)
    # What `ai.config.mark_referenced` writes when a simulation run or Class session pins it.
    query(
        ai_db,
        "UPDATE ai_model_configs SET referenced_at = now() WHERE id = %s RETURNING id",
        (first,),
    )

    code, lines, _ = run(capsys, "config", "list")
    assert code == 0
    assert lines == [
        f"config {first} name=openrouter-deepseek model=deepseek/deepseek-v4.1-flash-1017 "
        "endpoint=https://openrouter.ai/api/v1 region=eu-provider referenced=yes",
        f"config {second} name=mock model=mock-1 endpoint=mock://local region=local referenced=no",
    ]

    (prompts / "player_order" / "v2.md").write_text("prompt 2", encoding="utf-8")
    code, lines, _ = run(capsys, "config", "edit", first, "--prompt", "player_order=v2")
    assert code == 0
    third = added_id(lines)
    assert lines[1] == f"from {first}"
    code, lines, _ = run(capsys, "config", "show", third)
    shown = json.loads("\n".join(lines))
    assert shown["prompts"] == {"player_order": 2, "recognition_probe": 1}
    assert shown["derived_from"] == first and shown["referenced_at"] is None
    assert shown["credential_env"] == "OPENROUTER_API_KEY"
    code, lines, _ = run(capsys, "config", "show", first)
    # The referenced row is unchanged.
    assert json.loads("\n".join(lines))["prompts"] == {"player_order": 1, "recognition_probe": 1}

    code, lines, _ = run(
        capsys, "config", "edit", second, "--from", write(tmp_path, mock_config(name="b"))
    )
    assert code == 0 and lines[1] == f"from {second}"


@pytest.mark.parametrize(
    ("data", "line"),
    [
        (mock_config(api_key="abc"), "error credential_in_file api_key:"),
        (mock_config(prompts={"player_order": 2}), "error prompt_missing prompts.player_order:"),
        (
            mock_config(effort_levels=[{"name": "standard", "attempt_timeout_s": 4}]),
            "error missing effort_levels.0.order_time_budget_s:",
        ),
    ],
)
def test_config_add_refusals_name_the_field_and_store_nothing(ai_db, capsys, tmp_path, data, line):
    code, lines, err = run(capsys, "config", "add", write(tmp_path, data))
    assert (code, lines) == (1, [])
    assert err.startswith(line), err
    assert "abc" not in err
    assert query(ai_db, "SELECT count(*) FROM ai_model_configs") == [(0,)]


@pytest.mark.parametrize("content", [None, "[]", "{"])
def test_config_add_exits_2_on_an_unreadable_file(capsys, tmp_path, content):
    path = tmp_path / "config.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        main(["config", "add", str(path)])
    assert caught.value.code == 2


def test_config_add_accepts_a_file_with_a_byte_order_mark(ai_db, capsys, tmp_path):
    path = tmp_path / "bom.json"
    path.write_text(json.dumps(MOCK), encoding="utf-8-sig")
    code, lines, err = run(capsys, "config", "add", str(path))
    assert code == 0, err
    added_id(lines)


def test_the_cli_without_a_database_exits_1(capsys, monkeypatch, unreachable_database):
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    code, lines, err = run(capsys, "config", "list")
    assert (code, lines) == (1, [])
    assert err.strip() == "error db_unavailable: cannot reach the database"


def test_the_cli_reports_other_database_errors(capsys, monkeypatch):
    from sqlalchemy.exc import ProgrammingError

    from app.ai import budget

    async def broken(*args, **kwargs):
        raise ProgrammingError("INSERT", {}, Exception("relation ai_budgets does not exist"))

    monkeypatch.setattr(budget, "set_budget", broken)
    code, lines, err = run(capsys, "budget", "set", "--session", str(uuid.uuid7()))
    assert (code, lines) == (1, [])
    assert err.strip() == "error db_error: Exception"


def test_the_cli_as_a_program_prints_only_the_report_on_stdout(ai_db):
    import os
    import subprocess
    import sys
    from pathlib import Path

    result = subprocess.run(
        [sys.executable, "-m", "app.ai.cli", "config", "add", str(CONFIGS / "mock.json")],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    added_id(result.stdout.splitlines())
    assert len(result.stdout.splitlines()) == 1
    assert "placeholder values" in result.stderr


def test_config_edit_and_show_refuse_an_unknown_id(ai_db, capsys):
    missing = str(uuid.uuid7())
    code, _, err = run(capsys, "config", "edit", missing, "--prompt", "player_order=1")
    assert code == 1 and err.startswith("error config_not_found:")
    code, _, err = run(capsys, "config", "show", missing)
    assert code == 1 and err.startswith("error config_not_found:")
    with pytest.raises(SystemExit) as caught:
        main(["config", "edit", missing])  # neither --prompt nor --from
    assert caught.value.code == 2


def test_budget_set(ai_db, capsys, tmp_path):
    _, lines, _ = run(capsys, "config", "add", write(tmp_path, MOCK))
    config_id = added_id(lines)
    code, lines, _ = run(capsys, "budget", "set", "--evaluation", config_id, "--limit", "2")
    assert (code, lines) == (
        0,
        [
            f"budget evaluation {config_id} limit=2.00000000 reserve=1.00000000 "
            "spent=0.00000000 players_exhausted_at=-"
        ],
    )
    code, lines, _ = run(
        capsys, "budget", "set", "--evaluation", config_id, "--limit", "3", "--reserve", "0.5"
    )
    assert code == 0 and "limit=3.00000000 reserve=0.50000000" in lines[0]
    session = str(uuid.uuid7())
    code, lines, _ = run(capsys, "budget", "set", "--session", session)
    assert code == 0
    assert lines[0].startswith(f"budget class_session {session} limit=15.00000000 ")
    assert query(ai_db, "SELECT count(*) FROM ai_budgets") == [(2,)]


@pytest.mark.parametrize(
    ("argv", "code_name"),
    [
        (["--limit", "0.5"], "reserve_above_limit"),
        ([], "limit_required"),
    ],
)
def test_budget_set_refusals(ai_db, capsys, tmp_path, argv, code_name):
    _, lines, _ = run(capsys, "config", "add", write(tmp_path, MOCK))
    code, out, err = run(capsys, "budget", "set", "--evaluation", added_id(lines), *argv)
    assert (code, out) == (1, [])
    assert err.startswith(f"error {code_name}:")
    assert query(ai_db, "SELECT count(*) FROM ai_budgets") == [(0,)]


def test_budget_set_for_an_unknown_config(ai_db, capsys):
    code, _, err = run(capsys, "budget", "set", "--evaluation", str(uuid.uuid7()), "--limit", "1")
    assert code == 1 and err.startswith("error config_not_found:")


@pytest.mark.parametrize(
    "argv",
    [
        ["--limit", "1"],
        ["--evaluation", "x", "--limit", "1"],
        ["--session", str(uuid.uuid7()), "--limit", "-1"],
        ["--session", str(uuid.uuid7()), "--evaluation", str(uuid.uuid7())],
    ],
)
def test_budget_set_bad_arguments_exit_2(capsys, argv):
    with pytest.raises(SystemExit) as caught:
        main(["budget", "set", *argv])
    assert caught.value.code == 2


def logged_call(url: str, config_id: str, game: str | None, usd: str, day: str, outcome="ok"):
    """One `llm_call` row of the evaluation scope of `config_id`, as the gateway writes it."""
    caller = {"game": game, "seat": str(uuid.uuid7()), "week": 2} if game else {}
    query(
        url,
        "INSERT INTO llm_call (id, purpose, scope_kind, scope_id, caller_ref, model_config_id, "
        "provider, endpoint, model_version, quantisation, effort_level, prompt_version, attempt, "
        "input_tokens, output_tokens, reasoning_tokens, cost_usd, latency_ms, outcome, request, "
        "started_at) VALUES (%s, 'player_order', 'evaluation', %s, %s, %s, 'mock', 'mock://local', "
        "'mock-1', 'none', 'standard', 1, 1, 10, 5, 0, %s, 3, %s, '{}', %s) RETURNING id",
        (
            str(uuid.uuid7()),
            config_id,
            json.dumps(caller),
            config_id,
            usd,
            outcome,
            f"{day}T23:30:00+00:00",
        ),
    )


def test_cost_sums_the_scope_per_game_and_day(ai_db, capsys, tmp_path):
    """Story 2.8 (FR-69): from settled `llm_call` costs of every outcome, with the budget row."""
    _, lines, _ = run(capsys, "config", "add", write(tmp_path, MOCK))
    config_id = added_id(lines)
    run(capsys, "budget", "set", "--evaluation", config_id, "--limit", "2", "--reserve", "0.5")
    one, two = str(uuid.uuid7()), str(uuid.uuid7())
    logged_call(ai_db, config_id, one, "0.001", "2026-11-17")
    logged_call(ai_db, config_id, one, "0.002", "2026-11-18", outcome="timeout")
    logged_call(ai_db, config_id, two, "0.004", "2026-11-18")
    logged_call(ai_db, config_id, None, "0.0005", "2026-11-18")  # a probe: no Game
    query(ai_db, "UPDATE ai_budgets SET spent_usd = 0.0075, reserved_usd = 0.01 RETURNING id")
    code, lines, err = run(capsys, "cost", "--scope", config_id)
    assert code == 0, err
    assert lines == [
        f"budget evaluation {config_id} limit=2.00000000 reserve=0.50000000 "
        "spent=0.00750000 reserved=0.01000000 players_exhausted_at=-",
        "total usd=0.00750000 calls=4",
        f"game {two} usd=0.00400000 calls=1",
        f"game {one} usd=0.00300000 calls=2",
        "game - usd=0.00050000 calls=1",
        "day 2026-11-17 usd=0.00100000 calls=1",
        "day 2026-11-18 usd=0.00650000 calls=3",
    ]
    code, lines, _ = run(capsys, "cost", "--scope", config_id, "--kind", "evaluation")
    assert code == 0 and lines[1] == "total usd=0.00750000 calls=4"


def test_cost_refuses_an_unknown_or_ambiguous_scope(ai_db, capsys, tmp_path):
    _, lines, _ = run(capsys, "config", "add", write(tmp_path, MOCK))
    config_id = added_id(lines)
    code, out, err = run(capsys, "cost", "--scope", config_id)
    assert (code, out) == (1, []) and err.startswith("error budget_not_found:")
    run(capsys, "budget", "set", "--evaluation", config_id, "--limit", "1")
    run(capsys, "budget", "set", "--session", config_id)  # the same id as a session scope
    code, out, err = run(capsys, "cost", "--scope", config_id)
    assert (code, out) == (1, []) and err.startswith("error scope_ambiguous:")
    code, out, _ = run(capsys, "cost", "--scope", config_id, "--kind", "class_session")
    assert code == 0 and out[0].startswith(f"budget class_session {config_id} ")
    assert out[1:] == ["total usd=0.00000000 calls=0"]
