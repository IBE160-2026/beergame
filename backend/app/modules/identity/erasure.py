"""Erasing a User (Story 15.2, FR-76, FR-2, FR-3, AD-14, AD-15).

`erase_user` is the one shared routine: the Admin's deletion on the Institution's instruction
(`delete_user`) runs it now, and retention (Story 15.3, `ops.retention`) is to run it too. The User
is anonymised in place: the `users` row stays, under the same id, as the anonymous User every
Seat, occupancy row, `seat_week` and Decision log row keeps pointing to, so no game row changes
and other Students' Games still render with the Seat shown by Role (AD-15, AD-4).

`identity` imports no feature module, so the modules that own the rest register their part at
import, as they register revoke blockers:

1. preparations (`register_erasure_preparation`) run first, each in its own transactions: `games`
   hands every Seat the User holds in a running Game to an AI player (AD-2, AD-5);
2. aggregate writers (`register_aggregate_writer`) run first in the erasure's transaction. None is
   registered yet: `reports.service.write_aggregate` (Epic 14) is to register here;
3. the identity tables are anonymised, then every registered erasure step
   (`register_erasure_step`) deletes what its module holds of the User: free text, the AI
   answers that quote it, the scrubbed bodies of the AI calls. Steps 2–3 and the audit row are one
   transaction, so a failure part-way leaves nothing half done;
4. object erasers (`register_object_eraser`) run after the commit. None is registered yet: the
   `reports` bucket of `platform/storage` (Epic 13) is to register the removal of the User's
   report PDFs and every ZIP of their Class sessions here.

Every part is idempotent: running the routine again on an erased User repeats each step with
nothing left to do, and writes no second audit row. The personal-data registry
(`identity.personal_data`) names the handling of every table; its test keeps it and these steps
from drifting apart.
"""

import re
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import repo
from app.modules.identity.personal_data import REGISTRY
from app.modules.identity.schemas import ROLES_KEEP_ONE_ACTIVE, AccountRole
from app.platform import audit, events
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

_WORD = re.compile(r"[^\W\d_]{3,}")

ErasurePreparation = Callable[[uuid.UUID, datetime], Awaitable[None]]
"""`(user_id, now)`: work that needs its own transactions before the erasure's (a Takeover)."""
AggregateWriter = Callable[[AsyncSession, uuid.UUID], Awaitable[None]]
"""`(session, user_id)`: write the anonymised aggregates the User's data feeds, in the erasure's
transaction, before anything is deleted."""
ErasureStep = Callable[[AsyncSession, uuid.UUID], Awaitable[None]]
"""`(session, user_id)`: delete or clear what the module holds of the User, in the erasure's
transaction. Must be idempotent."""
ObjectEraser = Callable[[uuid.UUID], Awaitable[None]]
"""`(user_id)`: delete stored objects of the User after the commit. Must be idempotent."""


@dataclass(frozen=True)
class Step:
    name: str
    tables: frozenset[str]
    """The tables whose `delete` or `clear` handling this step carries out (`personal_data`)."""
    run: ErasureStep


_PREPARATIONS: dict[str, tuple[frozenset[str], ErasurePreparation]] = {}
_AGGREGATES: dict[str, AggregateWriter] = {}
_STEPS: dict[str, Step] = {}
_OBJECTS: dict[str, ObjectEraser] = {}


def register_erasure_preparation(
    name: str, tables: set[str] | frozenset[str], preparation: ErasurePreparation
) -> None:
    """Called at import by a module that must act before the erasure's transaction; `tables` are
    those whose `delete` handling it carries out (`personal_data`)."""
    _PREPARATIONS[name] = (frozenset(tables), preparation)


def register_aggregate_writer(name: str, writer: AggregateWriter) -> None:
    """Called at import by `reports` (Epic 14): it runs first in the erasure's transaction."""
    _AGGREGATES[name] = writer


def register_erasure_step(name: str, tables: set[str] | frozenset[str], run: ErasureStep) -> None:
    """Called at import by the module that owns `tables`."""
    _STEPS[name] = Step(name, frozenset(tables), run)


