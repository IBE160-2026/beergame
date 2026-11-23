"""Answer table and number Interactive items (Story 11.5, FR-80, FR-52, FR-85, AD-1, AD-10).

The test the page reads carries each table item's value table and each number item's column (a
Starting task item's from the Class session's pinned Starting task), never a rule, an expected
value or a score; `PUT …/answers/{item_id}` stores whole numbers in the item's shape through
`tests.commands.save_answer` (Story 11.4's path); `tests.scoring.score_answer` scores a stored
answer with the pure rules of `analysis.scoring` only. The api's clock is fixed."""

from app.analysis import scoring as rules
from app.modules.content import service as content
from app.modules.content.schemas import QuestionSetItem
from app.modules.tests import commands, scoring
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.individual_test.test_answer import Z, opened, put, stored
from tests.individual_test.test_open import code, path
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]


def item_of(test: dict, item_id: str) -> dict:
    return next(item for item in test["items"] if item["id"] == item_id)


async def test_table_and_number_items_carry_their_table_and_never_a_rule(klass):
    _, _, test = await opened(klass)
    table = item_of(test, "tabell-annen-bransje")
    assert table["column"] is None and table["options"] == []
    assert table["table"] == {
        "prompt": "Utkast: Et bakeri har 10 enheter på lager før uke 1. Fyll inn lageret ved "
        "slutten av hver uke.",
        "hint": None,
        "caption": "Utkast: Bakeriets lager per uke, i enheter",
        "rows": ["Uke 1", "Uke 2", "Uke 3", "Uke 4", "Uke 5"],
        "columns": [
            {"label": "Inn", "values": [20, 20, 25, 25, 20]},
            {"label": "Ut", "values": [22, 24, 20, 18, 25]},
        ],
        "asked_label": "Lager",
        "negative": False,
        "axis": None,  # a drawn item's only (Story 11.14)
    }
    number = item_of(test, "tall-annen-bransje")
    assert number["table"] is None
    assert number["column"]["rows"] == [
        {"label": "Uke 1", "value": 3},
        {"label": "Uke 2", "value": 5},
        {"label": "Uke 3", "value": 2},
        {"label": "Uke 4", "value": 6},
    ]
    assert (number["column"]["asked_label"], number["column"]["starting_task"]) == (
        "Legg til",
        False,
    )
    # A Starting task item: its text from the pinned Starting task, never copied (FR-52, FR-85).
    _, task = await content.starting_task(None)
    position = next(t for t in task.items if t.id == "position")
    column = item_of(test, "startoppgave-posisjon")["column"]
    assert column == {
        "prompt": position.prompt,
        "hint": position.hint,
        "caption": position.column,
        "rows": [{"label": r.label, "value": r.value} for r in position.rows],
        "asked_label": position.asked_label,
        "negative": True,
        "starting_task": True,
    }
    for item in test["items"]:
        if item["type"] in ("choice", "long"):
            assert (item["table"], item["column"]) == (None, None)
    # Nothing that would give the answer away.
    text = str(test)
    assert "criteria" not in text and "weight" not in text and "K1" not in text


async def test_a_table_and_a_number_answer_are_saved_with_the_revision(klass):
    session_id, _, _ = await opened(klass)
    partly = [8, None, 9, None, None]
    saved = await put(session_id, "tabell-annen-bransje", partly, 1)
    assert saved.json() == {
        "item_id": "tabell-annen-bransje",
        "value": partly,
        "revision": 1,
        "saved_at": Z,
    }
    assert (await put(session_id, "tabell-annen-bransje", [8, 4, 9, 16, 11], 2)).status_code == 200
    assert (await put(session_id, "tall-annen-bransje", 16, 1)).status_code == 200
    assert (await put(session_id, "tall-annen-bransje", None, 2)).json()["value"] is None
    # A Starting task item takes a negative whole number (a position can be below zero).
    assert (await put(session_id, "startoppgave-posisjon", -13, 1)).status_code == 200
    assert stored(session_id) == [
        ("startoppgave-posisjon", -13, 1),
        ("tabell-annen-bransje", [8, 4, 9, 16, 11], 2),
        ("tall-annen-bransje", None, 2),
    ]


async def test_a_value_that_is_not_whole_numbers_in_the_items_shape_stores_nothing(klass):
    session_id, _, _ = await opened(klass)
    table = "tabell-annen-bransje"  # five Uker, no negative values
    for value in (
        [1, 2, 3, 4],  # one short
        [1, 2, 3, 4, 5, 6],
        [1.5, 2, 3, 4, 5],
        [12.0, 2, 3, 4, 5],
        [True, 2, 3, 4, 5],
        ["12", 2, 3, 4, 5],
        [-3, 2, 3, 4, 5],  # negative where the item allows none
        [1_000_001, 2, 3, 4, 5],
        12,
        None,
        {"Uke 1": 12},
    ):
        assert code(await put(session_id, table, value, 1)) == (422, "invalid_answer"), value
    for value in ([16], "16", 1.5, -3, True, 1_000_001):
        assert code(await put(session_id, "tall-annen-bransje", value, 1)) == (
            422,
            "invalid_answer",
        ), value
    for value in (1.5, "-13", -1_000_001, [3]):
        assert code(await put(session_id, "startoppgave-posisjon", value, 1)) == (
            422,
            "invalid_answer",
        )
    assert stored(session_id) == []


