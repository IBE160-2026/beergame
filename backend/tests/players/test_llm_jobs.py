"""Story 2.5: LLM Orders as `ai-orders` jobs, with the Rule-based reference Order as fallback
(FR-31, FR-32, FR-67, AD-5, AD-6, AD-9, AD-15). Jobs are driven with `run_until_idle` or by
calling the task, never with a clock."""

import uuid

import pytest

from app.ai import mock
from app.engine import GameSettings
from app.modules.games import commands, service
from app.modules.players import jobs as player_jobs
from app.modules.players import service as players
from app.platform import jobs
from app.platform.db import get_sessionmaker
from tests.ai.helpers import mock_config, stored_config
from tests.games.helpers import query, seat_student

SHORT = {"weeks": 3, "guided_weeks": 1, "demand": {"kind": "fixed", "values": [4, 8, 8]}}
"""One Guided Week, then two Weeks in which the LLM players are asked."""
FIRST = SHORT["guided_weeks"] + 1
"""The first Week an LLM player is asked in."""
ROLES = ("retailer", "wholesaler", "distributor", "factory")


async def llm_game(
    llm_roles=ROLES, *, config_id: str | None = None, students=(), url: str = "", **settings
) -> str:
    """A started SHORT Game whose `llm_roles` are LLM players, `students` Students (`url` is
    then the database) and the rest Rule-based."""
    config_id = config_id or await stored_config()
    game_id = await commands.create(
        "simulation", GameSettings(**{**SHORT, **settings}), seed=3, model_config_id=config_id
    )
    for role in llm_roles:
        await commands.assign_seat(game_id, role, "llm")
    seat_student(url, game_id, *students)
    await commands.start(game_id)
    return game_id


def rows(url: str, game_id: str) -> list[tuple]:
    """(week, role, order, decided_by, fallback, call ids, reference) per Decision log row."""
    return query(
        url,
        "SELECT w.week, s.role, w.order, w.decided_by, w.fallback, w.llm_call_ids, "
        "w.rule_based_reference_order FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s ORDER BY w.week, s.position",
        (game_id,),
    )


def waiting_jobs(url: str) -> list[tuple]:
    return query(
        url,
        "SELECT queue_name, task_name, queueing_lock, args FROM procrastinate_jobs "
        "WHERE status = 'todo' ORDER BY id",
    )


def calls(url: str) -> int:
    ((count,),) = query(url, "SELECT count(*) FROM llm_call")
    return count


def seat_id(url: str, game_id: str, role: str) -> str:
    ((value,),) = query(
        url, "SELECT id FROM seats WHERE game_id = %s AND role = %s", (game_id, role)
    )
    return str(value)


async def test_guided_weeks_ask_no_model_and_the_first_open_week_defers_one_job_per_seat(
    games_db, ai_db
):
    game_id = await llm_game()
    logged = rows(games_db, game_id)
    assert {(week, by) for week, _, _, by, *_ in logged} == {(w, "guided") for w in range(1, FIRST)}
    assert len(logged) == 4 * (FIRST - 1)
    assert calls(games_db) == 0  # FR-31: no model call in a Guided Week
    waiting = waiting_jobs(games_db)
    seats = {role: seat_id(games_db, game_id, role) for role in ROLES}
    assert waiting == [
        (
            "ai-orders",
            "players.place_llm_order",
            f"ai-orders:{game_id}:{FIRST}:{seats[role]}",
            {"game_id": game_id, "seat_id": seats[role], "week": FIRST},
        )
        for role in ROLES
    ]


async def test_a_job_is_deferred_in_the_callers_transaction_and_only_once(games_db):
    async with get_sessionmaker()() as session:
        async with session.begin():
            await jobs.defer(session, "t", queue=jobs.AI_ORDERS, queueing_lock="k", game_id="g")
            await session.rollback()
    assert waiting_jobs(games_db) == []
    async with get_sessionmaker().begin() as session:
        first = await jobs.defer(session, "t", queue=jobs.AI_ORDERS, queueing_lock="k", week=1)
        second = await jobs.defer(session, "t", queue=jobs.AI_ORDERS, queueing_lock="k", week=1)
    assert (first, second) == (True, False)  # the refusal left the transaction usable
    assert waiting_jobs(games_db) == [("ai-orders", "t", "k", {"week": 1})]
    async with get_sessionmaker().begin() as session:
        with pytest.raises(TypeError):
            await jobs.defer(session, "t", queue=jobs.AI_ORDERS, queueing_lock="x", ids=[1])


