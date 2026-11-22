"""The Admin deletes a User on the Institution's instruction (Story 15.2, FR-76, FR-2, FR-3, AD-2,
AD-4, AD-5, AD-14, AD-15). Through the api: a Student who holds a Seat in a running Class game is
handed to an AI player first, then anonymised in place; their free text, the Messages to them and
their staged Roster row go; no name, address or student number survives in any table; the other
Student's game goes on with the Seat by Role, and the finished Game still verifies. The api's
clock is fixed; the database clock is never compared with it."""

import uuid
from datetime import timedelta

import psycopg
import pytest

from app.modules.games import checks
from app.modules.games import commands as games_commands
from app.modules.games import rules as game_rules
from app.modules.games import service as games_service
from app.modules.identity import service
from app.modules.identity.schemas import AccountRole
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, as_user, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW
from tests.conftest import libpq_dsn
from tests.identity.helpers import CSRF, client, login
from tests.messaging.helpers import rows
from tests.sessions.test_play import play, running
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]

ADMIN = "admin15@example.com"
NAME = "Torbjørn Erasmussen"
STUDENT_NUMBER = "987654321"
REFERENCE = "Sak 2026/0042, instruks fra USN"


@pytest.fixture
async def admin(klass) -> uuid.UUID:
    return await make(ADMIN, roles=(AccountRole.admin,))


async def delete(user_id, reference: str = REFERENCE, who: str = ADMIN):
    async with client() as c:
        await as_user(c, who)
        return await c.post(
            f"/api/admin/users/{user_id}/delete", json={"reference": reference}, headers=CSRF
        )


def user_id_of(address: str) -> uuid.UUID:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", address)
    return found


def everywhere(*terms: str) -> dict[str, list[str]]:
    """For each of `terms`, every table, in every schema the app writes (the job tables
    included), whose rows hold it anywhere, as text, case-insensitively. One scan per table."""
    from tests.conftest import TEST_DATABASE_URL

    found: dict[str, list[str]] = {term: [] for term in terms}
    tests = ", ".join("bool_or(t::text ILIKE %s)" for _ in terms)
    patterns = tuple(f"%{term}%" for term in terms)
    with psycopg.connect(libpq_dsn(TEST_DATABASE_URL), autocommit=True) as conn:
        tables = conn.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' "
            "AND table_schema NOT IN ('pg_catalog', 'information_schema')"
        ).fetchall()
        for schema, table in tables:
            hits = conn.execute(f'SELECT {tests} FROM "{schema}"."{table}" t', patterns).fetchone()
            for term, hit in zip(terms, hits, strict=True):
                if hit:
                    found[term].append(f"{schema}.{table}")
    return found


