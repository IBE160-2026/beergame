"""The Admin sees AI cost and sets the cost limit (Story 15.6, FR-69, FR-3, AD-6, AD-9, AD-12,
AD-22). Through the api: each saved Class session's cost against its budget row, per Game and per
Student against the targets, the simulation budgets apart; one Class session per Game and per
Europe/Oslo day; the limit on the one budget row, audited; the reserve used up with its two
actions (raise → `resume_for_session`, stop → `stop_for_session`); the sweep's cost-limit notice
to each owner once. The database clock is never compared with the api's."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.ai import budget, calls, config, seed
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.messaging import service as messaging
from app.modules.ops import ai_cost, cost_limit, sweep
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.identity.helpers import CSRF, client
from tests.messaging.helpers import drain, mails, rows
from tests.sessions.test_dates import new_session
from tests.sessions.test_play import running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

ADMIN = "admin156@example.com"
BASE = "/api/admin/ai"
WHEN = datetime(2026, 11, 18, 22, 59, 59, tzinfo=UTC)
"""23:59:59 on 18 November in Oslo (winter time, UTC+1)."""


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN, roles=(AccountRole.admin,))


@pytest.fixture
async def model() -> uuid.UUID:
    return (await config.add(config.parse({**seed.MOCK_SPEC, "name": "kostnad"}))).id


def spend(
    model: uuid.UUID,
    scope_id: str | uuid.UUID,
    usd: str,
    at: datetime = WHEN,
    *,
    purpose: str = "player_order",
    caller: str = "{}",
    kind: str = "class_session",
) -> None:
    """One `llm_call` attempt of `usd` started at `at`."""
    execute(
        "INSERT INTO llm_call (id, purpose, scope_kind, scope_id, caller_ref, model_config_id, "
        "provider, endpoint, model_version, quantisation, effort_level, prompt_version, attempt, "
        "input_tokens, output_tokens, reasoning_tokens, cost_usd, latency_ms, outcome, request, "
        "started_at) VALUES (%s, %s, %s, %s, %s, %s, 'mock', 'mock', 'mock-v1', 'none', 'fast', "
        "1, 1, 10, 5, 0, %s, 100, 'ok', '{}', %s)",
        uuid.uuid7(),
        purpose,
        kind,
        str(scope_id),
        caller,
        model,
        usd,
        at,
    )


async def call(method: str, path: str, who: str = ADMIN, **kwargs):
    async with client() as c:
        await as_user(c, who)
        return await c.request(method, f"{BASE}{path}", headers=CSRF, **kwargs)


def audited(action: str) -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = %s "
        "ORDER BY occurred_at, id",
        action,
    )


async def scope_budget(session_id: str, limit: str, reserve: str = "1.00") -> None:
    await budget.set_budget(
        budget.BudgetScope.class_session(session_id), limit=Decimal(limit), reserve=Decimal(reserve)
    )


def spent(session_id: str, amount: str, exhausted: bool = True) -> None:
    """The budget row as Epic 2's gateway leaves it once the players' limit is reached."""
    execute(
        "UPDATE ai_budgets SET spent_usd = %s, players_exhausted_at = "
        + ("now()" if exhausted else "NULL")
        + " WHERE scope_id = %s",
        amount,
        session_id,
    )


async def test_the_cost_page_lists_each_class_session_and_the_simulations_apart(
    klass, admin, model
):
    session_id, game_id, by_role = await running(klass, students=2)
    await scope_budget(session_id, "15.00")
    spend(model, session_id, "0.12345678", caller=f'{{"game": "{game_id}"}}')
    spend(model, session_id, "0.00000001", caller=f'{{"game": "{game_id}"}}', purpose="x")
    spend(model, session_id, "1.00000000", purpose="assessment", caller='{"attempt_id": "a"}')
    spend(model, session_id, "0.50000000", WHEN + timedelta(seconds=1))  # the next Oslo day
    await budget.set_budget(budget.BudgetScope.evaluation(model), limit=Decimal("5"))
    spend(model, model, "0.25000000", kind="evaluation")

    response = await call("GET", "/costs")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["game_target_usd"], body["student_target_usd"]) == ("0.10000000", "0.50000000")
    [item] = [i for i in body["sessions"] if i["class_session_id"] == session_id]
    assert item["label"] == "class-of-1994 · Klasseøkt 1"
    assert item["budget"]["limit_usd"] == "15.00000000"
    assert item["budget"]["reserve_usd"] == "1.00000000"
    assert (item["total_usd"], item["calls"]) == ("1.62345679", 4)  # unrounded, every purpose
    assert (item["games"], item["students"]) == (1, 2)
    assert item["per_game_usd"] == "0.12345679" and item["per_game_above"] is True
    assert item["per_student_usd"] == "0.81172840" and item["per_student_above"] is True
    [evaluation] = body["evaluations"]
    assert evaluation["model_config_id"] == str(model)
    assert evaluation["budget"]["spent_usd"] == "0.00000000"  # the row, as `ai.budget` holds it
    assert evaluation["model_name"].startswith("kostnad")

    detail = (await call("GET", f"/costs/{session_id}")).json()
    games = {line["game_id"]: line for line in detail["per_game"]}
    assert games[game_id]["number"] == 1 and games[game_id]["usd"] == "0.12345679"
    assert games[game_id]["above"] is True
    assert games[None]["usd"] == "1.50000000" and games[None]["above"] is False
    assert detail["per_day"] == [
        {"day": "2026-11-18", "usd": "1.12345679", "calls": 3},
        {"day": "2026-11-19", "usd": "0.50000000", "calls": 1},
    ]
    assert detail["reserve_used_up"] is False and detail["can_stop"] is False
    assert detail["budget"]["players_exhausted_at"] is None
    assert (await call("GET", f"/costs/{uuid.uuid7()}")).status_code == 404


async def test_the_limit_is_set_on_the_one_row_and_audited(klass, admin, model):
    session_id, _, _ = await running(klass, students=1)
    await scope_budget(session_id, "15.00")
    spent(session_id, "3.00000000", exhausted=False)

    raised = await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "20"})
    assert raised.status_code == 200, raised.text
    assert raised.json()["budget"] == {
        "limit_usd": "20.00000000",
        "reserve_usd": "1.00000000",
        "spent_usd": "3.00000000",
        "reserved_usd": "0.00000000",
        "players_exhausted_at": None,
    }
    [(actor, targets, change)] = audited(ai_cost.LIMIT_ACTION)
    assert actor == admin and targets == {"class_session_id": session_id}
    assert change == {"limit_usd": "20.00000000", "previous_limit_usd": "15.00000000"}
    # The same limit again changes nothing and audits nothing.
    same = await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "20.0"})
    assert same.status_code == 200 and len(audited(ai_cost.LIMIT_ACTION)) == 1
    # Below what is spent, or below the reserve: refused, nothing changed.
    below = await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "2"})
    assert below.status_code == 422
    assert below.json()["error"]["code"] == "limit_below_spent"
    assert below.json()["error"]["fields"] == {"limit_usd": "limit_below_spent"}
    under = await budget.state(budget.BudgetScope.class_session(session_id))
    assert under is not None and under.limit == Decimal("20")
    spent(session_id, "0", exhausted=False)
    reserve = await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "0.5"})
    assert reserve.json()["error"]["code"] == "reserve_above_limit"
    # A Class session with no row gets one, with the default reserve.
    fresh = await new_session(klass)
    execute("DELETE FROM ai_budgets WHERE scope_id = %s", fresh)
    made = await call("PUT", f"/class-sessions/{fresh}/budget", json={"limit_usd": "7"})
    assert made.json()["budget"]["limit_usd"] == "7.00000000"
    assert audited(ai_cost.LIMIT_ACTION)[-1][2]["previous_limit_usd"] is None
    unknown = await call("PUT", f"/class-sessions/{uuid.uuid7()}/budget", json={"limit_usd": "7"})
    assert unknown.status_code == 404


async def test_a_used_up_reserve_offers_the_stop_and_a_raise_resumes_the_assessment(
    klass, admin, model
):
    session_id, _, _ = await running(klass, students=1)
    await scope_budget(session_id, "2.00", reserve="1.00")
    spend(model, session_id, "0.40000000", purpose="assessment")
    # The players' limit reached, 0.30 left: less than the dearest reserve call (0.40).
    spent(session_id, "1.70000000")
    stop = f"/class-sessions/{session_id}/assessment/stop"
    detail = (await call("GET", f"/costs/{session_id}")).json()
    assert detail["budget"]["players_exhausted_at"] is not None
    assert (detail["reserve_used_up"], detail["can_stop"]) == (True, True)

    stopped = await call("POST", stop)
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["assessment_stopped_at"] is not None
    assert stopped.json()["can_stop"] is False
    [(actor, targets, _)] = audited("assessment.stopped")
    assert (actor, targets) == (admin, {"class_session_id": session_id})

    raised = await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "5"})
    assert raised.status_code == 200, raised.text
    body = raised.json()
    assert body["assessment_stopped_at"] is None and body["reserve_used_up"] is False
    # Still exhausted: a raise never switches the players back (Epic 2's state stays).
    assert body["budget"]["players_exhausted_at"] is not None
    assert [a for a, _, _ in audited("assessment.resumed")] == [admin]
    assert len(audited(ai_cost.LIMIT_ACTION)) == 1

    # Not used up any more: the stop is refused, nothing changed.
    refused = await call("POST", stop)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == ai_cost.RESERVE_NOT_USED_UP
    assert len(audited("assessment.stopped")) == 1
    # A raise that is not waiting on the assessment resumes nothing.
    assert await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "6"})
    assert len(audited("assessment.resumed")) == 1


def test_nothing_left_is_used_up_without_a_reserve_call():
    scope = budget.BudgetScope.class_session(uuid.uuid7())
    now = datetime(2026, 11, 18, tzinfo=UTC)

    def row(limit: str, spent: str, exhausted: bool = True) -> budget.Budget:
        at = now if exhausted else None
        return budget.Budget(scope, Decimal(limit), Decimal("1"), Decimal(spent), at, now)

    assert ai_cost.reserve_used_up(row("2", "2"), None) is True
    assert ai_cost.reserve_used_up(row("2", "1.5"), None) is False
    assert ai_cost.reserve_used_up(row("2", "1.5"), Decimal("0.6")) is True
    assert ai_cost.reserve_used_up(row("2", "2", exhausted=False), None) is False
    assert ai_cost.reserve_used_up(None, None) is False


async def test_each_owner_is_told_once_when_the_players_limit_is_reached(klass, admin, model):
    co_owner = await make("coowner156@example.com")
    session_id, _, _ = await running(klass, students=1)
    [(class_id,)] = rows("SELECT class_id FROM class_sessions WHERE id = %s", session_id)
    execute(
        "INSERT INTO class_staff (class_id, user_id, role, added_at) "
        "VALUES (%s, %s, 'owner', now())",
        class_id,
        co_owner,
    )
    await scope_budget(session_id, "2.00")
    now = datetime(2026, 11, 19, 9, tzinfo=UTC)
    assert await cost_limit.due_sessions(now) == []  # not reached: nothing
    spent(session_id, "1.00000000")

    assert await cost_limit.due_sessions(now) == [uuid.UUID(session_id)]
    done = await sweep.run(now)
    assert done["ops.cost_limit_notice"] == 1  # one Class session acted on
    lecturer = rows("SELECT id FROM users WHERE email = %s", LECTURER)[0][0]
    found = rows("SELECT user_id, kind, dedupe_key, ref FROM notices WHERE kind = 'ai_cost_limit'")
    assert sorted(found) == sorted(
        (user, "ai_cost_limit", f"ai_cost_limit:{session_id}:{user}", uuid.UUID(session_id))
        for user in (lecturer, co_owner)
    )
    # A second sweep sends nothing.
    assert (await sweep.run(now + timedelta(minutes=1)))["ops.cost_limit_notice"] == 0
    assert await cost_limit.due_sessions(now) == []

    # The digest's mail names the Class, the Klasseøkt and the time; never to a former owner.
    assert delivery.COST_LIMIT_KIND == cost_limit.COST_LIMIT_NOTICE
    assert delivery.table()[cost_limit.COST_LIMIT_NOTICE].mode == delivery.DIGEST
    async with get_sessionmaker().begin() as s:
        context = await sessions.cost_limit_mail_context(s, lecturer, uuid.UUID(session_id), now)
        assert context is not None
        assert (context["class_name"], context["session_number"]) == ("class-of-1994", 1)
        assert context["session_path"] == f"/klasseokter/{session_id}"
        assert context["reached_at"].tzinfo == calls.OSLO
        assert await sessions.cost_limit_mail_context(s, admin, uuid.UUID(session_id), now) is None

    # The digest renders both templates the next morning (07:00 in Oslo).
    morning = datetime(2026, 11, 20, 6, tzinfo=UTC)  # at most one digest a day: the next one
    for item in await messaging.due_items(morning):
        await messaging.claim(item, morning)
    await drain(morning)
    sent = [each for each in mails() if "Kostnadsgrensen for KI" in each.text]
    assert sorted(each.to for each in sent) == sorted([LECTURER, "coowner156@example.com"])
    mail = sent[0]
    for text in (mail.text, mail.html):
        assert "Klassen class-of-1994, Klasseøkt 1" in text
        assert "byttet til regelbaserte spillere" in text
        assert f"/klasseokter/{session_id}" in text

    # The Klasseøkt shows the switch.
    async with client() as c:
        await as_user(c, LECTURER)
        shown = (await c.get(f"/api/class-sessions/{session_id}")).json()
    assert shown["cost_limit_reached_at"] is not None


async def test_only_the_admin_reads_and_sets_cost(klass, admin, model):
    session_id, _, _ = await running(klass, students=1)
    for method, path, body in (
        ("GET", "/costs", None),
        ("GET", f"/costs/{session_id}", None),
        ("PUT", f"/class-sessions/{session_id}/budget", {"limit_usd": "9"}),
        ("POST", f"/class-sessions/{session_id}/assessment/stop", None),
    ):
        response = await call(method, path, LECTURER, json=body)
        assert response.status_code == 403, (method, path)
    assert audited(ai_cost.LIMIT_ACTION) == []


async def test_a_raise_that_clears_the_used_up_reserve_resumes_and_a_small_one_waits(
    klass, admin, model
):
    session_id, _, _ = await running(klass, students=1)
    await scope_budget(session_id, "2.00", reserve="1.00")
    spend(model, session_id, "0.40000000", purpose="assessment")
    spent(session_id, "1.70000000")  # 0.30 left: below the dearest reserve call
    put = f"/class-sessions/{session_id}/budget"

    # A raise that still leaves less than the dearest call: the assessment keeps waiting.
    small = await call("PUT", put, json={"limit_usd": "2.05"})
    assert small.status_code == 200 and small.json()["reserve_used_up"] is True
    assert audited("assessment.resumed") == []
    # A raise that leaves room: resumed once, in the same transaction, without a stop first.
    enough = await call("PUT", put, json={"limit_usd": "3"})
    assert enough.json()["reserve_used_up"] is False
    assert [a for a, _, _ in audited("assessment.resumed")] == [admin]


async def test_what_is_held_counts_with_what_is_spent(klass, admin, model):
    session_id, _, _ = await running(klass, students=1)
    await scope_budget(session_id, "5.00", reserve="1.00")
    execute(
        "UPDATE ai_budgets SET spent_usd = 2, reserved_usd = 1.5, players_exhausted_at = now() "
        "WHERE scope_id = %s",
        session_id,
    )
    below = await call("PUT", f"/class-sessions/{session_id}/budget", json={"limit_usd": "3.4"})
    assert below.json()["error"]["code"] == "limit_below_spent"
    # 5 − 2 − 1.5 = 1.5 left: more than any reserve call yet (none), so not used up.
    detail = (await call("GET", f"/costs/{session_id}")).json()
    assert detail["budget"]["reserved_usd"] == "1.50000000"
    assert detail["reserve_used_up"] is False
    execute("UPDATE ai_budgets SET reserved_usd = 3 WHERE scope_id = %s", session_id)
    assert (await call("GET", f"/costs/{session_id}")).json()["reserve_used_up"] is True


async def test_a_game_named_by_game_id_counts_and_calls_naming_none_come_last(klass, admin, model):
    session_id, game_id, _ = await running(klass, students=1)
    other = str(uuid.uuid7())  # a test Game: not a Class game of the session
    spend(model, session_id, "0.30000000", purpose="assessment")
    spend(model, session_id, "0.05000000", caller=f'{{"game_id": "{game_id}"}}', purpose="replay")
    spend(model, session_id, "0.20000000", caller=f'{{"game": "{other}"}}')
    spend(model, session_id, "0.01000000", caller='{"game": "no-id"}')  # no id: no Game
    detail = (await call("GET", f"/costs/{session_id}")).json()
    last = detail["per_game"][-1]
    assert (last["number"], last["usd"]) == (None, "0.31000000")
    assert detail["per_game"][-1]["game_id"] is None
    named = {line["game_id"]: line for line in detail["per_game"] if line["game_id"]}
    assert named[game_id]["usd"] == "0.05000000" and named[other]["number"] is None
    # Per Game counts the Class games only: the test Game's 0.20 is left out.
    assert detail["per_game_usd"] == "0.05000000" and detail["per_game_above"] is False
