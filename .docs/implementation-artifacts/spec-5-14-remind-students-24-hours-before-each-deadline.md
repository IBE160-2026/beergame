---
title: 'Story 5.14: Remind Students 24 hours before each deadline'
type: 'feature'
created: '2026-11-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'f19f60e76a558c07b25200ee7a987d7b20326dca'
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student hears nothing before a Play deadline, Debrief deadline or Test deadline passes, so a step can be missed by forgetting the date.

**Approach:** A new `ops.sweep` due action `sessions.send_deadline_reminder`. Its finder returns `(class_session_id, deadline)` for each deadline that is within 24 hours (`now < at <= now + 24 h`) and has no reminder for that exact deadline time. The action, `sessions.service.send_deadline_reminder(class_session_id, deadline, *, now)`, records the reminder in a new `deadline_reminders` table (migration 0041) and enqueues one `deadline_reminder` digest notice per Student from `reminder_recipients(class_session_id, deadline)`. The mail is read at send time from a new Jinja2 template.

## Boundaries & Constraints

**Always:**
- `deadline` is one of `play_deadline`, `debrief_deadline`, `test_deadline` (`DeadlineName`). Each finder item holds ids only (`(uuid, name)`), one item per transaction, idempotent. The action runs under the Class session's row lock and re-reads the deadline. It does nothing (returns False) when the deadline is unset, already passed, more than 24 h away, already reminded at this time, or the Class is archived.
- `deadline_reminders`: `id` (UUIDv7), `class_session_id` (FK, cascade), `deadline` (CHECK on the three names), `deadline_at`, `created_at`, UNIQUE `(class_session_id, deadline, deadline_at)`. A moved deadline has a new time, so it gets a new reminder; the old notice is dropped at send time.
- Notice: kind `deadline_reminder` (`DEADLINE_REMINDER_NOTICE`), `ref` = the reminder row id, dedupe key `deadline_reminder:{class_session_id}:{play|debrief|test}:{deadline_at.isoformat()}:{user_id}`. Ids only.
- `reminder_recipients(class_session_id, deadline)` → the registered Students of the session's Class, sorted. It is the only place recipients are chosen; Epics 11 and 13 narrow it.
- `messaging.delivery.KINDS` gets `deadline_reminder` as `DIGEST` with `deadline_reminder_mail_context`. The context returns None (no mail) when the reminder or session is gone, the deadline has moved from the reminded time, the deadline has passed at send time, the Class is archived, or the User is no longer a registered Student. Otherwise it returns `class_name`, `deadline` (`play|debrief|test`), `at` (Europe/Oslo) and `obligatory` (read at send time).
- Template `kinds/deadline_reminder.{txt,html}.j2`, Norwegian bokmål, draft copy. Subject «Påminnelse om frist». The body is «{Spillfristen|Debrieffristen|Testfristen} i Klassen {class} er {weekday} {d}. {month} kl. {HH:MM}.», and when obligatory it adds «Øvelsen er obligatorisk.». It never names Weeks, «Beer Game» or «bullwhip» (`npm run check:copy` scans it).
- Event registry: `sessions.send_deadline_reminder: {user}` (from `notify.enqueue`).

