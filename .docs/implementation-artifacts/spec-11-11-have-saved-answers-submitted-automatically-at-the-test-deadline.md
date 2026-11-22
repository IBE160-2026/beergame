---
title: 'Story 11.11: Have saved answers submitted automatically at the Test deadline'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '5d1e7e57ffe12d1f705f34b8552d1019d09605a9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-10-review-and-submit-the-individual-test.md'
  - '{project-root}/.docs/implementation-artifacts/spec-12-1-switch-the-ai-assessment-off-for-a-class-session.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** At the Test deadline nothing hands in a Student's saved answers: an open attempt stays `open` forever, and there is no single place, after the Test-deadline lock, where every attempt is closed (Epic 12 hangs the AI assessment there) (FR-51, FR-18, AD-9).

**Approach:** Add `tests.commands.close_attempt(attempt_id, now)` and a sweep due action `tests.close_attempt` right after `sessions.lock_test`. It closes each due attempt once (new `test_attempts.closed_at`): an open one becomes `auto_submitted`, scored through `score_answers` and recorded with `progress.record_step(test_submitted)`; a submitted one is only marked closed. `lock_test` (12.1 + 11.2) already pins the Scoring guide and the switch; it is extended by nothing but documentation. Hjem marks a never-opened test step past the deadline «ikke gjort, Testfristen er ute»; `tests.service.parts_with_content` exposes which parts of an attempt hold content (FR-17, Epic 13).

## Boundaries & Constraints

