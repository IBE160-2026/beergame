"""AI narration that only connects computed facts (Story 9.14, FR-15, FR-34, FR-44, FR-46, AD-6,
AD-7, AD-9, AD-17).

A finished Class game defers one `llm-batch` job per Seat a Student held, inside the finish
transaction, when the Class session's pinned `debrief_ai_text` is on; none when it is off. The job
words the narration and the quiz lines with the mock provider (or stores the code text when the
mock fails); step 4 shows what was stored before the Student's first view and never changes after
it; a wrong quiz answer gets the AI line stored before the attempt. No Debrief step waits on the
job: a Group debrief whose job never runs opens every step. The sweep defers a lost job again."""

import uuid
from datetime import timedelta

import psycopg
import pytest

from app.ai import mock, seed
from app.analysis import narration as narration_rules
from app.modules.content import service as content
from app.modules.debrief import commands, narration
from app.modules.debrief import jobs as debrief_jobs
from app.modules.games import service as games
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import open_
from tests.debrief.test_explanation import played as played_long
from tests.debrief.test_explanation import user_id
from tests.debrief.test_group import played as played_short
from tests.debrief.test_quiz import body
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

CODE = {"ai_generated": False, "llm_call_id": None}


def narration_jobs() -> list[tuple]:
    return rows(
        "SELECT queue_name, queueing_lock, args FROM procrastinate_jobs "
        "WHERE task_name = 'debrief.narrate' AND status = 'todo' ORDER BY id"
    )


def texts(fact_set_id: str) -> dict[str, tuple]:
    found = rows(
        "SELECT subject, text, ai_generated, llm_call_id FROM debrief_ai_texts "
        "WHERE fact_set_id = %s",
        fact_set_id,
    )
    return {subject: (text, ai, call_id) for subject, text, ai, call_id in found}


def pins(game_id: str) -> dict:
    [(found,)] = rows("SELECT session_runtime->'pins' FROM games WHERE id = %s", game_id)
    return found


async def step_four(me: str, path: str) -> dict:
    response = await call(me, "GET", f"{path}/steps/4")
    assert response.status_code == 200, response.text
    return response.json()["moments"]


async def reflect(me: str, path: str) -> None:
    for question in ("feelings", "evidence", "structure"):
        answered = await call(me, "POST", f"{path}/reflection/{question}", json={"text": "Svar."})
        assert answered.status_code == 200, answered.text


