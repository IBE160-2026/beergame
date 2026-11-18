"""Story 2.5: the simulation runner plays `llm` Seats through the real job, gateway and
fallback path (AD-22, NFR-4)."""

import json

from app import sim
from app.ai import mock
from app.platform import db
from tests.ai.helpers import stored_config
from tests.games.helpers import query

SETTINGS = {"weeks": 3, "guided_weeks": 1, "demand": {"kind": "fixed", "values": [4, 8, 8]}}
"""One Guided Week, then two Weeks the LLM players are asked in."""


def setup(coroutine):
    async def wrapped():
        try:
            return await coroutine
        finally:
            await db.dispose()

    return sim._run(wrapped())


def run(capsys, *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = sim.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def batch(tmp_path, config_id: str, **changes) -> str:
    data = {"seed": 5, "games": 1, "seats": "llm", "settings": SETTINGS}
    data["model_config"] = config_id
    data.update(changes)
    path = tmp_path / "llm.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_a_whole_game_with_the_provider_down_finishes_on_fallback_orders(
    capsys, tmp_path, games_db, ai_db
):
    """NFR-4: four `llm` Seats, every attempt fails; the Game still finishes, every
    non-Guided Order is the Rule-based reference marked `provider_error`, the check passes."""
    config_id = setup(stored_config())
    with mock.outage():
        code, out, err = run(capsys, "run", batch(tmp_path, config_id))
    assert code == 0, err
    assert "checks ok=1 failed=0" in out
    assert "orders rule_based=8 guided=4" in out
    logged = query(
        games_db,
        "SELECT week, decided_by, fallback, cardinality(llm_call_ids), "
        '"order" = rule_based_reference_order, occupant_kind FROM seat_weeks ORDER BY week',
    )
    assert [row[:3] for row in logged if row[0] == 1] == [(1, "guided", "none")] * 4
    later = [row for row in logged if row[0] > 1]
    assert later == [(row[0], "rule_based", "provider_error", 6, True, "llm") for row in later]
    assert len(later) == 8
    assert query(games_db, "SELECT lifecycle FROM games") == [("finished",)]


def test_create_and_run_take_llm_seats_with_a_config_and_effort_level(
    capsys, tmp_path, games_db, ai_db
):
    config_id = setup(stored_config())
    code, out, err = run(capsys, "create", "--seats", "llm", "--config", config_id)
    assert code == 0, err
    assert out.splitlines()[-4:] == [
        "seat retailer llm",
        "seat wholesaler llm",
        "seat distributor llm",
        "seat factory llm",
    ]
    code, _, err = run(capsys, "create", "--seats", "llm")
    assert code == 1
    assert "error model_config_required" in err
    code, _, err = run(capsys, "create", "--config", config_id, "--effort-level", "turbo")
    assert (code, err.splitlines()[0]) == (
        1,
        f"error effort_level_unknown: model config {config_id} has no Effort level 'turbo'",
    )
    code, out, err = run(
        capsys, "run", batch(tmp_path, config_id, effort_level="standard", seats="llm")
    )
    assert code == 0, err
    assert "orders llm=8 guided=4" in out
    (runtime,) = query(
        games_db,
        "SELECT session_runtime->>'effort_level' FROM games WHERE lifecycle = 'finished'",
    )
    assert runtime == ("standard",)
