---
title: 'Story 11.10: Review and submit the Individual test'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'b0eb5861c7901f44b781d326ea721fbd3a01168b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-4-answer-multiple-choice-items-with-autosave.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Student who hands in after the Test deadline reminder was enqueued still gets its digest mail.
    evidence: |-
      reminder_recipients is read when the notice is enqueued 24 hours ahead; deadline_reminder_mail_context, the send-time read, does not check test_submitted. The story narrows reminder_recipients without changing the sweep.
    location: >-
      backend/app/modules/sessions/service.py deadline_reminder_mail_context
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Student can open and answer the Individual test but cannot hand it in: no review of unanswered items, no `submit` command, no stored scores, and the Test deadline reminder still goes to Students who are done (FR-51, FR-18).

**Approach:** Add `tests.commands.submit` (attempt row `FOR UPDATE`, status `submitted` + time, computed scores stored on each saved answer with the question set version, `progress.record_step(test_submitted)` in the same transaction), a `POST …/test/submit` route, a `submitted` state on the test the page reads, and on the page an inline review («Lever testen» → unanswered items as links, the warning, one primary «Lever testen») and a read-only submitted view with focus on «Levert …». `reminder_recipients` leaves out Students with `test_submitted` for the Test deadline.

## Boundaries & Constraints

