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
