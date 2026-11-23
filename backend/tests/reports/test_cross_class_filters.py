"""Filtered comparisons and difference labels in Tverrklasse-statistikk (Story 14.4, FR-65, NFR-6,
AD-10, AD-14): `cross_class.compare` reads only the stored comparability keys of the aggregates
(pure cases below); `GET /api/class-statistics` applies the filters, reports the options with
their counts, labels what each compared Class session differs in and whether the Core-only
scores are comparable. The api tests store aggregate headers for fresh Class sessions, so no
game is played. Also Story 14.3's deferred item: the keys an aggregate stores."""

import json
import uuid

from app.ai import config
from app.modules.reports import aggregates, cross_class
from app.modules.sessions import service as sessions
from tests.ai.helpers import mock_config
from tests.classes.test_classes import LECTURER, OTHER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call
from tests.sessions.test_dates import new_session
from tests.sessions.test_game_end import _empty, clock, emitted, klass

__all__ = ["_empty", "clock", "emitted", "klass"]

SETTINGS = {"weeks": 30}
"""Stand-in Game settings: `compare` only hashes and names them."""
SCORE = {
    "question_set_version": 3,
    "item_weights": {"q1": 50, "q2": 50},
    "scoring_guide": {"id": "g", "version": 2},
}


def keys(**changed: object) -> dict[str, object]:
    found: dict[str, object] = {
        "game_settings": SETTINGS,
        "ai_mode": "llm",
        "model_config_id": "m1",
        "prompt_versions": {"order": 2, "debrief": 1},
        "effort_level": "low",
        **SCORE,
    }
    found.update(changed)
    return {k: v for k, v in found.items() if v is not ...}


A, B, C, D = (uuid.UUID(int=n) for n in range(1, 5))


def option(result: cross_class.Comparison, dimension: str, label: object):
    [found] = [f for f in result.filters if f.dimension == dimension]
    return next(o for o in found.options if o.label == label), found


def test_equal_keys_differ_in_nothing_and_the_scores_compare():
    result = cross_class.compare([(A, keys()), (B, keys()), (C, keys())], {})
    assert result.compared == [A, B, C]
    assert result.differs == {A: [], B: [], C: []}
    assert result.scores_comparable is True
    assert [f.dimension for f in result.filters] == list(cross_class.DIMENSIONS)


def test_the_odd_one_out_is_labelled_with_what_differs():
    rule = keys(ai_mode="rule_based", model_config_id=None, effort_level=None, prompt_versions=None)
    result = cross_class.compare([(A, keys()), (B, keys()), (C, rule)], {})
    assert result.differs[A] == result.differs[B] == []
    assert result.differs[C] == ["ai_mode", "model", "prompt_versions", "effort_level"]
    # Setup only: the scores still compare.
    assert result.scores_comparable is True


def test_a_tie_labels_both_sides():
    result = cross_class.compare([(A, keys()), (B, keys(ai_mode="rule_based"))], {})
    assert result.differs == {A: ["ai_mode"], B: ["ai_mode"]}


def test_a_filter_compares_only_the_matching_sessions_with_faceted_counts():
    rule = keys(ai_mode="rule_based")
    ready = [(A, keys()), (B, keys(effort_level="high")), (C, rule)]
    llm, _ = option(cross_class.compare(ready, {}), "ai_mode", "llm")
    assert (llm.count, llm.selected) == (2, False)
    result = cross_class.compare(ready, {"ai_mode": llm.value})
    assert result.compared == [A, B]
    chosen, group = option(result, "ai_mode", "llm")
    assert chosen.selected and group.all_count == 3
    # Effort level counts only the LLM sessions now: one «low», one «high»; «Alle» two.
    low, effort = option(result, "effort_level", "low")
    assert (low.count, effort.all_count) == (1, 2)
    assert result.differs == {A: ["effort_level"], B: ["effort_level"]}
    # Two filters hold together.
    both = cross_class.compare(ready, {"ai_mode": llm.value, "effort_level": low.value})
    assert both.compared == [A] and both.scores_comparable is None


def test_an_unknown_token_is_ignored():
    result = cross_class.compare([(A, keys()), (B, keys(ai_mode="x"))], {"ai_mode": "zzz"})
    assert result.compared == [A, B]
    assert not any(o.selected for f in result.filters for o in f.options)


def test_different_item_weights_make_the_scores_not_comparable():
    other = keys(item_weights={"q1": 40, "q2": 60})
    result = cross_class.compare([(A, keys()), (B, keys()), (C, other)], {})
    assert result.scores_comparable is False
    assert result.differs[C] == ["item_weights"]


def test_a_key_missing_from_an_older_aggregate_reads_as_none():
    older = keys(scoring_guide=...)
    assert "scoring_guide" not in older
    result = cross_class.compare([(A, keys()), (B, keys()), (C, older)], {})
    assert result.differs[C] == ["scoring_guide"] and result.scores_comparable is False
    # Absent from every aggregate: nothing proves the scores comparable.
    both = cross_class.compare([(A, older), (B, older)], {})
    assert both.differs == {A: [], B: []} and both.scores_comparable is False