**Never:** No frontend change. No new cron. No per-Student extensions (Epic 11) and no `progress.has_step` (Epic 13). No sleeps, no DB-vs-host clock comparison, and the demo Class is never touched.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 24 h ahead | Play deadline at T; sweep at T−24h | 1 reminder row; 1 notice per registered Student | — |
| Not yet | sweep at T−24h−1min | nothing | — |
| Second sweep | already reminded | finder empty; action returns False | — |
| Three deadlines | each reaches its window | one reminder each, own key | — |
| Moved | reminded at T, moved to T2 within 24 h | new row + notices for T2; T's notice gives no mail | — |
| Passed / unset | deadline ≤ now or NULL | nothing | — |
| Archived Class | archived | finder skips it; action False | — |
| Delivery | digest at 11:00 Oslo | one mail naming the deadline, Oslo time, obligatory line if marked | quiet hours hold it |
| Left Class | Student removed before send | no mail | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/models.py` -- add `deadline_reminders` Table and `DEADLINE_NAMES = DATE_NAMES[1:]`.
- `backend/migrations/versions/0041_deadline_reminders.py` (new) -- create and drop the table (pattern: `0040_class_session_lock.py`).
- `backend/app/modules/sessions/repo.py` -- `due_deadlines(s, now)` returns `(id, class_id, name)` for deadlines in `(now, now+24h]` with no matching reminder row (NOT EXISTS), and `insert_reminder(s, …) -> uuid | None` (ON CONFLICT DO NOTHING RETURNING id), and `reminder_row(s, id)`.
- `backend/app/modules/sessions/service.py` -- new section at the end. `DEADLINE_REMINDER_NOTICE`, `REMINDER_AHEAD = 24h`, `reminder_recipients`, `due_deadline_reminders(now)` (finder; skips archived Classes through `classes.is_writable`), `send_deadline_reminder`, `send_deadline_reminder_due(item, now)`, and `deadline_reminder_mail_context`. Reuse `DATE_KINDS` (`:169`), `repo.session_row(lock=True)`, `classes.registered_students`/`label_of_class`/`is_writable`, `OSLO`, and the pattern of `obligatory_mail_context` (`:1288`). Update the module docstring.
- `backend/app/modules/sessions/schemas.py:33` -- `DeadlineName` Literal.
- `backend/app/modules/ops/sweep.py` -- append the `DueAction` after `sessions.seat_late_registrant`.
- `backend/app/modules/messaging/delivery.py` -- `DEADLINE_REMINDER_KIND` and its context wrapper, listed in `KINDS`.
- `backend/app/platform/email/templates/kinds/` -- `deadline_reminder.txt.j2`, `deadline_reminder.html.j2` (date macro like `_lab_hour.j2`).
- `backend/app/platform/events/registry.py` -- the new command's topics.
- `backend/app/modules/sessions/README.md` -- section «Deadline reminders (Story 5.14)».
- Tests: `backend/tests/sessions/test_deadline_reminders.py` (new; reuse `test_dates.{PLAN,new_session,save,at,student_of}`, `test_lab_hours.{notices,sweep_at,two_students}`, `tests.messaging.helpers.{mails,rows}`), `backend/tests/test_migrations.py` (HEAD 0041, `SESSION_TABLES`, fold the 0041 check into `test_0037_to_0040_…`).

## Tasks & Acceptance

**Execution:**
- `models.py`, `0041_deadline_reminders.py`, `test_migrations.py` -- table, migration, migration check.
- `schemas.py`, `repo.py`, `service.py`, `README.md` -- finder, action, recipients, mail context, docs.
- `sweep.py`, `delivery.py`, `registry.py`, templates -- wiring.
- `test_deadline_reminders.py` -- every matrix row, ids-only notice rows and job args, delivery table entry, template copy.

**Acceptance Criteria:**
- Given a Class session with registered Students and a deadline T, when `ops.sweep` runs at T−24h, then each Student gets exactly one `deadline_reminder` notice keyed by session, deadline kind, deadline time and user, and a second sweep enqueues nothing.
- Given a reminder, when the digest is sent inside the digest hours, then the Student's mail names the deadline and its Europe/Oslo time, says «Øvelsen er obligatorisk.» only when the session is obligatory, and contains no «Beer Game», «bullwhip» or Weeks.
- Given a reminded deadline moved to a new time within 24 h, when the sweep runs, then a new reminder is enqueued and only the new time is mailed.
- Given the notice and job rows, then they hold ids only (kind, key, user id, ref; job `notice_id`).

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 21 findings — high 0, medium 0, low 16, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` blind: recipients were read before the row lock, so a Student registered in between missed a reminder that is never retried. `reminder_recipients` is now read after `insert_reminder`, inside the locked transaction.
  - `[low]` `[reject]` blind: any move of a deadline sends a second reminder. The story asks for this ("a new reminder is sent, because the dedupe key holds the deadline time"), and a not-yet-mailed old notice is dropped at send time.
  - `[low]` `[reject]` blind: a deadline set less than 24 h away is reminded at once, with no minimum lead time. This is a recorded design decision (Design Notes); a late reminder is better than none.
  - `[false]` `[reject]` blind: recipients ignore Seats and the debrief mode. The story says "this story sends to every Student of the Class session"; narrowing belongs to later epics.
  - `[low]` `[reject]` blind: the mail context loads the whole Roster per mail. This is the same pattern as `obligatory_mail_context` and `lab_hour_mail_context`; Classes are small.
  - `[low]` `[reject]` blind: `subject` in the txt template is unused in a digest. Every sibling kind template sets one; kept for consistency.
  - `[low]` `[reject]` blind: the mail has no link and no year. This is draft copy, the same as the other digest kinds, none of which link.
  - `[false]` `[reject]` blind: the `_deadline.j2` macro fails silently on an unknown kind. The context only ever passes `DATE_KINDS` of the three CHECK-constrained names.
  - `[low]` `[patch]` blind: the deadline names live in several places. Added `test_the_deadline_names_agree` (`DEADLINE_NAMES == get_args(DeadlineName) == DATE_NAMES[1:]`); the CHECK is pinned by the migration test.
  - `[low]` `[patch]` blind: a test name claimed a passed-deadline case it did not cover. Renamed to `test_a_student_who_left_before_the_digest_gets_no_mail`.
  - `[low]` `[reject]` blind: several cases are untested (racing insert, cascade, out-and-back move, late registrant, HTML body). Each is low; the conflict path is the DB's UNIQUE constraint, and the HTML shares the txt macro.
  - `[low]` `[reject]` blind: the finder scans three timestamp ranges every minute without an index. `class_sessions` holds a term's sessions (tens of rows), the same as `due_locks`.
  - `[low]` `[reject]` blind: reminder rows are never pruned. They are tiny and cascade with their session; retention belongs to the retention epic.
  - `[low]` `[reject]` edge: a deadline reminded at T, moved to T2 before the digest, then moved back to T gets no new reminder (the T row exists). Rare (two moves inside 24 h, back to the exact minute), and the fix would add row-revision logic.
  - `[low]` `[patch]` edge: recipients were read before the lock. Same as the first blind row, with the same patch.
  - `[low]` `[reject]` intent: a move after the old mail was *delivered* (reading C2) has no test of its own. The mechanism is the same (new time, new row), and the tested case also covers the drop-at-send rule.
  - `[low]` `[reject]` intent: the dedupe key alone is never shown stopping a duplicate. The reminder row guards first; the key's uniqueness is `platform/notify`'s, tested in Story 3.5.
  - `[false]` `[reject]` intent: the frontend copy check was not shown to run on the new templates. `npm run check:copy` was run and scanned 29 templates, the new ones included.
  - `[low]` `[reject]` intent: "at most one mail per day" is untested here. It is the digest delivery's rule (Story 3.5), tested there; this kind only registers as `DIGEST`, which is asserted.
  - `[false]` `[reject]` intent: the template subject is unused. This duplicates the blind row, and the story says nothing about the subject.
  - `[low]` `[patch]` verification-gap: archiving the Class between the enqueue and the digest was untested at send time. Added `test_an_archived_class_before_the_digest_gets_no_mail`.

