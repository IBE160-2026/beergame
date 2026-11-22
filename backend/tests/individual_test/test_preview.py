"""Preview the Adapted item templates with a sample Student (Story 11.9, FR-53, AD-7, AD-12,
UX-DR70).

The sample is a static facts set shipped in the repo, built by `analysis.facts` from the Takeover
golden Game's `seat_weeks` rows (`tests/golden/facts/takeover-seat-weeks.json`, which
`tests/games/test_facts.py` checks against the played Game). These tests rebuild it from the
fixture and compare, re-derive every number of the preview from the rows, and read the preview
through the api: the version it shows, its weights, who may read it, and that it touches no Game,
no stored facts set and no LLM. Rewrite the sample with `UPDATE_GOLDEN=1` after a deliberate
change of `analysis.facts` and review the diff."""

import json
import os
import re
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest

from app.analysis.adapted import ROLE_NAMES, AdaptedTemplates, picked
from app.analysis.facts import DecisionLog, facts
from app.analysis.patterns import PatternSet
from app.analysis.sentences import format_money, format_number
from app.modules.content import service as content
from app.modules.content.__main__ import SHIPPED
from app.modules.games import facts as game_facts
from app.modules.sessions import service as sessions
from app.modules.tests import preview
from tests.analysis.test_patterns import V1
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import EMAIL, call, shared
from tests.messaging.helpers import rows
from tests.question_set.test_question_set import _empty, body_of, planned, put, read
from tests.sessions.test_dates import START, new_session

__all__ = ["_empty", "clock", "klass", "shared"]

FIXTURE = Path(__file__).parents[1] / "golden" / "facts" / "takeover-seat-weeks.json"
TEMPLATES = json.loads((SHIPPED / "adapted_templates.json").read_text(encoding="utf-8"))
OWN, REPLAY = "tilpasset-eget-spill", "tilpasset-replay"
NUMBER = re.compile(r"\d+")


def path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/adapted-preview"


async def get(session_id: str, email: str = EMAIL["owner"]) -> dict:
    response = await call(email, "GET", path(session_id))
    assert response.status_code == 200, response.text
    return response.json()


def fixture_rows() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def rebuilt() -> dict:
    """The sample facts set built again from the fixture by `analysis.facts`."""
    found = fixture_rows()
    log = DecisionLog(
        roles=tuple(found["roles"]), rows=tuple(game_facts._logged(row) for row in found["rows"])
    )
    built = facts(log, preview.SAMPLE_ROLE, PatternSet.model_validate(V1))
    return {"patterns_version": 1, "facts": built.model_dump(mode="json")}


def test_the_sample_set_is_the_fixture_rebuilt_by_analysis_facts():
    found = rebuilt()
    if os.environ.get("UPDATE_GOLDEN") == "1":
        text = json.dumps(found, indent=2, ensure_ascii=False) + "\n"
        preview.SAMPLE.write_text(text, "utf-8", newline="\n")
        preview.sample.cache_clear()
    assert json.loads(preview.SAMPLE.read_text(encoding="utf-8")) == found
    version, sample = preview.sample()
    assert (version, sample.model_dump(mode="json")) == (found["patterns_version"], found["facts"])
    # A Student placed the Orders: enough own Orders for moments, so every template fills.
    assert sample.seat.student_orders >= 10 and len(sample.seat.moments) == 3
    assert sample.seat.simulated is None
    # The emptied `history` changes nothing: the played Game's stored golden set is the same but
    # for its «Simulert, samme kunder» rows, which the sample leaves out.
    golden = json.loads((FIXTURE.parent / "takeover.json").read_text(encoding="utf-8"))
    stored = golden[preview.SAMPLE_ROLE]
    stored["facts"]["seat"]["simulated"] = None
    assert found == stored


def expected_values(fact_id: str) -> dict[str, str]:
    """The values a template's fact gives, derived straight from the fixture's rows."""
    rows_ = [row for row in fixture_rows()["rows"] if row["role"] == preview.SAMPLE_ROLE]
    role = ROLE_NAMES[preview.SAMPLE_ROLE]
    if fact_id.startswith("outcome:"):

        def total(kind: str | None) -> Decimal:
            if kind is None:
                return sum((Decimal(r["state_seen"]["week_cost"]) for r in rows_), Decimal(0))
            return sum(
                (
                    Decimal(line["amount"])
                    for r in rows_
                    for line in r["state_seen"]["cost_lines"]
                    if line["kind"] == kind
                ),
                Decimal(0),
            )

        return {
            "role": role,
            "weeks": format_number(max(r["week"] for r in rows_)),
            "total_cost": format_money(total(None)),
            "holding_cost": format_money(total("holding")),
            "backorder_cost": format_money(total("backorder")),
        }
    _, sample = preview.sample()
    week = next(m.week for m in sample.seat.moments if m.id == fact_id)
    row = next(r for r in rows_ if r["week"] == week)
    assert row["decided_by"] == "student"
    seen = row["state_seen"]
    return {
        "role": role,
        "week": format_number(week),
        "order": format_number(row["order"]),
        **{
            key: format_number(seen[key])
            for key in ("incoming_order", "inventory", "backlog", "supply_line")
        },
    }


