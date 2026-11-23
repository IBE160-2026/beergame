"""«KI-kostnad per Klasseøkt»: the Admin sees AI cost and sets the cost limit (Story 15.6, FR-69,
FR-3, NFR-8, AD-6, AD-9, AD-22, UX-DR57).

- Every saved Class session's AI cost against its budget row, the simulation budgets apart
  (AD-22); for one Class session its cost per Game and per Europe/Oslo day. The sums are
  `ai.calls.session_costs` / `session_breakdown` (unrounded, every outcome) and the row is
  `ai.budget`'s: no sum here (AD-6).
- Per Game is shown against USD 0.10 and per Student against USD 0.50 (C-3).
- The Admin sets the limit through `ai.budget.set_limit` (the reserve, the spend and
  `players_exhausted_at` stay), audited as `ai_budget.limit_set`.
- The reserve is used up when the players' limit is reached and what is left of the limit cannot
  pay the dearest call the reserve has paid so far (nothing stored). Then the Debrief runs from
  code and the AI assessment waits for the Admin: raising the limit also calls
  `assessment.service.resume_for_session`, and «Stopp KI-vurderingen» calls `stop_for_session`
  (Story 12.4; both audit themselves). Neither command is built here.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget, calls, config
from app.modules.assessment import service as assessment
from app.modules.games import service as games
from app.modules.ops.ai_models import Refused
from app.modules.ops.ai_schemas import (
    BudgetOut,
    CostListOut,
    DayCostOut,
    EvaluationCostOut,
    GameCostOut,
    SessionCostDetailOut,
    SessionCostOut,
)
from app.modules.sessions import service as sessions
from app.platform import audit, authz
from app.platform.db import get_sessionmaker

GAME_TARGET_USD = Decimal("0.10")
"""The AI cost one Game should stay under (C-3)."""
STUDENT_TARGET_USD = Decimal("0.50")
"""The AI cost one Student should stay under (C-3)."""
LIMIT_ACTION = "ai_budget.limit_set"
RESERVE_NOT_USED_UP = "reserve_not_used_up"

_EIGHT = Decimal("1e-8")


def money(value: Decimal) -> str:
    """A USD amount with the column's eight places."""
    return format(value.quantize(_EIGHT), "f")


def _budget_out(found: budget.Budget) -> BudgetOut:
    return BudgetOut(
        limit_usd=money(found.limit),
        reserve_usd=money(found.reserve),
        spent_usd=money(found.spent),
        reserved_usd=money(found.reserved),
        players_exhausted_at=found.players_exhausted_at,
    )


def reserve_used_up(found: budget.Budget | None, dearest: Decimal | None) -> bool:
    """The players' limit is reached and what is left cannot pay the next reserve call: nothing
    is left, or less than the dearest one the reserve has paid so far."""
    if found is None or found.players_exhausted_at is None:
        return False
    left = found.limit - found.spent - found.reserved
    return left <= 0 or (dearest is not None and left < dearest)


def _per(amount: Decimal, count: int) -> Decimal | None:
    return None if count <= 0 else amount / count


def _session_out(
    item: sessions.ModelSetting,
    found: budget.Budget | None,
    cost: calls.SessionCost | None,
    class_games: list[games.ClassGame],
) -> SessionCostOut:
    total = cost.usd if cost else Decimal(0)
    # Only the Class games: a Lecturer's test Game is no Game of the Class session's count.
    class_ids = {game.id for game in class_games}
    game_usd = sum(
        (usd for game_id, usd in (cost.games.items() if cost else ()) if game_id in class_ids),
        Decimal(0),
    )
    students = {
        seat.user_id
        for game in class_games
        for seat in game.seats
        if seat.user_id is not None and seat.occupant_kind == "student"
    }
    per_game = _per(game_usd, len(class_games))
    per_student = _per(total, len(students))
    return SessionCostOut(
        class_session_id=item.id,
        label=f"{item.class_name} · Klasseøkt {item.number}",
        institution_name=item.institution_name,
        ai_mode=item.ai_mode,
        budget=None if found is None else _budget_out(found),
        total_usd=money(total),
        calls=cost.calls if cost else 0,
        games=len(class_games),
        students=len(students),
        per_game_usd=None if per_game is None else money(per_game),
        per_student_usd=None if per_student is None else money(per_student),
        per_game_above=per_game is not None and per_game > GAME_TARGET_USD,
        per_student_above=per_student is not None and per_student > STUDENT_TARGET_USD,
    )