No independent visual reviewer was run: this story changes no `frontend/` file.

## Design Notes

Founder-level decisions taken here:
- "Has no reminder yet" is a stored row (`deadline_reminders`), not a lookup of notices. `sessions` never reads `notices`, and the finder stops returning a deadline once it has been reminded.
- A deadline set or moved to less than 24 h away is reminded at the next sweep (no minimum notice).
- A Student who registers after the reminder went out gets none for that deadline.
- The mail is dropped at send time if the deadline moved or passed meanwhile; the moved deadline has its own reminder.
- Reminders go out whether or not the session is locked.
- Recipients are every registered Student of the Class (not only seated ones), as the story says.
- The mail copy is draft copy written here, since `open-assumptions.md` had none. The subject is «Påminnelse om frist». The body is «{Spillfristen|Debrieffristen|Testfristen} i Klassen … er {ukedag} {d}. {måned} kl. HH:MM.», plus «Øvelsen er obligatorisk.» when it applies.
- Implementation was done in the builder's own context, not by a sub-agent (runbook: sub-agents stop when the turn ends).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_deadline_reminders.py tests/ops/test_sweep.py -q` -- expected: pass, each test under 1 s
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run check:copy` -- expected: pass (scans the new template)

## Auto Run Result

Status: done

**Summary.** A new last `ops.sweep` due action, `sessions.send_deadline_reminder`. The finder `due_deadline_reminders(now)` returns `(class_session_id, deadline)` for each Play, Debrief or Test deadline in `(now, now + 24 h]` with no `deadline_reminders` row at its current time, and skips archived Classes. `send_deadline_reminder(class_session_id, deadline, *, now)` takes the session row lock, re-checks the window and the Class, and records the row (UNIQUE on session, deadline and time). It then enqueues one `deadline_reminder` digest notice per Student of `reminder_recipients` (every registered Student, sorted). Each notice is keyed `deadline_reminder:{session}:{kind}:{time}:{user}` and has the row as `ref`. At send time `deadline_reminder_mail_context` gives the Class name, the deadline, its Oslo time and the obligatory mark. It drops the notice if the deadline moved or passed, the Class is archived or the Student left. A moved deadline gets a new reminder.

**Files.**
- `backend/app/modules/sessions/models.py`, `backend/migrations/versions/0041_deadline_reminders.py`: the `deadline_reminders` table and `DEADLINE_NAMES`.
- `backend/app/modules/sessions/{repo,service,schemas}.py`, `README.md`: the finder SQL, the insert and read, the service functions, `DeadlineName` and the docs.
- `backend/app/modules/ops/sweep.py`, `backend/app/modules/messaging/delivery.py`, `backend/app/platform/events/registry.py`: the due action, the digest kind and the topics.
- `backend/app/platform/email/templates/kinds/{_deadline.j2,deadline_reminder.txt.j2,deadline_reminder.html.j2}`: the bokmål template (draft copy).
- `backend/tests/sessions/test_deadline_reminders.py` (new, 13 tests) and `backend/tests/test_migrations.py` (HEAD 0041, the table set, and 0041 folded into the 0037–0040 test).

**Review.** 21 findings: high 0, medium 0, low 16, false 5. Four rows were patched, forming three entries, all low: recipients are now read under the lock, a deadline-name agreement test was added and a test renamed, and a test covers archiving before the digest. Nothing was deferred. Every other finding was rejected, with its reason in the triage log. Follow-up review: false (no high or medium patched).

**Verification.**
- Backend: the full suite passed (2551 tests, 71 s), and `ruff check` and `ruff format --check` are clean. Each new test runs in 0.3 to 0.9 s, except the first test's call, which takes about 1.0 s on a cold start.
- `npm run check:copy` passed and scanned the new templates. No `frontend/` file changed, so typecheck, Vitest, build and Playwright were not run.
- New migration 0041. The shared test databases migrate to head per session, so 0041 was applied there by this run.

**Residual risks.** A deadline that is moved and then moved back to the exact earlier minute within 24 h, before the digest goes, gets no new reminder. Reminder rows are never pruned; they are tiny and cascade with the session.
