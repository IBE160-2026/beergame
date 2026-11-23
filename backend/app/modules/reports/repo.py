"""Reads and writes of `makeup_games` (Story 13.4) and of the Student report's requests and
snapshots (Story 13.7), in the caller's session."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.models import makeup_games, report_requests, report_snapshots


@dataclass(frozen=True)
class Makeup:
    """A Student's Oppfølgingsspill: its row id, its Game, who gave it (None once that User is
    deleted) and when."""

    id: uuid.UUID
    game_id: uuid.UUID
    given_by: uuid.UUID | None
    given_at: datetime


async def makeup_of(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> Makeup | None:
    """The Student's Oppfølgingsspill in the Class session, or None."""
    row = (
        await session.execute(
            select(
                makeup_games.c.id,
                makeup_games.c.game_id,
                makeup_games.c.given_by,
                makeup_games.c.given_at,
            ).where(
                makeup_games.c.user_id == user_id,
                makeup_games.c.class_session_id == class_session_id,
            )
        )
    ).first()
    return None if row is None else Makeup(*row)


async def makeup_game_of(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> uuid.UUID | None:
    """The id of the Student's Oppfølgingsspill Game in the Class session, or None."""
    found = await makeup_of(session, user_id, class_session_id)
    return None if found is None else found.game_id


async def insert_makeup(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    game_id: uuid.UUID,
    given_by: uuid.UUID,
    given_at: datetime,
) -> uuid.UUID | None:
    """Name `game_id` the Student's Oppfølgingsspill in the Class session and answer the row id.
    None, storing nothing, when they have one already: a press that ran at the same moment waits
    here on the unique key until the other commits, then finds its row."""
    return await session.scalar(
        insert(makeup_games)
        .values(
            id=uuid.uuid7(),
            user_id=user_id,
            class_session_id=class_session_id,
            game_id=game_id,
            given_by=given_by,
            given_at=given_at,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "class_session_id"])
        .returning(makeup_games.c.id)
    )


# The Student report (Story 13.7): its requests and snapshots.


@dataclass(frozen=True)
class ReportRequest:
    """A press of «Lag Studentrapport»: for whom, which variant, and how its render ended."""

    id: uuid.UUID
    class_session_id: uuid.UUID
    user_id: uuid.UUID
    requested_by: uuid.UUID | None
    variant: str
    status: str
    requested_at: datetime
    finished_at: datetime | None
    object_path: str | None
    failure: str | None


def _request_columns():
    return (
        report_requests.c.id,
        report_requests.c.class_session_id,
        report_requests.c.user_id,
        report_requests.c.requested_by,
        report_requests.c.variant,
        report_requests.c.status,
        report_requests.c.requested_at,
        report_requests.c.finished_at,
        report_requests.c.object_path,
        report_requests.c.failure,
    )


async def report_request(
    session: AsyncSession, request_id: uuid.UUID, *, lock: bool = False
) -> ReportRequest | None:
    query = select(*_request_columns()).where(report_requests.c.id == request_id)
    if lock:
        query = query.with_for_update()
    row = (await session.execute(query)).first()
    return None if row is None else ReportRequest(*row)


async def latest_report_requests(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID, variant: str
) -> tuple[ReportRequest | None, ReportRequest | None]:
    """The Student's latest request of `variant` in the Class session, and their latest ready
    one (the same when the latest is ready); each None when there is none."""
    base = (
        select(*_request_columns())
        .where(
            report_requests.c.class_session_id == class_session_id,
            report_requests.c.user_id == user_id,
            report_requests.c.variant == variant,
        )
        .order_by(report_requests.c.requested_at.desc(), report_requests.c.id.desc())
        .limit(1)
    )
    latest = (await session.execute(base)).first()
    ready = (await session.execute(base.where(report_requests.c.status == "ready"))).first()
    return (
        None if latest is None else ReportRequest(*latest),
        None if ready is None else ReportRequest(*ready),
    )


