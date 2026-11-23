"""Student data is deleted automatically when retention ends (Story 15.3, FR-77, FR-65, FR-6, FR-3,
AD-9, AD-14, AD-27).

The Admin sets an Institution's retention period (audited); every Class session of it whose
deletion date (Story 13.9, the one rule) has not come is redated in the same transaction. The
sweep's `ops.retention` finds each Class session whose date has come and runs the one shared
routine of `identity.erase_user`, one Student per transaction, after the registered aggregate
writers: a Student with no other Class session is anonymised as `identity.delete_user` does; one
with a later Class session keeps the account and that data. Once every Class session of a Class
is deleted, the Roster addresses that never registered and their Invitations go. The api's clock
is fixed; the database clock is never compared with it."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.modules.identity import erasure
from app.modules.identity import service as identity
from app.modules.identity.schemas import AccountRole
from app.modules.ops import retention, sweep
from app.modules.sessions import service as sessions
from tests.classes.test_classes import LECTURER, OTHER, as_user, institution, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW
from tests.identity.helpers import CSRF, client
from tests.identity.test_user_delete import delete
from tests.individual_test.test_extension import extend
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, START, STUDENT, TEST, new_session, save, student_of
from tests.sessions.test_lab_hours import two_students
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "klass"]

DAY = timedelta(days=1)
PAST = date(2026, 11, 1)
"""A deletion date before `NOW` (2026-11-19)."""
DELETION = date(2027, 6, 18)
"""`TEST` (2026-12-18 in Oslo) plus the six-month placeholder."""


ADMIN_EMAIL = "admin153@example.com"


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN_EMAIL, roles=(AccountRole.admin,))


@pytest.fixture
def no_aggregates(monkeypatch):
    """No aggregate writer is registered on this branch (Story 14.3 adds `write_aggregate`); the
    tests that need one register their own."""
    monkeypatch.setattr(erasure, "_SESSION_AGGREGATES", {})


def institution_of(class_id: str) -> uuid.UUID:
    [(found,)] = rows("SELECT institution_id FROM classes WHERE id = %s", class_id)
    return found


def stored(session_id: str) -> date | None:
    [(found,)] = rows("SELECT deletion_date FROM class_sessions WHERE id = %s", session_id)
    return found


def due_at(session_id: str, day: date = PAST) -> None:
    execute("UPDATE class_sessions SET deletion_date = %s WHERE id = %s", day, session_id)


def plant(session_id: str, user_id, lecturer_id, text: str) -> None:
    """What a Student leaves in a Class session without a game: a Message to them alone, a
    Lecturer's correction of their Completion status and their Tilrettelegging."""
    execute(
        "INSERT INTO messages (id, key, class_session_id, sender_id, recipient_kind, "
        "recipient_user_id, text) VALUES (%s, %s, %s, %s, 'student', %s, %s)",
        uuid.uuid7(),
        uuid.uuid4(),
        session_id,
        lecturer_id,
        user_id,
        text,
    )
    execute(
        "INSERT INTO completion_corrections (id, user_id, class_session_id, step, done, reason, "
        "actor_user_id, at) VALUES (%s, %s, %s, 'class_game', true, %s, %s, now())",
        uuid.uuid7(),
        user_id,
        session_id,
        text,
        lecturer_id,
    )
    execute(
        "INSERT INTO student_adjustments (class_session_id, user_id, time_factor, updated_at) "
        "VALUES (%s, %s, 2.0, now())",
        session_id,
        user_id,
    )


def footprint(session_id: str, user_id) -> dict[str, int]:
    """How many rows of the Student's personal data the Class session still holds, per table."""
    return {
        table: rows(f"SELECT count(*) FROM {table} WHERE {where}", session_id, user_id)[0][0]
        for table, where in {
            "messages": "class_session_id = %s AND recipient_user_id = %s",
            "completion_corrections": "class_session_id = %s AND user_id = %s",
            "student_adjustments": "class_session_id = %s AND user_id = %s",
        }.items()
    }