async def test_the_finish_defers_narration_the_job_words_it_and_the_first_view_fixes_it(klass):
    await seed.ensure_zero_config()  # the default mock config with the Debrief's prompts
    session_id, game_id, debrief, game_of, me = await played_long(klass)
    role = debrief["role"]
    path = f"/api/debriefs/{debrief['id']}"
    pin = pins(game_id)["debrief_ai_text"]
    assert pin["enabled"] is True and pin["model_config_id"]
    assert pins(game_id)["narration_templates"] == {"version": 2}  # with the hints (9.15)

    # The finish hook defers one job per Seat a Student held, ids only, on `llm-batch`. (This
    # 14-Uke game is marked finished by SQL, so the hook is run here as `finish` runs it; the
    # short games below finish through `games.commands.finish` itself.)
    async with get_sessionmaker().begin() as session:
        await games.run_finish_hooks(session, uuid.UUID(game_id))
    game = await games.get_game(game_id)
    held = sorted(s.id for s in game.seats if s.user_id is not None)
    assert len(held) == list(game_of.values()).count(game_id) >= 2
    assert sorted(narration_jobs()) == sorted(
        ("llm-batch", narration.narration_key(game_id, seat), {"game_id": game_id, "seat_id": seat})
        for seat in held
    )

    # Before the job: step 4 shows the code narration, and that first view fixes it.
    assert (await call(me, "POST", f"{path}/explanation", json={"text": "Min."})).status_code == 201
    await reflect(me, path)
    first = await step_four(me, path)
    stored = await games.fact_set(game_id, role)
    _, templates = await content.narration_templates(2)
    code = narration_rules.render(stored.facts, templates)
    assert code is not None
    assert first["narration"] == {"text": code.text, **CODE}

    # The job, with the mock failing: the code text is stored, unmarked, never retried.
    seat_id = next(s.id for s in game.seats if str(s.role) == role)
    with mock.outage():
        assert await narration.narrate(game_id, seat_id) is True
    assert texts(stored.id)["narration"] == (code.text, False, None)
    failed = rows("SELECT outcome FROM llm_call WHERE caller_ref->>'fact_set_id' = %s", stored.id)
    assert {outcome for (outcome,) in failed} == {"provider_error"}

    # The job again with the mock answering (a lost row given back by the dev path): the mock's
    # answer is the code's own choice, accepted by the validator, stored marked with its call.
    await commands.clear_ai_texts(uuid.UUID(stored.id))
    await debrief_jobs.narrate_seat.func(game_id, seat_id)
    saved = texts(stored.id)
    text, ai, call_id = saved["narration"]
    assert (text, ai) == (code.text, True) and call_id is not None
    [(purpose, kind, scope_id, config_id)] = rows(
        "SELECT purpose, scope_kind, scope_id::text, model_config_id::text FROM llm_call "
        "WHERE id = %s",
        call_id,
    )
    assert (purpose, kind, scope_id, config_id) == (
        "debrief_narration",
        "class_session",
        session_id,
        pin["model_config_id"],
    )
    # Version 2 also holds the follow-up's hints (Story 9.15); the narration is offered its own
    # four templates only.
    [(prompt,)] = rows("SELECT request->>'prompt' FROM llm_call WHERE id = %s", call_id)
    assert all(t in prompt for t in narration_rules.NARRATION_TEMPLATES) and "hint-" not in prompt
    # One quiz line per pinned question with an own-game sentence, marked too.
    _, quiz = await content.debrief_quiz(1)
    asked = {narration.quiz_subject(q.id) for q in quiz.questions if q.in_your_game}
    assert set(saved) == {"narration", *asked}
    assert all(saved[s][1] is True for s in asked)
    # Stored once: a second delivery calls nothing and changes nothing; no update is allowed.
    calls = rows("SELECT count(*) FROM llm_call")
    assert await narration.narrate(game_id, seat_id) is False
    assert rows("SELECT count(*) FROM llm_call") == calls and texts(stored.id) == saved
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE debrief_ai_texts SET text = 'endret'")
    assert COMMAND_TOPICS["debrief.store_ai_text"] == frozenset()

    # The Student who saw step 4 before keeps the code text; a first view after the narration was
    # stored shows the AI text, marked by `ai_generated` with its call.
    assert (await step_four(me, path))["narration"] == first["narration"]
    execute("DELETE FROM debrief_fact_sets WHERE user_id = %s", user_id(me))
    assert (await step_four(me, path))["narration"] == {
        "text": code.text,
        "ai_generated": True,
        "llm_call_id": str(call_id),
    }

    # The quiz: a wrong answer to a question with an AI line gets it under the explanation.
    mine = user_id(me)
    await progress.record_step(mine, uuid.UUID(session_id), progress.Step.DEBRIEF, await _db_now())
    question = next(q for q in quiz.questions if q.in_your_game)
    wrong = next(c.id for c in question.choices if c.id != question.answer)
    answers = [(q.id, wrong if q.id == question.id else q.answer) for q in quiz.questions]
    result = await call(me, "POST", f"{path}/quiz/attempts", json=body(answers))
    assert result.status_code == 201, result.text
    missed = next(r for r in result.json()["results"] if not r["correct"])
    ai_text, _, ai_call = saved[narration.quiz_subject(question.id)]
    assert missed["ai_explanation"] == {
        "text": ai_text,
        "ai_generated": True,
        "llm_call_id": str(ai_call),
    }
    assert missed["explanation"]["ai_generated"] is False

    # The other Student of the game, whose Seat was Rule-based: no moments, no narration.
    mate = next(e for e, g in game_of.items() if g == game_id and e != me)
    assert (
        await call(mate, "POST", f"{path}/explanation", json={"text": "Min."})
    ).status_code == 201
    await reflect(mate, path)
    assert (await step_four(mate, path))["narration"] is None


async def _db_now():
    async with get_sessionmaker()() as session:
        return await games.database_now(session)


