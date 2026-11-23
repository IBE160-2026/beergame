"""Read Adapted items in natural wording (Story 11.8, FR-53, FR-34, AD-6, AD-7, AD-9, AD-17).

The sweep defers one `tests.prepare_adapted` job on `llm-batch` per Student through the Replay
with no attempt and no prepared set; the job builds the Student's Adapted items as opening would,
asks the mock provider (`adapted_item_wording`) to choose one approved wording for each, validates
the choice against the facts set the item cites and stores one prepared set; opening freezes it.
A rejected choice or a provider failure keeps the code text; a job after the open, or an open
during the job, changes nothing the Student has. The Student's two Games are stood in with
hand-built facts sets (`test_adapted.stand_in`); the api's clock is fixed."""

import uuid

import pytest
from structlog.testing import capture_logs

from app.ai import mock, seed
from app.analysis.adapted import render_wording
from app.modules.content import service as content
from app.modules.ops import sweep
from app.modules.tests import jobs as tests_jobs
from app.modules.tests import prepare
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import user_id
from tests.individual_test.test_adapted import OWN, REPLAY, locked_with, stand_in
from tests.individual_test.test_open import REPLACEMENTS, attempts, path
from tests.messaging.helpers import rows
from tests.sessions.test_dates import START
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

LATER = START + 2 * MINUTE
"""A sweep after the lock: the Students' `replay` steps are recorded at the api's fixed clock."""


def prepare_jobs() -> list[tuple]:
    return rows(
        "SELECT queue_name, queueing_lock, args FROM procrastinate_jobs WHERE task_name = %s",
        prepare.PREPARE_TASK,
    )


def prepared(session_id: str) -> list[tuple]:
    return rows(
        "SELECT user_id, question_set_version, adapted_weight, items FROM test_prepared_items "
        "WHERE class_session_id = %s",
        session_id,
    )


def wording_calls() -> list[tuple]:
    return rows(
        "SELECT id::text, scope_kind, scope_id::text FROM llm_call WHERE purpose = %s",
        prepare.PURPOSE,
    )


async def run_job(session_id: str, who: int = 0) -> None:
    await tests_jobs.prepare_adapted.func(str(user_id(email(who))), session_id)


async def ai_locked(klass: str, monkeypatch, own: range = range(1, 13)):
    """A locked Class session of one Student through the Replay, the Debrief AI text on with the
    default mock config (which names `adapted_item_wording`)."""
    await seed.ensure_zero_config()
    sets = stand_in(monkeypatch, own=own)
    session_id, _ = await locked_with(klass, 30, ai_mode="llm")
    [(pin,)] = rows(
        "SELECT snapshot->'session_runtime'->'pins'->'debrief_ai_text' FROM class_sessions "
        "WHERE id = %s",
        session_id,
    )
    assert pin["enabled"] is True and pin["model_config_id"]
    return session_id, sets