async def test_a_starting_task_item_shows_the_starting_task_its_session_pinned(klass):
    """A Starting task published after the lock changes nothing in a locked Class session's
    test: its columns come from the pinned version (FR-52, FR-85)."""
    session_id, _, test = await opened(klass)
    pinned = item_of(test, "startoppgave-posisjon")["column"]
    version, task = await content.starting_task(None)
    changed = task.model_dump(mode="json")
    changed["items"] = [
        {
            **item,
            "prompt": "Ny tekst etter låsen.",
            "rows": [{**r, "value": 1} for r in item["rows"]],
        }
        for item in changed["items"]
    ]
    newer = await content.publish("starting_task", changed)
    try:
        assert newer == version + 1
        again = (await call(email(0), "GET", path(session_id))).json()
        assert item_of(again, "startoppgave-posisjon")["column"] == pinned
        assert pinned["prompt"] != "Ny tekst etter låsen."
        reopened = (await call(email(0), "POST", path(session_id))).json()
        assert item_of(reopened, "startoppgave-posisjon")["column"] == pinned
    finally:
        execute("DELETE FROM content_records WHERE kind = 'starting_task' AND version = %s", newer)


def test_an_item_that_takes_negative_values_takes_them_whole():
    """`negative: true` on an Interactive item lets a table and a number answer below zero."""
    base = {"weight": 10, "scoring_rule": "units-balance", "tags": []}
    spec = {
        "prompt": "Utkast: netto per uke, i enheter.",
        "caption": "Utkast: netto",
        "rows": ["Uke 1", "Uke 2"],
        "given": [{"key": "inn", "label": "Inn", "values": [3, -2]}],
        "asked": "Netto",
        "negative": True,
        "criteria": [
            {"code": "K1", "weight": 100, "check": {"kind": "cell", "row": 0, "value": -3}}
        ],
    }
    table = QuestionSetItem.model_validate(
        {**base, "id": "t", "type": "table", "title": "t", "interactive": spec}
    )
    number = QuestionSetItem.model_validate(
        {**base, "id": "n", "type": "number", "title": "n", "interactive": spec}
    )
    assert commands._valid("table", table, [-3, None])
    assert commands._valid("number", number, -3)
    assert not commands._valid("table", table, [-3.5, None])
    assert not commands._valid("number", number, -1_000_001)
    plain = number.model_copy(
        update={"interactive": number.interactive.model_copy(update={"negative": False})}
    )
    assert not commands._valid("number", plain, -3)


async def test_an_attempt_on_version_1_refuses_a_table_answer_with_no_table(klass):
    """Version 1 of the question set has no tables: its table items show their title only and a
    save is refused (an attempt opened before Story 11.5)."""
    session_id, _, _ = await opened(klass)
    execute("UPDATE test_attempts SET question_set_version = 1")
    test = (await call(email(0), "GET", path(session_id))).json()
    assert item_of(test, "tabell-annen-bransje")["table"] is None
    assert item_of(test, "tall-annen-bransje")["column"] is None
    assert item_of(test, "startoppgave-posisjon")["column"]["starting_task"] is True
    answer = [8, 4, 9, 16, 11]
    assert code(await put(session_id, "tabell-annen-bransje", answer, 1)) == (
        422,
        "invalid_answer",
    )
    assert stored(session_id) == []


async def test_a_stored_answer_is_scored_by_the_pure_rules_only():
    """`score_answer` (Epic 12's caller): a choice by its key, a Starting task item by the
    Starting task's sum (FR-85), a table or number item by `score_interactive` alone (FR-80)."""
    _, question_set = await content.question_set(None)
    _, task = await content.starting_task(None)
    by_id = {item.id: item for item in (*question_set.items, *question_set.replacements)}

    choice = by_id["flervalg-forklaring"]
    assert scoring.score_answer(choice, choice.answer_key, task).credit == 1.0
    assert scoring.score_answer(choice, None, task).answered is False

    position = by_id["startoppgave-posisjon"]
    item = next(t for t in task.items if t.id == "position")
    rows = {row.key: row.value for row in item.rows}
    right = rules.score_sum(((t.sign, rows[t.row]) for t in item.terms), 0).expected
    assert scoring.score_answer(position, right, task).credit == 1.0
    assert scoring.score_answer(position, right + 1, task).credit == 0.0
    assert scoring.score_answer(position, None, task).answered is False

    bakery = by_id["tabell-annen-bransje"]
    full = scoring.score_answer(bakery, [8, 4, 9, 16, 11], task)
    assert full.credit == 1.0 and [c.code for c in full.criteria] == ["K1", "K2"]
    assert full == scoring.ItemScore(
        answered=True,
        credit=1.0,
        criteria=rules.score_interactive(
            [8, 4, 9, 16, 11], bakery.interactive.rule("table")
        ).criteria,
    )
    slip = scoring.score_answer(bakery, [8, 5, 10, 17, 11], task)
    assert (slip.credit, [c.met for c in slip.criteria]) == (0.4, [False, True])
    partly = scoring.score_answer(bakery, [8, None, None, None, None], task)
    assert (partly.answered, partly.credit) == (True, 0.0)
    empty = scoring.score_answer(bakery, None, task)
    assert (empty.answered, empty.credit) == (False, 0.0)

    shortfall = by_id["tall-annen-bransje"]
    assert scoring.score_answer(shortfall, 16, task).credit == 1.0
    assert scoring.score_answer(shortfall, 15, task).credit == 0.0
    assert scoring.score_answer(by_id["langsvar-forsinkelse"], "tekst", task) is None
