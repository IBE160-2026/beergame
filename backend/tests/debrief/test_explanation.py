"""The Explanation before the reveal (Story 9.3, FR-5, FR-14, FR-41, AD-12, AD-14, AD-16, AD-21).

Step 1 reads the Student's own Netto lager from the Decision log; «Send Forklaring» stores the
Explanation once, as typed, and records the `explanation` step in the same transaction; every
step after step 1 answers 403 `explanation_required` until then. The Class's owners and
Assistant lecturers read a Student's Explanation; another Student and an Admin without a staff
role do not. One Class game played 14 Uker (the first Student ordering after the Guided Uker,
the others Rule-based), then marked finished, serves each test."""

import json
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import psycopg
import pytest

from app.analysis import moments as moment_text
from app.engine import ROLES
from app.modules.content import service as content
from app.modules.debrief import insight
from app.modules.games import commands as game_commands
from app.modules.games import service as games
from app.modules.identity.schemas import AccountRole
from app.modules.ops import sweep
from app.modules.progress import service as progress
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call, put_staff
from tests.classes.test_student_registration import emitted
from tests.debrief.test_debrief import LOCKED, finish, home, open_, refused
from tests.games.helpers import open_turns, play_week
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_start_game import start, task_done
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ASSISTANT = "assistent-93@x.no"
ADMIN = "admin-93@x.no"
TEXT = "  Restordren vokste, så jeg bestilte mye.\nDet som var på vei, regnet jeg lite med.  "


def base(debrief_id: str) -> str:
    return f"/api/debriefs/{debrief_id}"


def user_id(address: str) -> uuid.UUID:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", address)
    return found


def explanations() -> list[tuple]:
    return rows("SELECT user_id, text, length FROM debrief_explanations ORDER BY user_id")


def answers() -> list[tuple]:
    return rows(
        "SELECT user_id, question_id, questions_version, text, length "
        "FROM debrief_reflection_answers ORDER BY saved_at, question_id"
    )


OWN_ORDERS = (4, 12, 0, 8, 16, 4, 8, 2, 8, 20, 8, 6)
"""The first Student's Orders after the Guided Uker (14 Uker in all): at least 10 of them, so
they get moments."""


async def play_own_week(game_id: str, user: uuid.UUID, order: int) -> None:
    """The open Uke with the Student's own Order (`decided_by = student`), the rest Rule-based."""
    found = await open_turns(game_id)
    if found is not None:  # an ordinary Uke, read in one query
        week, _ = found
        [(role,)] = rows(
            "SELECT s.role FROM seats s JOIN seat_occupancy o ON o.seat_id = s.id "
            "WHERE s.game_id = %s AND o.user_id = %s ORDER BY o.id DESC LIMIT 1",
            game_id,
            user,
        )
        await game_commands.place_order(game_id, role, week, order, "student", actor=user)
        await play_week(game_id)
        return
    game = await games.get_game(game_id)
    seat = next(s for s in game.seats if s.user_id == str(user))
    week = (await games.seat_state(game_id, seat.id)).week
    turn = await games.open_turn(game_id, seat.id, week)
    if not turn.guided:
        await game_commands.place_order(game_id, seat.role, week, order, "student", actor=user)
    await play_week(game_id)


async def played(klass: str) -> tuple[str, str, dict, dict[str, str], str]:
    """A Class session with two Class games (five Students); the game of a Student who shares it
    with another (the allocation is random) played 14 Uker and finished, its Debrief opened.
    That Student ordered after the Guided Uker (`OWN_ORDERS`); every other Seat was Rule-based.
    Returns the session id, game id, Debrief, each Student's game and that Student."""
    session_id, seated = await confirmed(klass, 5)
    await sweep.run(LOCKED)
    game_of = {email(i): (await home(email(i)))["game"]["id"] for i in range(5)}
    games_ = list(game_of.values())
    first = next(i for i in range(5) if games_.count(games_[i]) > 1)
    me, game_id = email(first), games_[first]
    await task_done(seated[first], session_id)
    assert (await start(me, game_id)).status_code == 200
    for order in (4, 4, *OWN_ORDERS):
        await play_own_week(game_id, user_id(me), order)
    finish(game_id)
    opened = await open_(me, session_id)
    assert opened.status_code == 200
    return session_id, game_id, opened.json(), game_of, me


