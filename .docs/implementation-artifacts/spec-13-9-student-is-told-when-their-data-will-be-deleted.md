---
title: 'Story 13.9: A Student is told when their data will be deleted'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '7f90bd148a82aa83db688b63c0bc584644e41a2b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Student data is deleted a set period after the Test deadline (FR-77), but nothing stores that date, nothing shows it to the Student, and nobody reminds them to download their Student report before it (FR-57).

**Approach:** One pure rule (`app/analysis/retention.deletion_date`: the latest effective Test deadline, read on the Europe/Oslo calendar, plus the retention months, clamped to the month's end, the same rule as Epic 15's placeholder in `ops.retention`) feeds a `class_sessions.deletion_date` column that `sessions.service` recomputes in the transaction of every Test deadline save and every per-Student extension. Hjem shows the date under «Rapport»; a sweep due action sends one `digest` notice per Student a configurable number of days before.

## Boundaries & Constraints

**Always:**
- `deletion_date` is a `date` (Oslo calendar day; the data is deleted on that day), NULL while the Class session has no Test deadline. Latest effective Test deadline = max(Class session's `test_deadline`, every `student_deadline_extensions.test_deadline` of the session).
- Settings placeholders: `RETENTION_MONTHS` = 6 (PRD: course end plus six months; Epic 15 adds the per-Institution Admin setting), `DELETION_REMINDER_DAYS` = 14.
- Written only in `sessions/service.py` (`_store_deletion_date`), called from the Class session save when `test_deadline` changed, from `save_extension`, and from the dev route that moves dates. `extend_deadline` takes the Class session row `FOR UPDATE` (not share) so two concurrent extensions cannot deadlock on the update.
- Migration 0305 adds the column and backfills it in SQL with the same rule (6 months).
- Due action `sessions.send_deletion_reminder`: finder returns ids of Class sessions with a deletion date, no `deletion_reminded_at`, and `today(Oslo) >= deletion_date - N days` and `today < deletion_date`; the act (one Class session per transaction, row lock, ids only) enqueues one `deletion_reminder` notice per registered Student of the Class (archived Classes included: their data is kept until this date), key `deletion_reminder:<session>:<user>`, ref the session, then sets `deletion_reminded_at`. Idempotent; registered in `COMMAND_TOPICS`.
- Digest mail `deletion_reminder` (txt + html), context read at send time: Class name and date; left out when the session or date is gone, the date has passed, or the User is no longer a registered Student.
- Hjem: `EnrolledSessionOut.deletion_date`; under «Rapport» (locked or open) one line from `nb.ts`: «Dataene dine fra denne Klasseøkten slettes 24. mai 2027. Last ned Studentrapporten før det.»

**Never:** no deletion itself (Story 15.3); no Admin setting; no per-Student deletion date; no import of `ops` from `sessions`; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Dates saved | Test deadline 2026-12-18 10:00 UTC | `deletion_date` 2027-06-18 | — |
| Oslo day boundary | Test deadline 2026-12-31 23:30 UTC (1 Jan Oslo) | 2027-07-01 | — |
| Month end | Test deadline 31 Aug (Oslo) | 28/29 Feb | — |
| Deadline moved | Lecturer moves Test deadline later / earlier | date recomputed in the same save | — |
| Extension | one Student extended past Class deadline | date from the extension; moving the Class deadline earlier keeps it | — |
| No Test deadline | session without dates | NULL; no line on Hjem; no reminder | — |
| Reminder window | sweep at deletion_date − 14 d (Oslo) | one notice per Student; second sweep adds none | — |
| Removed Student | not registered at send time | mail leaves the notice out | — |

</intent-contract>

## Code Map

- `backend/app/platform/retention.py` (new; first placed in `app/analysis`, whose purity test forbids `datetime`) -- pure `add_months`, `deletion_date(latest, months)`; Oslo calendar. Lane 1's `ops/retention.py` (`origin/epic-15`) has the same rule for one deadline; at merge it can delegate here.
- `backend/app/platform/config.py` -- add `retention_months`, `deletion_reminder_days` near `turn_reminder_delay_minutes`.
- `backend/app/modules/sessions/models.py` :34 `class_sessions` -- add `deletion_date` (Date), `deletion_reminded_at` (timestamptz).
- `backend/migrations/versions/0305_deletion_date.py` (new, Revises 0304).
- `backend/app/modules/sessions/repo.py` -- `latest_test_deadline(s, id)` (class + extensions), `set_deletion_date`, `due_deletion_reminders(s, today, ahead)`, `mark_deletion_reminded`.
- `backend/app/modules/sessions/service.py` -- save path :1328 (`"test_deadline" in changed`), `save_extension` :2319, Hjem `EnrolledSessionOut(...)` :1538, deadline reminders :5303 pattern, `deadline_reminder_mail_context` :5423 pattern.
- `backend/app/modules/tests/commands.py` :616 `extend_deadline` -- lock the row for update (`test_session(..., lock=True)`).
- `backend/app/modules/sessions/dev.py` :167 `pass_test_deadline` -- recompute.
- `backend/app/modules/ops/sweep.py` -- register the due action after the deadline reminders.
- `backend/app/modules/messaging/delivery.py` -- `DELETION_REMINDER_KIND` digest; templates `app/platform/email/templates/kinds/deletion_reminder.{txt,html}.j2`.
- `backend/app/platform/events/registry.py` :133 -- `sessions.send_deletion_reminder`.
- `frontend/src/components/stegene.tsx` -- render `action` under a locked step too.
- `frontend/src/modules/games/student-hjem.tsx` :213 -- deletion line under «Rapport»; `frontend/src/modules/sessions/dates.ts` -- `calendarDateText`; `frontend/src/copy/nb.ts` -- copy.
- Tests: `backend/tests/sessions/test_deadline_reminders.py` (helpers `dated`, `notices`), `tests/individual_test/test_extension.py` (`extend`), `tests/sessions/test_student_home.py` (`home`).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/retention.py` + `tests/platform/test_retention.py` -- pure rule and edge cases.
- config, models, migration, repo, service, tests/commands, dev, sweep, registry, delivery, templates -- as in the Code Map.
- `backend/tests/sessions/test_deletion_date.py` (new) -- stored on save, moved deadline (both ways), extension, Class deadline moved below an extension, Hjem field, reminder once per Student, idempotent, mail text, removed Student left out.
- `npm run api:generate`; frontend Stegene, Hjem, dates, copy; Vitest for `calendarDateText` and the Hjem line; e2e line in `frontend/e2e/student-report.spec.ts` (or `homes`).

**Acceptance Criteria:**
- Given a Class session with a Test deadline, when its dates are saved or a Student's deadline is extended, then `deletion_date` equals the rule over the latest effective Test deadline, written in the same transaction.
- Given a Student on Hjem with a dated Class session, when the steps show, then under «Rapport» they read the deletion date and that they should download the report before it.
- Given the sweep runs on or after deletion_date − 14 days, then each registered Student gets exactly one `deletion_reminder` digest notice and the mail names the Class and date.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: two (blind, edge case) on Sonnet, as the orchestrator asked; verification gap and intent alignment skipped.
- verdicts: 20 findings — high 0, medium 1, low 13, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: the reminder is never re-armed when the date moves after it. Grouped with the Edge medium row; fixed there.
  - `[low]` `[reject]` Blind: Students registered after the reminder, or an empty roster, get none. The reminder runs about 5.5 months after the Test deadline; registering then is not an everyday case, and a fix adds per-Student state.
  - `[low]` `[reject]` Blind: the backfill hardcodes six months. It is the stated placeholder; Story 15.3 recomputes every date when the Institution's period is set.
  - `[low]` `[reject]` Blind: a changed `RETENTION_MONTHS` does not recompute stored dates. Same: Story 15.3's AC recomputes them; until then the setting is a placeholder.
  - `[low]` `[reject]` Blind: the copy promises a deletion that Epic 15 performs. By design (FR-77 split, AD-9); Epic 15 lands before production.
  - `[low]` `[reject]` Blind: Hjem shows a past date. After the date Story 15.3 deletes the data; a client clock branch is not worth it.
  - `[low]` `[reject]` Blind: `calendarDateText` falls back to the raw string. The api serialises a `date`; the fallback only guards a broken contract.
  - `[low]` `[reject]` Blind: the extension now takes an exclusive row lock. Extensions are rare Lecturer actions; Student commands share-lock the row first, then the attempt row, the same order, so the wait is one short transaction.
  - `[low]` `[reject]` Blind: test gaps (archived Class, mail context None cases, dev route, html template). The dev route is covered by the e2e (the date moves with it); the other branches mirror the tested deadline reminder.
  - `[false]` `[reject]` Blind: copy inconsistency mail vs Hjem. The mail must name the Class (it is not read on a Klasseøkt page); templates hold mail copy by convention (`check:copy` covers them); no html template carries a subject.
  - `[false]` `[reject]` Blind: the date change is not audited. It is derived from saved and audited deadlines; no new actor decision.
  - `[false]` `[reject]` Blind: a cleared Test deadline ignores extensions. `effective_test_deadline` is None too when the Class session has none (`_effective`), so no Student has a deadline to count from.
  - `[medium]` `[patch]` Edge: a date moved later after the reminder gets no reminder before the real date. `repo.set_deletion_date` clears `deletion_reminded_at` when the date changes and the dedupe key holds the date; test `test_a_date_moved_after_the_reminder_is_told_again_in_its_window`.
  - `[low]` `[reject]` Edge: late registrants / empty roster. Same as the Blind row.
  - `[false]` `[reject]` Edge: clearing the Test deadline with extensions. Same as the Blind row.
  - `[low]` `[reject]` Edge: config change not recomputed. Same as the Blind rows.
  - `[low]` `[reject]` Edge: the backfill could trigger reminders for imminent dates on deploy. No production data exists yet; a reminder for a near date is the wanted behaviour.
  - `[low]` `[reject]` Edge: Hjem with a past date. Same as the Blind row.
  - `[false]` `[reject]` Edge: month 00 or 13 renders «undefined». The value is a Postgres `date` serialised by pydantic; such a string cannot reach the page.
  - `[false]` `[reject]` Edge: the dev route does not hold the row lock. `pass_test_deadline` reads the row with `lock=True` before the update and the refresh.

## Design Notes

A date, not an instant: deletion happens on an Oslo calendar day, matching lane 1's placeholder (`add_months(test_deadline in Oslo, 6)`). The reminder marker column keeps the finder from returning the same session every minute for 14 days; the notice's dedupe key alone makes the act idempotent.

## Verification

**Commands:**
- `uv run pytest tests/platform/test_retention.py tests/sessions/test_deletion_date.py tests/individual_test/test_extension.py tests/test_imports.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/games src/modules/sessions src/components` -- pass

## Auto Run Result

Status: done

**Summary.** `class_sessions.deletion_date` (migration 0305, backfilled) is the latest effective Test deadline (the Class session's or the latest Student extension) on the Oslo calendar plus `RETENTION_MONTHS` (placeholder 6), by one pure rule in `app/platform/retention.py` (`add_months`, `latest_test_deadline`, `deletion_date`): the same rule as lane 1's `ops/retention.py` placeholder, which can delegate to it at merge. `sessions.service._store_deletion_date` is the only writer, in the transaction of every Test deadline save, every extension (`save_extension`; `extend_deadline` now locks the row for update) and the dev route that passes the dates. Hjem: `EnrolledSessionOut.deletion_date`, and under «Rapport» (locked or open) «Dataene dine fra denne Klasseøkten slettes 18. juni 2027. Last ned Studentrapporten før det.». Sweep action `sessions.send_deletion_reminder`: `DELETION_REMINDER_DAYS` (placeholder 14) before the date, one `deletion_reminder` digest per registered Student (archived Classes included), keyed by session, date and Student; a moved date clears the mark.

**Implementation note.** Step 3 ran in the builder's own context, as the lane brief says. The rule moved from `app/analysis` to `app/platform` because the analysis purity test forbids `datetime`.

**Files.** Backend: `platform/retention.py`, `platform/config.py`, `sessions/{models,repo,service,schemas,dev,README}`, `tests/commands.py`, `ops/sweep.py`, `events/registry.py`, `messaging/delivery.py`, mail templates `deletion_reminder.{txt,html}.j2` and `_deadline.j2` (`day`), migration 0305; tests `tests/platform/test_retention.py`, `tests/sessions/test_deletion_date.py`, `test_migrations.py` (0305 backfill, head), `test_dates.py`, `test_deadline_reminders.py`. Frontend: `components/stegene.tsx` (action under a locked step), `modules/games/student-hjem.tsx` (`DeletionLine`), `modules/sessions/dates.ts` (`calendarDateText`), `copy/nb.ts`, regenerated api client, tests `deletion-line.test.tsx`, `components.test.tsx`, `dates.test.ts`, e2e `student-report.spec.ts`.

**Review.** Two layers, 20 findings: 0 high, 1 medium, 13 low, 6 false. Patched: the reminder re-arms when the date moves (medium, with its low twin). Nothing deferred; the rest rejected with reasons above. Follow-up review: false (one medium patched, covered by a test).

**Verification.** Full backend suite (8 processes): 3792 passed, 1 failed (`tests/ai/test_gateway.py::test_a_mock_answer_is_validated_and_logged_with_every_field`, unrelated, passes alone); ruff check and format pass. Frontend: typecheck, Vitest 1221 passed, lint:colours, check:copy, build (in the image). Playwright (lane stack, 4 workers): student-report, homes, student-home, order-field, order-confirm, game-end, completion: 62 passed; after the patch student-report, homes, student-home: 34 passed (axe at both widths in student-report). No new test over 1 s except the 0305 migration test (about 2 s; it migrates a schema).

**Decisions taken for the founder [ASSUMPTION].** The date is an Oslo calendar day (data deleted on that day); placeholders 6 months and 14 days; existing rows backfilled with 6 months; the reminder goes to every registered Student of the Class (archived Classes too), again if the date moves; Hjem line and mail copy as above (draft).
