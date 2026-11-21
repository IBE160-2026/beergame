"""Story 10.1 (FR-79, AD-22): `python -m app.sim run` plays a batch on the default Replay scenario,
each Game on the settings its seed resolves, so the Play guard band can be calibrated on it. No
Game is played here: the batch is loaded and the create call is caught."""

import asyncio
import json
from pathlib import Path

import pytest

from app import sim
from app.engine import GameSettings, default_replay_template, replay_settings


def batch_file(tmp_path, **changes) -> str:
    data = {"seed": 11, "games": 3, "seats": "rule_based", "scenario": "replay_default"}
    data.update(changes)
    path = tmp_path / "replay.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_each_game_of_a_replay_batch_plays_its_own_draw(tmp_path):
    batch = sim.load_batch(batch_file(tmp_path, settings={"shipping_delay": 3}))
    template = default_replay_template(GameSettings(shipping_delay=3))
    assert batch.template == template
    drawn = [sim.game_settings(batch, index) for index in range(3)]
    assert drawn == [(replay_settings(template, 11 + index), None) for index in range(3)]
    assert len({(s.weeks, s.demand.change_week) for s, _ in drawn}) > 1


def test_the_shipped_replay_batch_loads_ten_draws_of_the_classic_default():
    path = Path(__file__).parents[1] / "batches" / "replay-default-rule-based.json"
    batch = sim.load_batch(str(path))
    assert (batch.games, batch.template) == (10, default_replay_template(GameSettings()))


def test_a_batch_without_a_scenario_plays_its_own_settings(tmp_path):
    batch = sim.load_batch(batch_file(tmp_path, scenario=None))
    assert batch.template is None
    assert sim.game_settings(batch, 2) == (GameSettings(), None)


def test_a_replay_batch_refuses_its_own_demand(tmp_path):
    demand = {"kind": "step", "start": 4, "new_level": 8, "change_week": 5}
    with pytest.raises(sim.BatchError, match="demand"):
        sim.load_batch(batch_file(tmp_path, demand=demand))
    with pytest.raises(sim.BatchError, match="scenario"):
        sim.load_batch(batch_file(tmp_path, scenario="replay_own"))
    # The scenario draws the Weeks and sets no Guided Weeks: a batch that names them is refused.
    for key, value in (("weeks", 20), ("guided_weeks", 2)):
        with pytest.raises(sim.BatchError, match=f"settings.{key}"):
            sim.load_batch(batch_file(tmp_path, settings={key: value}))


def test_the_runner_creates_the_game_on_the_resolved_settings(tmp_path, monkeypatch):
    batch = sim.load_batch(batch_file(tmp_path))
    seen = []

    class Stop(Exception):
        pass

    async def create(purpose, settings, demand, **kwargs):
        seen.append((purpose, settings, demand, kwargs["seed"]))
        raise Stop

    monkeypatch.setattr(sim.game_commands, "create", create)
    with pytest.raises(Stop):
        asyncio.run(sim._play_one(batch, 1, [], worker=False))
    assert seen == [("simulation", replay_settings(batch.template, 12), None, 12)]