def account(user_id) -> tuple:
    [found] = rows(
        "SELECT name, email LIKE 'slettet-%%@slettet.invalid', password_hash IS NULL, is_active, "
        "deleted_at IS NOT NULL FROM users WHERE id = %s",
        user_id,
    )
    return tuple(found)


def lecturer_id() -> uuid.UUID:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", LECTURER)
    return found


def audits(action: str) -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = %s "
        "ORDER BY occurred_at, id",
        action,
    )


async def set_retention(institution_id, months, who: str = ADMIN_EMAIL):
    async with client() as c:
        await as_user(c, who)
        return await c.put(
            f"/api/admin/institutions/{institution_id}/retention",
            json={"months": months},
            headers=CSRF,
        )


# The Admin's retention period.


async def test_the_admin_sets_the_period_and_the_deletion_date_moves(klass, admin):
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    assert stored(session_id) == DELETION
    place = institution_of(klass)

    answer = await set_retention(place, 12)
    assert answer.status_code == 200
    assert answer.json()["retention_months"] == 12
    assert answer.json()["retention_default_months"] == 6
    assert stored(session_id) == date(2027, 12, 18)
    assert (await home(STUDENT))["deletion_date"] == "2027-12-18"
    # The same value again writes nothing; null goes back to the placeholder.
    assert (await set_retention(place, 12)).status_code == 200
    assert (await set_retention(place, None)).status_code == 200
    assert stored(session_id) == DELETION
    assert [change for _, _, change in audits("institution.retention_changed")] == [
        {"months": 12, "previous_months": None},
        {"months": None, "previous_months": 12},
    ]
    [(actor, target, _)] = audits("institution.retention_changed")[:1]
    assert actor == admin and target == {"institution_id": str(place)}
    # A new Test deadline uses the Institution's own period.
    assert (await set_retention(place, 3)).status_code == 200
    assert (await save(session_id, {**PLAN, "test_deadline": TEST + DAY})).status_code == 200
    assert stored(session_id) == date(2027, 3, 19)


async def test_a_session_whose_date_has_come_keeps_it(klass, admin):
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    due_at(session_id)
    assert (await set_retention(institution_of(klass), 24)).status_code == 200
    assert stored(session_id) == PAST


async def test_the_period_is_checked_and_only_the_admin_sets_it(klass, admin):
    place = institution_of(klass)
    for months in (0, 121, "6", 2.5):
        assert (await set_retention(place, months)).status_code == 422
    assert (await set_retention(place, 6, who=LECTURER)).status_code == 403
    assert (await set_retention(uuid.uuid4(), 6)).status_code == 404
    assert audits("institution.retention_changed") == []


async def test_a_control_test_follows_the_operator_institutions_period(klass, admin):
    """A Control test's Class belongs to the operator-owned Institution (AD-27): its date follows
    that Institution's period, not the course Institution's."""
    course = await institution("Kursinstitusjonen")
    execute("UPDATE institutions SET operator_owned = true WHERE id = %s", institution_of(klass))
    assert (await set_retention(course, 24)).status_code == 200
    assert (await set_retention(institution_of(klass), 2)).status_code == 200
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    assert stored(session_id) == date(2027, 2, 18)


# Retention.


