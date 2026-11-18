"""Story 2.12: `python -m app.sim approve` turns a batch report into an approved Effort level,
`python -m app.ai.cli pin` makes the config the default, `config show` prints the offer
(FR-68, FR-78, FR-79, AD-6). The batches run on the mock provider; a "real" batch is one stored
with `mock = false` because the runner's endpoint check is told the endpoint is real, while the
gateway still asks the mock: no test reaches a real endpoint."""

import json
import uuid

import pytest

from app import sim, sim_report
from app.ai import adapters, config, endpoint
from app.ai import cli as ai_cli
from tests.ai.helpers import stored_config
from tests.games.helpers import query
from tests.players.test_llm_jobs import llm_game
from tests.test_sim_llm import run, setup
from tests.test_sim_measure import batch_file, batch_id_of


def ai_run(capsys, *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = ai_cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


ONE_LLM = {
    "retailer": "llm",
    "wholesaler": "rule_based",
    "distributor": "rule_based",
    "factory": "rule_based",
}
"""One LLM Seat keeps the batch short."""


def one_game(tmp_path) -> str:
    return batch_file(tmp_path, games=1, seats=ONE_LLM)


@pytest.fixture
def real_endpoint(monkeypatch):
    """The runner's endpoint check says `real`: the batch is stored as not mock."""

    async def availability(config_id: str):
        return adapters.Availability("real")

    monkeypatch.setattr(endpoint, "availability", availability)


def test_a_mock_batch_is_never_approved(capsys, tmp_path, games_db, ai_db):
    config_id = setup(stored_config())
    code, out, err = run(capsys, "run", one_game(tmp_path), "--config", config_id)
    assert code == 0, err
    code, out, err = run(capsys, "approve", batch_id_of(out), "--level", "standard")
    assert code == 1
    assert out.splitlines()[0] == sim_report.MOCK_WARNING  # the report it was judged on
    assert err.startswith("error mock_batch: ")
    assert query(games_db, "SELECT count(*) FROM effort_measurements") == [(0,)]
    assert setup(config.offered_effort_levels(config_id)) == []


def test_a_real_batch_that_passed_is_approved_offered_and_pinned(
    capsys, tmp_path, games_db, ai_db, real_endpoint
):
    config_id = setup(stored_config())
    code, out, err = run(capsys, "run", one_game(tmp_path), "--config", config_id)
    assert code == 0, err
    batch_id = batch_id_of(out)
    assert query(games_db, "SELECT mock FROM simulation_batches") == [(False,)]

    code, out, err = run(capsys, "approve", batch_id, "--level", "turbo")
    assert (code, err.split(":")[0]) == (1, "error effort_level_unknown")
    code, out, err = run(capsys, "approve", batch_id, "--level", "standard")
    assert code == 0, err
    lines = out.splitlines()
    assert lines[0] == "provider real"
    (measurement,) = query(
        games_db,
        "SELECT id::text, model_config_id::text, effort_level, batch_id::text, mock, games, "
        "fallback_share, switched_share, pass_lines FROM effort_measurements",
    )
    assert measurement[1:6] == (config_id, "standard", batch_id, False, 1)
    assert measurement[6:8] == (0, 0)  # no fallback, no switch on the mock
    assert {line["verdict"] for line in measurement[8].values()} == {"pass"}
    assert lines[-1] == (
        f"approved config {config_id} effort_level standard batch {batch_id} "
        f"measurement {measurement[0]}"
    )
    code, _, err = run(capsys, "approve", batch_id, "--level", "standard")
    assert (code, err.split(":")[0]) == (1, "error already_approved")

    (offered,) = setup(config.offered_effort_levels(config_id))
    assert (offered.name, offered.default, str(offered.measurement.id)) == (
        "standard",
        True,
        measurement[0],
    )
    code, out, err = ai_run(capsys, "pin", config_id)
    assert code == 0, err
    pinned = out.splitlines()
    assert pinned[:2] == [f"pinned {config_id} name=mock", "level standard default=yes"]
    assert pinned[2].startswith(f"evidence effort_level=standard batch={batch_id} mock=no games=1 ")
    code, out, err = ai_run(capsys, "config", "show", config_id)
    shown = json.loads(out)
    assert shown["active_default"] is True
    assert [(level["name"], level["default"]) for level in shown["offered_effort_levels"]] == [
        ("standard", True)
    ]
    assert shown["offered_effort_levels"][0]["measurement"]["batch_id"] == batch_id


async def test_a_scope_keeps_its_config_when_the_default_changes(games_db, ai_db):
    """FR-68, AD-6: a Game holds the config id it was created with; pinning another config
    afterwards changes nothing for it, and all its LLM calls use its own config."""
    first = await stored_config()
    second = await stored_config(name="second")
    await config.add_mock_measurement(uuid.UUID(second), "standard")
    game_id = await llm_game(("retailer",), config_id=first)  # started, no Order asked yet
    await config.pin(second)
    assert str((await config.active_default()).id) == second
    game = await sim._wait_finished(game_id)
    assert game.lifecycle == "finished"
    assert game.session_runtime.model_config_id == first
    assert query(games_db, "SELECT DISTINCT model_config_id::text FROM llm_call") == [(first,)]


def test_pin_refuses_a_config_with_no_offered_level(capsys, ai_db):
    config_id = setup(stored_config())
    code, out, err = ai_run(capsys, "pin", config_id)
    assert (code, out) == (1, "")
    assert err.startswith("error no_offered_level: ")
    code, _, err = ai_run(capsys, "pin", str(uuid.uuid4()))
    assert code == 1 and err.startswith("error config_not_found: ")
    code, out, _ = ai_run(capsys, "config", "show", config_id)
    shown = json.loads(out)
    assert (shown["active_default"], shown["offered_effort_levels"]) == (False, [])


def test_approve_refuses_a_batch_without_a_config_or_an_unknown_one(capsys, tmp_path, games_db):
    code, out, err = run(capsys, "run", batch_file(tmp_path, seats="rule_based", games=1))
    assert code == 0, err
    code, out, err = run(capsys, "approve", batch_id_of(out), "--level", "standard")
    assert code == 1 and err.startswith("error model_config_missing: ")
    code, out, err = run(capsys, "approve", str(uuid.uuid4()), "--level", "standard")
    assert (code, out) == (1, "") and err.startswith("error batch_not_found: ")


def test_effort_figures_carry_the_report_figures_in_seconds():
    """The stored measurement is the report's figures: cost per Game, time per Order in
    seconds (median, p95), retries, the fallback share and the switched share."""
    from datetime import UTC, datetime
    from decimal import Decimal
    from types import SimpleNamespace

    from app.modules.games.service import Fallback

    total = SimpleNamespace(
        fallbacks=((Fallback.NONE, 3), (Fallback.TIMEOUT, 1)),
        llm_orders=4,
        order_time_ms=sim_report.Spread(1200, 2500),
        retries_mean=Decimal("0.5"),
        switched_seats=1,
        llm_seats=4,
    )
    lines = (
        sim_report.PassLine("cost_per_game_usd", Decimal("0.1"), Decimal("0.03")),
        sim_report.PassLine("time_per_order_p95_s", Decimal("8"), Decimal("2.5")),
        sim_report.PassLine("switched_share", Decimal("0.25"), Decimal("0.25")),
    )
    report = SimpleNamespace(
        model_config_id="c",
        effort_levels=("standard",),
        mock=False,
        games=(object(), object()),
        cost_per_game_usd=Decimal("0.03"),
        total=total,
        pass_lines=lines,
        started_at=datetime.now(UTC),
    )
    found = sim.effort_figures(report)
    assert (found.games, found.cost_per_game_usd) == (2, Decimal("0.03"))
    assert (found.time_per_order_median_s, found.time_per_order_p95_s) == (
        Decimal("1.2"),
        Decimal("2.5"),
    )
    assert (found.retries_per_order_mean, found.fallback_share, found.switched_share) == (
        Decimal("0.5"),
        Decimal("0.25"),
        Decimal("0.25"),
    )
    assert [(v.name, v.verdict) for v in found.pass_lines] == [
        ("cost_per_game_usd", "pass"),
        ("time_per_order_p95_s", "pass"),
        ("switched_share", "pass"),
    ]