def holds_no_reveal(body: object, own_role: str) -> None:
    """No demand, incoming order or other Role anywhere in an answer (FR-14, FR-41)."""
    text = json.dumps(body)
    for word in ("demand", "incoming", "customer", "orders", "backlog"):
        assert word not in text, (word, text)
    others = {"retailer", "wholesaler", "distributor", "factory"} - {own_role}
    assert not any(role in text for role in others), text


@pytest.mark.long
async def test_step_one_the_one_send_the_gate_and_the_readers(klass, emitted):
    session_id, game_id, debrief, game_of, me = await played(klass)
    role = debrief["role"]
    mate = next(who for who, game in game_of.items() if game == game_id and who != me)
    stranger = next(who for who, game in game_of.items() if game != game_id)
    path = base(debrief["id"])

    # Step 1: the own Seat's Netto lager in every logged Uke, nothing else.
    net = await call(me, "GET", f"{path}/net-inventory")
    assert net.status_code == 200
    logged = [r for r in await games.decision_log(game_id) if r.role == role]
    assert net.json() == {
        "weeks": [
            {"week": r.week, "net_inventory": r.state_seen.net_inventory}
            for r in sorted(logged, key=lambda r: r.week)
        ]
    }
    weeks = [w["week"] for w in net.json()["weeks"]]
    assert len(weeks) >= 2 and weeks == list(range(1, len(weeks) + 1))

    # Without an Explanation: every Debrief data endpoint holds no demand and no other Seat,
    # and every step after step 1 is refused.
    for method, url in (
        ("POST", f"/api/me/class-sessions/{session_id}/debrief"),
        ("GET", path),
        ("GET", f"{path}/net-inventory"),
        ("GET", f"{path}/explanation"),
    ):
        response = await call(me, method, url)
        assert response.status_code == 200, url
        holds_no_reveal(response.json(), role)
    for step in range(2, 6):
        refused(await call(me, "GET", f"{path}/steps/{step}"), "explanation_required")
    refused(await call(me, "GET", f"{path}/reflection"), "explanation_required")
    early = await call(me, "POST", f"{path}/reflection/feelings", json={"text": "Tidlig."})
    refused(early, "explanation_required")
    assert answers() == []
    assert (await call(me, "GET", f"{path}/explanation")).json() == {"explanation": None}

    # White space only and too long are refused and store nothing.
    for text, reason in (("  \n\t ", "blank"), ("x" * 5001, "too_long")):
        response = await call(me, "POST", f"{path}/explanation", json={"text": text})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert response.json()["error"]["fields"] == {"text": reason}
    assert explanations() == []

    # Sent once, as typed, with its length and time, and the step recorded with it.
    emitted.clear()
    sent = await call(me, "POST", f"{path}/explanation", json={"text": TEXT})
    assert sent.status_code == 201
    body = sent.json()
    assert (body["text"], body["length"]) == (TEXT, len(TEXT))
    assert set(body) == {"text", "length", "saved_at"}
    assert explanations() == [(user_id(me), TEXT, len(TEXT))]
    assert await progress.has_step(user_id(me), uuid.UUID(session_id), "explanation")
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.save_explanation"]
    assert ("debrief", debrief["id"]) in emitted

    # A second send is refused and changes nothing; nor can the row be changed in the database.
    again = await call(me, "POST", f"{path}/explanation", json={"text": "Noe annet."})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "explanation_exists"
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE debrief_explanations SET text = 'endret', length = 6")
    assert explanations() == [(user_id(me), TEXT, len(TEXT))]
    assert (await call(me, "GET", f"{path}/explanation")).json() == {"explanation": body}

    # With it, the steps after step 1 answer; step 2 is the reveal (Story 9.4), step 3 the whole
    # chain (Story 9.5).
    response = await call(me, "GET", f"{path}/steps/5")
    assert response.status_code == 200
    assert response.json() == {
        "debrief_id": debrief["id"],
        "step": 5,
        "reveal": None,
        "chain": None,
        "moments": None,
        "bill": None,
    }
    await revealed(me, path, debrief, game_id)
    await chained(me, path, debrief, game_id)
    await reflected(me, mate, path, debrief, emitted)
    await momented(me, mate, path, debrief, game_id, emitted)
    await billed(me, path, game_id)
    await finished(me, mate, path, debrief, session_id, game_id, emitted)

    # Another Student of the same game reads only their own (none) and is still gated.
    other = mate
    assert (await call(other, "GET", f"{path}/explanation")).json() == {"explanation": None}
    refused(await call(other, "GET", f"{path}/steps/2"), "explanation_required")
    refused(await call(other, "GET", f"{path}/reflection"), "explanation_required")

    await readers(session_id, game_id, path, klass, body, me, mate, stranger)