async def test_nothing_is_due_before_the_date_an_extension_set(klass):
    first, _ = await two_students(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    assert (await extend(session_id, first, TEST + 20 * DAY)).status_code == 200
    assert stored(session_id) == date(2027, 7, 7)
    sid = uuid.UUID(session_id)
    assert sid not in await retention.due_sessions(datetime(2027, 6, 30, 12, tzinfo=UTC))
    assert sid not in await retention.due_sessions(datetime(2027, 7, 6, 21, 59, tzinfo=UTC))
    # 22:00 UTC on 6 July is midnight on 7 July in Oslo: due.
    assert sid in await retention.due_sessions(datetime(2027, 7, 6, 22, tzinfo=UTC))
    early = await retention.retain(sid, datetime(2027, 7, 6, 12, tzinfo=UTC))
    assert early.outcome == "not_due"
    assert rows("SELECT data_deleted_at FROM class_sessions WHERE id = %s", session_id) == [(None,)]


async def other_class() -> str:
    async with client() as c:
        await as_user(c, LECTURER)
        created = await c.post(
            "/api/classes",
            json={"name": "class-of-1995", "institution_id": str(await institution("NTNU"))},
            headers=CSRF,
        )
    assert created.status_code == 201
    return created.json()["id"]


def enrol(class_id: str, user_id, address: str) -> None:
    execute(
        "INSERT INTO roster_entries (id, class_id, email, user_id, registration, added_at) "
        "VALUES (gen_random_uuid(), %s, %s, %s, 'registered', %s)",
        class_id,
        address,
        user_id,
        NOW,
    )


async def test_a_student_with_no_other_session_is_anonymised_and_one_with_a_later_keeps_it(
    klass, no_aggregates
):
    lecturer = lecturer_id()
    only = await student_of(klass, "bare.denne@x.no")
    later = await student_of(klass, "har.senere@x.no")
    first = await new_session(klass)
    # `later` also takes a second course, whose Class session runs later.
    second_class = await other_class()
    enrol(second_class, later, "har.senere@x.no")
    second = await new_session(second_class)
    for who in (only, later):
        plant(first, who, lecturer, f"Notat {who}")
    plant(second, later, lecturer, f"Notat {later}")
    # An address that never registered, and its Invitation, in each Class.
    entries = {}
    for class_id in (klass, second_class):
        entry = entries[class_id] = uuid.uuid7()
        execute(
            "INSERT INTO roster_entries (id, class_id, email, registration, added_at) "
            "VALUES (%s, %s, 'aldri@x.no', 'invited', %s)",
            entry,
            class_id,
            NOW,
        )
        execute(
            "INSERT INTO invitations (id, email, token_hash, created_at, expires_at, kind, "
            "class_id, roster_entry_id) VALUES (%s, 'aldri@x.no', %s, %s, %s, 'student', %s, %s)",
            uuid.uuid7(),
            uuid.uuid4().hex,
            NOW,
            NOW + DAY,
            class_id,
            entry,
        )
    due_at(first)

    done = await retention.retain(uuid.UUID(first), NOW)
    assert (done.outcome, done.students, done.anonymised, done.kept) == ("deleted", 2, 1, 1)
    # `only` has no other Class session: anonymised.
    assert account(only) == ("Slettet bruker", True, True, False, True)
    # `later` keeps the account and the second Class session's data; the first one's is gone.
    assert account(later)[0] != "Slettet bruker" and account(later)[4] is False
    none = {"messages": 0, "completion_corrections": 0, "student_adjustments": 0}
    assert footprint(first, only) == footprint(first, later) == none
    assert footprint(second, later) == {
        "messages": 1,
        "completion_corrections": 1,
        "student_adjustments": 1,
    }
    # Every Class session of the first Class is deleted: its address that never registered and
    # the Invitation go; the second Class still has one to run, so its address stays.
    assert rows("SELECT count(*) FROM roster_entries WHERE id = %s", entries[klass]) == [(0,)]
    assert rows("SELECT count(*) FROM invitations WHERE class_id = %s", klass) == [(0,)]
    assert rows("SELECT count(*) FROM roster_entries WHERE id = %s", entries[second_class]) == [
        (1,)
    ]
    [(actor, target, change)] = audits("class_session.data_deleted")
    assert (actor, target) == (None, {"class_session_id": first})
    assert change == {"students": 2, "anonymised": 1, "kept": 1}

    # Run again: nothing to do, nothing written twice.
    assert (await retention.retain(uuid.UUID(first), NOW)).outcome == "not_due"
    assert uuid.UUID(first) not in await retention.due_sessions(NOW)

    # The second Class session's date comes, through the sweep: `later` is anonymised.
    due_at(second)
    assert (await sweep_only_retention(NOW))["ops.retention"] == 1
    assert account(later)[0] == "Slettet bruker"
    assert footprint(second, later) == none
    for class_id in (klass, second_class):
        assert rows("SELECT count(*) FROM roster_entries WHERE class_id = %s", class_id) == [(0,)]
        assert rows("SELECT count(*) FROM invitations WHERE class_id = %s", class_id) == [(0,)]
        # The Class row stays, with no personal data, as the owner of its aggregates.
        assert rows("SELECT count(*) FROM classes WHERE id = %s", class_id) == [(1,)]
    assert len(audits("class_session.data_deleted")) == 2
    # The system erased both, one audit row each, no actor.
    assert [actor for actor, _, _ in audits("user.deleted")] == [None, None]


async def sweep_only_retention(now: datetime) -> dict[str, int]:
    keep = {"ops.retention", "ops.retention_archived_classes"}
    original = sweep.DUE_ACTIONS
    sweep.DUE_ACTIONS = tuple(a for a in original if a.name in keep)
    try:
        return await sweep.run(now)
    finally:
        sweep.DUE_ACTIONS = original


async def test_both_entry_points_run_the_same_routine(klass, admin, no_aggregates):
    """The Admin's deletion (Story 15.2) and retention leave the same result for the same data."""
    lecturer = lecturer_id()
    by_admin = await student_of(klass, "admin.sletter@x.no")
    by_retention = await student_of(klass, "oppbevaring@x.no")
    session_id = await new_session(klass)
    for who in (by_admin, by_retention):
        plant(session_id, who, lecturer, f"Notat om {who}")
    assert (await delete(by_admin, who=ADMIN_EMAIL)).status_code == 200
    due_at(session_id)
    done = await retention.retain(uuid.UUID(session_id), NOW)
    assert (done.outcome, done.anonymised) == ("deleted", 1)
    assert (
        account(by_admin)
        == account(by_retention)
        == (
            "Slettet bruker",
            True,
            True,
            False,
            True,
        )
    )
    assert footprint(session_id, by_admin) == footprint(session_id, by_retention)
    assert footprint(session_id, by_retention) == {
        "messages": 0,
        "completion_corrections": 0,
        "student_adjustments": 0,
    }
    for who in (by_admin, by_retention):
        assert rows("SELECT count(*) FROM roster_entries WHERE user_id = %s", who) == [(0,)]


async def test_retention_waits_for_the_aggregates(klass, monkeypatch):
    lecturer = lecturer_id()
    student = await student_of(klass)
    session_id = await new_session(klass)
    plant(session_id, student, lecturer, "Notat")
    due_at(session_id)
    seen: list[dict[str, int]] = []

    async def failing(class_session_id):
        raise RuntimeError("the aggregate store is down")

    monkeypatch.setattr(erasure, "_SESSION_AGGREGATES", {"reports": failing})
    assert (await retention.retain(uuid.UUID(session_id), NOW)).outcome == "aggregate_failed"
    assert account(student)[4] is False
    assert footprint(session_id, student)["messages"] == 1
    assert uuid.UUID(session_id) in await retention.due_sessions(NOW)

    async def writing(class_session_id):
        # It runs before anything of the Class session is deleted.
        seen.append(footprint(str(class_session_id), student))

    monkeypatch.setattr(erasure, "_SESSION_AGGREGATES", {"reports": writing})
    assert (await retention.retain(uuid.UUID(session_id), NOW)).outcome == "deleted"
    assert seen == [{"messages": 1, "completion_corrections": 1, "student_adjustments": 1}]
    assert account(student)[4] is True


async def test_an_interrupted_run_continues_and_deletes_nothing_twice(klass, no_aggregates):
    lecturer = lecturer_id()
    first = await student_of(klass, "en@x.no")
    second = await student_of(klass, "to@x.no")
    session_id = await new_session(klass)
    for who in (first, second):
        plant(session_id, who, lecturer, "Notat")
    due_at(session_id)
    # The sweep stopped after the first Student: they are erased, the session is not marked.
    assert await identity.erase_user(first, now=NOW) is True
    assert uuid.UUID(session_id) in await retention.due_sessions(NOW)
    done = await retention.retain(uuid.UUID(session_id), NOW)
    # The erased Student is on the Roster no more; the other one is erased now.
    assert (done.outcome, done.students, done.anonymised) == ("deleted", 1, 1)
    assert account(second)[4] is True
    assert len(audits("user.deleted")) == 2
    assert len(audits("class_session.data_deleted")) == 1


async def test_an_archived_class_with_no_session_keeps_its_roster_until_the_period_ends(klass):
    execute(
        "INSERT INTO roster_entries (id, class_id, email, registration, added_at) "
        "VALUES (gen_random_uuid(), %s, 'aldri@x.no', 'invited', %s)",
        klass,
        NOW,
    )
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW - 150 * DAY, klass)
    assert uuid.UUID(klass) not in await retention.archived_classes(NOW)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW - 200 * DAY, klass)
    assert await retention.archived_classes(NOW) == [uuid.UUID(klass)]
    await sweep_only_retention(NOW)
    assert rows("SELECT count(*) FROM roster_entries WHERE class_id = %s", klass) == [(0,)]
    assert await retention.archived_classes(NOW) == []


