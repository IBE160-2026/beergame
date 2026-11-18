"""Story 2.4: `python -m app.sim prompt` and `python -m app.sim probe` (FR-31, issue #19)."""

import json
import uuid
from decimal import Decimal

from app import sim
from app.ai import budget, config
from app.engine import GameSettings
from app.modules.games import commands
from app.platform import db
from tests.ai.helpers import mock_config, query
from tests.games.helpers import seat_student, tamper

PROMPTS = {"player_order": 1, "recognition_probe": 1}


def run(capsys, *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()  # drop what the setup logged
    code = sim.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def setup(coroutine):
    async def wrapped():
        try:
            return await coroutine
        finally:
            await db.dispose()

    return sim._run(wrapped())


async def _running_game(url: str) -> str:
    """A started Game whose wholesaler is a Student: Week 1 stays open."""
    game_id = await commands.create("simulation", GameSettings(), seed=3)
    seat_student(url, game_id, "wholesaler")
    await commands.start(game_id)
    return game_id


async def _finished_game() -> str:
    """A short Game of four Rule-based players (4 Guided Weeks, then 4 more): finished when
    `start` returns, and much cheaper than a full Classic Game."""
    game_id = await commands.create("simulation", GameSettings(weeks=8), seed=5)
    await commands.start(game_id)
    return game_id


async def _config(limit: str = "1") -> str:
    row = await config.add(config.parse(mock_config(prompts=PROMPTS)))
    await budget.set_budget(
        budget.BudgetScope.evaluation(row.id), limit=Decimal(limit), reserve=Decimal(0)
    )
    return str(row.id)


def test_prompt_prints_the_request_for_the_open_week(games_db, ai_db, capsys):
    game_id = setup(_running_game(games_db))
    config_id = setup(_config())
    code, out, err = run(capsys, "prompt", game_id, "--seat", "wholesaler")
    assert code == 0, err
    lines = out.splitlines()
    assert lines[0] == "purpose player_order prompt_version 1 from newest file"
    assert lines[1] == "--- prompt"
    assert lines[2].startswith("You are the supply chain manager")
    assert "Your business is the wholesaler." in out
    assert "customer demand" not in out.lower()
    schema_text = out.split("--- output_schema\n")[1].split("--- model_settings")[0]
    schema = json.loads(schema_text)
    assert schema["title"] == "OrderDecision"
    assert schema["properties"]["order"]["maximum"] == 999
    assert lines[-1] == "--- model_settings {}"
    assert "Week 1 is a Guided Week" in err
    assert game_id not in out
    # The same request, resolved for a stored config, as `run` would send it.
    code, with_config, err = run(
        capsys, "prompt", game_id, "--seat", "wholesaler", "--config", config_id
    )
    assert code == 0, err
    assert with_config.splitlines()[0] == "purpose player_order prompt_version 1 from config"
    # The config's Effort level adds its output bound (Story 2.8); the rest is the same.
    assert with_config.splitlines()[1:-1] == lines[1:-1]
    assert with_config.splitlines()[-1] == '--- model_settings {"max_tokens": 4096}'
    # A Seat id in any form `uuid.UUID` reads names the same Seat.
    (seat_id,) = query(
        games_db,
        "SELECT id::text FROM seats WHERE game_id = %s AND role = 'wholesaler'",
        (game_id,),
    )[0:1][0]
    code, by_id, err = run(capsys, "prompt", game_id, "--seat", seat_id.upper())
    assert (code, by_id) == (0, out), err
    assert query(ai_db, "SELECT count(*) FROM llm_call") == [(0,)]  # no model was asked


def test_prompt_refuses_unknown_and_finished_games(games_db, ai_db, capsys):
    code, _, err = run(capsys, "prompt", str(uuid.uuid4()), "--seat", "retailer")
    assert code == 1 and err.startswith("error game_not_found")
    running = setup(_running_game(games_db))
    code, _, err = run(capsys, "prompt", running, "--seat", "captain")
    assert code == 1 and err.startswith("error seat_not_found")
    code, _, err = run(capsys, "prompt", running, "--seat", "retailer", "--config", "x")
    assert code == 1 and err.startswith("error config_not_found")
    code, _, err = run(
        capsys, "prompt", running, "--seat", "retailer", "--config", str(uuid.uuid4())
    )
    assert code == 1 and err.startswith("error config_not_found")
    tamper(games_db, "UPDATE games SET lifecycle = 'finished' WHERE id = %s", (running,))
    code, _, err = run(capsys, "prompt", running, "--seat", "retailer")
    assert (code, err.strip()) == (1, "error game_finished: the Game has no open Week")


def test_probe_logs_and_prints_answers_and_places_no_order(games_db, ai_db, capsys):
    game_id = setup(_finished_game())
    config_id = setup(_config())
    before = query(games_db, "SELECT count(*) FROM seat_weeks")
    code, out, err = run(
        capsys,
        "probe",
        "--config",
        config_id,
        "--sample",
        "3",
        "--game",
        game_id,
        "--game",
        game_id,
    )
    assert code == 0, err
    lines = out.splitlines()
    assert lines[-1] == "probed 3 answered=3 recognised=0"
    heads = [line for line in lines if line.startswith("game ")]
    assert len(heads) == 3 and all(f"game {game_id} week " in line for line in heads)
    assert out.count("  recognised no name ''") == 3
    rows = query(
        ai_db,
        "SELECT purpose, scope_kind, scope_id::text, prompt_version, outcome, caller_ref, "
        "request->>'prompt' FROM llm_call",
    )
    assert len(rows) == 3
    for purpose, kind, scope_id, version, outcome, caller, prompt in rows:
        assert (purpose, kind, scope_id, version, outcome) == (
            "recognition_probe",
            "evaluation",
            config_id,
            1,
            "ok",
        )
        assert caller["game"] == game_id and set(caller) == {"game", "seat", "week"}
        assert prompt.startswith("You are the supply chain manager")
        assert "known exercise, game, simulation" in prompt
        assert '{"order": N}' not in prompt  # one answer format only: the probe's own
        assert game_id not in prompt
    assert query(games_db, "SELECT count(*) FROM seat_weeks") == before
    # The same seed samples the same Seat states.
    code, again, _ = run(capsys, "probe", "--config", config_id, "--sample", "3", "--game", game_id)
    assert code == 0
    assert [line.split(" calls")[0] for line in again.splitlines() if line.startswith("game")] == [
        line.split(" calls")[0] for line in heads
    ]


def test_probe_refuses_without_states_or_budget(games_db, ai_db, capsys):
    config_id = setup(_config())
    code, _, err = run(capsys, "probe", "--config", config_id)
    assert (code, err.strip()) == (
        1,
        "error no_seat_states: no stored non-Guided Seat state to probe",
    )
    game_id = setup(_finished_game())
    no_budget = setup(config.add(config.parse(mock_config(prompts=PROMPTS))))
    code, _, err = run(capsys, "probe", "--config", str(no_budget.id), "--game", game_id)
    assert code == 1 and err.startswith("error budget_not_found")


def test_probe_samples_only_non_guided_states_by_default(games_db, ai_db, capsys):
    """Without `--game` the newest finished Games are sampled; Guided Weeks never are."""
    game_id = setup(_finished_game())
    config_id = setup(_config("10"))
    ((non_guided,),) = query(
        games_db,
        "SELECT count(*) FROM seat_weeks WHERE game_id = %s AND decided_by <> 'guided'",
        (game_id,),
    )
    code, out, err = run(capsys, "probe", "--config", config_id, "--sample", "1000")
    assert code == 0, err
    assert out.splitlines()[-1] == f"probed {non_guided} answered={non_guided} recognised=0"
    weeks = {int(line.split()[3]) for line in out.splitlines() if line.startswith("game ")}
    assert min(weeks) == GameSettings().guided_weeks + 1


def test_probe_prints_failures_and_exits_1_without_an_answer(games_db, ai_db, capsys):
    from app.ai import mock

    game_id = setup(_finished_game())
    config_id = setup(_config())
    with mock.script("invalid", "invalid", "invalid"):
        code, out, _ = run(
            capsys, "probe", "--config", config_id, "--sample", "1", "--game", game_id
        )
    assert code == 1
    lines = out.splitlines()
    assert lines[0].startswith(f"game {game_id} week ") and lines[0].count(",") == 2
    assert lines[1].startswith("  failure invalid_output: ")
    assert lines[-1] == "probed 1 answered=0 recognised=0"