async def list_costs(*, now: datetime) -> CostListOut:
    """Every saved Class session's AI cost against its budget, newest first, and the evaluation
    budgets apart."""
    async with get_sessionmaker().begin() as s:
        items = await sessions.model_settings(s, now=now)
        ids = [item.id for item in items]
        states = await budget.class_session_states(ids, session=s)
        costs = await calls.session_costs(ids, session=s)
        by_session = await games.class_games_of(s, ids)
        evaluations = await budget.evaluation_states(session=s)
    labels = await config.config_labels([found.scope.id for found in evaluations])
    return CostListOut(
        game_target_usd=money(GAME_TARGET_USD),
        student_target_usd=money(STUDENT_TARGET_USD),
        sessions=[
            _session_out(item, states.get(item.id), costs.get(item.id), by_session.get(item.id, []))
            for item in items
        ],
        evaluations=[
            EvaluationCostOut(
                model_config_id=found.scope.id,
                model_name=labels.get(found.scope.id, str(found.scope.id)),
                budget=_budget_out(found),
            )
            for found in evaluations
        ],
    )


async def _detail(
    s: AsyncSession, class_session_id: uuid.UUID, *, now: datetime
) -> SessionCostDetailOut | None:
    found = await sessions.model_settings(s, [class_session_id], now=now)
    if not found:
        return None
    [item] = found
    states = await budget.class_session_states([class_session_id], session=s)
    state = states.get(class_session_id)
    cost = (await calls.session_costs([class_session_id], session=s)).get(class_session_id)
    breakdown = await calls.session_breakdown(class_session_id, session=s)
    class_games = await games.class_games(s, class_session_id)
    switch = await assessment.switch_of(s, class_session_id)
    numbers = {game.id: game.number for game in class_games}
    used_up = reserve_used_up(state, breakdown.dearest_reserve_call)
    base = _session_out(item, state, cost, class_games)
    return SessionCostDetailOut(
        **base.model_dump(),
        per_game=[
            GameCostOut(
                game_id=line.game_id,
                number=numbers.get(line.game_id) if line.game_id else None,
                usd=money(line.usd),
                calls=line.calls,
                above=line.game_id is not None and line.usd > GAME_TARGET_USD,
            )
            for line in breakdown.games
        ],
        per_day=[
            DayCostOut(day=line.day, usd=money(line.usd), calls=line.calls)
            for line in breakdown.days
        ],
        reserve_used_up=used_up,
        assessment_stopped_at=switch.stopped_at,
        can_stop=used_up and switch.stopped_at is None,
    )


async def session_cost(
    class_session_id: uuid.UUID, *, now: datetime
) -> SessionCostDetailOut | None:
    """One Class session's cost per Game and per day with its cost-limit state; None when there
    is no such Class session."""
    async with get_sessionmaker().begin() as s:
        return await _detail(s, class_session_id, now=now)


async def set_limit(
    actor: authz.Principal, class_session_id: uuid.UUID, limit: Decimal, *, now: datetime
) -> SessionCostDetailOut | None:
    """Set the Class session's cost limit (FR-69), audited as `ai_budget.limit_set`. A raise
    while the AI assessment waits (the reserve used up, or stopped) also resumes it, when the new
    limit leaves room for the next assessment call. None when
    there is no such Class session. Raises `Refused` (422 `limit_below_spent`,
    `reserve_above_limit`, `amount_invalid`)."""
    scope = budget.BudgetScope.class_session(class_session_id)
    async with get_sessionmaker().begin() as s:
        if not await sessions.model_settings(s, [class_session_id], now=now):
            return None
        try:
            # Under the budget row's lock: the state before the change is read there, so a
            # concurrent change cannot make the resume decision stale.
            change = await budget.set_limit(scope, limit, session=s)
        except budget.BudgetRefused as refused:
            raise Refused(422, refused.code, refused.message, {"limit_usd": refused.code}) from None
        dearest = (await calls.session_breakdown(class_session_id, session=s)).dearest_reserve_call
        stopped = (await assessment.switch_of(s, class_session_id)).stopped_at is not None
        waiting = reserve_used_up(change.previous, dearest) or stopped
        # The assessment restarts only when the raise leaves room for its next call.
        room = not reserve_used_up(change.budget, dearest)
        if change.changed:
            previous = change.previous_limit
            await audit.record(
                s,
                actor.id,
                LIMIT_ACTION,
                {"class_session_id": class_session_id},
                {
                    "limit_usd": money(change.budget.limit),
                    "previous_limit_usd": None if previous is None else money(previous),
                },
                now,
            )
            raised = previous is None or change.budget.limit > previous
            if raised and waiting and room:
                await assessment.resume_for_session(class_session_id, actor.id, now=now, within=s)
    return await session_cost(class_session_id, now=now)


async def stop_assessment(
    actor: authz.Principal, class_session_id: uuid.UUID, *, now: datetime
) -> SessionCostDetailOut | None:
    """Stop the Class session's AI assessment while its reserve is used up
    (`assessment.service.stop_for_session`, which audits it). None when there is no such Class
    session; raises `Refused` (409 `reserve_not_used_up`)."""
    async with get_sessionmaker().begin() as s:
        found = await _detail(s, class_session_id, now=now)
        if found is None:
            return None
        if not found.reserve_used_up:
            raise Refused(409, RESERVE_NOT_USED_UP, "The reserve is not used up.")
        await assessment.stop_for_session(class_session_id, actor.id, now=now, within=s)
    return await session_cost(class_session_id, now=now)