async def test_valid_answers_are_placed_as_llm_orders_with_their_call_ids(games_db, ai_db):
    game_id = await llm_game()
    await jobs.run_until_idle([jobs.AI_ORDERS])
    game = await service.get_game(game_id)
    assert game.lifecycle == "finished"
    played = [row for row in rows(games_db, game_id) if row[0] >= FIRST]
    assert len(played) == 8
    for week, role, order, by, fallback, ids, reference in played:
        assert (by, fallback, len(ids)) == ("llm", "none", 1)
        assert order == reference  # the mock answers the reference Order
        ((caller, purpose),) = query(
            games_db, "SELECT caller_ref, purpose FROM llm_call WHERE id = %s", (ids[0],)
        )
        assert caller == {
            "game": game_id,
            "seat": seat_id(games_db, game_id, role),
            "week": week,
        }
        assert purpose == "player_order"
    assert calls(games_db) == 8
    assert (await service.verify_finished(game_id)).ok
    log = await service.decision_log(game_id)
    assert [len(row.llm_call_ids) for row in log if row.week >= FIRST] == [1] * 8
    assert waiting_jobs(games_db) == []


async def test_invalid_answers_are_retried_inside_one_gateway_call(games_db, ai_db):
    game_id = await llm_game(("wholesaler",))
    with mock.script(mock.INVALID, mock.INVALID):
        await jobs.run_until_idle([jobs.AI_ORDERS])
    wholesaler = [
        row for row in rows(games_db, game_id) if row[1] == "wholesaler" and row[0] >= FIRST
    ]
    assert [(by, fallback, len(ids)) for _, _, _, by, fallback, ids, _ in wholesaler] == [
        ("llm", "none", 3),
        ("llm", "none", 1),
    ]


async def test_a_typed_failure_places_the_reference_order_marked_with_its_type(games_db, ai_db):
    game_id = await llm_game(("distributor",))
    with mock.outage():
        await jobs.run_until_idle([jobs.AI_ORDERS])
    assert (await service.get_game(game_id)).lifecycle == "finished"
    distributor = [row for row in rows(games_db, game_id) if row[1] == "distributor"]
    for week, _, order, by, fallback, ids, reference in distributor[FIRST - 1 :]:
        assert (order, by, fallback, len(ids)) == (reference, "rule_based", "provider_error", 6)
        outcomes = query(games_db, "SELECT outcome FROM llm_call WHERE id = ANY(%s)", (ids,))
        assert outcomes == [("provider_error",)] * 6, week
    # The occupancy stays `llm`: the model is asked again every Week (FR-32).
    occupancy = query(
        games_db,
        "SELECT o.occupant_kind FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND s.role = 'distributor'",
        (game_id,),
    )
    assert occupancy == [("llm",)]
    assert calls(games_db) == 2 * 6


@pytest.mark.parametrize(
    ("limit", "steps", "fallback", "attempts"),
    [
        ("10", (mock.INVALID,) * 6, "invalid_output", 6),
        ("0", (), "budget_exhausted", 0),
    ],
)
async def test_each_failure_type_is_the_fallback_mark(
    games_db, ai_db, limit, steps, fallback, attempts
):
    """FR-32: the stored mark is the gateway's failure type, with the ids of its attempts (none
    when the budget allows no attempt)."""
    game_id = await llm_game(("retailer",), config_id=await stored_config(limit=limit))
    seat = seat_id(games_db, game_id, "retailer")
    with mock.script(*steps):
        await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)
    ((_, _, order, by, mark, ids, reference),) = [
        row for row in rows(games_db, game_id) if row[1] == "retailer" and row[0] == FIRST
    ]
    assert (order, by, mark, len(ids)) == (reference, "rule_based", fallback, attempts)


async def test_any_other_failure_of_the_call_still_places_the_fallback(
    games_db, ai_db, monkeypatch
):
    from app.ai import gateway

    async def broken(*_, **__):
        raise RuntimeError("database gone")

    game_id = await llm_game(("retailer",))
    monkeypatch.setattr(gateway, "run", broken)
    seat = seat_id(games_db, game_id, "retailer")
    await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)
    ((by, mark),) = [(r[3], r[4]) for r in rows(games_db, game_id) if r[1] == "retailer"][-1:]
    assert (by, mark) == ("rule_based", "provider_error")


async def test_a_job_whose_turn_no_longer_waits_asks_no_model(games_db, ai_db):
    """A late job (its Week moved on), a Guided Week's job and a job for a Seat no LLM player
    holds end at once, without a call."""
    game_id = await llm_game(("retailer",))
    retailer = seat_id(games_db, game_id, "retailer")
    await jobs.run_until_idle([jobs.AI_ORDERS])  # the Game finishes
    late = await llm_game(("retailer",))
    await player_jobs.place_llm_order(game_id=late, seat_id=retailer, week=FIRST)  # foreign Seat
    before = calls(games_db)
    for game, seat, week in [
        (game_id, retailer, FIRST),  # finished Game
        (late, seat_id(games_db, late, "retailer"), 1),  # a Guided Week, long gone
        (late, seat_id(games_db, late, "wholesaler"), FIRST),  # Rule-based Seat
        (late, seat_id(games_db, late, "retailer"), FIRST + 1),  # not open yet
    ]:
        await player_jobs.place_llm_order(game_id=game, seat_id=seat, week=week)
    assert calls(games_db) == before
    assert [r for r in rows(games_db, late) if r[1] == "retailer" and r[0] >= FIRST] == []