async def test_after_the_date_the_studentside_says_the_data_is_deleted(klass):
    student = await student_of(klass)
    session_id = await new_session(klass)
    path = f"/api/class-sessions/{session_id}/students/{student}/record"
    async with client() as c:
        await as_user(c, LECTURER)
        before = await c.get(path)
        due_at(session_id)
        after = await c.get(path)
        await as_user(c, OTHER)
        outsider = await c.get(path)
    assert before.status_code != 409
    assert after.status_code == 409 and after.json()["error"]["code"] == "data_deleted"
    assert outsider.status_code == 403


async def test_after_retention_the_games_still_render_with_seats_by_role(klass, no_aggregates):
    session_id, seated = await confirmed(klass, 2)
    for item in await sessions.due_locks(START + MINUTE):
        await sessions.lock_due(item, START + MINUTE)
    [(game_id,)] = rows("SELECT id FROM games WHERE class_session_id = %s", session_id)
    names = [name for (name,) in rows("SELECT name FROM users WHERE id = ANY(%s)", seated)]
    paths = (f"/api/class-sessions/{session_id}/overview", f"/api/games/{game_id}/insight")
    async with client() as c:
        await as_user(c, LECTURER)
        before = [await c.get(path) for path in paths]
    assert all(r.status_code == 200 for r in before)
    assert all(any(name in r.text for name in names) for r in before)
    due_at(session_id)
    assert (await retention.retain(uuid.UUID(session_id), NOW)).outcome == "deleted"
    async with client() as c:
        await as_user(c, LECTURER)
        after = [await c.get(path) for path in paths]
    assert all(r.status_code == 200 for r in after)
    assert not any(name in r.text for r in after for name in names)
    assert "retailer" in after[1].text