def register_object_eraser(name: str, eraser: ObjectEraser) -> None:
    """Called at import by the module that stores objects naming the User (Epic 13)."""
    _OBJECTS[name] = eraser


def covered_tables() -> dict[str, set[str]]:
    """Each table a registered part erases, with the parts that name it, for the registry
    test: the identity step, the preparations and the steps."""
    found: dict[str, set[str]] = {table: {IDENTITY_STEP} for table in IDENTITY_TABLES}
    for name, (tables, _) in _PREPARATIONS.items():
        for table in tables:
            found.setdefault(table, set()).add(name)
    for step in _STEPS.values():
        for table in step.tables:
            found.setdefault(table, set()).add(step.name)
    return found


ANONYMOUS_NAME = repo.ERASED_NAME
anonymous_email = repo.erased_email


IDENTITY_STEP = "identity"
IDENTITY_TABLES = frozenset(
    {
        "users",
        "user_roles",
        "password_resets",
        "invitations",
        "roster_entries",
        "roster_upload_rows",
        "access_requests",
    }
)

KEEP_ONE_ACTIVE = ROLES_KEEP_ONE_ACTIVE
"""The roles one active User always holds (`schemas.ROLES_KEEP_ONE_ACTIVE`)."""

USER_DELETED = "user.deleted"
"""The audit action of an erasure (FR-3): actor, time and the User's id, never a name."""


async def _erase_identity(s: AsyncSession, user_id: uuid.UUID) -> None:
    """Anonymise the User in the `identity` tables: every row that holds the address goes, and the
    `users` row keeps only its id. The address locks first, as a send and an account creation
    take them, so no Invitation to the address is issued during the erasure."""
    user = await repo.user_by_id(s, user_id)
    if user is None:
        return
    address = user["email"]
    await repo.lock_user_address(s, address)
    for role in sorted(r.value for r in AccountRole):
        await repo.lock_invitation_address(s, address, role)
    await repo.erase_user_rows(s, user_id, address)


ERASED_HANDLINGS = frozenset({"anonymise", "delete", "clear"})


def _check_complete() -> None:
    """Every table the registry says is erased has a registered part, or nothing is erased."""
    covered = covered_tables()
    missing = sorted(
        name
        for name, entry in REGISTRY.items()
        if entry.handling in ERASED_HANDLINGS and not covered.get(name)
    )
    if missing:
        raise RuntimeError(f"no erasure part is registered for {', '.join(missing)}")


class _Refused(Exception):
    def __init__(self, refusal: Any) -> None:
        self.refusal = refusal


Guard = Callable[[AsyncSession, RowMapping], Awaitable[Any]]
"""Asked under the User lock in the erasure's transaction: None to go on, or a refusal that
`erase_user` returns with nothing changed."""


