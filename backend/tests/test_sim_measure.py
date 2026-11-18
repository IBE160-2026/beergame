"""Story 2.11: measure a model config and Effort level on a batch of simulated Games. `run`
stores the batch and its Games, `report` reads them back from the Decision log and `llm_call`
(AD-22, AD-15, FR-78). All on the mock provider; tiny batches."""

import asyncio
import json
import uuid

import psycopg
import pytest

from app import sim, sim_report
from app.ai import calls
from app.engine import GameSettings
from app.modules.games import commands
from app.modules.players import llm
from app.platform import jobs
from tests.ai.helpers import stored_config
from tests.games.helpers import execute, query
from tests.players.test_llm_jobs import llm_game
from tests.test_sim_llm import SETTINGS, run, setup

LINES = {"cost_per_game_usd": 0.10, "time_per_order_p95_s": 8, "switched_share": 0.25}


def batch_file(tmp_path, **changes) -> str:
    data = {"seed": 5, "games": 2, "seats": "llm", "settings": SETTINGS, "pass_lines": LINES}
    data.update(changes)
    path = tmp_path / "measure.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def batch_id_of(out: str) -> str:
    (line,) = [line for line in out.splitlines() if line.startswith("batch_id ")]
    return line.split(" ")[1]


def test_a_mock_batch_is_stored_measured_and_reported(capsys, tmp_path, games_db, ai_db):
    config_id = setup(stored_config())
    code, out, err = run(capsys, "run", batch_file(tmp_path), "--config", config_id)
    assert code == 0, err
    batch_id = batch_id_of(out)
    printed = [
        line.split(" ")[0] for line in out.splitlines() if line.startswith(("batch", "game"))
    ]
    assert printed[0] == "batch_id"  # before the first Game, so a stopped run still names it

    (stored,) = query(
        games_db, "SELECT batch_file, pass_lines, mock, started_at FROM simulation_batches"
    )
    assert stored[0]["model_config"] == config_id and stored[0]["seats"] == "llm"
    assert stored[1] == LINES and stored[2] is True
    game_ids = [
        str(row[0])
        for row in query(
            games_db, "SELECT id FROM games WHERE batch_id = %s ORDER BY id", (batch_id,)
        )
    ]
    assert len(game_ids) == 2
    # FR-78: the Effort level is on every LLM call and every Decision log row of an LLM player;
    # the calls are charged to the config's evaluation budget.
    assert query(
        games_db, "SELECT DISTINCT effort_level, scope_kind, scope_id::text FROM llm_call"
    ) == [("standard", "evaluation", config_id)]
    assert query(games_db, "SELECT DISTINCT effort_level, occupant_kind FROM seat_weeks") == [
        ("standard", "llm")
    ]
    assert calls.PLAYER_PURPOSE == llm.PURPOSE
    logged = setup(sim.game_service.decision_log(game_ids[0]))
    assert {row.effort_level for row in logged} == {"standard"}
    # A call of another purpose on a batch Game (`sim probe`) is no player attempt: the report
    # leaves it out.
    execute(
        games_db,
        "CREATE TEMP TABLE probe AS SELECT * FROM llm_call LIMIT 1; "
        "UPDATE probe SET id = gen_random_uuid(), purpose = 'recognition_probe'; "
        "INSERT INTO llm_call SELECT * FROM probe",
    )

    code, out, err = run(capsys, "report", batch_id)
    assert code == 0, err
    report = out.splitlines()
    assert report[0] == sim_report.MOCK_WARNING
    assert report[1].startswith(f"batch {batch_id} started ")
    assert report[1].endswith(f"games 2 model_config {config_id} effort_level standard")
    assert [line.split(" ")[1] for line in report if line.startswith("game ")] == game_ids
    (count,) = query(games_db, "SELECT count(*) FROM llm_call WHERE purpose = 'player_order'")[0]
    batch_block = report[report.index("batch games 2") :]
    assert batch_block[1].startswith("  ai_cost usd=") and batch_block[1].endswith(f"calls={count}")
    assert "  llm_share orders=16/16 share=1.0000" in batch_block
    assert "  fallback llm_orders=16 none=1.0000" in batch_block
    assert "  guard_switched seats=0/8 share=0.0000" in batch_block
    assert "  retries_per_order mean=0.00 max=0" in batch_block
    assert "cut_short no" in report
    verdicts = [line for line in report if line.startswith("pass_line ")]
    assert [line.split(" ")[1] for line in verdicts] == list(sim_report.PASS_LINES)
    assert all(line.endswith(" pass") for line in verdicts), verdicts


def test_the_pass_lines_never_change_once_stored(capsys, tmp_path, games_db, ai_db):
    code, out, err = run(capsys, "run", batch_file(tmp_path, seats="rule_based", games=1))
    assert code == 0, err
    batch_id = batch_id_of(out)
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(
            games_db,
            "UPDATE simulation_batches SET pass_lines = '{}' WHERE id = %s",
            (batch_id,),
        )
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute(games_db, "DELETE FROM simulation_batches")
    code, out, _ = run(capsys, "report", batch_id)
    assert code == 0
    report = out.splitlines()
    assert report[0] == "provider none (no llm Seats)"
    assert report[-3:] == [
        "pass_line cost_per_game_usd line=0.1 measured=n/a n/a",
        "pass_line time_per_order_p95_s line=8 measured=n/a n/a",
        "pass_line switched_share line=0.25 measured=n/a n/a",
    ]


