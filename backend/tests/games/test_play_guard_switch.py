"""Story 2.10: `place_order` runs the Play guard on every LLM Order and switches a drifting
Seat to a Rule-based player for the rest of the Game (FR-79, FR-67, AD-5).

The Games are Classic Games cut to `SHORT`, which the guard treats as calibrated through
an extra settings profile served with the shipped set (`short_profile`): the same mechanism as a
new profile in a new version of the set, and short enough to keep the tests fast."""

import ast
import json
import uuid
from pathlib import Path

import pytest

from app.ai import gateway
from app.analysis import play_guard
from app.engine import GameSettings
from app.modules.games import commands, service
from app.modules.players import llm
from app.platform import jobs
from tests.ai.helpers import stored_config
from tests.games.helpers import execute, query

WEEKS = 10
GUIDED = 1
SHORT = {"weeks": WEEKS, "guided_weeks": GUIDED}
"""Classic settings cut to 10 Weeks with one Guided Week: nine LLM Orders per Game."""
MINIMUM = 8
"""`minimum_weeks` of the shipped placeholder set."""
SWITCH_WEEK = GUIDED + MINIMUM + 1
"""The first Week a Seat switched at the minimum is Rule-based in."""


@pytest.fixture
def short_profile(monkeypatch):
    """Serve the shipped Play guard set with one more calibrated profile: Classic cut to
    `SHORT`."""
    original = commands.read_parameter_set

    def read(kind: str, set_id: str) -> str:
        text = original(kind, set_id)
        if kind != "play_guard":
            return text
        data = json.loads(text)
        data["calibrated_profiles"]["short"] = GameSettings(**SHORT).model_dump(mode="json")
        return json.dumps(data)

    monkeypatch.setattr(commands, "read_parameter_set", read)


def scripted(monkeypatch, url: str, answer) -> None:
    """Make the mock LLM player answer `answer(rule_based_reference, near_optimal_reference)`
    instead of the Rule-based reference Order (the mock's default answer)."""
    original = llm.request_inputs

    def request_inputs(game_id, seat_id, week, seat_state, reference_order):
        ((near_optimal,),) = query(
            url,
            "SELECT near_optimal_reference_order FROM seat_turns "
            "WHERE game_id = %s AND seat_id = %s AND week = %s",
            (str(game_id), str(seat_id), week),
        )
        inputs = original(game_id, seat_id, week, seat_state, reference_order)
        return gateway.Inputs(
            values=inputs.values,
            caller=inputs.caller,
            mock_answer={"order": answer(reference_order, near_optimal)},
        )

    monkeypatch.setattr(llm, "request_inputs", request_inputs)


async def simulated_game(config_id: str) -> str:
    """A `SHORT` simulation Game whose retailer is an LLM player, played to the end through
    the real job and mock gateway path."""
    game_id = await commands.create(
        "simulation", GameSettings(**SHORT), seed=7, model_config_id=config_id
    )
    await commands.assign_seat(game_id, "retailer", "llm")
    await commands.start(game_id)
    await jobs.run_until_idle([jobs.AI_ORDERS])
    return game_id


def switches(history) -> list[tuple[str, int, str]]:
    return [
        (row.role, row.from_week, row.occupant_kind)
        for row in history
        if row.reason == "guard_switch"
    ]


async def retailer_log(game_id: str):
    return [row for row in await service.decision_log(game_id) if row.role == "retailer"]


def guard_rows(log) -> list[play_guard.GuardRow]:
    return [
        play_guard.GuardRow(
            week=row.week,
            order=row.order,
            decided_by=row.decided_by,
            rule_based_reference_order=row.rule_based_reference_order,
            near_optimal_reference_order=row.near_optimal_reference_order,
        )
        for row in log
    ]


@pytest.mark.parametrize(
    ("answer", "statistic"),
    [
        pytest.param(lambda rb, no: rb + 20, "lower_share", id="far-above"),
        # It strays more than the lower distance from the Rule-based reference first.
        pytest.param(lambda rb, no: no, "lower_share", id="near-optimal"),
        pytest.param(lambda rb, no: rb + 1 if rb + 1 != no else rb, None, id="within-band"),
    ],
)
async def test_three_scripted_llm_players(
    monkeypatch, short_profile, games_db, ai_db, answer, statistic
):
    scripted(monkeypatch, games_db, answer)
    game_id = await simulated_game(await stored_config())
    assert (await service.get_game(game_id)).lifecycle == "finished"
    history = await service.occupancy_history(game_id)
    log = await retailer_log(game_id)
    llm_weeks = [row.week for row in log if row.decided_by == "llm"]
    if statistic is None:
        assert switches(history) == []
        assert llm_weeks == list(range(GUIDED + 1, WEEKS + 1))
        assert {row.reason for row in log} == {"initial"}
        return
    # Switched after exactly the minimum number of LLM Orders, from the next Week on.
    assert switches(history) == [("retailer", SWITCH_WEEK, "rule_based")]
    assert llm_weeks == list(range(GUIDED + 1, SWITCH_WEEK))
    params = commands._play_guard_params(commands.DEFAULT_PLAY_GUARD_SET)
    assert play_guard.evaluate(guard_rows(log), params).statistic == statistic
    later = [row for row in log if row.week >= SWITCH_WEEK]
    assert len(later) == WEEKS - SWITCH_WEEK + 1
    for row in later:
        assert (row.decided_by, row.occupant_kind, row.reason) == (
            "rule_based",
            "rule_based",
            "guard_switch",
        )
        assert (row.fallback, row.llm_call_ids) == ("none", ())
        assert row.order == row.rule_based_reference_order
    ((calls,),) = query(games_db, "SELECT count(*) FROM llm_call")
    assert calls == MINIMUM  # the model is never asked again
    assert (await service.get_game(game_id)).seats[0].occupant_kind == "rule_based"
    assert (await service.verify_finished(game_id)).ok