async def revealed(me: str, path: str, debrief: dict, game_id: str) -> None:
    """Step 2, the reveal of customer demand (Story 9.4, FR-44, NFR-9): every number equals the
    Game's stored demand series and the Seat's own `seat_weeks` rows, read here by SQL. Part of
    the test above, so the played game is set up once."""
    response = await call(me, "GET", f"{path}/steps/2")
    assert response.status_code == 200
    body = response.json()
    assert (body["debrief_id"], body["step"]) == (debrief["id"], 2)
    shown = body["reveal"]
    [(series, pins)] = rows(
        "SELECT demand_series, session_runtime->'pins' FROM games WHERE id = %s", game_id
    )
    stored = rows(
        "SELECT w.week, w.\"order\", (w.state_seen->>'incoming_order')::int FROM seat_weeks w "
        "JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = %s ORDER BY w.week",
        game_id,
        debrief["role"],
    )
    assert len(stored) >= 2
    assert shown["role"] == debrief["role"]
    assert shown["weeks"] == [
        {"week": week, "demand": series[week - 1], "incoming_order": seen, "order": order}
        for week, order, seen in stored
    ]
    top = max(order for _, order, _ in stored)
    first_top = next(week for week, order, _ in stored if order == top)
    assert shown["largest_order"] == {"week": first_top, "order": top}
    # The Classic demand steps once (4, then 8 from Uke 5); the lock pinned the templates.
    assert series[:5] == [4, 4, 4, 4, 8]
    assert pins["sentence_templates"] == {"version": 1}
    assert pins["moment_templates"] == {"version": 1}
    assert (shown["template_id"], shown["heading"]) == (
        "demand-step",
        "Kundene bestilte 4, så 8. Etter det endret de seg aldri.",
    )
    # Every Uke of the own Seat only: no other Role's number.
    assert {"week", "demand", "incoming_order", "order"} == set(shown["weeks"][0])
    assert body["chain"] is None


async def chained(me: str, path: str, debrief: dict, game_id: str) -> None:
    """Step 3, the whole chain (Story 9.5, FR-44, NFR-9, AD-7): every Role, Fabrikk first, with
    each Uke's Order and Week state equal to its `seat_weeks` row (read here by SQL), and
    Forsterkning and the first large Uke equal to the stored facts set. Part of the test above."""
    response = await call(me, "GET", f"{path}/steps/3")
    assert response.status_code == 200
    body = response.json()
    assert (body["debrief_id"], body["step"], body["reveal"]) == (debrief["id"], 3, None)
    chain = body["chain"]
    assert [r["role"] for r in chain["roles"]] == [
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
    ]
    assert (chain["own_role"], chain["large_order"]) == (debrief["role"], 10)
    stored = await games.fact_set(game_id, debrief["role"])
    facts = {str(r.role): r for r in stored.facts.chain.by_role}
    [(count,)] = rows("SELECT count(*) FROM fact_sets WHERE game_id = %s", game_id)
    for role in chain["roles"]:
        logged = rows(
            "SELECT w.week, w.\"order\", (w.state_seen->>'incoming_order')::int, "
            "(w.state_seen->>'inventory')::int, (w.state_seen->>'backlog')::int, "
            "(w.state_seen->>'supply_line')::int FROM seat_weeks w JOIN seats s "
            "ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = %s ORDER BY w.week",
            game_id,
            role["role"],
        )
        assert role["weeks"] == [
            {
                "week": week,
                "order": order,
                "incoming_order": incoming,
                "inventory": inventory,
                "backlog": backlog,
                "supply_line": supply,
            }
            for week, order, incoming, inventory, backlog, supply in logged
        ]
        fact = facts[role["role"]]
        amplification = None if fact.amplification is None else str(fact.amplification)
        assert role["amplification"] == amplification
        assert role["first_large_order_week"] == fact.first_large_order_week
        # The Classic settings cap no Role.
        assert role["capacity"] is None
    assert chain["last_week"] == stored.facts.chain.weeks == len(chain["roles"][0]["weeks"])
    # The facts were stored once per Seat read, never rebuilt by a second read.
    assert count == 1

    # A capped Role states its capacity while `FEATURE_CAPACITY` is on, and none with it off.
    execute(
        "UPDATE games SET settings = jsonb_set(settings, '{capacity}', '{\"factory\": 12}') "
        "WHERE id = %s",
        game_id,
    )
    try:
        on = (await call(me, "GET", f"{path}/steps/3")).json()["chain"]["roles"]
        assert [r["capacity"] for r in on] == [12, None, None, None]
        off = SimpleNamespace(feature_capacity=False)
        with patch("app.modules.debrief.service.get_settings", return_value=off):
            gone = (await call(me, "GET", f"{path}/steps/3")).json()["chain"]["roles"]
        assert [r["capacity"] for r in gone] == [None] * 4
    finally:
        execute("UPDATE games SET settings = settings - 'capacity' WHERE id = %s", game_id)