def test_at_the_cost_limit_the_batch_finishes_on_rule_based_players_and_is_cut_short(
    capsys, tmp_path, games_db, ai_db
):
    config_id = setup(stored_config(limit="0"))
    code, out, err = run(capsys, "run", batch_file(tmp_path), "--config", config_id)
    assert code == 0, err
    batch_id = batch_id_of(out)
    first, second = (str(row[0]) for row in query(games_db, "SELECT id FROM games ORDER BY id"))
    # The second Game had Rule-based players from its start: no LLM Order, no fallback.
    assert query(
        games_db,
        "SELECT DISTINCT decided_by, fallback FROM seat_weeks WHERE game_id = %s AND week > 1",
        (second,),
    ) == [("rule_based", "none")]
    # FR-78: the Effort level is on the LLM player's rows only, never on a Rule-based one.
    assert query(
        games_db, "SELECT DISTINCT occupant_kind, effort_level FROM seat_weeks ORDER BY 1"
    ) == [("llm", "standard"), ("rule_based", None)]
    code, out, _ = run(capsys, "report", batch_id)
    assert code == 0
    assert f"cut_short game {first} week 2 " in out
    # Its later Games ran on Rule-based players: no line can pass on them.
    verdicts = [line for line in out.splitlines() if line.startswith("pass_line ")]
    assert len(verdicts) == 3 and all(line.endswith(" miss (cut short)") for line in verdicts)


@pytest.mark.parametrize(
    ("lines", "detail"),
    [
        ({"cost_per_game_usd": -1}, "pass_lines.cost_per_game_usd"),
        ({"switched_share": 2}, "pass_lines.switched_share"),
        ({"cost_per_game": 0.1}, "pass_lines.cost_per_game"),
    ],
)
def test_bad_pass_lines_are_refused(capsys, tmp_path, games_db, lines, detail):
    code, out, err = run(capsys, "run", batch_file(tmp_path, seats="rule_based", pass_lines=lines))
    assert code == 2 and out == ""
    assert err.startswith("error invalid_batch: ") and detail in err
    assert query(games_db, "SELECT count(*) FROM simulation_batches") == [(0,)]


def test_config_must_match_the_one_the_file_names(capsys, tmp_path, games_db):
    path = batch_file(tmp_path, model_config=str(uuid.uuid4()))
    code, _, err = run(capsys, "run", path, "--config", str(uuid.uuid4()))
    assert code == 2
    assert err.startswith("error invalid_batch: model_config: the file names ")
    same = str(uuid.uuid4())
    assert sim.load_batch(batch_file(tmp_path, model_config=same), same).model_config_id == same


def test_an_unknown_config_stops_the_run_before_a_batch_is_stored(capsys, tmp_path, games_db):
    code, out, err = run(capsys, "run", batch_file(tmp_path), "--config", str(uuid.uuid4()))
    assert (code, out) == (1, "")
    assert err.startswith("error config_not_found: ")
    assert query(games_db, "SELECT count(*) FROM simulation_batches") == [(0,)]


@pytest.mark.parametrize("batch_id", ["01a1ecc9-0000-7000-8000-000000000000", "x"])
def test_report_refuses_an_unknown_batch(capsys, games_db, batch_id):
    code, out, err = run(capsys, "report", batch_id)
    assert (code, out) == (1, "")
    assert err.startswith("error batch_not_found: ")


async def test_create_refuses_an_unknown_batch(games_db):
    with pytest.raises(commands.CommandError) as info:
        await commands.create("simulation", GameSettings(), batch_id=str(uuid.uuid4()))
    assert info.value.code == "batch_not_found"


async def test_with_worker_the_runner_waits_for_a_worker_to_play_the_game(
    games_db, ai_db, monkeypatch
):
    """`run --worker`: the runner runs no job itself; here a loop of `run_until_idle` stands in
    for the `worker-ai` process (CI runs the real one, `scripts/sim-llm-smoke.sh`)."""
    monkeypatch.setattr(sim, "WORKER_POLL_S", 0.02)
    ran: list[str] = []
    monkeypatch.setattr(sim, "_work_off_llm_orders", lambda game: ran.append(game.id))
    game_id = await llm_game(("retailer",))
    done = asyncio.Event()

    async def worker() -> None:
        while not done.is_set():
            await jobs.run_until_idle([jobs.AI_ORDERS])
            await asyncio.sleep(0.02)

    async def wait() -> object:
        try:
            return await sim._wait_finished(game_id, worker=True)
        finally:
            done.set()

    game, _ = await asyncio.gather(wait(), worker())
    assert game.lifecycle == "finished" and ran == []


async def test_with_worker_a_game_nobody_plays_stops_after_the_stall_time(
    games_db, ai_db, monkeypatch
):
    monkeypatch.setattr(sim, "WORKER_POLL_S", 0.02)
    monkeypatch.setattr(sim, "WORKER_STALL_S", 0.2)
    game_id = await llm_game(("retailer",))
    with pytest.raises(commands.CommandError) as info:
        await sim._wait_finished(game_id, worker=True)
    assert info.value.code == "game_not_finished"


@pytest.mark.parametrize("name", ["measure-mock-smoke", "measure-openrouter-small"])
def test_the_shipped_measure_batches_load_with_a_config_and_carry_pass_lines(name):
    from pathlib import Path

    path = Path(__file__).parents[1] / "batches" / f"{name}.json"
    with pytest.raises(sim.BatchError):
        sim.load_batch(str(path))  # llm Seats need a model config
    config_id = str(uuid.uuid4())
    batch = sim.load_batch(str(path), config_id)
    assert batch.stored["model_config"] == config_id
    assert set(batch.pass_lines) == set(sim_report.PASS_LINES)
    assert all(kind == "llm" for kind, _ in batch.occupants)
