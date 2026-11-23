"""Answer drawn Interactive items in a graph (Story 11.14, FR-80, AD-10, UX-DR38).

The content load takes an item of type `drawn` (a table Interactive item with a value axis); the
test the page reads carries its value table with the axis, never a rule; a save takes the table's
shape; and `tests.scoring.score_answer` scores it with `score_interactive` over the values alone,
so a graph's answer and a typed one with the same values score the same. The api's clock is
fixed; every version a test publishes is deleted again."""

import json
import uuid

import pytest
from pydantic import ValidationError

from app.analysis import scoring as rules
from app.modules.content import __main__ as cli
from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet, QuestionSetItem
from app.modules.tests import commands, scoring
from app.modules.tests import service as tests_service
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.individual_test.test_answer import opened, put, stored
from tests.individual_test.test_interactive import item_of
from tests.individual_test.test_open import code
from tests.question_set.test_question_set import SET, UNSHIPPED, V
from tests.sessions.test_lock import _empty

__all__ = ["_empty", "clock", "klass"]

DRAWN = "tabell-annen-bransje"
"""The shipped bakery table item, made a drawn item in these tests' sets."""
AXIS = {"min": 0, "max": 40}


def drawn_set(**axis_or_none) -> dict:
    """The shipped set with the bakery table item as a drawn item (`axis` given or left out)."""
    body = json.loads(json.dumps(SET))
    for item in body["items"]:
        if item["id"] == DRAWN:
            item["type"] = "drawn"
            if axis_or_none:
                item["interactive"] = {**item["interactive"], **axis_or_none}
    return body


@pytest.fixture
def published():
    execute(UNSHIPPED)
    yield
    execute(UNSHIPPED)


async def load(tmp_path, body: dict) -> tuple[list[str], list[str]]:
    (tmp_path / "question_set.json").write_text(json.dumps(body), encoding="utf-8")
    return await cli.load(tmp_path)


async def test_the_load_takes_a_set_with_a_drawn_item(tmp_path, published):
    done, refused = await load(tmp_path, drawn_set(axis=AXIS))
    assert (done, refused) == ([f"question_set v{V + 1}"], [])
    _, found = await content.question_set(None)
    item = next(i for i in found.items if i.id == DRAWN)
    assert (item.type, item.interactive.axis.max, item.needs_interactive()) == ("drawn", 40, True)
    # Its graph and table are one answer: the rule reads one value per row, like a table.
    assert item.interactive.rule("drawn").labels == item.interactive.rows


async def test_a_drawn_item_without_its_table_or_axis_is_refused(tmp_path, published):
    no_table = drawn_set()
    next(i for i in no_table["items"] if i["id"] == DRAWN)["interactive"] = None
    assert (await load(tmp_path, no_table))[1][0].split(": ")[1] == "interactive_missing"
    # No axis on a drawn item, an axis on a table item, an axis below zero with no negatives,
    # an axis that runs the wrong way.
    on_table = json.loads(json.dumps(SET))
    table = next(i for i in on_table["items"] if i["type"] == "table")
    table["interactive"] = {**table["interactive"], "axis": AXIS}
    for body in (
        drawn_set(),
        on_table,
        drawn_set(axis={"min": -5, "max": 40}),
        drawn_set(axis={"min": 40, "max": 40}),
        drawn_set(axis={"min": 0, "max": 1_000_001}),
    ):
        assert (await load(tmp_path, body))[1][0].split(": ")[1] == "invalid_record"
    assert await content.latest_version("question_set") == V


def test_the_stored_table_items_keep_their_bodies_without_an_axis():
    """`axis` is left out of a stored body when absent, so the shipped version 2 is still found
    unchanged by the load (`stored_version_of` compares stored bodies)."""
    assert QuestionSet.model_validate(SET).model_dump(mode="json") == SET


async def test_a_drawn_item_is_served_with_its_table_and_axis_and_saved_as_a_table(
    klass, tmp_path, published
):
    assert (await load(tmp_path, drawn_set(axis=AXIS)))[1] == []
    session_id, seated, test = await opened(klass)
    item = item_of(test, DRAWN)
    assert item["type"] == "drawn" and item["column"] is None
    assert item["table"]["axis"] == AXIS
    assert item["table"]["rows"] == ["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5"]
    assert "criteria" not in str(item) and "K1" not in str(item)
    # A table item's table has no axis.
    assert all(i["table"]["axis"] is None for i in test["items"] if i["type"] == "table")
    parts = tests_service.parts_with_content
    sid = uuid.UUID(session_id)
    assert (await parts(seated[0], sid))["interactive"] is False
    assert (await put(session_id, DRAWN, [None] * 5, 1)).status_code == 200
    assert (await parts(seated[0], sid))["interactive"] is False  # every point empty
    assert (await put(session_id, DRAWN, [8, None, 9, None, None], 2)).status_code == 200
    # A drawn answer counts for the Interactive part (Story 11.11's parts, FR-17).
    assert (await parts(seated[0], sid))["interactive"] is True
    # Out of the axis but whole: the table is the answer, the graph widens.
    assert (await put(session_id, DRAWN, [8, 4, 9, 60, 11], 3)).status_code == 200
    for value in ([8, 4, 9, 16], 12, [1.5, 2, 3, 4, 5], [-3, 2, 3, 4, 5], {"Uke 1": 1}):
        assert code(await put(session_id, DRAWN, value, 4)) == (422, "invalid_answer"), value
    assert stored(session_id) == [(DRAWN, [8, 4, 9, 60, 11], 3)]


async def test_a_drawn_answer_is_scored_from_its_values_only(tmp_path, published):
    """However the values came (a point dragged, tapped or moved by keys, or a typed cell), the
    stored answer is the same list, and the same list scores the same as the table item's."""
    assert (await load(tmp_path, drawn_set(axis=AXIS)))[1] == []
    _, found = await content.question_set(None)
    _, task = await content.starting_task(None)
    drawn = next(i for i in found.items if i.id == DRAWN)
    table = QuestionSetItem.model_validate(
        {
            **drawn.model_dump(mode="json"),
            "type": "table",
            "interactive": {**drawn.interactive.model_dump(mode="json"), "axis": None},
        }
    )
    for values in ([8, 4, 9, 16, 11], [8, 5, 10, 17, 11], [8, None, None, None, None], None):
        assert scoring.score_answer(drawn, values, task) == scoring.score_answer(
            table, values, task
        ), values
    full = scoring.score_answer(drawn, [8, 4, 9, 16, 11], task)
    assert full == scoring.ItemScore(
        answered=True,
        credit=1.0,
        criteria=rules.score_interactive(
            [8, 4, 9, 16, 11], drawn.interactive.rule("drawn")
        ).criteria,
    )
    assert commands._valid("drawn", drawn, [8, 4, 9, 16, 11])
    assert not commands._valid("drawn", drawn, 16)


def test_an_axis_needs_a_drawn_item_and_a_drawn_item_an_axis():
    base = next(i for i in SET["items"] if i["id"] == DRAWN)
    with pytest.raises(ValidationError):
        QuestionSetItem.model_validate({**base, "type": "drawn"})
    with pytest.raises(ValidationError):
        QuestionSetItem.model_validate(
            {**base, "interactive": {**base["interactive"], "axis": AXIS}}
        )
    negative = {**base["interactive"], "negative": True, "axis": {"min": -20, "max": 40}}
    item = QuestionSetItem.model_validate({**base, "type": "drawn", "interactive": negative})
    assert item.interactive.axis.min == -20