**Always:**
- Migration `0127_test_answer_scores.py`: `test_answers.score JSONB NULL` (`{answered, credit, criteria: [{code, weight, met, explanation}]}`) and `test_answers.scored_version INTEGER NULL` (question set version), check `score IS NULL OR scored_version IS NOT NULL`.
- `submit(user, class_session_id, now)` → `Submitted(attempt, submitted: bool)` or None (not theirs / not opened). One transaction: Class session via `individual_test_session_of`, attempt `FOR UPDATE`; not `open` → returns it unchanged with `submitted=False` (idempotent command); open and `effective_deadline <= now` → `DeadlinePassed`; else score every saved answer of a non-Adapted frozen item with `tests.scoring.score_answer` (Starting task = the session's pinned one), store `score` + `scored_version`, set `status='submitted'`, `submitted_at=now`, `record_step(..., TEST_SUBMITTED, now, within=s)`. Scoring lives in a helper `score_answers(s, attempt, pins)` that 11.11/11.12 reuse. Logs ids and counts only.
- Route `POST /api/me/class-sessions/{id}/test/submit` (`submitMyTest`, `tests.take_own`): 200 `MyTestOut` in state `submitted`; an already handed-in attempt → 409 `attempt_submitted`; 409 `test_deadline_passed`; 403 `forbidden` for not theirs / not opened.
- `MyTestOut.state` gains `submitted` and `auto_submitted`; new field `submitted_at`; items and saved answers still served; no score, key or weight in the response (FR-54).
- `COMMAND_TOPICS["tests.submit"] = {"session", "user"}` (only `record_step`'s emits); api test asserts exactly those.
- `sessions.service.reminder_recipients(id, "test_deadline")` drops users in `progress.users_with_step(s, id, TEST_SUBMITTED)` (the batch form of `has_step`); other deadlines unchanged; sweep unchanged.
- Page: after the items a primary «Lever testen»; pressing it replaces it with a review section (focus to its heading): «N oppgaver er ikke besvart: 4, 7 og 9.» (each number a link to `#oppgave-<n>`, the item's `li` id) or «Alle oppgavene er besvart.», then «Du kan ikke endre svarene etter at du har levert.», then the one primary «Lever testen» — no dialog. Unanswered = stored value null, blank text, or a table with every cell null (display rule over the cached test, kept in sync by autosave). While any item has an unsent change the submit button is unavailable with «Svarene lagres …».
- Submit success: cache set to the response; «Levert <osloDateText>. Du kan ikke endre svarene.» focused (`tabIndex=-1`), answers shown read-only as text (choice option text, numbers, a read-only table, long text), every item's draft cleared. Failure/timeout: inline `role="alert"` «Det ble ikke lagret. Prøv igjen.», button active, attempt open; `attempt_submitted` reads the test again (shows submitted); `test_deadline_passed` shows its line and reads again.
- `auto_submitted` shows «Testfristen er passert. Svarene dine ble levert automatisk.» with the same read-only answers (11.11 makes the state).
- Copy in `nb.tests.individual.submit`; new strings not quoted by the epic are `[ASSUMPTION]`.

**Never:** No score, right/wrong or weight to the Student; no LLM call; no scoring of long/Adapted answers; no confirmation dialog; no change to `ops.sweep`, `close_attempt` or auto-submit (11.11); no answer text in logs; no new table.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Submit | open attempt, choice + table + number + long answers saved | 200 `submitted`, `submitted_at=now`; choice/table/number answers carry `score` and `scored_version`; long answer `score` null; step `test_submitted` | — |
| Unanswered item | item without answer row | no row is created; nothing stored for it | — |
| Second submit | attempt `submitted` | command returns it unchanged; API 409 `attempt_submitted`; nothing emitted | — |
| Save after submit | PUT answer | 409 `attempt_submitted` (existing); web drops draft, reads test → submitted view | — |
| Past deadline | open, `effective_deadline <= now` | 409 `test_deadline_passed`, attempt stays open | — |
| Not theirs / not opened / bad id | other Student, Lecturer, unknown id | 403 `forbidden` | — |
| Two submits at once | concurrent POSTs | one 200, one 409; scores stored once | — |
| Reminder | Test deadline, one submitted and one not | only the not-submitted Student is enqueued | — |

</intent-contract>

## Code Map

- `backend/app/modules/tests/commands.py` -- `save_answer` (~296) is the lock/raise pattern; add `submit`, `score_answers`, `Submitted`; export.
- `backend/app/modules/tests/scoring.py` -- `score_answer(item, value, task) -> ItemScore|None`; `CriterionScore` in `analysis/scoring.py:153`.
- `backend/app/modules/tests/attempt.py` -- `read`/`_open` (~156); add `submit` service fn and the submitted state; `_items(attempt, pins)`; Starting task via `content.starting_task(content.pinned_version(pins))`.
- `backend/app/modules/tests/models.py` -- `test_answers` (~167): add two columns.
- `backend/migrations/versions/0127_test_answer_scores.py` -- new; head is `0126`.
- `backend/app/modules/tests/routes.py` -- `_TEST` routes (~249); `error_response` codes.
- `backend/app/modules/tests/schemas.py` -- `MyTestOut` (~329).
- `backend/app/platform/events/registry.py` -- add `tests.submit` near `tests.save_answer`.
- `backend/app/modules/sessions/service.py` `reminder_recipients` (~4365); `progress.users_with_step`.
- `backend/app/modules/tests/README.md` -- document submit and score columns.
- Tests: `backend/tests/individual_test/test_answer.py` (`opened`, `put`, `stored`), `test_open.py` (`locked_session`, `replayed`, `code`, `path`), `emitted` fixture; reminder tests in `backend/tests/sessions/` (grep `reminder_recipients`).
- Frontend: `src/modules/tests/{api.ts, individual-test.ts, individual-test-page.tsx, use-autosave.tsx, autosave.ts}`, `src/lib/drafts.ts` (`clearDraft`), `src/modules/sessions/dates.ts` (`osloDateText`), `src/components/{button,action-error}.tsx`, `src/copy/nb.ts` (`tests.individual`), `e2e/individual-test.spec.ts` (stand-ins `standIn`, `ITEMS`, live test with `/api/dev/…/replay-done`).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0127_test_answer_scores.py`, `models.py` -- score columns.
- `commands.py` -- `score_answers`, `submit`.
- `schemas.py`, `attempt.py`, `routes.py`, `registry.py`, `README.md` -- state, service fn, route, topics.
- `sessions/service.py` -- reminder narrowing.
- `backend/tests/individual_test/test_submit.py` (new) -- matrix rows, stored scores equal `score_answer`, topics, concurrency, reminder (submitted vs not).
- Frontend: `npm run api:generate`; `api.ts` `submitMyTest`; `individual-test.ts` `unansweredNumbers`, `submittedLine`, view states; `submitted-items.tsx` (new, read-only answers); `individual-test-page.tsx` review + submitted; `use-autosave.tsx` unsent reporting via context; `nb.ts` copy; Vitest for the pure functions; `e2e/individual-test.spec.ts` review with/without unanswered, submitted, save-after-submit at 320/360/1440 + axe, failure alert, live submit marks Stegene done.

**Acceptance Criteria:**
- Given an open test with items 4, 7 and 9 unanswered, when the Student presses «Lever testen», then «3 oppgaver er ikke besvart: 4, 7 og 9.» shows with three links to those items, the warning, and exactly one primary button «Lever testen».
- Given the review, when the Student presses «Lever testen» and the api stores it, then «Levert … Du kan ikke endre svarene.» is focused, no input is editable, and Hjem's Stegene shows the test step done.
- Given the submit request fails, then «Det ble ikke lagret. Prøv igjen.» shows with `role="alert"` and the button stays active.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, per the team lead's brief: a data-model change, a state transition under a row lock and a deadline). The generated `openapi.json`/`schema.ts` and this spec were left out of the review diff.
- verdicts: 29 findings — high 0, medium 1, low 17, false 11, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: `attempt.submit` read the Class session again after the commit and answered 403 if it was no longer theirs — `commands.Submitted` now carries the pins the command read; the route answers with the committed attempt.
  - `[low]` `[reject]` Blind: a scoring exception rolls back the hand-in — answers are validated against the same version at save time and content records are schema-validated; a guard would add a branch for a state not shown reachable.
  - `[false]` `[reject]` Blind: no row for an unanswered item — deliberate (Design Notes); the attempt's frozen item list with weights tells Epic 12 every item, so a missing row is credit 0.
  - `[low]` `[reject]` Blind: past the deadline the page stays open until the sweep — auto-submit at the deadline is Story 11.11 (intent: build only this story); the line says the saved answers are handed in automatically.
  - `[low]` `[patch]` Blind: focus lost when a 409 `attempt_submitted` re-read shows the handed-in view — the page now marks it just handed in, so «Levert …» takes focus; the e2e test asserts it.
  - `[low]` `[patch]` Blind: the «Svarene lagres …» status region was inserted with its text — the region is now always there (hidden while empty). Rejected part: a failing save keeps the button waiting; each item shows its own failure line and retries every 5 s, and a hand-in offline would fail anyway.
  - `[false]` `[reject]` Blind: «Det ble ikke lagret. Prøv igjen.» is autosave wording — it is the spine's exact line for this failure (AC, UX-DR59).
  - `[low]` `[reject]` Blind: a half-filled table counts as answered — the review lists unanswered items; a partly answered item is answered (spec rule).
  - `[false]` `[reject]` Blind: a choice shows only «Alternativ B», and the AI disclosure is gone — the draft set has option ids only (issue #16) and the open view shows the same; the label comes from `itemLabel`, which keeps the «KI-generert, kan ta feil:» prefix.
  - `[false]` `[reject]` Blind: `auto_submitted` shows no time; a null `submitted_at` renders empty — the auto-submitted line is the epic's exact copy; `ck_test_attempts_submitted` makes `submitted_at` non-null once handed in.
  - `[low]` `[reject]` Blind: the FR-54 check stringifies the body — it holds for the shipped draft content and fails loudly if a score field appears.
  - `[low]` `[reject]` Blind: backend test gaps (extension, zero answers, `auto_submitted` repeat) — extensions are Story 11.13 and auto-submit 11.11; zero answers runs the same path with an empty loop.
  - `[false]` `[reject]` Blind: the downgrade drops scores and the column is personal data — downgrades drop their columns throughout the repo; `score` holds computed codes and explanations, no Student text.
  - `[low]` `[reject]` Blind: the 44 px links stretch the sentence's line height — the 44 px target is required (EXPERIENCE.md); the review stays readable at 320 px in the e2e run.
  - `[low]` `[reject]` Edge: a scoring exception aborts the hand-in — same as the second Blind row.
  - `[low]` `[patch]` Edge: 403 after a committed hand-in — same patch as the first Blind row.
  - `[low]` `[reject]` Edge: `AbortSignal.timeout` missing in old browsers — supported by every browser the app targets; a fallback adds a branch.
  - `[low]` `[reject]` Edge: a failed save keeps «Lever testen» waiting with «Svarene lagres …» — same as the sixth Blind row's rejected part.
  - `[low]` `[patch]` Edge: focus drops to body after the 409 re-read — same patch as the fifth Blind row.
  - `[false]` `[reject]` Edge: a table item without its table shows a stored array as «Ikke besvart» — such items (question set version 1) refuse every answer (`InvalidAnswer`), so no array is stored.
  - `[false]` `[reject]` Edge: null `submitted_at` — same as the tenth Blind row.
  - `[false]` `[reject]` Edge: a session locked before the Starting task pin scores with the latest version — the page showed that same version (`attempt._items`), so the Student answered it.
  - `[medium]` `[patch]` Verification: no test told the pinned Starting task from a later one — new `test_scores_use_the_pinned_starting_task_not_a_later_version` publishes version 2 with a moved row and asserts full credit from the pinned version.
  - `[low]` `[defer]` Verification: a Student who hands in after the Test reminder was enqueued still gets its digest mail — the story narrows `reminder_recipients` "without changing the sweep"; the send-time check belongs with the reminder mail (recorded in `deferred`).
  - `[low]` `[reject]` Verification: the 30 s timeout branch has no test — a two-line conversion to the existing `network_error`; mocking the generated client's fetch for it costs more than it guards.
  - `[low]` `[patch]` Verification: `test_a_save_or_submit_after_the_hand_in_is_refused` overstated its coverage — renamed `test_a_save_after_the_hand_in_is_refused`.
  - `[false]` `[reject]` Verification: the Adapted branch of `score_answers` is not observed — Adapted ids are never in the question set, and `score_answer` returns None for long answers either way.
  - `[false]` `[reject]` Intent: the visible ACs run against stand-ins, the real stack in one viewport — the project's e2e pattern (stand-ins at 320/360/1440 with axe, one live test); the live test covers the hand-in, focus, Hjem's live step and the read-only reload.
  - `[false]` `[reject]` Intent: `tests.scoring` and `users_with_step` instead of `analysis.scoring` and `has_step` — `tests.scoring.score_answer` only picks `analysis.scoring`'s pure rules; `users_with_step` is `progress`'s batch read of the same rows (AD-16).

## Design Notes

- `submit` is idempotent as a command (11.11/11.12 call the same scoring and may meet a submitted attempt), but the API answers a repeat with 409 `attempt_submitted` as the story's save/submit-after-submit criterion requires; the page then reads the test and shows the submitted state either way.
- Scores go on existing answer rows only; an item with no row scores 0 for Epic 12 by absence. Long and Adapted answers keep `score` null (Scoring guide, Epic 12).
- The submitted time uses the app's shared `osloDateText` («to. 18. des. kl. 21:40»), the same format as the Testfrist line, rather than the epic's «des kl.» without the period.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/sessions -k "submit or reminder" -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Student hands in the Individual test once. Under the items one primary «Lever testen» opens a review on the page, with focus on its heading: «3 oppgaver er ikke besvart: 4, 7 og 9.» (each number a 44 px link to its item) or «Alle oppgavene er besvart.», then «Du kan ikke endre svarene etter at du har levert.» over the one primary «Lever testen». No dialog follows. The button waits («Svarene lagres …») while an answer typed on the device is not yet stored. `POST /api/me/class-sessions/{id}/test/submit` (`submitMyTest`) runs `tests.commands.submit`: under the attempt row lock it sets `submitted` with the time, scores every saved choice, table and number answer through `tests.scoring.score_answer` (with the pinned Starting task) into `test_answers.score` with `scored_version`, and records `test_submitted` through `progress.record_step` in the same transaction (topics `session` and `user`, registered as `tests.submit`). A repeat answers 409 `attempt_submitted`; the command itself returns the attempt unchanged, and Stories 11.11/11.12 reuse `score_answers`. Past the deadline the route answers 409 `test_deadline_passed`. The page then shows «Levert fr. 18. des. kl. 21:40. Du kan ikke endre svarene.» with focus and every answer read-only, and drops the test's drafts. A failure shows «Det ble ikke lagret. Prøv igjen.» (`role="alert"`) with the button active; no answer within 30 s counts as a failure. A save or submit after the hand-in gets 409, and the page reads the test again and shows it handed in. Hjem's Stegene marks the step done through the `user:<id>` event. `reminder_recipients` leaves Students with `test_submitted` out of the Test deadline reminder.

**Files.**
- `backend/migrations/versions/0127_test_answer_scores.py` (new), `backend/app/modules/tests/models.py`: `test_answers.score`, `scored_version`.
- `backend/app/modules/tests/{commands.py (submit, score_answers, Submitted), attempt.py (submit, handed-in states), routes.py (submitMyTest), schemas.py (MyTestOut states, submitted_at), README.md}`.
- `backend/app/platform/events/registry.py` (`tests.submit`), `backend/app/modules/sessions/service.py` (`reminder_recipients`).
- `backend/tests/individual_test/test_submit.py` (new, 7 tests), `tests/individual_test/test_open.py`, `tests/test_migrations.py` (head 0127, downgrade step).
- Frontend: `src/modules/tests/{individual-test-page.tsx (Submit, Submitted), submitted-items.tsx (new), individual-test.ts (isAnswered, unansweredNumbers, listSeparator, itemAnchor, submittedLine), use-autosave.tsx (UnsentContext), api.ts (submitMyTest), autosave.ts (draftPrefix), individual-test.test.ts}`, `src/copy/nb.ts` (`tests.individual.submit`), `src/lib/api/{openapi.json, schema.ts}` (regenerated), `e2e/individual-test.spec.ts`.

**Review.** Four sonnet reviewers reported 29 findings: high 0, medium 1, low 17, false 11. Patched: the medium one (a test that tells the pinned Starting task from a later version) and four low root causes (the committed hand-in answered with the command's pins, focus after a 409 re-read, an always-present status region, a test name). Deferred: one low finding (the reminder mail of a Student who hands in after the reminder was enqueued). Every rejected finding has its reason in the triage log.

**Follow-up review: not recommended.** Patched: high 0, medium 1, low 4 (root causes).

**Verification.**
- Backend: the full suite with `--maxprocesses=8` gave 3357 passed. `ruff check` and `ruff format --check` are clean. The new tests take 0.9-1.3 s each. That time is the shared `opened()` setup (lock, allocation, open), as in `test_answer.py`.
- Frontend: `tsc` clean, Vitest 1074 passed, and `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt with the change): 130 passed. The specs were individual-test, homes, student-home, order-confirm, order-field, week-table, game-start and guided-week. Individual-test covers the review with and without unanswered items, the submitted state and save-after-submit at 320/360/1440 with axe. It also covers the failure, the 409 re-read, the waiting state, the auto-submitted state, and a live hand-in in which Hjem's step turns done on another page. The two specs patched after the review were re-run.

**Decisions taken for the founder.**
- The review opens on the page in place of the first button, not as a dialog or a separate page.
- «Lever testen» waits while an answer typed on the device is not yet stored, so nothing typed is left out.
- A partly filled table counts as answered; blank text and a cleared number do not.
- The handed-in time uses the app's date format («fr. 18. des. kl. 21:40»), with the period after the month as in the Testfrist line.
- A repeated submit answers 409 `attempt_submitted`; the command itself stays idempotent.
- Scores are stored only on saved answers; an item never answered has no row (credit 0 for Epic 12).
- New `[ASSUMPTION]` copy: the review heading, «Alle oppgavene er besvart.», «Svarene lagres …», the past-deadline line, «Svarene dine» and «Ditt svar».

**Personal data.** No new table. `test_answers` (already personal data) gains `score` and `scored_version`: computed codes and explanations, no Student text.

**Residual risks.**
- Until Story 11.11, an attempt past its deadline stays `open`, and «Lever testen» answers with the past-deadline line.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