async def insert_report_request(
    session: AsyncSession,
    *,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    requested_by: uuid.UUID,
    variant: str,
    requested_at: datetime,
) -> uuid.UUID | None:
    """A new pending request, or None, storing nothing, when one is pending already (the partial
    unique index: a press at the same moment waits here until the other commits)."""
    return await session.scalar(
        insert(report_requests)
        .values(
            id=uuid.uuid7(),
            class_session_id=class_session_id,
            user_id=user_id,
            requested_by=requested_by,
            variant=variant,
            status="pending",
            requested_at=requested_at,
        )
        .on_conflict_do_nothing(
            index_elements=["class_session_id", "user_id", "variant"],
            index_where=text("status = 'pending'"),
        )
        .returning(report_requests.c.id)
    )


async def finish_report_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    object_path: str | None = None,
    failure: str | None = None,
) -> bool:
    """Mark a pending request `ready` or `failed`; False when it was no longer pending."""
    done = await session.execute(
        update(report_requests)
        .where(report_requests.c.id == request_id, report_requests.c.status == "pending")
        .values(status=status, finished_at=at, object_path=object_path, failure=failure)
    )
    return done.rowcount == 1


async def insert_snapshot(
    session: AsyncSession,
    *,
    request_id: uuid.UUID,
    token_hash: bytes,
    expires_at: datetime,
    data: dict,
) -> uuid.UUID:
    snapshot_id = uuid.uuid7()
    await session.execute(
        insert(report_snapshots).values(
            id=snapshot_id,
            request_id=request_id,
            token_hash=token_hash,
            expires_at=expires_at,
            data=data,
        )
    )
    return snapshot_id


async def use_snapshot(
    session: AsyncSession, snapshot_id: uuid.UUID, token_hash: bytes, now: datetime
) -> dict | None:
    """The snapshot's data, marking it used, only while it is unused, unexpired and the token's
    hash matches; None for every other case alike."""
    return await session.scalar(
        update(report_snapshots)
        .where(
            report_snapshots.c.id == snapshot_id,
            report_snapshots.c.token_hash == token_hash,
            report_snapshots.c.used_at.is_(None),
            report_snapshots.c.expires_at > now,
        )
        .values(used_at=now)
        .returning(report_snapshots.c.data)
    )


async def delete_snapshot(session: AsyncSession, snapshot_id: uuid.UUID) -> None:
    await session.execute(delete(report_snapshots).where(report_snapshots.c.id == snapshot_id))


async def delete_expired_snapshots(session: AsyncSession, now: datetime) -> int:
    """Snapshots a crashed render left behind, once expired."""
    done = await session.execute(
        delete(report_snapshots).where(report_snapshots.c.expires_at <= now)
    )
    return done.rowcount


async def snapshot_used(session: AsyncSession, snapshot_id: uuid.UUID) -> bool:
    """Whether the print route read the snapshot."""
    used = await session.scalar(
        select(report_snapshots.c.used_at).where(report_snapshots.c.id == snapshot_id)
    )
    return used is not None


async def release_older_objects(session: AsyncSession, request: ReportRequest) -> list[str]:
    """The object paths of the Student's earlier ready requests of the same variant, now cleared
    from their rows: the caller deletes the objects once this commits."""
    earlier = (
        report_requests.c.class_session_id == request.class_session_id,
        report_requests.c.user_id == request.user_id,
        report_requests.c.variant == request.variant,
        report_requests.c.id != request.id,
        report_requests.c.object_path.is_not(None),
    )
    paths = list(
        (
            await session.execute(
                select(report_requests.c.object_path).where(*earlier).with_for_update()
            )
        ).scalars()
    )
    # RETURNING would give the new (empty) values: the paths are read first, under the lock.
    await session.execute(update(report_requests).where(*earlier).values(object_path=None))
    return [path for path in paths if path]