async def test_from_the_date_on_the_staff_views_show_no_names_before_the_run(klass):
    """Names are hidden by the stored date (Epic 13's `data_deleted`), so a Student who keeps the
    account, and every Student before the sweep has run, is shown by Role only."""
    session_id, seated = await confirmed(klass, 2)
    for item in await sessions.due_locks(START + MINUTE):
        await sessions.lock_due(item, START + MINUTE)
    [(game_id,)] = rows("SELECT id FROM games WHERE class_session_id = %s", session_id)
    names = [name for (name,) in rows("SELECT name FROM users WHERE id = ANY(%s)", seated)]
    [(email,)] = rows("SELECT email FROM users WHERE id = %s", seated[0])
    # A Student paused the game: the staff views name who paused (an actor name).
    execute("UPDATE games SET paused_at = now(), paused_by = %s WHERE id = %s", seated[1], game_id)
    paths = (
        f"/api/class-sessions/{session_id}/overview",
        f"/api/games/{game_id}/insight",
        f"/api/class-sessions/{session_id}/allocation",
    )
    async with client() as c:
        await as_user(c, LECTURER)
        before = [await c.get(path) for path in paths]
        await as_user(c, email)
        own_before = await c.get(f"/api/me/games/{game_id}")
    assert any(name in before[2].text for name in names)  # the allocation names them before
    assert any(name in own_before.text for name in names[1:])  # a fellow player, by name
    due_at(session_id)
    async with client() as c:
        await as_user(c, LECTURER)
        after = [await c.get(path) for path in paths]
        # The Students' own game view, every name reader of the Class session (the Debrief's
        # joined Students, Story 9.11) and the Klasseøkt's Students: none named.
        await as_user(c, email)
        own = await c.get(f"/api/me/games/{game_id}")
    assert all(r.status_code == 200 for r in [*after, own])
    assert not any(name in r.text for r in [*after, own] for name in names)
    sid = uuid.UUID(session_id)
    assert await sessions.student_names(sid, list(seated)) == {}
    assert await sessions.session_students(sid) == {}
    # Nothing was deleted: the names are still stored.
    assert all(account(user)[4] is False for user in seated)