async def test_every_number_in_the_preview_equals_the_fixtures_seat_week_rows(klass):
    session_id = await new_session(klass)
    shown = await get(session_id)
    templates = AdaptedTemplates.model_validate(TEMPLATES)
    _, sample = preview.sample()
    assert [item["id"] for item in shown["items"]] == [OWN, REPLAY]
    for item, template in zip(shown["items"], templates.templates, strict=True):
        found = picked(template, sample, {})
        assert found is not None
        fact_id, values = found
        assert values == expected_values(fact_id)
        assert item["text"] == template.text.format(**values)
        allowed = {n for value in values.values() for n in NUMBER.findall(value)}
        assert set(NUMBER.findall(item["text"])) <= allowed


async def test_an_owner_sees_the_latest_draft_templates_with_the_adapted_total(klass):
    session_id = await new_session(klass)
    latest = await content.latest_version("adapted_templates")
    shown = await get(session_id)
    assert (shown["version"], shown["draft"], shown["pinned"], shown["adapted_weight"]) == (
        latest,
        True,
        False,
        30,
    )
    assert [(i["source"], i["fact"], i["weight"]) for i in shown["items"]] == [
        ("game", "moment", 15),
        ("replay", "outcome", 15),
    ]
    assert all(item["text"] and item["text"].startswith("Utkast:") for item in shown["items"])
    # A saved Adapted total is the one shown, split by the templates' shares.
    block = await read(session_id)
    weights = body_of(block)["weights"] | {"langsvar-forsinkelse": 0}
    saved = await put(session_id, body_of(block, weights=weights, adapted_weight=40))
    assert saved.status_code == 200, saved.text
    shown = await get(session_id)
    assert shown["adapted_weight"] == 40
    assert [item["weight"] for item in shown["items"]] == [20, 20]


async def test_once_locked_the_preview_reads_the_pins(klass):
    session_id = await planned(klass)
    block = await read(session_id)
    weights = body_of(block)["weights"] | {"langsvar-forsinkelse": 15}
    assert (
        await put(session_id, body_of(block, weights=weights, adapted_weight=25))
    ).status_code == 200
    assert await sessions.lock(uuid.UUID(session_id), now=START) is True
    [(pin,)] = rows(
        "SELECT snapshot->'session_runtime'->'pins'->'adapted_templates'->>'version' "
        "FROM class_sessions WHERE id = %s",
        session_id,
    )
    shown = await get(session_id)
    assert (shown["version"], shown["pinned"], shown["adapted_weight"]) == (int(pin), True, 25)
    assert [item["weight"] for item in shown["items"]] == [13, 12]


@pytest.mark.parametrize("role", ["assistant", "lecturer_assistant"])
async def test_an_assistant_lecturer_reads_the_preview(shared, role):
    session_id = await new_session(shared)
    assert await get(session_id, EMAIL[role]) == await get(session_id)


@pytest.mark.parametrize("who", ["outsider", "student"])
async def test_a_user_outside_the_class_staff_is_refused(shared, who):
    session_id = await new_session(shared)
    response = await call(EMAIL[who], "GET", path(session_id))
    assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden")


@pytest.mark.parametrize("session_id", ["0190a1b2-0000-7000-8000-00000000beef", "not-an-id"])
async def test_an_unknown_session_is_refused_like_one_not_reachable(klass, session_id):
    response = await call(EMAIL["owner"], "GET", path(session_id))
    assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden")


async def test_the_preview_creates_no_game_reads_no_stored_facts_and_calls_no_llm(klass):
    session_id = await new_session(klass)
    counts = (
        "SELECT (SELECT count(*) FROM games), (SELECT count(*) FROM fact_sets), "
        "(SELECT count(*) FROM llm_call)"
    )
    before = rows(counts)
    refused = mock.AsyncMock(side_effect=AssertionError("no stored facts set"))
    with (
        mock.patch.object(game_facts, "get_or_create", refused),
        mock.patch.object(game_facts, "compute", refused),
    ):
        await get(session_id)
    assert rows(counts) == before
    refused.assert_not_called()


def test_a_template_whose_fact_the_sample_lacks_has_no_text():
    templates = AdaptedTemplates.model_validate(
        {
            "status": "draft",
            "templates": [
                {**TEMPLATES["templates"][0], "wordings": []},
                {
                    "id": "monster",
                    "source": "game",
                    "fact": "pattern",
                    "pick": 1,
                    "share": 50,
                    "text": "Utkast: I uke {week} så vi {pattern}.",
                },
            ],
        }
    )
    _, sample = preview.sample()
    # No pattern named: the pattern template finds no fact to fill, the other still fills.
    items = preview.preview_items(templates, sample, {}, 31)
    assert (items[0].weight, items[1].weight) == (16, 15)
    assert items[0].text is not None and items[1].text is None