**Always:**
- Migration `0128_test_attempt_closed.py`: `test_attempts.closed_at TIMESTAMPTZ NULL`, check `closed_at IS NULL OR status <> 'open'`, partial index on `effective_deadline` `WHERE closed_at IS NULL`.
- `close_attempt(attempt_id, now) -> bool` (True when this call closed it). One transaction: read the attempt's Class session id, share-lock the Class session row through a new `sessions.test_locked_session(s, id)` (None unless `test_locked_at` is set → return False, nothing changes), then the attempt `FOR UPDATE`; nothing when `closed_at` is set or `effective_deadline` is NULL or `> now`. Open → `score_answers(s, attempt, pins)`, `status='auto_submitted'`, `submitted_at = effective_deadline` (the hand-in is what was saved by the deadline, also when the sweep runs late), `record_step(..., TEST_SUBMITTED, effective_deadline, within=s)`. Always `closed_at = now`. Ids and counts only in logs.
- Finder `due_closes(now)`: ids of attempts with `closed_at IS NULL AND effective_deadline <= now`, oldest deadline first, at most 200 per sweep. Due action `DueAction("tests.close_attempt", …)` placed directly after `sessions.lock_test`; act = `close_attempt(UUID, now)`.
- `move_deadline` moves every attempt not yet closed (`closed_at IS NULL`), so a submitted attempt is never closed before the Class session's moved Test deadline.
- `COMMAND_TOPICS["tests.close_attempt"] = {"session", "user"}` (from `record_step`); a submitted attempt's close emits nothing.
- `save_answer` past `effective_deadline` stays 409 `test_deadline_passed` (existing); `open_attempt` past the deadline with no attempt stays 409 `test_deadline_passed` and creates nothing (existing); GET answers `closed` (existing).
- Stegene: `StepOut.closed` also for the current `test` step when `effective_test_deadline <= now` (the test step is current only when not submitted); web shows `nb.homes.student.testClosed` «ikke gjort, Testfristen er ute» [ASSUMPTION, same words as the Replay's].
- `tests.service.parts_with_content(user_id, class_session_id) -> dict[str, bool] | None`: None without an attempt; else for each part present in the frozen items (`choice`, `interactive` = table/number, `long`, `adapted`) whether any of its items has a saved answer with content (not null, not blank text, not a table of only nulls) [ASSUMPTION: the parts].
- Docs: `tests/README.md`, `sessions/README.md`, `lock_test` docstring, sweep comment record the order `sessions.lock_test` → `tests.close_attempt`.

**Never:** No AI assessment or LLM call (Epic 12); no second `lock_test` or a second pin; no change to `submit`'s API behaviour; no answer text in logs; no new table; no extension logic (11.13) or sitting logic (11.12).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Lock before close | session past Test deadline, not test-locked, attempt open | one `sweep.run`: `lock_test` pins, then the attempt is `auto_submitted` | — |
| Not locked | `close_attempt` called with `test_locked_at` NULL | returns False, attempt unchanged | — |
| Auto-submit | open, answers saved | `auto_submitted`, `submitted_at = effective_deadline`, scores stored as 11.10, step recorded, `user`+`session` emitted, `closed_at=now` | — |
| Already submitted | `submitted` | only `closed_at` set; status, scores, `submitted_at` unchanged; nothing emitted | — |
| Repeat | closed attempt | no change, False; finder no longer lists it | — |
| Not due | `effective_deadline > now` | not found; direct call returns False | — |
| Late save | PUT after deadline, before sweep | 409 `test_deadline_passed`; the saved value is what is scored | — |
| Never opened | no attempt past deadline | GET `closed`; POST open 409 `test_deadline_passed`; no row; Hjem test step `current` + `closed` | — |
| Deadline moved | Lecturer moves Test deadline later while one attempt is submitted | both attempts take the new deadline | — |
| Parts | auto-submitted with only a choice answered | `{"choice": True, "interactive": False, "long": False, "adapted": False}` (parts present only) | no attempt → None |

</intent-contract>

## Code Map

- `backend/app/modules/tests/commands.py` -- `submit` (~452) is the lock/score/record pattern; `score_answers` (~417) reuse; `move_deadline` (~511) filter; add `close_attempt`, `due_closes`, `close_due`.
- `backend/app/modules/tests/models.py` -- `test_attempts` (~131): `closed_at`, check, index.
- `backend/migrations/versions/0128_test_attempt_closed.py` -- new; head `0127`. `backend/tests/test_migrations.py` -- head + downgrade.
- `backend/app/modules/sessions/service.py` -- `lock_test` (~3973) docstring; `IndividualTestSession` (~1691) reuse for `test_locked_session`; `stegene` (~1404) + caller (~1377) `test_closed`; `repo.session_row(s, id, share=True)`, `repo.session_pins`.
- `backend/app/modules/sessions/schemas.py` -- `StepOut.closed` doc (~674).
- `backend/app/modules/ops/sweep.py` -- `DUE_ACTIONS` after `sessions.lock_test` (~165); import `tests.commands`.
- `backend/app/platform/events/registry.py` -- `tests.close_attempt` next to `tests.submit` (~174).
- `backend/app/modules/tests/service.py` -- add `parts_with_content`.
- Tests: `backend/tests/individual_test/test_submit.py` helpers (`opened`, `put`, `scores`, `status`, `submit_path`), `tests/sessions/test_dates.py` (`TEST`, `at`), `tests/sessions/test_ai_assessment_switch.py` (sweep order assertion ~146), `tests/sessions/test_student_home.py` (`home`), `app.modules.ops.sweep.run`.
- Frontend: `src/modules/games/home.ts` `stepItems` (~47), `src/copy/nb.ts` `homes.student` (~448), Vitest next to `src/modules/replay/replay.test.ts` pattern; `e2e/individual-test.spec.ts` closed (~256, in the VIEWPORTS loop) and auto-submitted (~589) stand-ins.

## Tasks & Acceptance

**Execution:**
- `0128` migration, `models.py` -- column, check, partial index.
- `sessions/service.py` -- `test_locked_session`; `stegene(test_closed=)` and its caller; `lock_test` docstring; README.
- `tests/commands.py` -- `close_attempt`, `due_closes`, `close_due`, `move_deadline` filter; `tests/service.py` `parts_with_content`; README.
- `ops/sweep.py`, `registry.py` -- due action and topics.
- `backend/tests/individual_test/test_auto_submit.py` (new) -- every matrix row with a fixed clock; sweep order test updated.
- Frontend: `npm run api:generate` (StepOut doc only if changed); `home.ts` test step closed; `nb.ts` `testClosed`; Vitest; e2e: the auto-submitted state moved into the VIEWPORTS loop with axe (closed already there).

**Acceptance Criteria:**
- Given a Class session past its Test deadline with an open attempt holding saved answers, when `ops.sweep` runs once, then the Test-deadline lock runs first and the attempt is `auto_submitted` with its answers scored and the step recorded; a second sweep changes nothing.
- Given an auto-submitted attempt, when the Student opens the test, then «Testfristen er passert. Svarene dine ble levert automatisk.» shows with read-only answers (Playwright 320/360/1440 + axe).
- Given a Student who never opened the test, when the deadline has passed, then the page shows «Testfristen er passert. Testen er ikke levert.» and Hjem's test step reads «ikke gjort, Testfristen er ute».

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, per the team lead's brief for deadlines and sweeps). The implementation was done in the main context per the brief, not by a step-03 subagent.
- verdicts: 30 findings — high 0, medium 0, low 14, false 16, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: Hjem says «ikke gjort, Testfristen er ute» for an opened attempt between the deadline and the sweep, while the copy comment said "never opened" — the comment now names both cases; the line is true in that minute (not handed in, deadline out) and turns «ferdig» when the sweep emits `user:<id>`. Checking for an attempt from `sessions` would need a new provider for a one-minute state.
  - `[low]` `[patch]` Blind: the 200-per-sweep cap and its order are untested — new `test_a_sweep_closes_at_most_its_share_oldest_deadline_first` (cap 1: the earlier deadline first, the rest next sweep).
  - `[false]` `[reject]` Blind: an opened attempt with no answers is auto-submitted and marked done — the AC says an open attempt is auto-submitted and `test_submitted` recorded; whether it counts for Completion is the FR-17 minimum, which `parts_with_content` serves (Epic 13).
  - `[false]` `[reject]` Blind: no backfill; old open attempts past a locked deadline are auto-submitted at the first sweep — that is the intended catch-up (the sweep repairs what it missed, AD-9), with `submitted_at` the deadline; nothing is deployed yet.
  - `[false]` `[reject]` Blind: `test_locked_ids` leaks the `sessions` table shape — `sessions` builds the whole subquery; `tests` names no `class_sessions` column.
  - `[false]` `[reject]` Blind: lock order not shown safe — `save_answer` and `submit` share-lock the Class session row (`individual_test_session_of`) before the attempt `FOR UPDATE`, the same order as `close_attempt`; `extend_deadline` is not built.
  - `[false]` `[reject]` Blind: `move_deadline` overwrites extensions of early hand-ins — no extension exists before Story 11.13, whose note stays on the mover; `judge_dates` raises `DeadlinePassed` for a passed date.
  - `[false]` `[reject]` Blind: `parts_with_content` speculative; dict values, missing `type` — the AC asks for it through `tests.service`; `_valid` admits only option ids, text, whole numbers or null and lists of those, and every frozen item carries `type` (`_frozen`).
  - `[low]` `[reject]` Blind: the migration test does not check the index; the CHECK hard-codes `'open'` — `test_a_closed_attempt_is_never_open_in_the_database` proves the CHECK; the sibling `ck_test_attempts_submitted` hard-codes `'open'` the same way.
  - `[low]` `[reject]` Blind: `StepOut.closed` shared by Replay and test, no e2e for the Hjem note — the step name tells them apart, as in Stories 10.3/10.6; Vitest and the api test cover it.
  - `[false]` `[reject]` Blind: `_empty` unused, adjacency test brittle — `_empty` is the shared autouse cleanup fixture re-exported as in `test_submit.py`; adjacency is exactly the order the AC requires.
  - `[low]` `[patch]` Blind: README lines over 100 columns; ordering repeated in several places — the two long lines are rewrapped; the repetition is each module's own docstring of its part.
  - `[low]` `[reject]` Edge: an attempt that fails every sweep holds a place in the 200 window — 200 permanently failing attempts are needed to block the rest, each logged by the sweep; a backoff column adds state for a case not shown reachable.
  - `[low]` `[reject]` Edge: `score_answers` raising rolls the close back forever — as in Story 11.10's rejected row: answers are validated against the same version at save time.
  - `[false]` `[reject]` Edge: a failing `lock_test` stalls silently — the sweep logs `sweep_item_failed` for it every minute.
  - `[low]` `[patch]` Edge: Hjem note for an opened attempt before the sweep — same patch as the first Blind row.
  - `[false]` `[reject]` Edge: unknown statuses silently closed — `ck_test_attempts_status` allows only the three statuses; a non-open one is correctly only marked closed.
  - `[false]` `[reject]` Edge: migration burst — same as the fourth Blind row.
  - `[false]` `[reject]` Edge: `move_deadline` overwrites per-Student deadlines — same as the seventh Blind row.
  - `[false]` `[reject]` Edge: `_has_content` misreads dicts — same as the eighth Blind row.
  - `[low]` `[reject]` Edge: a new item type (11.14 `drawn`) is left out of the parts — the content load refuses unknown types, and the test's `PARTS[t]` fails loudly when one appears, so 11.14 extends the map.
  - `[low]` `[patch]` Edge (claim): the spec says never-opened, the code marks any test not handed in — same patch as the first Blind row; the Boundaries line states the deadline rule the code follows.
  - `[low]` `[reject]` Edge (claim): failing attempts defeat "the next sweep takes the rest" — same as the first Edge row.
  - `[low]` `[patch]` Verification: cap and order unpinned — same patch as the second Blind row.
  - `[low]` `[patch]` Verification: a cleared number (null) not tested in `parts_with_content` — the test now saves 4 then null for the number item and asserts the part stays False.
  - `[low]` `[patch]` Verification (other): the interim Hjem state has no test — same root and patch as the first Blind row; the state lasts until the next sweep.
  - `[false]` `[reject]` Intent: page states tested on stand-ins, not a swept attempt — the api test reads `GET …/test` after `sweep.run` (state and answers); stand-ins at 320/360/1440 with axe are the project's e2e pattern (as in 11.10).
  - `[false]` `[reject]` Intent: Hjem wording «ikke gjort, Testfristen er ute» versus «ikke gjort» — the note begins with the AC's words; the page shows the AC's exact «Testfristen er passert. Testen er ikke levert.».
  - `[false]` `[reject]` Intent: `move_deadline` changes 11.3 behaviour — required so `close_attempt` never runs for a handed-in attempt before the Class session's (moved) Test deadline, as the AC demands.
  - `[false]` `[reject]` Intent: `lock_test` "added in this story" already existed — the team lead's brief says to extend the existing seam (Story 12.1), not add a second; 11.2 already pins the guide there.

## Design Notes

- `closed_at` is the "close_attempt ran" marker the story needs because it runs for every attempt, submitted or not; it makes the sweep idempotent and is where Epic 12 defers `assess`.
- `close_attempt` checks the Test-deadline lock itself (not only the finder), so "always after `lock_test`" holds whatever calls it; since `effective_deadline` is never before the original Test deadline, the lock is due in the same sweep, just before.
- Lock order is the Class session row (share) then the attempt row, as in `save_answer`/`submit`; `lock_test` holds the session row `FOR UPDATE`, so a close waits for a running lock.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/sessions/test_ai_assessment_switch.py tests/test_migrations.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/games src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** At the Test deadline the sweep now hands in saved answers. Right after `sessions.lock_test` (which already pins the «KI-vurdering» switch and the Scoring guide in force), a new due action `tests.close_attempt` closes each attempt whose `effective_deadline` has passed, one per transaction with its id, at most 200 a sweep, and only in Class sessions the lock has run for (`sessions.test_locked_ids`). `tests.commands.close_attempt` share-locks the Class session row (`sessions.test_locked_session`; None before the lock, so nothing happens) and then the attempt row. An `open` attempt becomes `auto_submitted` as of its deadline: its saved answers are scored exactly as at a hand-in (`score_answers`), and `test_submitted` is recorded through `progress.record_step` (emits `user` and `session`, registered as `tests.close_attempt`). A handed-in attempt is only marked closed. `closed_at` (migration 0128) makes it run once for every attempt, so it is the one place Epic 12 can start the assessment. `move_deadline` now moves every attempt not yet closed, so an early hand-in is never closed before the Class session's moved deadline. A save after the deadline stays 409 `test_deadline_passed`; a Student who never opened gets no attempt (`closed`, 409 on open). Hjem marks the current test step past the deadline «ikke gjort, Testfristen er ute». `tests.service.parts_with_content` tells Epic 13 which parts (choice, interactive, long, adapted) hold content.

**Files.**
- `backend/migrations/versions/0128_test_attempt_closed.py` (new), `backend/app/modules/tests/models.py`: `closed_at`, check, partial index.
- `backend/app/modules/tests/commands.py`: `close_attempt`, `due_closes`, `close_due`, `CLOSES_PER_SWEEP`, `move_deadline` filter, the order documented.
- `backend/app/modules/tests/service.py`: `parts_with_content`, `PARTS`.
- `backend/app/modules/sessions/{service.py, repo.py, schemas.py}`: `test_locked_session`, `test_locked_ids`, Stegene `test_closed`, `lock_test` docstring.
- `backend/app/modules/ops/sweep.py` (due action), `backend/app/platform/events/registry.py` (topics), `tests/README.md`, `sessions/README.md`.
- Tests: `backend/tests/individual_test/test_auto_submit.py` (new, 12 tests), `test_open.py` (moved-deadline rule), `tests/test_migrations.py` (head 0128).
- Frontend: `src/modules/games/home.ts` (test step note), `home.test.ts`, `src/copy/nb.ts` (`homes.student.testClosed`), `e2e/individual-test.spec.ts` (auto-submitted state at 320/360/1440 with axe). The OpenAPI schema did not change.

**Review.** Four sonnet reviewers reported 30 findings: high 0, medium 0, low 14, false 16. Patched (low): the cap and order test, the cleared-number case of `parts_with_content`, the copy comment on the Hjem note, two README lines rewrapped. Nothing deferred. Every rejection has its reason in the triage log.

**Follow-up review: not recommended.** Patched: high 0, medium 0, low 4 (root causes).

**Verification.**
- Backend: full suite with `--maxprocesses=8`: 3368 passed (before the review patches); after them the touched files' tests (`test_auto_submit`, `test_open`, `test_submit`, `test_ai_assessment_switch`): 39 passed. `ruff check` and `ruff format --check` clean; the migration round trip passes. New tests take 1.2-1.8 s each: the shared `opened()` setup (lock, allocation, open) and one or two full `sweep.run` calls.
- Frontend: `tsc` clean, Vitest 1075 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt): individual-test, homes, student-home, order-confirm, order-field, week-table, game-start, guided-week: 132 passed.

**Decisions taken for the founder.**
- An auto-submitted attempt's hand-in time (`submitted_at`) and its `test_submitted` step are the deadline, not the sweep's minute.
- An attempt handed in early follows a later move of the Class session's Test deadline, so nothing closes before it.
- Hjem's note for a test not handed in after the deadline reuses the Replay's words «ikke gjort, Testfristen er ute» [ASSUMPTION]; it also shows in the minute before the sweep hands an opened attempt in.
- The parts for Completion are choice, interactive (table and number), long and adapted [ASSUMPTION]; an opened attempt with no answers is still auto-submitted.
- At most 200 attempts close per sweep minute.

**Personal data.** No new table. `test_attempts` gains `closed_at` (a time, no text).

**Residual risks.**
- Story 11.13 must keep Students with their own extension out of `move_deadline`, which now also moves early hand-ins.
- Story 12.2 must defer the assessment inside `close_attempt`, the one place that runs for every attempt.