def plant_personal_data(
    session_id: str, game_id: str, class_id: str, user_id, address: str, other_id
):
    """What a Student leaves behind besides the game: free text naming themselves, a Message to
    them alone, a reset link, a request for access and a staged Roster row with their number."""
    execute("UPDATE users SET name = %s WHERE id = %s", NAME, user_id)
    explanation = f"Jeg, {NAME}, bestilte for mye."
    execute(
        "INSERT INTO debrief_explanations (user_id, class_session_id, game_id, text, length, "
        "saved_at) VALUES (%s, %s, %s, %s, %s, now())",
        user_id,
        session_id,
        game_id,
        explanation,
        len(explanation),
    )
    answer = f"Hilsen {NAME}"
    execute(
        "INSERT INTO debrief_reflection_answers (user_id, class_session_id, question_id, game_id, "
        "questions_version, text, length, saved_at) VALUES (%s, %s, 'q1', %s, 1, %s, %s, now())",
        user_id,
        session_id,
        game_id,
        answer,
        len(answer),
    )
    # A finished Debrief's summary copies the reflection: it stays, with the copy emptied.
    [(seat_id,)] = rows("SELECT id FROM seats WHERE game_id = %s ORDER BY id LIMIT 1", game_id)
    fact_set = uuid.uuid7()
    execute(
        "INSERT INTO fact_sets (id, game_id, seat_id, analysis_version, payload) "
        "VALUES (%s, %s, %s, 1, '{}')",
        fact_set,
        game_id,
        seat_id,
    )
    execute(
        "INSERT INTO debrief_summaries (user_id, class_session_id, game_id, fact_set_id, "
        "moment_ids, reflection, finished_at) VALUES (%s, %s, %s, %s, '[]', %s, now())",
        user_id,
        session_id,
        game_id,
        fact_set,
        f'[{{"question_id": "q1", "questions_version": 1, "text": "Hilsen {NAME}"}}]',
    )
    execute(
        "INSERT INTO debrief_follow_ups (id, user_id, class_session_id, fact_set_id, question, "
        "outcome, answer, llm_call_id) VALUES (%s, %s, %s, %s, %s, 'answered', %s, %s)",
        uuid.uuid7(),
        user_id,
        session_id,
        fact_set,
        f"Hvorfor bestilte {NAME} så mye?",
        f"{NAME} bestilte mer enn etterspørselen.",
        uuid.uuid7(),
    )
    [(lecturer,)] = rows("SELECT id FROM users WHERE email = %s", LECTURER)
    # A Message to the whole Class session: it stays for the others; the User leaves its recipients.
    to_all = uuid.uuid7()
    execute(
        "INSERT INTO messages (id, key, class_session_id, sender_id, recipient_kind, text) "
        "VALUES (%s, %s, %s, %s, 'class_session', 'Husk Debriefen.')",
        to_all,
        uuid.uuid4(),
        session_id,
        lecturer,
    )
    for each in (user_id, other_id):
        execute(
            "INSERT INTO message_recipients (message_id, user_id) VALUES (%s, %s)", to_all, each
        )
        notice = uuid.uuid7()
        execute(
            "INSERT INTO notices (id, user_id, kind, dedupe_key) VALUES (%s, %s, 'message', %s)",
            notice,
            each,
            f"planted:{notice}",
        )
        execute(
            "INSERT INTO mail_deliveries (id, user_id, mode, notice_ids, claimed_at) "
            "VALUES (%s, %s, 'immediate', ARRAY[%s]::uuid[], now())",
            uuid.uuid7(),
            each,
            notice,
        )
    execute(
        "INSERT INTO messages (id, key, class_session_id, sender_id, recipient_kind, "
        "recipient_user_id, text) VALUES (%s, %s, %s, %s, 'student', %s, %s)",
        uuid.uuid7(),
        uuid.uuid4(),
        session_id,
        lecturer,
        user_id,
        f"Hei {NAME}, husk Debriefen.",
    )
    execute(
        "INSERT INTO password_resets (id, user_id, token_hash, created_at, expires_at) "
        "VALUES (%s, %s, %s, now(), now() + interval '1 hour')",
        uuid.uuid7(),
        user_id,
        uuid.uuid4().hex,
    )
    execute(
        "INSERT INTO access_requests (id, name, email, institution, requested_at) "
        "VALUES (%s, %s, %s, 'USN', now())",
        uuid.uuid7(),
        NAME,
        address,
    )
    upload = uuid.uuid7()
    execute(
        "INSERT INTO roster_uploads (id, class_id, uploaded_by, file_name, headers, has_header, "
        "column_count, row_count, chosen_column, created_at, expires_at) VALUES (%s, %s, %s, "
        "'liste.csv', '[\"E-post\", \"Studentnr\"]', true, 2, 2, 0, now(), "
        "now() + interval '1 day')",
        upload,
        class_id,
        lecturer,
    )
    for number, cells in (
        (2, f'["{address.upper()} ", "{STUDENT_NUMBER}"]'),
        (3, '["a@b.no", "1"]'),
    ):
        execute(
            "INSERT INTO roster_upload_rows (upload_id, row_number, cells) VALUES (%s, %s, %s)",
            upload,
            number,
            cells,
        )