@pytest.mark.parametrize("why", ["account_role", "class_staff", "waiting_class"])
async def test_a_student_keeps_the_account_for_each_reason(klass, no_aggregates, why):
    lecturer = lecturer_id()
    student = await student_of(klass, "beholder@x.no")
    session_id = await new_session(klass)
    plant(session_id, student, lecturer, "Notat")
    if why == "account_role":
        execute(
            "INSERT INTO user_roles (user_id, role, granted_at) VALUES (%s, 'lecturer', now())",
            student,
        )
    elif why == "class_staff":
        later = await other_class()
        execute(
            "INSERT INTO class_staff (class_id, user_id, role, added_at) "
            "VALUES (%s, %s, 'assistant', now())",
            later,
            student,
        )
    else:
        # On the Roster of a Class that has no Class session yet, and is not archived.
        enrol(await other_class(), student, "beholder@x.no")
    due_at(session_id)
    done = await retention.retain(uuid.UUID(session_id), NOW)
    assert (done.outcome, done.kept, done.anonymised) == ("deleted", 1, 0)
    assert account(student)[4] is False
    assert footprint(session_id, student) == {
        "messages": 0,
        "completion_corrections": 0,
        "student_adjustments": 0,
    }


async def test_a_date_saved_after_the_deletion_date_keeps_it(klass):
    """Epic 15 close-out: once the date has come, a date saved later does not move it (the names
    stay hidden and a retention run is not stopped half-way); before, it moves as ever."""
    await student_of(klass)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    assert stored(session_id) == DELETION
    due_at(session_id)
    later = {**PLAN, "test_deadline": TEST + 30 * DAY}
    assert (await save(session_id, later)).status_code == 200
    assert stored(session_id) == PAST
    # Marked deleted by retention: the mark alone counts, whatever the date says.
    row = {"deletion_date": None, "data_deleted_at": NOW}
    assert sessions.data_deleted(row, NOW) is True


async def test_a_class_session_with_no_date_keeps_the_account_only_while_its_class_is_current(
    klass, no_aggregates
):
    student = await student_of(klass, "uten.dato@x.no")
    session_id = await new_session(klass)
    later = await other_class()
    enrol(later, student, "uten.dato@x.no")
    await new_session(later)  # no date at all
    due_at(session_id)
    assert await retention._keeps_account(student, uuid.UUID(session_id)) is True
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW - DAY, later)
    assert await retention._keeps_account(student, uuid.UUID(session_id)) is False