async def test_the_sweep_defers_one_job_whose_worded_set_the_open_freezes(klass, monkeypatch):
    session_id, sets = await ai_locked(klass, monkeypatch)
    student = str(user_id(email(0)))

    # The sweep defers one job, ids only, keyed by Student and Class session; run twice, it
    # waits once (the queueing lock).
    assert (await sweep.run(LATER))["tests.prepare_adapted"] == 1
    await sweep.run(LATER + MINUTE)
    assert prepare_jobs() == [
        (
            "llm-batch",
            prepare.prepare_key(student, session_id),
            {"user_id": student, "class_session_id": session_id},
        )
    ]

    # The job: the mock chooses each template's first wording, accepted and rendered by code.
    with capture_logs() as logs:
        await run_job(session_id)
    [(owner, version, weight, items)] = prepared(session_id)
    assert (str(owner), weight) == (student, 30) and version >= 1
    adapted_items = [item for item in items if item["type"] == "adapted"]
    assert [item["id"] for item in adapted_items] == [OWN, REPLAY]
    _, templates = await content.adapted_templates(None)
    by_id = {template.id: template for template in templates.templates}
    calls = {call_id: (kind, scope) for call_id, kind, scope in wording_calls()}
    assert len(calls) == 2
    for item in adapted_items:
        template = by_id[item["id"]]
        facts = sets[next(g for g, s in sets.items() if s.id == item["fact_set_id"])].facts
        expected = render_wording(template, template.wordings[0].id, facts, {})
        assert expected is not None and tuple(item["fact_ids"]) == expected.fact_ids
        assert item["text"]["text"] == expected.text and item["text"]["ai_generated"] is True
        assert calls[item["text"]["llm_call_id"]] == ("class_session", session_id)
        assert item["text"]["text"] not in str(logs)
    # Prepared: the sweep looks no more, and a second delivery calls nothing.
    assert (await sweep.run(LATER + 2 * MINUTE))["tests.prepare_adapted"] == 0
    assert await prepare.prepare(student, session_id) is False
    assert len(wording_calls()) == 2

    # The open freezes the prepared items, and the page marks them as AI text.
    opened = await call(email(0), "POST", path(session_id))
    assert opened.status_code == 201
    [frozen] = [row[4] for row in attempts(session_id)]
    assert [item for item in frozen if item["type"] == "adapted"] == adapted_items
    assert sum(item["weight"] for item in frozen) == 100
    shown = next(item for item in opened.json()["items"] if item["id"] == OWN)
    assert shown["wording"] == adapted_items[0]["text"]
    assert shown["title"] == adapted_items[0]["text"]["text"]

    # The job again after the open, or a late answer: the attempt never changes.
    execute("DELETE FROM test_prepared_items WHERE class_session_id = %s", session_id)
    assert await prepare.prepare(student, session_id) is False
    assert prepared(session_id) == [] and len(wording_calls()) == 2
    assert attempts(session_id)[0][4] == frozen
    assert (await sweep.run(LATER + 3 * MINUTE))["tests.prepare_adapted"] == 0


@pytest.mark.parametrize(
    ("answer", "why"),
    [
        ('{"sentences": [{"template_id": "tilpasset-x", "fact_ids": ["F"]}]}', "unknown_template"),
        ('{"sentences": [{"template_id": "W", "fact_ids": ["moment:x:99"]}]}', "unknown_fact"),
        (mock.ERROR, "provider_error"),
    ],
)
async def test_a_rejected_wording_or_a_failure_keeps_the_code_text(klass, monkeypatch, answer, why):
    session_id, _ = await ai_locked(klass, monkeypatch)
    _, templates = await content.adapted_templates(None)
    first = templates.templates[0]
    answer = answer.replace("W", first.wordings[0].id)

    real = prepare._word

    async def first_fact(item, template, stored, scope):
        # The item's own fact id, known only once the item is built.
        with mock.script(answer.replace('"F"', f'"{item["fact_ids"][0]}"')):
            return await real(item, template, stored, scope)

    monkeypatch.setattr(prepare, "_word", first_fact)
    with capture_logs() as logs:
        await run_job(session_id)
    [(_, _, _, items)] = prepared(session_id)
    own = next(item for item in items if item["id"] == OWN)
    assert own["text"]["ai_generated"] is False and own["text"]["llm_call_id"] is None
    assert own["text"]["text"].startswith("Utkast: I uke")  # the template's code text
    if why == "provider_error":
        assert any(e["event"] == "ai_text_fallback" for e in logs)
    else:
        # Both items are rejected for the same reason.
        assert [e["reason"] for e in logs if e["event"] == "adapted_wording_rejected"] == [why] * 2
    # Opened: the code text is frozen, unmarked.
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    shown = next(i for i in attempts(session_id)[0][4] if i["id"] == OWN)
    assert shown["text"] == own["text"]


