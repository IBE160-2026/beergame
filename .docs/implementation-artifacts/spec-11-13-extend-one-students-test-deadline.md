---
title: "Story 11.13: Extend one Student's Test deadline"
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'c0d7d2384406b83fd93ce91191de2b57ee11b9d6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-12-require-one-timed-sitting.md'
  - '{project-root}/.docs/implementation-artifacts/spec-8-9-give-one-student-more-time-with-tilrettelegging.md'
warnings: ['oversized', 'multiple-goals']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot give one Student with a valid reason a later Test deadline: `effective_test_deadline` and `effective_debrief_deadline` return the Class session's dates for everyone, `move_deadline` writes the Class date onto every attempt, and the reminders go to the whole Class at the Class date (FR-18, AD-9).

**Approach:** `sessions` stores a per-Student extension row (Test and Debrief deadline moved by the same amount); the two effective functions return the later of the Student's own and the Class session's date, read from rows the `sessions` per-Student helpers enrich. `tests.commands.extend_deadline` stores it through `sessions.service` and moves the open attempt's `effective_deadline` in one transaction. A new Studentside block «Frister» holds the in-place form; reminders get a per-Student case.

## Boundaries & Constraints

**Always:**
- Migration `0130_student_deadline_extensions.py`: table `student_deadline_extensions` (`class_session_id` FK CASCADE + `user_id` FK users CASCADE, PK both; `test_deadline timestamptz NOT NULL`; `debrief_deadline timestamptz NULL`; `updated_by` FK users SET NULL; `updated_at NOT NULL`); `deadline_reminders.user_id` NULL FK users CASCADE, unique becomes `(class_session_id, deadline, deadline_at, user_id) NULLS NOT DISTINCT`. Head 0130 in `tests/test_migrations.py`.
- Effective rule: Class date None → None; else `max(class date, own date)` where own exists. `effective_*` on a Mapping read the own dates from keys the per-Student helpers add (`own_test_deadline`, `own_debrief_deadline`); a Mapping without them raises (so no Student path reads the Class date silently). `ClassSessionOut` keeps the Class date. Every per-Student reader goes through an enriched row: `enrolled_sessions` (Hjem), `replay_session_of`, `individual_test_session_of`, `_test_deadline_of` (Replay close/Orders), `student_deadlines` (Debrief, quiz, follow-up). No second function.
- Save rule (`sessions.service.save_extension`, called in the command's transaction): Class session row share-locked; Class writable (409 `class_archived`); the Class session has a Test deadline (else 422 `invalid_extension` `{test_deadline: no_test_deadline}`); new date > the Class session's Test deadline (`not_later`) and > now (`passed`); own Debrief = Class Debrief + (new − Class Test) when the Class has a Debrief deadline, else NULL; existing extension row `FOR UPDATE`, then upsert; `audit.record(actor, "deadline_extension.saved", {class_session_id, user_id}, {test_deadline, debrief_deadline, was}, now)`. No reason field.
- `tests.commands.extend_deadline(user, class_session_id, student_id, test_deadline, now)`: target judged through `sessions.service.student_target` (policy `class_sessions.manage`, Student of the Class now; else None → 403 `forbidden` for Assistant lecturers, other Classes' Lecturers, non-Students alike); one transaction: Class session share-lock, attempt row `FOR UPDATE` when one exists — a `submitted`/`auto_submitted` attempt raises `AttemptSubmitted` (409 `attempt_submitted`) before anything is stored; extension stored; an open, unclosed attempt gets `effective_deadline` = the new effective date; `sitting_ends_at` is never touched; emits `user:<student>` and `session:<id>`; registry `tests.extend_deadline` = {session, user}.
- `move_deadline`: attempts of Students with an extension take `GREATEST(new, own)`, the others the new date (None stays None).
- Route `PUT /api/class-sessions/{session_id}/students/{user_id}/deadline` (operation `extendTestDeadline`, `tests/routes.py`, dependency `authz.require("class_sessions.manage")`), body `{test_deadline: datetime}` → `StudentDeadlinesOut`. `StudentPageOut.deadlines: StudentDeadlinesOut` {class_test_deadline, class_debrief_deadline, test_deadline, debrief_deadline (effective), extended, submitted}.
- Reminders: `reminder_recipients` leaves Students with an extension out of the Class-wide Debrief and Test reminders. New due action `sessions.send_own_deadline_reminder` (after the Class one): finder = each extension's effective Debrief/Test date in `(now, now+24h]` with no reminder row for that user at that time, Class not archived; `send_deadline_reminder(class_session_id, deadline, now=, user_id=)` records a user row and enqueues one `deadline_reminder` (digest kind) keyed `deadline_reminder:<session>:<kind>:<at>:<user>`; a Test reminder is skipped for a Student who has handed in. `deadline_reminder_mail_context`: a user row is valid only for that user at their effective date; a Class row is dropped for a user with an extension.
- Studentside block «Frister» (`frontend/src/modules/reports/deadline-block.tsx`): idle lines with the Student's Testfrist and Debrieffrist (Europe/Oslo), «Forlenget. Klassens testfrist: …» when extended; secondary «Forleng testfrist»; form in place: `datetime-local` «Ny testfrist» prefilled with the effective date, hint with the Class's date, the line «Debrieffristen flyttes like mye. Gjelder bare {name}. Endringen logges.», primary «Lagre frist», «Avbryt». Errors inline on the field (focus to it); result line «Lagret. Ny testfrist for {name}: …» replaces the form and takes focus. Submitted: no button, the line «{name} har levert testen. Fristen kan ikke forlenges.». One form open at a time on the page: opening one closes the other (page-level state; `AdjustmentBlock` takes it as props). Copy in `nb.ts` (`reports.deadline`), marked draft for founder review.

**Never:** No reason field; no change to `sitting_ends_at`; no second effective function; no earlier date than the Class session's; no removal of an extension (not asked); no change to `lock_test` or the pin at the original deadline; no demo-Class change; no DB-vs-host time comparison; no answer text or dates in logs (ids only).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Extend, attempt open | Class Test T, Debrief D, new T+3d | row (T+3d, D+3d); attempt `effective_deadline` T+3d, `sitting_ends_at` same; audit; events | — |
| Extend, not opened | no attempt | row stored; open later reads T+3d | — |
| Not later / past | new ≤ T, or ≤ now | nothing stored | 422 `invalid_extension` `not_later` / `passed` |
| Handed in | attempt submitted or auto_submitted | nothing stored | 409 `attempt_submitted` |
| No Test deadline | Class Test NULL | nothing stored | 422 `no_test_deadline` |
| Assistant / other Lecturer / non-Student | PUT | — | 403 `forbidden` |
| Archived Class | PUT | — | 409 `class_archived` |
| Class deadline passes | sweep at T+1m | `lock_test` runs; others closed; extended attempt open until T+3d, then closed | — |
| Class deadline moved | Class T → T2 | extended attempt `GREATEST(T2, own)` | — |
| Gates | after T, before own | Debrief, quiz, Replay start, Replay close, open test follow own date | — |
| Reminders | T−23h; own T+3d | Class Test reminder skips the Student; own reminder at T+3d−24h once | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/service.py` -- `effective_debrief_deadline`/`effective_test_deadline` (~676), `_value` (~588), `_next_deadline` + `enrolled_sessions` (~1376-1490, Hjem), `test_deadline_passed` (~1649), `_test_deadline_of` (~1658, registered with `games`), `enrolled_locked_row`/`replay_session_of`/`individual_test_session_of` (~1765-1830), `student_deadlines` (~1917), `register_test_deadline_mover` (~1847), reminders `reminder_recipients` (~4754), `due_deadline_reminders`, `send_deadline_reminder` (~4845), `deadline_reminder_mail_context` (~4884); `_class_for`, `_writable` patterns.
- `backend/app/modules/sessions/adjustments.py` -- `_reach`/`_page` (Studentside; move the reach into `service.student_target`, add `deadlines`).
- `backend/app/modules/sessions/{models.py (deadline_reminders ~211, student_adjustments), repo.py (due_deadlines ~479, insert_reminder ~507, reminder_row), schemas.py (StudentPageOut), README.md}`.
- `backend/app/modules/tests/commands.py` -- `move_deadline` (~554), `AttemptSubmitted`; new `extend_deadline`. `tests/routes.py` (route), `tests/schemas.py` (body), `tests/README.md`.
- `backend/app/modules/ops/sweep.py` (~337 reminder DueAction), `backend/app/platform/events/registry.py` (~207), `backend/app/platform/audit` (`record`).
- Tests reuse: `tests/sessions/test_adjustment.py` (`save`, `user_id`, Studentside), `tests/individual_test/test_timed_sitting.py` (`timed`, `open_test`, `attempt`), `test_auto_submit.py` (sweep), `tests/sessions/test_reminders*` (clock, recipients), `tests/replay/test_close.py`, debrief gate tests.
- Frontend: `src/modules/reports/{student-page.tsx, adjustment-block.tsx, api.ts}`, `src/modules/sessions/dates.ts` (`toOsloInput`, `fromOsloInput`, `osloDateText`), `src/components/text-field.tsx`, `src/copy/nb.ts`; e2e `e2e/student-page*.spec.ts` / `support/classes.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0130_student_deadline_extensions.py`, `sessions/models.py`, `sessions/repo.py` -- table, reminder user column, reads/upsert/finders.
- `sessions/service.py` -- effective rule, enriched rows, `student_target`, `save_extension`, `own_test_deadlines`, `deadlines_out`, reminders per Student; `sessions/adjustments.py`, `schemas.py` -- `deadlines` on the Studentside.
- `tests/commands.py`, `routes.py`, `schemas.py`, `registry.py`, `sweep.py` -- command, route, mover, topics, due action.
- `backend/tests/individual_test/test_extension.py` (new) -- every matrix row, gates, reminders with a fixed clock; `test_migrations.py` head.
- Frontend: `npm run api:generate`; `reports/deadline.ts` (+ Vitest), `deadline-block.tsx`, page state in `student-page.tsx`, `adjustment-block.tsx` props, `api.ts`, `nb.ts`; `e2e/deadline-extension.spec.ts` (save, rejected date, the Student's own view on Hjem and the test, 360 and 1440 px, axe).

**Acceptance Criteria:**
- Given a Lecturer on a Student's Studentside, when they open «Forleng testfrist», type a date after the Class's and save, then «Lagret. …» replaces the form with focus and the block shows the new dates; a date not later is refused inline on the field.
- Given a Student with an extension, when they read Hjem or open the Individual test after the Class Test deadline, then their own date shows and the test stays open until it.
- Given the form is open, when the Lecturer opens «Endre tilrettelegging», then the deadline form closes and keeps nothing.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, per the team lead's brief for deadlines and access). The implementation was done in the main context per the brief, not by a step-03 subagent.
- verdicts: 33 findings — high 0, medium 0, low 24, false 9, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: no upper bound on the date; year 9999 overflows the Debrief shift (500), a far typo is accepted — a Lecturer picks the date in a date field; a ceiling needs a new rule, reason and copy for a case not met in use.
  - `[low]` `[patch]` Blind: `extended` stays true after the Class date is moved past the own one — `deadlines_out` now sets `extended` only while the Student's effective date differs from the Class's; the schema docstring says so; asserted in the new reminder test.
  - `[low]` `[reject]` Blind: an extension can never be removed — not asked by the story («only ever extends»); a route, UI and audit action would be new surface. Listed for the founder.
  - `[low]` `[reject]` Blind: the form is prefilled with the Class's date, which it refuses unchanged — the spec's prefill (the Student's date) gives the picker a starting point; saving it unchanged says on the field why.
  - `[false]` `[reject]` Blind: `class_archived` falls to «Prøv igjen», an unknown `invalid_extension` reason to the no-deadline text — `useAction` maps `class_archived` for every action (`SHARED_MESSAGES`, `lib/api/mutation.ts:39`); the api has exactly three reasons, two shown on the field.
  - `[low]` `[reject]` Blind: an auto-submitted attempt is called «levert» — it is handed in (Hjem and the test say «levert» for both); the extension refuses both alike.
  - `[low]` `[reject]` Blind: an own reminder row is recorded with no recipient (handed in, deregistered) — the Class reminder of Story 5.14 records its row the same way; the row stops a repeat; filtering adds a branch for a log count.
  - `[false]` `[reject]` Blind: the raise on a missing key may hit an unaudited caller; `user` unused; `ClassSessionOut` reads the Class date — every caller of the two functions in `app/` was traced (the verification layer confirms); the full suite runs through them; `ClassSessionOut` is never a Student's view.
  - `[low]` `[patch]` Blind: tests do not check the audit's `was`, a session without a Debrief deadline, a naive datetime, concurrency — the `was` assertion is added (Verification row 3); the rest is pydantic's `AwareDatetime` and code paths the matrix tests run.
  - `[low]` `[reject]` Blind: two first saves at once both audit `was: null` — two Lecturers saving the same Student's first extension in the same instant; the stored row stays consistent.
  - `[false]` `[reject]` Blind: the Student is never told — the story asks for `user:<id>` and their own date on Hjem and the test, no notice; the reminders tell them 24 hours ahead.
  - `[false]` `[reject]` Blind: the generated client is not in the diff — `openapi.json`/`schema.ts` were regenerated with `npm run api:generate` and left out of the review diff on purpose; typecheck and Playwright ran on them.
  - `[low]` `[reject]` Blind: no index on the new `user_id` foreign keys; `NULLS NOT DISTINCT` needs Postgres 15 — the stack runs Postgres 17; both tables hold a row per extension or reminder, scanned only on a User's deletion.
  - `[low]` `[reject]` Blind: `move_deadline` updates per extended Student, no sweep cap, `_reach` pass-through, a redundant `moved` check — extensions are a handful per session; the cap guards nothing shown; cosmetic.
  - `[low]` `[reject]` Edge: Debrief shift overflows near year 9999 — first Blind row.
  - `[low]` `[reject]` Edge: an absurdly far date is accepted — first Blind row.
  - `[low]` `[patch]` Edge: `extended` wrong once the Class date passes the own one — second Blind row.
  - `[low]` `[reject]` Edge: the stored own Debrief date is a snapshot when the Class Debrief date moves — read as the later of the two, so a Class move never shortens it; recomputing on every Class save is new coupling for a rare move.
  - `[low]` `[reject]` Edge: the Student is removed from the Class between `student_target` and the transaction — a race of seconds; the row then belongs to a User no longer on the Roster and reads nowhere.
  - `[false]` `[reject]` Edge: a deregistered or handed-in Student yields an item every sweep — the reminder row is inserted on the first run, so the finder skips it after (seventh Blind row covers the one empty row).
  - `[low]` `[reject]` Edge: `send_deadline_reminder(user_id=)` for a Student with no extension stores a row at the Class's time — only the finder calls it, which joins the extensions; a direct call sends nothing.
  - `[false]` `[reject]` Edge: `class_archived` message — fifth Blind row.
  - `[low]` `[patch]` Edge (claim): the `extended` docstring — second Blind row.
  - `[low]` `[patch]` Verification: no test moves the Class date past an extension before a reminder — new `test_reminders_follow_a_class_date_moved_to_or_past_the_own_one`.
  - `[low]` `[patch]` Verification: the Class finder's `user_id IS NULL` is unverified — the same new test moves the Class date onto a Student's reminded own date and asserts the Class finder still lists it and the others are reminded.
  - `[low]` `[patch]` Verification: the audit's `was` is never asserted — assertion added after the second save.
  - `[low]` `[reject]` Verification: the form's 409/server 422 handling is not exercised in a browser — needs a mocked-api component harness the repo lacks; the api side is tested and the client rule refuses the same dates first.
  - `[low]` `[reject]` Intent: the Debrief and quiz gates are proven at the shared reader, not their endpoints — both gates read only `sessions.student_deadlines`, which the test asserts per Student; the Replay through Hjem's `can_start` and the registered reader, the test through its own route.
  - `[low]` `[reject]` Intent: Hjem is checked through its api, not in a browser — the Playwright AC names the Student's own view, shown on the test's statement at 360 and 1440 px; Hjem's api carries the dates its page renders unchanged.
  - `[low]` `[reject]` Intent: a server 422/409 never reaches the field in a browser — fourth Verification row.
  - `[false]` `[reject]` Intent: reminders use a passed `now`, not the api clock — the sweep's clock is its `now` (AD-9); controlled either way.
  - `[false]` `[reject]` Intent: no new authz policy — `class_sessions.manage` is the policy that denies Assistant lecturers and other Classes' Lecturers; the route depends on it.
  - `[false]` `[reject]` Intent: `extend_deadline` takes the Student and the clock beyond the AC's signature — the AC's tuple omits whom it extends; every command takes `now`.

## Design Notes

- `sessions` cannot import `tests`; `tests` owns the command, so the route lives in `tests/routes.py` and answers only the block (`StudentDeadlinesOut`), which the page merges into its cached Studentside.
- The effective functions stay synchronous: the per-Student helpers read the extension in the same session and add the two keys, so no caller changes shape; the raise on a missing key makes a forgotten path fail in tests rather than show the Class date.
- Lock order Class session row → attempt row, as `save_session` → `move_deadline`, so a concurrent Class-deadline save and an extension serialise.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/sessions tests/replay tests/debrief tests/test_migrations.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/reports` -- pass
- `npx playwright test e2e/deadline-extension.spec.ts e2e/homes.spec.ts e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can now give one Student a later Test deadline. The Studentside has a block «Frister» with the Student's Testfrist and Debrieffrist (Europe/Oslo), «Som klassen.» or «Forlenget. Klassens testfrist: …», and the secondary «Forleng testfrist»; its in-place form («Ny testfrist», a date and time field) is one of the page's forms, so opening «Endre tilrettelegging» closes it and the other way round. `PUT /api/class-sessions/{id}/students/{user_id}/deadline` (`class_sessions.manage`) runs `tests.commands.extend_deadline`: in one transaction the Class session is share-locked, the attempt locked (a handed-in one: 409 `attempt_submitted`), `sessions.service.save_extension` judges the date (422 `invalid_extension`: `not_later`, `passed`, `no_test_deadline`; 409 `class_archived`), locks and upserts the Student's row in the new `student_deadline_extensions` (migration 0130) with the Debrief deadline moved by the same amount, and audits `deadline_extension.saved`; the open attempt takes the new `effective_deadline` while `sitting_ends_at` stays; `user:<id>` and `session:<id>` are emitted. `effective_test_deadline` and `effective_debrief_deadline` (no second function) return the later of the Class's and the Student's own date from rows the per-Student readers enrich (Hjem, the Replay, the test, `student_deadlines` for the Debrief and quiz, the reader `games` closes Replays by); a row that did not come through one raises. `move_deadline` keeps the later of the own and the new Class date. Reminders: the Class's Debrief and Test reminders leave extended Students out, and a new due action `sessions.send_own_deadline_reminder` reminds each of them 24 hours before their own dates (`deadline_reminders.user_id`, same `digest` notice and key shape). `lock_test` still runs at the original Test deadline; the extended attempt closes at its own.

**Files.**
- `backend/migrations/versions/0130_student_deadline_extensions.py` (new), `sessions/models.py`: the table; `deadline_reminders.user_id` with a NULLS NOT DISTINCT unique key.
- `backend/app/modules/sessions/service.py`: `_effective` and the per-Student rows, `student_target`, `deadlines_out`, `save_extension`, `own_test_deadlines`, `InvalidExtension`, the own reminders (`due_own_deadline_reminders`, `send_deadline_reminder(user_id=)`, recipients, mail context).
- `sessions/repo.py` (extension reads, upsert, `due_own_deadlines`, the Class finder's `user_id IS NULL`), `schemas.py` (`StudentDeadlinesOut`, `StudentPageOut.deadlines`), `adjustments.py` (reach through `student_target`, the block on the page), `README.md`.
- `backend/app/modules/tests/{commands.py, routes.py, schemas.py, README.md}`: `extend_deadline`, the route, `DeadlineExtensionIn`, the mover.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py`: the due action and the topics.
- Tests: `backend/tests/individual_test/test_extension.py` (new, 16 tests), `tests/sessions/test_dates.py`, `test_deadline_reminders.py`, `tests/test_migrations.py` (head 0130).
- Frontend: `src/modules/reports/{deadline.ts, deadline-block.tsx, deadline.test.tsx}` (new), `student-page.tsx` (one form at a time), `adjustment-block.tsx` (controlled), `adjustment.test.tsx`, `api.ts`, `src/copy/nb.ts` (`reports.deadline`), regenerated `src/lib/api/{openapi.json, schema.ts}`, `e2e/deadline-extension.spec.ts` (new).

**Review.** Four sonnet reviewers reported 33 findings: high 0, medium 0, low 24, false 9. Patched (low): `extended` now false once a moved Class date passes the own one; tests for the audit's `was`, a Class date moved to and past the own one (both reminder finders). Nothing deferred. Every rejection has its reason in the triage log.

**Follow-up review: not recommended.** Patched: high 0, medium 0, low 3 entries.

**Verification.**
- Backend: full suite `--maxprocesses=8`: 3668 passed, 4 skipped. `ruff check`, `ruff format --check` clean; the migration walk passes (0130 → 0120 → 0064 → 0053 → 0119 …). New tests over 1 s: those in `test_extension.py` that lock a session and run the sweep (1.1-1.9 s), as the sibling Epic 11 files.
- Frontend: `tsc` clean, Vitest 1163 passed, `lint:colours`, `check:copy`, `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt after the patches, fresh app database): deadline-extension, tilrettelegging, individual-test, timed-sitting, homes, student-home, order-confirm, order-field, week-table: 130 passed (axe at 360 and 1440 px for the block, the form and the Student's statement).

**Decisions taken for the founder.**
- The own date is stored absolute; the Student's date is the later of it and the Class's, so moving the Class date later overtakes it, earlier never shortens it; with no Class Test deadline there is nothing to extend (and none applies).
- The Debrief deadline moves by the same amount at save time (a snapshot), read as the later of it and the Class's.
- A date must be after the Class's Test deadline and after now; a saved extension may be changed to any such date; it cannot be removed (not asked).
- A handed-in or auto-submitted attempt cannot be extended (409); a Student who never opened can be extended after the Class deadline and then open the test.
- The route lives in `tests` (the command's owner) and answers the block only; the Studentside block «Frister» and all its Norwegian strings are draft [ASSUMPTION] copy in `nb.ts` (`reports.deadline`) for review.
- The extended Student is not mailed about the extension; they are reminded 24 hours before their own dates.

**Personal data.** New table `student_deadline_extensions` (`user_id`, `updated_by`, the Student's own dates; no text). `deadline_reminders` gains a `user_id` column.

**Residual risks.**
- The form's handling of a server-side 409/422 is unit-tested by mapping only, not in a browser.
- A Class Debrief date moved after an extension leaves the stored own Debrief date as saved (read as the later of the two).
