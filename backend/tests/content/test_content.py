"""`modules/content` (Story 6.3, AD-23): immutable, versioned records; the Starting task is the
first kind, version 1 holds the placeholder items, an edit is a new version, and the lock pins
the latest through its registered provider."""

import json

import pytest
from pydantic import ValidationError

from app.modules.content import __main__ as cli
from app.modules.content import service as content
from app.modules.sessions import service as sessions
from tests.classes.test_invitation_counts import execute


@pytest.fixture(autouse=True)
def only_version_1(test_database):
    execute("DELETE FROM content_records WHERE version > 1")
    yield
    execute("DELETE FROM content_records WHERE version > 1")


async def test_version_1_holds_the_placeholder_items_with_the_position_sum():
    version, task = await content.starting_task(None)
    assert version == 1
    position = task.items[-1]
    assert position.prompt == "Regn posisjonen for én Uke."
    assert [(t.row, t.sign) for t in position.terms] == [
        ("inventory", 1),
        ("backlog", -1),
        ("on-order", 1),
    ]


async def test_an_edit_is_a_new_version_and_the_old_one_stays():
    old = await content.get("starting_task", 1)
    body = old.model_dump(mode="json")
    body["items"][0]["prompt"] = "Ny tekst."
    assert await content.publish("starting_task", body) == 2
    assert await content.latest_version("starting_task") == 2
    assert (await content.get("starting_task", 1)) == old
    assert (await content.get("starting_task", 2)).items[0].prompt == "Ny tekst."
    with pytest.raises(content.ContentNotFound):
        await content.get("starting_task", 9)


async def test_a_body_that_does_not_validate_is_not_stored():
    body = (await content.get("starting_task", 1)).model_dump(mode="json")
    bad_term = json.loads(json.dumps(body))
    bad_term["items"][0]["terms"][0]["row"] = "nowhere"
    twice = json.loads(json.dumps(body))
    twice["items"][1]["id"] = twice["items"][0]["id"]
    named = json.loads(json.dumps(body))
    named["items"][0]["prompt"] = "Som i Beer Game"
    shouted = json.loads(json.dumps(body))
    shouted["items"][0]["hint"] = "Regn!"
    too_big = json.loads(json.dumps(body))
    too_big["items"][0]["rows"][0]["value"] = 80_001
    for bad in (bad_term, twice, named, shouted, too_big, {"items": []}):
        with pytest.raises(ValidationError):
            await content.publish("starting_task", bad)
    assert await content.latest_version("starting_task") == 1


async def test_the_lock_pins_the_latest_starting_task_version():
    """`sessions` registered the provider; `pinned_version` reads what the lock stored."""
    assert sessions._pin_providers["starting_task"] is content.starting_task_pin
    body = (await content.get("starting_task", 1)).model_dump(mode="json")
    await content.publish("starting_task", body)
    snapshot = await sessions.build_snapshot(_session_row())
    pins = snapshot["session_runtime"]["pins"]
    # Story 9.1 pins the Detected pattern definitions the same way, Story 9.4 the sentence
    # templates, Story 9.6 the reflection questions, Story 9.7 the moment templates, Story 9.9
    # the Debrief quiz.
    assert pins == {
        "starting_task": {"version": 2},
        "detected_patterns": {"version": 1},
        "sentence_templates": {"version": 1},
        "reflection_questions": {"version": 1},
        "moment_templates": {"version": 1},
        "debrief_quiz": {"version": 1},
    }
    assert sessions._pin_providers["reflection_questions"] is content.reflection_questions_pin
    assert sessions._pin_providers["moment_templates"] is content.moment_templates_pin
    assert sessions._pin_providers["debrief_quiz"] is content.debrief_quiz_pin
    assert content.pinned_version(pins) == 2
    assert content.pinned_version(pins, "detected_patterns") == 1
    assert content.pinned_version(pins, "sentence_templates") == 1
    assert sessions._pin_providers["detected_patterns"] is content.detected_patterns_pin
    assert sessions._pin_providers["sentence_templates"] is content.sentence_templates_pin
    # A session locked before the pin reads the latest version.
    assert (await content.sentence_templates(None))[0] == 1
    assert content.pinned_version({}) is None and content.pinned_version(None) is None
    for odd in (True, 0, "2", 1.0):
        assert content.pinned_version({"starting_task": {"version": odd}}) is None


async def test_version_1_holds_the_reflection_questions_in_order():
    """Story 9.6 (FR-45): feelings, then evidence, then structure; why, not who."""
    version, body = await content.reflection_questions(None)
    assert version == 1
    assert [q.kind for q in body.questions] == ["feelings", "evidence", "structure"]
    assert body.questions[-1].hint == "Struktur gir atferd, derfor spør vi hvorfor og ikke hvem."
    assert all("!" not in q.prompt and q.prompt.endswith("?") for q in body.questions)


async def test_reflection_questions_out_of_order_or_shouting_are_not_stored():
    body = (await content.get("reflection_questions", 1)).model_dump(mode="json")
    swapped = json.loads(json.dumps(body))
    swapped["questions"].reverse()
    missing = json.loads(json.dumps(body))
    missing["questions"] = missing["questions"][:2]
    twice = json.loads(json.dumps(body))
    twice["questions"][1]["id"] = twice["questions"][0]["id"]
    shouted = json.loads(json.dumps(body))
    shouted["questions"][0]["prompt"] = "Hvorfor!"
    odd = json.loads(json.dumps(body))
    odd["questions"][0]["kind"] = "blame"
    for bad in (swapped, missing, twice, shouted, odd, {"questions": []}):
        with pytest.raises(ValidationError):
            await content.publish("reflection_questions", bad)
    # Two of a kind in a row is fine.
    more = json.loads(json.dumps(body))
    more["questions"].insert(1, {**more["questions"][0], "id": "feelings-2"})
    assert await content.publish("reflection_questions", more) == 2


async def test_version_1_holds_the_moment_templates_and_a_cause_is_not_stored():
    """Story 9.7 (FR-44, AD-7): every moment template, read back as stored; one stating a cause
    is refused like any invalid record."""
    version, body = await content.moment_templates(None)
    assert version == 1
    assert body.text_of("moments-heading").startswith("Ditt øyeblikk: Uke {week}.")
    bad = json.loads(json.dumps(body.model_dump(mode="json")))
    bad["templates"][0]["text"] = "Uke {week}: du bestilte {order} fordi det var mye på vei."
    with pytest.raises(ValidationError):
        await content.publish("moment_templates", bad)


async def test_version_1_holds_the_placeholder_quiz_and_a_bad_quiz_is_not_stored():
    """Story 9.9 (FR-46, AD-23): the Debrief quiz, read back as stored and marked placeholder; one
    whose answer is not one of its choices is refused like any invalid record."""
    version, body = await content.debrief_quiz(None)
    assert (version, body.placeholder, len(body.questions)) == (1, True, 3)
    bad = json.loads(json.dumps(body.model_dump(mode="json")))
    bad["questions"][0]["answer"] = "ingen"
    with pytest.raises(ValidationError):
        await content.publish("debrief_quiz", bad)
    assert await content.latest_version("debrief_quiz") == 1


def _session_row() -> dict:
    from app.engine import GameSettings

    return {
        "game_settings": GameSettings().model_dump(mode="json"),
        "ai_mode": "rule_based",
        "model_config_id": None,
        "effort_level": None,
        "inactivity_limit_hours": 24,
    }


def test_the_cli_needs_a_kind_and_a_file(capsys):
    assert cli.main([]) == 2
    assert "usage" in capsys.readouterr().err