async def reflected(me: str, mate: str, path: str, debrief: dict, emitted) -> None:
    """The reflection questions between steps 3 and 4 (Story 9.6, FR-43, FR-45, AD-14, AD-21):
    the pinned version in the order feelings, evidence, structure, answered one at a time, each
    stored once through `complete_step`, and read back by their own Student only. Part of the
    test above."""
    shown = await call(me, "GET", f"{path}/reflection")
    assert shown.status_code == 200
    body = shown.json()
    assert body["version"] == 1
    assert [(q["id"], q["kind"], q["answer"]) for q in body["questions"]] == [
        ("feelings", "feelings", None),
        ("evidence", "evidence", None),
        ("structure", "structure", None),
    ]
    answer = f"{path}/reflection"

    # Refused, storing nothing: blank, too long, an unknown id, and any but the next question.
    for text, reason in (("  \n ", "blank"), ("x" * 2001, "too_long")):
        bad = await call(me, "POST", f"{answer}/feelings", json={"text": text})
        assert bad.status_code == 422 and bad.json()["error"]["fields"] == {"text": reason}
    unknown = await call(me, "POST", f"{answer}/nope", json={"text": "Svar."})
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "not_found"
    for later in ("evidence", "structure"):
        ahead = await call(me, "POST", f"{answer}/{later}", json={"text": "Svar."})
        assert ahead.status_code == 409
        assert ahead.json()["error"]["code"] == "reflection_out_of_order"
    assert answers() == []

    # The next question: stored as typed, through the locked Debrief row, which emits.
    emitted.clear()
    first = await call(me, "POST", f"{answer}/feelings", json={"text": " Stressende. "})
    assert first.status_code == 200
    saved = first.json()
    assert (saved["id"], saved["kind"]) == ("feelings", "feelings")
    assert (saved["answer"]["text"], saved["answer"]["length"]) == (" Stressende. ", 13)
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.complete_step"]
    assert ("debrief", debrief["id"]) in emitted

    # Again, with other text: the stored answer, unchanged, and no event.
    emitted.clear()
    again = await call(me, "POST", f"{answer}/feelings", json={"text": "Noe annet."})
    assert again.status_code == 200 and again.json() == saved
    blank = await call(me, "POST", f"{answer}/feelings", json={"text": " "})
    assert blank.status_code == 200 and blank.json() == saved
    assert emitted == []
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE debrief_reflection_answers SET text = 'endret', length = 6")
    refused_last = await call(me, "POST", f"{answer}/structure", json={"text": "Svar."})
    assert refused_last.json()["error"]["code"] == "reflection_out_of_order"
    for qid, text in (("evidence", "Fabrikken svingte mest."), ("structure", "Forsinkelser.")):
        assert (await call(me, "POST", f"{answer}/{qid}", json={"text": text})).status_code == 200
    mine = user_id(me)
    assert answers() == [
        (mine, "feelings", 1, " Stressende. ", 13),
        (mine, "evidence", 1, "Fabrikken svingte mest.", 23),
        (mine, "structure", 1, "Forsinkelser.", 13),
    ]
    read = (await call(me, "GET", f"{path}/reflection")).json()
    assert [q["answer"]["text"] for q in read["questions"]] == [
        " Stressende. ",
        "Fabrikken svingte mest.",
        "Forsinkelser.",
    ]

    # Another Student of the same game, once past their own Explanation, sees none of them.
    sent = await call(mate, "POST", f"{path}/explanation", json={"text": "Min egen."})
    assert sent.status_code == 201
    theirs = (await call(mate, "GET", f"{path}/reflection")).json()
    assert [q["answer"] for q in theirs["questions"]] == [None, None, None]
    assert "Stressende" not in json.dumps(theirs)
    execute("DELETE FROM debrief_explanations WHERE user_id = %s", user_id(mate))
    execute("DELETE FROM progress_steps WHERE user_id = %s AND step = 'explanation'", user_id(mate))