async def test_a_call_the_gateway_cannot_prepare_still_places_the_fallback(games_db, ai_db):
    from app.ai import config

    no_prompt = await config.add(config.parse(mock_config()))  # names no player_order prompt
    game_id = await llm_game(("factory",), config_id=str(no_prompt.id))
    await jobs.run_until_idle([jobs.AI_ORDERS])
    factory = [row for row in rows(games_db, game_id) if row[1] == "factory" and row[0] >= FIRST]
    assert [(by, fallback, ids) for _, _, _, by, fallback, ids, _ in factory] == [
        ("rule_based", "provider_error", [])
    ] * 2
    assert (await service.get_game(game_id)).lifecycle == "finished"


async def test_a_job_delivered_twice_places_one_order_and_asks_once(games_db, ai_db):
    game_id = await llm_game(("retailer", "factory"))
    seat = seat_id(games_db, game_id, "retailer")
    await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)
    await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)
    retailer = [row for row in rows(games_db, game_id) if row[1] == "retailer" and row[0] == FIRST]
    assert len(retailer) == 1
    assert calls(games_db) == 1


async def test_a_job_that_loses_the_race_gets_order_exists_and_ends_cleanly(
    games_db, ai_db, monkeypatch
):
    game_id = await llm_game(("retailer", "factory"))
    seat = seat_id(games_db, game_id, "retailer")
    stale = await service.llm_turn(game_id, seat, FIRST)
    await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)

    async def still_waiting(*_):
        return stale  # read before the first job placed its Order

    monkeypatch.setattr(service, "llm_turn", still_waiting)
    await player_jobs.place_llm_order(game_id=game_id, seat_id=seat, week=FIRST)  # no error
    retailer = [row for row in rows(games_db, game_id) if row[1] == "retailer" and row[0] == FIRST]
    assert len(retailer) == 1
    assert calls(games_db) == 2  # the late job asked, then `place_order` refused it


async def test_ensure_order_defers_nothing_for_a_seat_that_has_ordered(games_db, ai_db):
    game_id = await llm_game(("retailer",))
    async with get_sessionmaker().begin() as session:
        game = service.OpenGame(session=session, game_id=uuid.UUID(game_id))
        await players.ensure_order(game, seat_id(games_db, game_id, "wholesaler"))
        await players.ensure_order(game, seat_id(games_db, game_id, "retailer"))
    assert len(waiting_jobs(games_db)) == 1  # the waiting job's key refused a second one


UNUSED_ID = "0198d1c8-0000-7000-8000-000000000000"


REFUSALS = [
    ("wholesaler", None, "llm", "none", [UNUSED_ID], "decided_by_invalid"),
    ("retailer", None, "llm", "none", [], "llm_call_ids_invalid"),
    ("retailer", None, "rule_based", "none", [], "fallback_invalid"),
    ("wholesaler", None, "rule_based", "timeout", [], "fallback_invalid"),
    ("retailer", 99, "rule_based", "timeout", [], "fallback_invalid"),
    ("retailer", None, "llm", "timeout", [UNUSED_ID], "fallback_invalid"),
    ("retailer", None, "llm", "late", [], "fallback_invalid"),
    ("wholesaler", None, "student", "none", [UNUSED_ID], "llm_call_ids_invalid"),
    ("retailer", None, "llm", "none", ["nope"], "llm_call_ids_invalid"),
    ("retailer", None, "llm", "none", UNUSED_ID, "llm_call_ids_invalid"),
]
"""(Role, Order or None for the reference, decided_by, fallback, call ids, refusal code)."""


async def test_place_order_refuses_llm_marks_that_do_not_fit_the_seat(games_db, ai_db):
    """A Student holds the wholesaler Seat, an LLM player the retailer Seat; Week 1 is open. A
    refusal writes nothing, so one Game serves every case."""
    game_id = await llm_game(("retailer",), students=("wholesaler",), url=games_db, guided_weeks=0)
    for role, order, by, fallback, ids, code in REFUSALS:
        turn = await service.open_turn(game_id, role, 1)
        with pytest.raises(commands.CommandError) as refused:
            await commands.place_order(
                game_id,
                role,
                1,
                turn.rule_based_reference_order if order is None else order,
                by,
                fallback=fallback,
                llm_call_ids=ids,
            )
        assert (refused.value.code, refused.value.status) == (code, 422), (role, by, fallback)
    assert [row[1] for row in rows(games_db, game_id)] == ["distributor", "factory"]