async def test_a_student_in_a_running_game_is_erased_and_the_game_goes_on(klass, admin):
    session_id, game_id, by_role = await running(klass, students=2)
    (gone_role, gone), (stay_role, stay) = sorted(by_role.items())
    gone_id = user_id_of(gone)
    plant_personal_data(session_id, game_id, klass, gone_id, gone, user_id_of(stay))
    planted = everywhere(NAME, gone, STUDENT_NUMBER)
    assert all(planted.values()), planted  # the search sees what is planted
    [(seat_id,)] = rows("SELECT id FROM seats WHERE game_id = %s AND role = %s", game_id, gone_role)
    weeks_before = rows(
        'SELECT id, "order" FROM seat_weeks WHERE game_id = %s ORDER BY id', game_id
    )

    response = await delete(gone_id)
    assert response.status_code == 200, response.text
    assert response.json() == {"id": str(gone_id)}

    # The Seat went to an AI player first, by the system, with the Takeover reason of Story 8.2.
    [(kind, reason, actor, holder)] = rows(
        "SELECT occupant_kind, reason, actor_user_id, user_id FROM seat_occupancy "
        "WHERE seat_id = %s ORDER BY id DESC LIMIT 1",
        seat_id,
    )
    assert (kind != "student", reason, actor, holder) == (True, "takeover_inactivity", None, None)
    # The other Student is told as for any Takeover; the erased one is not.
    told = {user for (user,) in rows("SELECT user_id FROM notices WHERE kind = 'takeover_notice'")}
    assert told == {user_id_of(stay)}
    # No Decision log row changed, and every occupancy row still names the same id.
    assert (
        rows('SELECT id, "order" FROM seat_weeks WHERE game_id = %s ORDER BY id', game_id)[
            : len(weeks_before)
        ]
        == weeks_before
    )
    assert rows(
        "SELECT count(*) FROM seat_occupancy WHERE seat_id = %s AND user_id = %s", seat_id, gone_id
    ) == [(1,)]

    # The User row is the anonymous User now.
    [(name, address, password, active, deleted_at)] = rows(
        "SELECT name, email, password_hash, is_active, deleted_at FROM users WHERE id = %s",
        gone_id,
    )
    assert (name, address, password, active) == (
        "Slettet bruker",
        f"slettet-{gone_id.hex}@slettet.invalid",
        None,
        False,
    )
    assert deleted_at is not None
    # Nothing of the person is left anywhere: name, address or student number.
    left = everywhere(NAME, gone, STUDENT_NUMBER, "Erasmussen")
    assert left == {term: [] for term in left}, left
    # Their rows in the messaging and Debrief tables are gone; the other Student's stay.
    for table in ("debrief_follow_ups", "message_recipients", "notices", "mail_deliveries"):
        assert rows(f"SELECT count(*) FROM {table} WHERE user_id = %s", gone_id) == [(0,)], table
    other = user_id_of(stay)
    assert rows("SELECT count(*) FROM message_recipients WHERE user_id = %s", other) == [(1,)]
    # Planted, and the Takeover notice's own: the other Student's deliveries stay.
    [(kept,)] = rows("SELECT count(*) FROM mail_deliveries WHERE user_id = %s", other)
    assert kept >= 1
    assert rows("SELECT count(*) FROM messages WHERE recipient_kind = 'class_session'") == [(1,)]
    # The Studentside answers as for anyone who is no Student of the Class.
    async with client() as c:
        await as_user(c, LECTURER)
        page = await c.get(f"/api/class-sessions/{session_id}/students/{gone_id}")
        nobody = await c.get(f"/api/class-sessions/{session_id}/students/{uuid.uuid7()}")
        kept = await c.get(f"/api/class-sessions/{session_id}/students/{user_id_of(stay)}")
    assert kept.status_code == 200
    assert (page.status_code, page.json()) == (nobody.status_code, nobody.json())
    # The Debrief summary still counts, with no reflection.
    assert rows("SELECT reflection FROM debrief_summaries WHERE user_id = %s", gone_id) == [([],)]
    # The staged row of another Student stays.
    assert rows("SELECT count(*) FROM roster_upload_rows") == [(1,)]

    # One audit row: the Admin, the time and the id, with the reference only.
    [(actor_id, targets, change)] = rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = 'user.deleted'"
    )
    assert (actor_id, targets, change) == (
        admin,
        {"user_id": str(gone_id)},
        {"reference": REFERENCE},
    )

    # The User cannot log in, and is in no search and on no Roster.
    async with client() as c:
        assert (await login(c, gone, "et-passord")).status_code == 401
    assert (await service.list_users("Slettet", None, 50)).items == []
    assert (await service.list_users("", None, 50)).items != []
    assert gone_id not in await service.registered_users(uuid.UUID(klass))
    assert await service.student_names(uuid.UUID(klass), [gone_id]) == {}

    # The other Student plays on and sees the Seat by Role, with no name.
    envelope = (await play(stay, game_id)).json()
    seat = next(s for s in envelope["table_status"]["seats"] if s["role"] == gone_role)
    assert (seat["holder"], seat["taken_over"], seat["ordering_for"]) == ("ai", True, None)
    assert stay_role != gone_role

    # Deleting again finishes nothing new and writes no second audit row.
    again = await delete(gone_id)
    assert again.status_code == 200
    assert rows("SELECT count(*) FROM audit_events WHERE action = 'user.deleted'") == [(1,)]

    # Played to its end by AI players (the Play deadline's playout, Story 8.14), the finished
    # Game replays through the engine and its stored states verify (AD-4).
    deadline = NOW - timedelta(minutes=1)
    assert await games_commands.playout(game_id, now=NOW, latest=deadline)
    assert (await games_service.get_game(game_id)).lifecycle == "finished"
    check = await checks.verify_finished(game_id)
    assert check.ok, check.violations