async def test_with_ai_text_off_or_few_orders_the_set_is_prepared_without_a_call(
    klass, monkeypatch
):
    # AI text off (a rule-based Class session): the code items, no call.
    stand_in(monkeypatch, own=range(1, 13))
    session_id, _ = await locked_with(klass, 30, n=2)
    await run_job(session_id)
    [(_, _, _, items)] = prepared(session_id)
    assert all(not i["text"]["ai_generated"] for i in items if i["type"] == "adapted")
    # Fewer than ten own Orders: the replacement items, prepared, no call.
    stand_in(monkeypatch, own=range(1, 10))
    await run_job(session_id, 1)
    other = next(r[3] for r in prepared(session_id) if r[0] == user_id(email(1)))
    assert [(i["id"], i["replaces"]) for i in other] == [(r, "few_orders") for r in REPLACEMENTS]
    assert wording_calls() == []
    # Opening copies each prepared set.
    for who in (0, 1):
        assert (await call(email(who), "POST", path(session_id))).status_code == 201
    frozen = {row[1]: row[4] for row in attempts(session_id)}
    assert frozen[user_id(email(1))][-2:] == other


async def test_an_open_during_the_job_wins_and_nothing_is_stored(klass, monkeypatch):
    session_id, _ = await ai_locked(klass, monkeypatch)
    real = prepare._word
    opened: list[int] = []

    async def open_meanwhile(item, template, stored, scope):
        if not opened:  # the Student opens the test while the job waits on the provider
            opened.append((await call(email(0), "POST", path(session_id))).status_code)
        return await real(item, template, stored, scope)

    monkeypatch.setattr(prepare, "_word", open_meanwhile)
    with capture_logs() as logs:
        await run_job(session_id)
    assert opened == [201]
    assert prepared(session_id) == []
    assert any(e["event"] == "adapted_items_not_prepared" for e in logs)
    frozen = attempts(session_id)[0][4]
    assert all(not i["text"]["ai_generated"] for i in frozen if i["type"] == "adapted")


@pytest.mark.parametrize("change", ["adapted_weight = 29", "question_set_version = 1"])
async def test_a_set_prepared_for_another_selection_is_not_used(klass, monkeypatch, change):
    session_id, _ = await ai_locked(klass, monkeypatch)
    await run_job(session_id)
    execute(
        f"UPDATE test_prepared_items SET {change} WHERE class_session_id = %s",
        session_id,
    )
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    frozen = attempts(session_id)[0][4]
    adapted_items = [i for i in frozen if i["type"] == "adapted"]
    assert [i["weight"] for i in adapted_items] == [15, 15]
    assert all(not i["text"]["ai_generated"] for i in adapted_items)


async def test_replacements_prepared_for_a_passing_reason_are_built_again_at_the_open(
    klass, monkeypatch
):
    """The Replay could not be read when the job ran: the replacement items it prepared are not
    frozen; the open builds the Adapted items from the Replay it now finds."""
    stand_in(monkeypatch, own=range(1, 13), replay=False)
    session_id, _ = await locked_with(klass, 30)
    await run_job(session_id)
    [(_, _, _, items)] = prepared(session_id)
    assert {i.get("replaces") for i in items} == {"no_replay"}
    stand_in(monkeypatch, own=range(1, 13))
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    frozen = attempts(session_id)[0][4]
    assert [i["id"] for i in frozen if i["type"] == "adapted"] == [OWN, REPLAY]


async def test_the_sweep_skips_an_opened_attempt_and_an_old_replay(klass, monkeypatch):
    stand_in(monkeypatch, own=range(1, 13))
    session_id, _ = await locked_with(klass, 30, n=2)
    assert (await call(email(0), "POST", path(session_id))).status_code == 201
    due = await prepare.due_prepares(LATER)
    assert due == [(str(user_id(email(1))), session_id)]
    assert await prepare.due_prepares(LATER + prepare.PREPARE_WINDOW + MINUTE) == []
    assert uuid.UUID(due[0][1])