async def erase_user(
    user_id: uuid.UUID,
    *,
    now: datetime,
    actor: uuid.UUID | None = None,
    change: Mapping[str, Any] | None = None,
    guard: Guard | None = None,
) -> Any:
    """The one shared erasure routine (see the module doc). Returns True when the User is erased
    (now or before), False when there is no such User, or the `guard`'s refusal. The first
    erasure writes one audit row `user.deleted` with `actor` (None: the system) and `change`.

    The `guard` is asked before the preparations and again under the locks. A refusal from the
    first ask changes nothing; one only the second ask gives (the User took a Class in between)
    leaves the Seats the preparations handed to AI players as they are, and so does a failure
    of the erasure's transaction: a repeat finishes it. Raises `RuntimeError`, changing nothing,
    when a table the registry says is erased has no registered part (a process that did not
    import every module)."""
    _check_complete()
    async with get_sessionmaker().begin() as s:
        user = await repo.user_by_id(s, user_id)
    if user is None:
        return False
    if guard is not None and user["deleted_at"] is None:
        async with get_sessionmaker().begin() as s:
            refused = await guard(s, user)
        if refused is not None:
            return refused
    for _, preparation in list(_PREPARATIONS.values()):
        await preparation(user_id, now)
    try:
        async with get_sessionmaker().begin() as s:
            if guard is not None:
                # The same role locks as a revoke and a deactivation take, before the User row.
                for role in sorted(KEEP_ONE_ACTIVE):
                    await repo.lock_role(s, role)
            user = await repo.lock_user(s, user_id)
            if user is None:
                return False
            first = user["deleted_at"] is None
            if guard is not None and first and (refused := await guard(s, user)) is not None:
                raise _Refused(refused)
            for writer in list(_AGGREGATES.values()):
                await writer(s, user_id)
            await _erase_identity(s, user_id)
            for step in list(_STEPS.values()):
                await step.run(s, user_id)
            await repo.mark_erased(s, user_id, now)
            if first:
                await audit.record(s, actor, USER_DELETED, {"user_id": user_id}, change or {}, now)
            await events.emit(s, "user", str(user_id))
    except _Refused as refused:
        return refused.refusal
    for eraser in list(_OBJECTS.values()):
        await eraser(user_id)
    log.info("user_erased", user_id=str(user_id), action=USER_DELETED, repeat=not first)
    return True


# The Admin's deletion on the Institution's instruction (Story 15.2, FR-76, FR-2, FR-3).


@dataclass(frozen=True)
class DeleteRefused:
    code: str  # not_found | last_admin | role_revoke_blocked | reference_names_user
    classes: int = 0


def _reference_names(reference: str, name: str, address: str) -> bool:
    """Whether the reference holds the User's name, a word of it, their address or its local
    part (AD-14: the audit row never names a person)."""
    folded = reference.casefold()
    local = address.split("@", 1)[0]
    terms = {name.strip(), address.strip(), local}
    # Each word of three letters or more of the name and of the address's local part, as the AI
    # gateway scrubs them (`platform/pii`): «Nordmann» alone names «Ola Nordmann».
    terms |= set(_WORD.findall(name)) | set(_WORD.findall(local))
    # Shorter terms («Al», the «a» of a@uni.no) would match almost any reference.
    return any(len(term) >= 3 and term.casefold() in folded for term in terms)


async def delete_user(
    actor: uuid.UUID,
    user_id: uuid.UUID,
    reference: str,
    *,
    now: datetime,
    blockers: list[Callable[[AsyncSession, uuid.UUID], Awaitable[int]]],
) -> bool | DeleteRefused:
    """Erase the User on the Institution's instruction, `reference` naming it (FR-76). Refused,
    with nothing changed, for oneself or the last active Admin (`last_admin`), a User who owns
    Classes (`role_revoke_blocked` with the count, the same rule as revoking the Lecturer role,
    FR-2), and a reference holding the User's name or address (`reference_names_user`). An erased
    User is erased again (the routine is idempotent) with no checks and no second audit row."""

    async def guard(s: AsyncSession, user: RowMapping) -> DeleteRefused | None:
        if _reference_names(reference, user["name"], user["email"]):
            return DeleteRefused("reference_names_user")
        if user_id == actor:
            return DeleteRefused("last_admin")
        # As a deactivation: an active holder of a role someone must keep is not the last one.
        held = KEEP_ONE_ACTIVE & set(await repo.roles_of(s, user_id))
        for role in sorted(held) if user["is_active"] else ():
            if await repo.count_active_holders(s, role, excluding=user_id) == 0:
                return DeleteRefused("last_admin")
        classes = 0
        for blocker in blockers:
            classes += max(0, await blocker(s, user_id))
        if classes > 0:
            return DeleteRefused("role_revoke_blocked", classes)
        return None

    outcome = await erase_user(
        user_id, now=now, actor=actor, change={"reference": reference}, guard=guard
    )
    if outcome is False:
        return DeleteRefused("not_found")
    if isinstance(outcome, DeleteRefused):
        log.info("user_delete_refused", user_id=str(user_id), error_code=outcome.code)
    return outcome