def cited() -> list[tuple]:
    return rows(
        "SELECT user_id, game_id::text, fact_set_id::text FROM debrief_fact_sets ORDER BY user_id"
    )


async def momented(me: str, mate: str, path: str, debrief: dict, game_id: str, emitted) -> None:
    """Step 4, the own moments (Story 9.7, FR-43, FR-44, AD-7, NFR-9): rendered by code from the
    stored facts set of the caller's own Seat, whose id is recorded once for them; with fewer than
    10 own Orders the game was played mostly by AI players. Part of the test above."""
    role = debrief["role"]
    assert cited() == []
    emitted.clear()
    response = await call(me, "GET", f"{path}/steps/4")
    assert response.status_code == 200
    body = response.json()
    assert (body["step"], body["reveal"], body["chain"]) == (4, None, None)
    shown = body["moments"]
    stored = await games.fact_set(game_id, role)
    seat = stored.facts.seat
    assert (shown["role"], shown["mostly_ai"]) == (role, False)
    # Every Order after the Guided Uker was the Student's: at least 10.
    assert shown["student_orders"] == seat.student_orders >= 10 and not seat.sm_excluded

    # The facts set's id is recorded once for the Student, through the locked Debrief row.
    assert cited() == [(user_id(me), game_id, stored.id)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.record_facts"]
    assert ("debrief", debrief["id"]) in emitted
    emitted.clear()
    assert (await call(me, "GET", f"{path}/steps/4")).json() == body
    assert emitted == [] and len(cited()) == 1
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE debrief_fact_sets SET recorded_at = now()")

    # Every text is the code's, from the stored facts with the pinned templates: never AI text.
    _, templates = await content.moment_templates(1)
    _, patterns = await content.detected_patterns(stored.patterns_version)
    rendered = moment_text.render(stored.facts, templates, patterns)
    code = {"ai_generated": False, "llm_call_id": None}
    assert rendered.heading is not None
    assert shown["heading"] == {"text": rendered.heading.text, **code}
    assert shown["heading"]["text"].startswith("Ditt øyeblikk: Uke ")
    student_weeks = {
        week
        for (week,) in rows(
            "SELECT w.week FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
            "WHERE w.game_id = %s AND s.role = %s AND w.decided_by = 'student'",
            game_id,
            role,
        )
    }
    logged = {(e.week, e.role): e for e in await games.decision_log(game_id)}
    assert len(shown["moments"]) == 3 == len(rendered.moments)
    for out, text, fact in zip(shown["moments"], rendered.moments, seat.moments, strict=True):
        own = logged[(fact.week, role)]
        assert (out["id"], out["week"], out["order"]) == (fact.id, fact.week, fact.order)
        assert out["week"] in student_weeks and out["order"] == own.order
        assert out["chosen_by"] == fact.chosen_by
        assert out["heading"] == {"text": text.heading.text, **code}
        assert out["reckoning"] == {"text": text.reckoning.text, **code}
        assert out["later"] == {"text": text.later.text, **code}
        assert out["patterns"] == [{"text": p.text, **code} for p in text.patterns]
        assert out["seen"] == own.state_seen.model_dump(mode="json")
        assert [o["role"] for o in out["others"]] == [r.value for r in ROLES if r.value != role]
        for other in out["others"]:
            seen = logged[(fact.week, other["role"])].state_seen
            assert other == {
                "role": other["role"],
                "incoming_order": seen.incoming_order,
                "inventory": seen.inventory,
                "backlog": seen.backlog,
                "supply_line": seen.supply_line,
            }

    # Another Student of the same game: only their own Seat, played Rule-based, so no moments;
    # the rest of the Debrief stays theirs to finish.
    sent = await call(mate, "POST", f"{path}/explanation", json={"text": "Min egen."})
    assert sent.status_code == 201
    theirs = (await call(mate, "GET", f"{path}/steps/4")).json()["moments"]
    seats = (await games.get_game(game_id)).seats
    mate_role = next(str(x.role) for x in seats if x.user_id == str(user_id(mate)))
    assert mate_role != role
    assert theirs == {
        "role": mate_role,
        "student_orders": 0,
        "mostly_ai": True,
        "heading": None,
        "moments": [],
        "narration": None,
    }
    assert (await games.fact_set(game_id, mate_role)).facts.seat.sm_excluded
    assert len(cited()) == 2
    execute("DELETE FROM debrief_explanations WHERE user_id = %s", user_id(mate))
    execute("DELETE FROM progress_steps WHERE user_id = %s AND step = 'explanation'", user_id(mate))
    refused(await call(mate, "GET", f"{path}/steps/4"), "explanation_required")


def _percent(part: Decimal, whole: Decimal) -> int:
    return int((part * 100 / whole).quantize(Decimal(1), rounding=ROUND_HALF_UP))


async def billed(me: str, path: str, game_id: str) -> None:
    """Step 4's lines under Kjedens regning (Story 9.8, FR-44, UX-DR36, NFR-9): every number from
    the stored facts set, which equals the `seat_weeks` rows read here by SQL. Part of the test
    above."""
    body = (await call(me, "GET", f"{path}/steps/4")).json()
    bill = body["bill"]
    role = body["moments"]["role"]
    stored = await games.fact_set(game_id, role)
    [(total, backorder, ai_held)] = rows(
        "SELECT sum((w.state_seen->>'week_cost')::numeric), "
        "sum((SELECT coalesce(sum((l->>'amount')::numeric), 0) "
        "     FROM jsonb_array_elements(w.state_seen->'cost_lines') l "
        "     WHERE l->>'kind' = 'backorder')), "
        "coalesce(sum((w.state_seen->>'week_cost')::numeric) "
        "FILTER (WHERE w.occupant_kind <> 'student'), 0) "
        "FROM seat_weeks w WHERE w.game_id = %s",
        game_id,
    )
    assert Decimal(bill["total_cost"]) == total == stored.facts.chain.total_cost
    assert Decimal(bill["backorder_cost"]) == backorder
    assert Decimal(bill["ai_held_cost"]) == ai_held == stored.facts.chain.ai_held_cost
    assert bill["backorder_share_percent"] == _percent(backorder, total)
    assert bill["ai_held_share_percent"] == _percent(ai_held, total)
    # Every Seat stayed a Student's (the Rule-based Orders were placed for them): none was held
    # by an AI player, so the web app shows no AI line (it shows one only above 0).
    assert (ai_held, bill["ai_held_share_percent"]) == (0, 0)
    # The Classic costs: a unit in backlog costs 1,00, in inventory 0,50.
    assert (bill["role"], bill["backorder_costs_double"]) == (role, True)
    simulated = stored.facts.seat.simulated
    assert simulated is not None
    assert bill["simulated"] == {
        "params_id": "placeholder-unverified",
        "rows": [row.model_dump(mode="json") for row in simulated.rows],
    }
    assert [r["counts_supply_line"] for r in bill["simulated"]["rows"]] == ["own", "all"]


def conflict(response, code: str) -> None:
    assert response.status_code == 409
    assert response.json()["error"]["code"] == code


def summaries() -> list[tuple]:
    return rows("SELECT user_id, moment_ids, reflection FROM debrief_summaries ORDER BY user_id")


async def finished(
    me: str, mate: str, path: str, debrief: dict, session_id: str, game_id: str, emitted
) -> None:
    """«Fullfør Debriefen» (Story 9.8, FR-47, AD-7, AD-16): the summary is stored once with the
    `debrief` step in the same transaction; not before every reflection answer and step 4, and
    not after the Test deadline. Part of the test above."""
    mine, theirs = user_id(me), user_id(mate)
    assert (await call(me, "GET", f"{path}/summary")).json() == {"summary": None}
    refused(await call(mate, "POST", f"{path}/finish"), "explanation_required")
    refused(await call(mate, "GET", f"{path}/summary"), "explanation_required")

    emitted.clear()
    done = await call(me, "POST", f"{path}/finish")
    assert done.status_code == 200
    summary = done.json()["summary"]
    stored = await games.fact_set(game_id, debrief["role"])
    moment_ids = [moment.id for moment in stored.facts.seat.moments]
    assert summary["fact_set_id"] == stored.id
    assert [m["id"] for m in summary["moments"]] == moment_ids and len(moment_ids) == 3
    shown = (await call(me, "GET", f"{path}/steps/4")).json()["moments"]["moments"]
    for out, moment in zip(summary["moments"], shown, strict=True):
        assert out["week"] == moment["week"]
        for key in ("heading", "reckoning", "later", "patterns"):
            assert out[key] == moment[key]
    assert [(a["question_id"], a["text"]) for a in summary["reflection"]] == [
        ("feelings", " Stressende. "),
        ("evidence", "Fabrikken svingte mest."),
        ("structure", "Forsinkelser."),
    ]
    assert all(a["prompt"] for a in summary["reflection"])
    [(finished_at, late)] = rows(
        "SELECT s.finished_at, s.finished_at > c.debrief_deadline FROM debrief_summaries s "
        "JOIN class_sessions c ON c.id = s.class_session_id WHERE s.user_id = %s",
        mine,
    )
    assert summary["late"] is bool(late)
    assert summaries() == [
        (
            mine,
            moment_ids,
            [
                {"question_id": q, "questions_version": 1, "text": t}
                for q, t in (
                    ("feelings", " Stressende. "),
                    ("evidence", "Fabrikken svingte mest."),
                    ("structure", "Forsinkelser."),
                )
            ],
        )
    ]
    [(step_at,)] = rows(
        "SELECT at FROM progress_steps WHERE user_id = %s AND step = 'debrief'", mine
    )
    assert step_at == finished_at
    assert await progress.has_step(mine, uuid.UUID(session_id), "debrief")
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["debrief.finish"]
    assert ("debrief", debrief["id"]) in emitted

    # Again: the stored summary, unchanged, and no event; the row cannot be changed; every step
    # still reads.
    emitted.clear()
    again = await call(me, "POST", f"{path}/finish")
    assert again.status_code == 200 and again.json() == done.json()
    assert (await call(me, "GET", f"{path}/summary")).json() == done.json()
    assert emitted == []
    # (Only the erasure of Story 15.2 may empty its reflection, and change nothing else.)
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute("UPDATE debrief_summaries SET reflection = '[]', moment_ids = '[\"x\"]'")
    with pytest.raises(psycopg.errors.RestrictViolation):
        execute('UPDATE debrief_summaries SET reflection = \'[{"text": "endret"}]\'')
    for step in (2, 3, 4):
        assert (await call(me, "GET", f"{path}/steps/{step}")).status_code == 200

    # The mate: not before every reflection answer, nor before step 4 was read, nor after the
    # Test deadline (judged in the database's time); nothing is stored for them.
    assert (
        await call(mate, "POST", f"{path}/explanation", json={"text": "Min."})
    ).status_code == 201
    conflict(await call(mate, "POST", f"{path}/finish"), "debrief_incomplete")
    for qid in ("feelings", "evidence", "structure"):
        answer = await call(mate, "POST", f"{path}/reflection/{qid}", json={"text": "Svar."})
        assert answer.status_code == 200
    execute("DELETE FROM debrief_fact_sets WHERE user_id = %s", theirs)
    conflict(await call(mate, "POST", f"{path}/finish"), "debrief_incomplete")
    assert (await call(mate, "GET", f"{path}/steps/4")).status_code == 200
    past = AsyncMock(return_value=(None, datetime(2000, 1, 1, tzinfo=UTC)))
    with patch("app.modules.debrief.service.sessions.student_deadlines", past):
        conflict(await call(mate, "POST", f"{path}/finish"), "test_deadline_passed")
    assert [row[0] for row in summaries()] == [mine]
    assert not await progress.has_step(theirs, uuid.UUID(session_id), "debrief")
    execute("DELETE FROM debrief_reflection_answers WHERE user_id = %s", theirs)
    execute("DELETE FROM debrief_explanations WHERE user_id = %s", theirs)
    execute("DELETE FROM progress_steps WHERE user_id = %s AND step = 'explanation'", theirs)


async def readers(
    session_id: str,
    game_id: str,
    path: str,
    klass: str,
    sent: dict,
    me: str,
    mate: str,
    stranger: str,
) -> None:
    """Who reads the first Student's sent Explanation, and who reaches the Debrief's routes.
    Part of the test above, so the played game is set up once."""
    staff_path = f"/api/class-sessions/{session_id}/students/{user_id(me)}/explanation"
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    await make(ADMIN, roles=(AccountRole.admin,))

    # The staff are told when a Student has sent none.
    none_path = f"/api/class-sessions/{session_id}/students/{user_id(mate)}/explanation"
    missing = await call(ASSISTANT, "GET", none_path)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"

    for who in (ASSISTANT, LECTURER):
        read = await call(who, "GET", staff_path)
        assert read.status_code == 200 and read.json() == sent
    # Another Student of the same game, an Admin and a Lecturer of no role in the Class.
    for who in (mate, ADMIN, OTHER):
        refused(await call(who, "GET", staff_path), "forbidden")
    for bad in ("nope", str(uuid.uuid4())):
        refused(
            await call(ASSISTANT, "GET", f"/api/class-sessions/{bad}/students/x/explanation"),
            "forbidden",
        )

    # The Debrief summary (Story 9.8, FR-47, AD-12): the same readers; the Explanation beside it.
    summary_path = f"/api/class-sessions/{session_id}/students/{user_id(me)}/debrief-summary"
    own = (await call(me, "GET", f"{path}/summary")).json()["summary"]
    for who in (ASSISTANT, LECTURER):
        read = await call(who, "GET", summary_path)
        assert read.status_code == 200
        body = read.json()
        assert (body["student_id"], body["game_id"]) == (str(user_id(me)), game_id)
        assert body["explanation"] == sent and body["summary"] == own
        assert body["role"] is not None and body["game_number"] is not None
        assert body["name"]  # the Roster name, read now (Story 9.10)
    unfinished = f"/api/class-sessions/{session_id}/students/{user_id(mate)}/debrief-summary"
    theirs = (await call(LECTURER, "GET", unfinished)).json()
    assert (theirs["explanation"], theirs["summary"]) == (None, None)
    for who in (me, mate, ADMIN, OTHER):
        refused(await call(who, "GET", summary_path), "forbidden")
    for bad in ("nope", str(uuid.uuid4())):
        url = f"/api/class-sessions/{bad}/students/{user_id(me)}/debrief-summary"
        refused(await call(LECTURER, "GET", url), "forbidden")

    # Spillinnsikt's links (Story 7.7's hook): one Explanation and one summary link per
    # Student-held Seat.
    links = await insight.links(None, uuid.UUID(game_id))  # type: ignore[arg-type]
    held = [s for s in (await games.get_game(game_id)).seats if s.user_id is not None]
    assert len(links) == 2 * len(held) >= 4
    page = insight.summary_path(session_id, user_id(me))
    assert page == f"/klasseokter/{session_id}/studenter/{user_id(me)}/debrief"
    mine = [link for link in links if str(user_id(me)) in link.href]
    assert [(link.kind, link.href) for link in mine] == [
        ("explanation", f"{page}#forklaring"),
        ("debrief_summary", page),
    ]
    registered = []
    with patch.object(games, "register_insight_links", registered.append):
        insight.register()
    assert registered == [insight.links]
    # They reach the Lecturer in Spillinnsikt's answer, on the Student-held Seats only.
    answer = (await call(LECTURER, "GET", f"/api/games/{game_id}/insight")).json()
    for seat in answer["seats"]:
        offered = [(link["kind"], link["href"]) for link in seat["links"]]
        expected = [(link.kind, link.href) for link in links if link.role == seat["role"]]
        assert offered == (expected if seat["holder"] == "student" else [])
    assert sum(len(seat["links"]) for seat in answer["seats"]) >= 4

    # The Student of the other Class game and the staff reach none of the Debrief's routes.
    for who in (stranger, ASSISTANT):
        for method, url in (
            ("GET", f"{path}/net-inventory"),
            ("GET", f"{path}/explanation"),
            ("POST", f"{path}/explanation"),
            ("GET", f"{path}/steps/2"),
            ("GET", f"{path}/steps/3"),
            ("GET", f"{path}/steps/4"),
            ("GET", f"{path}/reflection"),
            ("POST", f"{path}/reflection/feelings"),
            ("GET", f"{path}/summary"),
            ("POST", f"{path}/finish"),
        ):
            kw = {"json": {"text": "x"}} if method == "POST" else {}
            refused(await call(who, method, url, **kw), "forbidden")

    # A game that is not finished refuses them alike, with the envelope only.
    execute("UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", game_id)
    for url in (
        f"{path}/net-inventory",
        f"{path}/explanation",
        f"{path}/steps/2",
        f"{path}/steps/3",
        f"{path}/steps/4",
        f"{path}/reflection",
        f"{path}/summary",
    ):
        refused(await call(me, "GET", url), "debrief_not_open")
    refused(await call(me, "POST", f"{path}/finish"), "debrief_not_open")
    late = await call(me, "POST", f"{path}/reflection/feelings", json={"text": "x"})
    refused(late, "debrief_not_open")
