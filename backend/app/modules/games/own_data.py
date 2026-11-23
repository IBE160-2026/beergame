"""The Student's own `games` rows for «Mine data» (Story 15.1, FR-75, AD-12): their Orders (the
Decision log rows of the weeks they held a Seat), the Seats they held, their believability
ratings, time proposals and acceptances and queued Reclaims. Through `authz.own_seat` and the
caller's own id only: another Seat appears by Role at most, never by its occupant."""

import uuid
from collections import defaultdict

from sqlalchemy import select

from app.modules.games.models import (
    believability_ratings,
    games,
    seat_occupancy,
    seat_reclaims,
    seat_weeks,
    seats,
    time_acceptances,
    time_proposals,
)
from app.platform import authz
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


def _spans(rows: list, user_id: uuid.UUID) -> dict[uuid.UUID, list[tuple[int, int | None]]]:
    """Per Seat, the week spans `[from, to)` in which its occupancy named the User."""
    by_seat: dict[uuid.UUID, list] = defaultdict(list)
    for row in rows:
        by_seat[row["seat_id"]].append(row)
    spans: dict[uuid.UUID, list[tuple[int, int | None]]] = {}
    for seat_id, items in by_seat.items():
        items.sort(key=lambda r: (r["from_week"], r["id"]))
        for i, row in enumerate(items):
            if row["user_id"] != user_id:
                continue
            # Held until the next occupancy row; a row replaced within its week spans nothing.
            nxt = items[i + 1]["from_week"] if i + 1 < len(items) else None
            if nxt is None or nxt > row["from_week"]:
                spans.setdefault(seat_id, []).append((row["from_week"], nxt))
    return spans


def _held(spans: list[tuple[int, int | None]], week: int) -> bool:
    return any(start <= week and (end is None or week < end) for start, end in spans)


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    async with get_sessionmaker()() as s:
        own_games = authz.own_seat(user_id)
        seat_rows = (
            (
                await s.execute(
                    select(
                        seats.c.id,
                        seats.c.role,
                        seats.c.game_id,
                        games.c.game_number,
                        games.c.purpose,
                        games.c.class_session_id,
                    )
                    .join(games, games.c.id == seats.c.game_id)
                    .where(seats.c.game_id.in_(own_games))
                )
            )
            .mappings()
            .all()
        )
        seat_of = {row["id"]: row for row in seat_rows}
        occupancy = (
            (
                await s.execute(
                    select(seat_occupancy).where(seat_occupancy.c.seat_id.in_(list(seat_of)))
                )
            )
            .mappings()
            .all()
            if seat_of
            else []
        )
        spans = _spans(list(occupancy), user_id)
        weeks = (
            (
                await s.execute(
                    select(
                        seat_weeks.c.seat_id,
                        seat_weeks.c.week,
                        seat_weeks.c.order,
                        seat_weeks.c.decided_by,
                        seat_weeks.c.ordered_at,
                    )
                    .where(seat_weeks.c.seat_id.in_(list(spans)))
                    .order_by(seat_weeks.c.seat_id, seat_weeks.c.week)
                )
            )
            .mappings()
            .all()
            if spans
            else []
        )
        ratings = (
            (
                await s.execute(
                    select(believability_ratings, games.c.game_number, games.c.class_session_id)
                    .join(games, games.c.id == believability_ratings.c.game_id)
                    .where(believability_ratings.c.user_id == user_id)
                )
            )
            .mappings()
            .all()
        )
        proposals = (
            (
                await s.execute(
                    select(time_proposals, games.c.game_number, games.c.class_session_id)
                    .join(games, games.c.id == time_proposals.c.game_id)
                    .where(time_proposals.c.proposed_by == user_id)
                )
            )
            .mappings()
            .all()
        )
        accepted = (
            (
                await s.execute(
                    select(
                        time_acceptances.c.accepted_at,
                        time_proposals.c.at,
                        games.c.game_number,
                        games.c.class_session_id,
                    )
                    .join(time_proposals, time_proposals.c.id == time_acceptances.c.proposal_id)
                    .join(games, games.c.id == time_proposals.c.game_id)
                    .where(time_acceptances.c.user_id == user_id)
                )
            )
            .mappings()
            .all()
        )
        reclaims = (
            (
                await s.execute(
                    select(seat_reclaims.c.seat_id, seat_reclaims.c.requested_at).where(
                        seat_reclaims.c.user_id == user_id
                    )
                )
            )
            .mappings()
            .all()
        )

    weeks = sorted(weeks, key=lambda w: (seat_of[w["seat_id"]]["game_number"] or 0, w["week"]))
    orders = [
        record(
            "week",
            [
                ("game_number", "number", seat_of[w["seat_id"]]["game_number"]),
                ("purpose", "code", seat_of[w["seat_id"]]["purpose"]),
                ("role", "code", seat_of[w["seat_id"]]["role"]),
                ("week", "number", w["week"]),
                ("order", "number", w["order"]),
                ("decided_by", "code", w["decided_by"]),
            ],
            class_session_id=seat_of[w["seat_id"]]["class_session_id"],
            at=w["ordered_at"],
        )
        for w in weeks
        if _held(spans[w["seat_id"]], w["week"])
    ]
    game = [
        record(
            "seat",
            [
                ("game_number", "number", seat_of[o["seat_id"]]["game_number"]),
                ("purpose", "code", seat_of[o["seat_id"]]["purpose"]),
                ("role", "code", seat_of[o["seat_id"]]["role"]),
                ("from_week", "number", o["from_week"]),
                ("reason", "code", o["reason"]),
            ],
            class_session_id=seat_of[o["seat_id"]]["class_session_id"],
            at=o["created_at"],
        )
        for o in sorted(occupancy, key=lambda r: r["id"])
        if o["user_id"] == user_id
    ]
    game += [
        record(
            "rating",
            [
                ("game_number", "number", r["game_number"]),
                ("purpose", "code", r["purpose"]),
                ("rating", "number", r["rating"]),
            ],
            class_session_id=r["class_session_id"],
            at=r["created_at"],
        )
        for r in ratings
    ]
    game += [
        record(
            "time_proposal",
            [("game_number", "number", p["game_number"]), ("proposed_time", "datetime", p["at"])],
            class_session_id=p["class_session_id"],
            at=p["created_at"],
        )
        for p in proposals
    ]
    game += [
        record(
            "time_acceptance",
            [("game_number", "number", a["game_number"]), ("proposed_time", "datetime", a["at"])],
            class_session_id=a["class_session_id"],
            at=a["accepted_at"],
        )
        for a in accepted
    ]
    game += [
        record(
            "reclaim",
            [
                ("game_number", "number", seat_of[r["seat_id"]]["game_number"])
                if r["seat_id"] in seat_of
                else ("game_number", "number", None),
            ],
            class_session_id=seat_of[r["seat_id"]]["class_session_id"]
            if r["seat_id"] in seat_of
            else None,
            at=r["requested_at"],
        )
        for r in reclaims
    ]
    return {"orders": orders, "game": game}
