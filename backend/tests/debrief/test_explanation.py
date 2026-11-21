"""The Explanation before the reveal (Story 9.3, FR-5, FR-14, FR-41, AD-12, AD-14, AD-16, AD-21).

Step 1 reads the Student's own Netto lager from the Decision log; «Send Forklaring» stores the
Explanation once, as typed, and records the `explanation` step in the same transaction; every
step after step 1 answers 403 `explanation_required` until then. The Class's owners and
Assistant lecturers read a Student's Explanation; another Student and an Admin without a staff
role do not. One Class game played a few Uker, then marked finished, serves each test."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import psycopg
import pytest

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
from tests.games.helpers import play_week
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


async def played(klass: str) -> tuple[str, str, dict, dict[str, str], str]:
    """A Class session with two Class games (five Students); the game of a Student who shares it
    with another (the allocation is random) played a few Uker and finished, its Debrief opened.
    Returns the session id, game id, Debrief, each Student's game and that Student."""
    session_id, seated = await confirmed(klass, 5)
    await sweep.run(LOCKED)
    game_of = {email(i): (await home(email(i)))["game"]["id"] for i in range(5)}
    games_ = list(game_of.values())
    first = next(i for i in range(5) if games_.count(games_[i]) > 1)
    me, game_id = email(first), games_[first]
    await task_done(seated[first], session_id)
    assert (await start(me, game_id)).status_code == 200
    for _ in range(2):
        await play_week(game_id)
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
    for step in range(4, 6):
        response = await call(me, "GET", f"{path}/steps/{step}")
        assert response.status_code == 200
        assert response.json() == {
            "debrief_id": debrief["id"],
            "step": step,
            "reveal": None,
            "chain": None,
        }
    await revealed(me, path, debrief, game_id)
    await chained(me, path, debrief, game_id)
    await reflected(me, mate, path, debrief, emitted)

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

    # The Student of the other Class game and the staff reach none of the Debrief's routes.
    for who in (stranger, ASSISTANT):
        for method, url in (
            ("GET", f"{path}/net-inventory"),
            ("GET", f"{path}/explanation"),
            ("POST", f"{path}/explanation"),
            ("GET", f"{path}/steps/2"),
            ("GET", f"{path}/steps/3"),
            ("GET", f"{path}/reflection"),
            ("POST", f"{path}/reflection/feelings"),
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
        f"{path}/reflection",
    ):
        refused(await call(me, "GET", url), "debrief_not_open")
    late = await call(me, "POST", f"{path}/reflection/feelings", json={"text": "x"})
    refused(late, "debrief_not_open")