async def test_the_sweep_defers_a_lost_job_again(klass):
    # The minute sweep runs this action (AD-9).
    [action] = [a for a in sweep.DUE_ACTIONS if a.name == "debrief.narration"]
    assert (action.find, action.act) == (narration.due_narrations, narration.narrate_due)
    await seed.ensure_zero_config()
    session_id, game_id = await played_short(klass, 2, ordering=2, mode="personal")
    deferred = narration_jobs()
    assert len(deferred) == 2
    # Within ten minutes of the finish nothing is due; a waiting job is never doubled.
    now = await _db_now()
    assert await narration.due_narrations(now) == []
    later = now + narration.SWEEP_AFTER + timedelta(minutes=1)
    due = await narration.due_narrations(later)
    assert sorted(due) == sorted((g, s) for _, _, args in deferred for g, s in [args.values()])
    assert await narration.narrate_due(due[0], later) is False
    # The jobs were lost: the sweep defers them again.
    execute("DELETE FROM procrastinate_jobs WHERE task_name = 'debrief.narrate'")
    assert await narration.narrate_due(due[0], later) is True
    # Once narrated (a 2-Uke game has no moments: an empty code row, no call), nothing is due.
    for game, seat in due:
        assert await narration.narrate(game, seat) is True
    assert await narration.due_narrations(later) == []
    assert rows("SELECT count(*) FROM llm_call WHERE purpose = 'debrief_narration'") == [(0,)]


async def test_with_ai_text_off_no_job_is_deferred_and_the_switch_is_frozen_at_the_lock(klass):
    await seed.ensure_zero_config()
    session_id, game_id = await played_short(
        klass, 2, ordering=2, mode="personal", debrief_ai_text=False
    )
    assert pins(game_id)["debrief_ai_text"] == {
        "enabled": False,
        "model_config_id": None,
        "effort_level": None,
    }
    assert narration_jobs() == []
    # Nor does the sweep defer one later; the job, had it been deferred, would do nothing either.
    later = await _db_now() + narration.SWEEP_AFTER + timedelta(minutes=1)
    assert await narration.due_narrations(later) == []
    seat = rows("SELECT id::text FROM seats WHERE game_id = %s LIMIT 1", game_id)[0][0]
    assert await narration.narrate(game_id, seat) is False
    assert rows("SELECT count(*) FROM debrief_ai_texts") == [(0,)]
    assert rows("SELECT count(*) FROM llm_call") == [(0,)]  # no Debrief call reached the gateway
    # Frozen at the lock.
    shown = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert shown["debrief_ai_text"] is False
    changed = await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "debrief_ai_text": True},
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["fields"] == {"debrief_ai_text": "locked"}


async def test_a_group_debrief_opens_every_step_while_the_job_never_runs(klass):
    await seed.ensure_zero_config()
    session_id, game_id = await played_short(klass, 2, ordering=2)
    assert len(narration_jobs()) == 2  # deferred, and never run here
    a, b = email(0), email(1)
    opened = (await open_(a, session_id)).json()
    path = f"/api/debriefs/{opened['id']}"
    assert opened["group"]["joined"] is True
    assert (await open_(b, session_id)).status_code == 200
    assert (await call(b, "POST", f"{path}/join")).status_code == 200
    for who in (a, b):
        sent = await call(who, "POST", f"{path}/explanation", json={"text": "Min."})
        assert sent.status_code == 201
    for step in (2, 3):
        for who in (a, b):
            assert (await call(who, "GET", f"{path}/steps/{step}")).status_code == 200
            assert (await call(who, "POST", f"{path}/steps/{step}/done")).status_code == 200
    for who in (a, b):
        await reflect(who, path)
        moments = await step_four(who, path)
        assert moments["narration"] is None  # two Uker: no moments to connect
        assert (await call(who, "POST", f"{path}/finish")).status_code == 200
        assert (await call(who, "GET", f"{path}/quiz")).status_code == 200
    assert len(narration_jobs()) == 2 and rows("SELECT count(*) FROM llm_call") == [(0,)]


async def test_a_config_without_the_debriefs_prompt_pins_ai_text_off():
    """A Class session that holds a model config made before Story 9.14 stays code-only."""
    from app.ai import config
    from app.modules.sessions import service as sessions
    from tests.ai.helpers import mock_config

    old = await config.add(config.parse(mock_config(prompts={"player_order": 1})))
    new = await config.add(config.parse(mock_config(prompts={"debrief_narration": 1})))
    async with get_sessionmaker().begin() as s:
        off = await sessions.debrief_ai_text_pin(
            s, {"model_config_id": old.id, "effort_level": None}
        )
        on = await sessions.debrief_ai_text_pin(s, {"model_config_id": new.id, "effort_level": "x"})
    assert off == {"enabled": False, "model_config_id": None, "effort_level": None}
    assert on == {"enabled": True, "model_config_id": str(new.id), "effort_level": "x"}