def test_the_labels_are_data_never_copy():
    names = {"m1": sessions.ModelName("DeepSeek flash", {"low": "Lav"})}
    other = keys(game_settings={"weeks": 20}, model_config_id="gone", effort_level="mid")
    result = cross_class.compare([(A, keys()), (B, other), (C, keys(ai_mode="x"))], {}, names)
    labels = {f.dimension: [(o.label, o.ordinal) for o in f.options] for f in result.filters}
    # Neither stand-in is the Classic preset: numbered in order.
    assert labels["game_settings"] == [(None, 1), (None, 2)]
    assert labels["model"] == [("DeepSeek flash", 0), ("gone", 0)]
    assert labels["prompt_versions"] == [("debrief 1, order 2", 0)]
    assert labels["effort_level"] == [("Lav", 0), ("mid", 0)]
    assert labels["ai_mode"] == [("llm", 0), ("x", 0)]


def test_the_classic_preset_is_named_and_no_filter_under_two():
    classic = {k: v for k, v in sessions.classic_settings().model_dump(mode="json").items()}
    classic.pop("demand_seed")
    result = cross_class.compare([(A, keys(game_settings=classic)), (B, keys())], {})
    assert option(result, "game_settings", "classic")[0].ordinal == 0
    assert cross_class.compare([(A, keys())], {}).filters == []


def store(session_id: str, stored: dict[str, object]) -> None:
    execute(
        "INSERT INTO class_aggregates (class_session_id, written_at, students, game_students, "
        "games_finished, keys) VALUES (%s, now(), 12, 12, 3, %s::jsonb)",
        session_id,
        json.dumps(stored),
    )
    execute(
        "INSERT INTO class_aggregate_measures (class_session_id, measure, group_size, value, "
        "withheld) VALUES (%s, 'core.median', 12, 70, false)",
        session_id,
    )


async def statistics(query: str = "", who: str = LECTURER):
    return await call(who, "GET", f"/api/class-statistics{query}")


async def test_the_api_filters_and_labels_on_the_stored_keys(klass):
    first, second, third, waiting = [await new_session(klass) for _ in range(4)]
    store(first, keys())
    store(second, keys())
    store(third, keys(ai_mode="rule_based", item_weights={"q1": 10, "q2": 90}))
    body = (await statistics()).json()
    by_id = {s["class_session_id"]: s for s in body["sessions"]}
    assert [by_id[i]["compared"] for i in (first, second, third, waiting)] == [1, 1, 1, 0]
    assert by_id[third]["differs"] == ["ai_mode", "item_weights"]
    assert by_id[first]["differs"] == [] and by_id[waiting]["differs"] == []
    core = next(m for m in body["measures"] if m["key"] == "core.median")
    assert core["comparable"] is False
    assert all(m["comparable"] is None for m in body["measures"] if m["key"] != "core.median")
    [ai] = [f for f in body["filters"] if f["dimension"] == "ai_mode"]
    llm = next(o for o in ai["options"] if o["label"] == "llm")
    assert llm["count"] == 2 and ai["all_count"] == 3

    filtered = (await statistics(f"?ai_mode={llm['value']}")).json()
    assert [s["class_session_id"] for s in filtered["sessions"] if s["compared"]] == [first, second]
    core = next(m for m in filtered["measures"] if m["key"] == "core.median")
    assert [v["class_session_id"] for v in core["values"]] == [first, second]
    assert core["comparable"] is True
    # An unknown value is ignored; an overlong one is refused; another Lecturer sees nothing.
    assert (
        len([s for s in (await statistics("?ai_mode=zzz")).json()["sessions"] if s["compared"]])
        == 3
    )
    assert (await statistics("?model=" + "x" * 65)).status_code == 422
    assert (await statistics(who=OTHER)).json() == {"sessions": [], "measures": [], "filters": []}


async def test_an_aggregate_stores_every_comparability_key(klass):
    """Story 14.3's deferred item: model config, Effort level and prompt versions from the lock's
    snapshot over the row, Item weights and the Scoring guide's version."""
    session_id = await new_session(klass)
    row = await aggregates._keys(uuid.UUID(session_id))
    assert row["ai_mode"] == "rule_based" and row["model_config_id"] is None
    assert row["item_weights"] and set(row["scoring_guide"]) == {"id", "version"}
    snapshot = {
        "settings": row["game_settings"] | {"demand_seed": 7},
        "session_runtime": {
            "ai_mode": "llm",
            "model_config_id": "11111111-1111-1111-1111-111111111111",
            "effort_level": "high",
            "prompt_versions": {"order": 3},
        },
    }
    execute(
        "UPDATE class_sessions SET snapshot = %s::jsonb, locked_at = now() WHERE id = %s",
        json.dumps(snapshot),
        session_id,
    )
    row = await aggregates._keys(uuid.UUID(session_id))
    assert (row["ai_mode"], row["effort_level"], row["prompt_versions"]) == (
        "llm",
        "high",
        {"order": 3},
    )
    assert row["model_config_id"] == "11111111-1111-1111-1111-111111111111"
    assert "demand_seed" not in row["game_settings"]


async def test_model_names_name_a_stored_config_and_leave_out_what_is_gone():
    row = await config.add(config.parse(mock_config()))
    found = await sessions.model_names([str(row.id), "not-a-uuid", str(uuid.uuid4())])
    assert list(found) == [str(row.id)]
    assert found[str(row.id)].name == row.spec.name
    assert found[str(row.id)].levels == {
        level.name: level.label or level.name for level in row.spec.effort_levels
    }