async def test_the_deletion_is_refused_with_nothing_changed(klass, admin):
    [(lecturer,)] = rows("SELECT id FROM users WHERE email = %s", LECTURER)
    owner = await delete(lecturer)
    assert owner.status_code == 409
    assert owner.json()["error"]["code"] == "role_revoke_blocked"
    assert owner.json()["error"]["fields"] == {"classes": 1}

    oneself = await delete(admin)
    assert (oneself.status_code, oneself.json()["error"]["code"]) == (409, "last_admin")

    student = await make("ola.nordmann@example.com", roles=())
    for reference, code in (
        ("  ", "reference_empty"),
        ("x" * 201, "reference_too_long"),
        ("sendt fra ola@uni.no", "reference_invalid"),
        ("Instruks om Nordmann", "reference_names_user"),
        ("instruks ola.nordmann", "reference_names_user"),
    ):
        refused = await delete(student, reference)
        assert refused.status_code == 422, reference
        assert refused.json()["error"]["fields"] == {"reference": code}

    assert (await delete(uuid.uuid7())).status_code == 404
    # Only an Admin may delete.
    assert (await delete(student, who=LECTURER)).status_code == 403
    assert rows("SELECT count(*) FROM audit_events WHERE action = 'user.deleted'") == [(0,)]
    assert rows("SELECT deleted_at FROM users WHERE id = %s", student) == [(None,)]

    # A second Admin can be deleted while another active Admin remains.
    other_admin = await make("admin.two@example.com", roles=(AccountRole.admin,))
    assert (await delete(other_admin, "Sak 7")).status_code == 200
    assert rows("SELECT count(*) FROM user_roles WHERE user_id = %s", other_admin) == [(0,)]