async def placed_directly(url: str, answer, *, guarded: bool = True) -> str:
    """A `SHORT` Game whose retailer is an LLM player, played by placing its LLM Orders with
    `place_order` (a made-up call id) instead of through the job, which is slower; the guard
    runs in `place_order` either way. `guarded=False` strips the guard set from the snapshot,
    as on a Game created before Story 2.10."""
    game_id = await commands.create(
        "simulation", GameSettings(**SHORT), seed=7, model_config_id=await stored_config()
    )
    if not guarded:
        runtime = (await service.get_game(game_id)).session_runtime.model_dump(mode="json")
        old = {key: value for key, value in runtime.items() if not key.startswith("play_guard")}
        execute(
            url,
            "UPDATE games SET session_runtime = %s::jsonb WHERE id = %s",
            (json.dumps(old), game_id),
        )
    await commands.assign_seat(game_id, "retailer", "llm")
    await commands.start(game_id)
    while (await service.get_game(game_id)).lifecycle != "finished":
        turn = await service.open_turn(game_id, "retailer")
        if turn.ordered_at is not None:
            break  # not the LLM player's to place: nothing left to drive
        order = answer(turn.rule_based_reference_order, turn.near_optimal_reference_order)
        await commands.place_order(
            game_id, "retailer", turn.week, order, "llm", llm_call_ids=[uuid.uuid4()]
        )
    return game_id


async def test_uncalibrated_settings_apply_only_the_large_deviation(games_db, ai_db):
    """Off by 10 every Week: outside the lower distance (4), so a calibrated Game would switch,
    but inside the large one (16). Off by 20 is a large deviation."""
    params = commands._play_guard_params(commands.DEFAULT_PLAY_GUARD_SET)
    assert not play_guard.is_calibrated(GameSettings(**SHORT), params)
    moderate = await placed_directly(games_db, lambda rb, no: rb + 10)
    assert switches(await service.occupancy_history(moderate)) == []
    large = await placed_directly(games_db, lambda rb, no: rb + 20)
    assert switches(await service.occupancy_history(large)) == [
        ("retailer", SWITCH_WEEK, "rule_based")
    ]


async def test_place_order_feeds_the_guard_the_stored_references(
    monkeypatch, short_profile, games_db, ai_db
):
    """The guard sees each LLM Order with both stored references (the upper limit needs the
    near-optimal one) and the calibration of the Game's settings."""
    seen = []
    evaluate = play_guard.evaluate

    def spy(rows, params, *, calibrated):
        seen.append((list(rows), calibrated))
        return evaluate(seen[-1][0], params, calibrated=calibrated)

    monkeypatch.setattr(commands.play_guard, "evaluate", spy)
    game_id = await placed_directly(games_db, lambda rb, no: rb)
    log = await retailer_log(game_id)
    assert len(seen) == WEEKS - GUIDED
    rows, calibrated = seen[-1]
    assert calibrated is True
    assert rows == guard_rows(log)
    assert any(r.near_optimal_reference_order != r.rule_based_reference_order for r in rows)
    assert all(r.near_optimal_reference_order is not None for r in rows)


async def test_a_game_from_before_the_guard_is_not_guarded(short_profile, games_db, ai_db):
    game_id = await placed_directly(games_db, lambda rb, no: rb + 20, guarded=False)
    assert switches(await service.occupancy_history(game_id)) == []
    log = await retailer_log(game_id)
    assert [row.decided_by for row in log] == ["guided"] + ["llm"] * (WEEKS - GUIDED)


async def test_the_game_snapshot_holds_the_guard_set(games_db):
    game_id = await commands.create("simulation", GameSettings(), seed=1)
    runtime = (await service.get_game(game_id)).session_runtime
    assert (runtime.play_guard_params, runtime.play_guard_params_version) == ("placeholder-1", 1)


async def test_an_unknown_guard_set_is_refused(games_db):
    with pytest.raises(commands.CommandError) as refused:
        await commands.create("simulation", GameSettings(), seed=1, play_guard_params="nope")
    assert (refused.value.code, refused.value.status) == ("unknown_parameter_set", 422)


async def test_an_invalid_guard_set_is_refused(monkeypatch, games_db):
    monkeypatch.setattr(commands, "read_parameter_set", lambda kind, set_id: "{}")
    with pytest.raises(commands.CommandError) as refused:
        commands._play_guard_params("placeholder-0")
    assert (refused.value.code, refused.value.status) == ("invalid_parameter_set", 422)


async def test_a_changed_guard_set_version_is_refused(games_db):
    game_id = await commands.create("simulation", GameSettings(), seed=1)
    execute(
        games_db,
        "UPDATE games SET session_runtime = jsonb_set(session_runtime, "
        "'{play_guard_params_version}', '999') WHERE id = %s",
        (game_id,),
    )
    with pytest.raises(commands.CommandError) as refused:
        await commands.start(game_id)
    assert (refused.value.code, refused.value.status) == ("parameter_set_changed", 409)


async def test_occupancy_history_of_an_unknown_game_is_refused(games_db):
    with pytest.raises(service.ViewError):
        await service.occupancy_history("not-a-game")


def test_the_ai_orders_job_never_runs_the_guard():
    players = Path(__file__).parents[2] / "app" / "modules" / "players"
    for path in players.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        modules = {
            node.module or ""
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom)
        }
        assert not any("analysis" in module for module in modules), path.name
        assert "play_guard" not in source, path.name