async def test_the_erasure_clears_the_bodies_of_the_ai_calls_made_for_the_user(klass):
    from app.ai import calls, seed

    user_id = await make("carl@example.com", roles=())
    await seed.ensure_zero_config()
    [(config,)] = rows("SELECT id FROM ai_model_configs ORDER BY id LIMIT 1")
    ids = [uuid.uuid7(), uuid.uuid7()]
    for call_id, owner in zip(ids, (user_id, uuid.uuid7()), strict=True):
        execute(
            "INSERT INTO llm_call (id, purpose, scope_kind, scope_id, caller_ref, model_config_id, "
            "provider, endpoint, model_version, quantisation, effort_level, prompt_version, "
            "attempt, input_tokens, output_tokens, reasoning_tokens, cost_usd, latency_ms, "
            "outcome, request, response, started_at) VALUES (%s, 'debrief_follow_up', "
            "'evaluation', %s, %s, %s, 'mock', 'mock', 'm', 'none', 'low', 1, 1, 1, 1, 0, "
            "0.001, 5, 'ok', %s, 'svar', now())",
            call_id,
            uuid.uuid7(),
            f'{{"user_id": "{owner}"}}',
            config,
            '{"question": "spørsmål"}',
        )
    async with get_sessionmaker().begin() as s:
        assert await calls.clear_bodies_of_user(s, user_id) == 1
    async with get_sessionmaker().begin() as s:
        assert await calls.clear_bodies_of_user(s, user_id) == 0
    assert [
        rows("SELECT request::text, response, cost_usd > 0 FROM llm_call WHERE id = %s", each)[0]
        for each in ids
    ] == [("{}", None, True), ('{"question": "spørsmål"}', "svar", True)]


def test_the_system_may_take_over_at_once_a_seat_whose_user_is_erased():
    from datetime import UTC, datetime

    now = datetime(2026, 11, 20, 12, tzinfo=UTC)
    game = {"lifecycle": "running", "purpose": "class", "paused_at": now}
    seat = {"occupant_kind": "student", "reason": "allocated"}
    turn = {
        "occupant_kind": "student",
        "ordered_at": now,
        "viewed_at": None,
        "takeover_due_at": now + timedelta(days=1),
        "insert_allowed_at": None,
    }
    common = {"guided": False, "seat": seat}
    # Paused, ordered and not due: the ordinary system Takeover may not, the erasing one may.
    assert game_rules.can_take_over(game, turn, "system", now, **common) == "game_paused"
    assert game_rules.can_take_over(game, turn, "system", now, erasing=True, **common) is None
    assert (
        game_rules.can_take_over(
            {**game, "paused_at": None}, {**turn, "ordered_at": None}, "system", now, **common
        )
        == "takeover_not_due"
    )
    # A Seat taken over already stays so.
    taken = {"occupant_kind": "rule_based", "reason": "takeover_inactivity"}
    assert (
        game_rules.can_take_over(game, turn, "system", now, erasing=True, guided=False, seat=taken)
        == "takeover_exists"
    )
    with pytest.raises(ValueError):
        game_rules.can_take_over(game, turn, "staff", now, erasing=True, **common)


async def test_an_assistant_lecturer_leaves_every_class_staff(klass, admin):
    assistant = await make("assistent15@example.com", roles=())
    execute(
        "INSERT INTO class_staff (class_id, user_id, role, added_at) "
        "VALUES (%s, %s, 'assistant', now())",
        klass,
        assistant,
    )
    assert (await delete(assistant, "Sak 9")).status_code == 200
    assert rows("SELECT count(*) FROM class_staff WHERE user_id = %s", assistant) == [(0,)]
    assert rows("SELECT count(*) FROM class_staff WHERE class_id = %s", klass) == [(1,)]
    # An erased User is no one to give a role or reactivate.
    async with client() as c:
        await as_user(c, ADMIN)
        granted = await c.post(
            f"/api/admin/users/{assistant}/roles", json={"role": "admin"}, headers=CSRF
        )
        reactivated = await c.post(f"/api/admin/users/{assistant}/reactivate", headers=CSRF)
    assert (granted.status_code, reactivated.status_code) == (404, 404)
    assert rows("SELECT is_active FROM users WHERE id = %s", assistant) == [(False,)]


async def test_the_routine_without_an_admin_audits_the_system(klass):
    user_id = await make("retention15@example.com", roles=())
    assert await service.erase_user(user_id, now=NOW) is True
    [(actor, targets, change)] = rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = 'user.deleted'"
    )
    assert (actor, targets, change) == (None, {"user_id": str(user_id)}, {})
    assert await service.erase_user(uuid.uuid7(), now=NOW) is False
