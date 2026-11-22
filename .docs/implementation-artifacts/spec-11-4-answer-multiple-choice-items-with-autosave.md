---
title: 'Story 11.4: Answer multiple-choice items with autosave'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '42c98b8afa7f41aff075ca9541e5727656410744'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-3-open-the-individual-test-with-the-own-work-statement.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The open Individual test (11.3) lists items but nothing can be answered: there is no `save_answer` command, no answer in the test the page reads, no autosave and no computed score for multiple-choice items (FR-51, FR-52, AD-1, AD-9, AD-10, UX-DR65).

**Approach:** `tests.commands.save_answer` (attempt row `FOR UPDATE`, upsert keeping the highest revision) behind `PUT /api/me/class-sessions/{id}/test/answers/{item_id}`; `GET`/`POST …/test` items carry `options` and the stored `answer`; the page renders choice items with `QuizChoice`, autosaves each change with a rising revision, keeps unsent answers in `lib/drafts.ts` and retries; `analysis.scoring.score_choice` is the pure scorer.

## Boundaries & Constraints

**Always:** `save_answer(user, class_session_id, item_id, value, revision, now)` runs in one transaction: the Student's own locked session via `sessions.individual_test_session_of` (else None → 403 `forbidden`, also when no attempt exists), the attempt row `SELECT … FOR UPDATE`; status ≠ `open` → 409 `attempt_submitted`; `effective_deadline` ≤ now → 409 `test_deadline_passed`; item not in the frozen list → 422 `unknown_item`; value invalid for the item (choice: one of the item's option ids) → 422 `invalid_answer`; other item types → 422 `invalid_answer` until 11.5/11.6 extend the validator. Insert `ON CONFLICT (attempt_id, item_id) DO UPDATE … WHERE test_answers.revision < excluded.revision`; always answer 200 with the stored `{item_id, value, revision, saved_at}` (a lower or equal revision changes nothing and is no error). No event emitted (registry `tests.save_answer: frozenset()`); no answer value in logs. Each item out gets `options` (choice only, else `[]`) and `answer` (stored `{value, revision, saved_at}` or null); never weight, answer key or score. `score_choice(answer, key) -> ChoiceScore(answered, correct, credit)` pure, in `backend/app/analysis/scoring.py`. Frontend: one `QuizChoice` per choice item (legend = item title, option text «Alternativ A» from copy since the draft set has option ids only); a change raises the item's revision by one, writes `{value, revision}` to `drafts.ts` under field `test:<sessionId>:<itemId>`, and sends; at most one save in flight per item, the latest value sent after it; success shows «Lagret HH:MM» (Europe/Oslo, `role="status"` polite) and clears the draft when the stored revision ≥ local; a stored answer from a higher revision (another device) replaces the local one; network/5xx failure shows «Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.» and retries every 5 s and on `online`; 409/403/422 drop the draft, stop retrying, show the refusal in words and read the test again. On load a draft with a revision above the stored one is shown and sent. A refetched test (live `user` topic) only replaces an item whose stored revision is above the local one.

**Never:** No right/wrong state, explanation or score in the api response or page; no scoring in the browser; no table/number/long answering (11.5/11.6), no submit (11.10), no sweep close (11.11); no new table or migration; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First save | open attempt, `{value:"b", revision:1}` | 200 stored rev 1, `saved_at`=now; GET item shows `answer` | — |
| Change | stored rev 1, send rev 2 `"c"` | stored rev 2 `"c"` | — |
| Stale | stored rev 3, send rev 2 | 200 with stored rev 3, unchanged | no error |
| Two devices | rev 2 and rev 3 at once | rev 3 stored either order | row lock serialises |
| Bad value | `"z"` not an option, or a non-choice item | nothing stored | 422 `invalid_answer` |
| Unknown item | id not in frozen list | nothing stored | 422 `unknown_item` |
| Deadline | `effective_deadline` ≤ now | nothing stored | 409 `test_deadline_passed` |
| Submitted | status `submitted` | nothing stored | 409 `attempt_submitted` |
| Other caller / no attempt | other Student, Lecturer, bad id, own session not opened | nothing stored | 403 `forbidden` |
| Offline | save fails (network) | failure line, draft kept, retried until stored | retry |

</intent-contract>

## Code Map

- `backend/app/modules/tests/commands.py` -- add `save_answer`, `AttemptSubmitted`, `UnknownItem`, `InvalidAnswer`; attempt `FOR UPDATE` (`select(test_attempts).with_for_update()`), upsert on `uq_test_answers_item` with `where` on revision; reuse `DeadlinePassed`; update docstring.
- `backend/app/modules/tests/models.py` -- `test_answers` (exists since 0123; no migration).
- `backend/app/modules/tests/attempt.py` -- `_items` adds `options` (from `content.get(QUESTION_SET, version)`) and the stored answers (select `test_answers` by attempt id); `save(user, id, item_id, value, revision, now)` wrapper.
- `backend/app/modules/tests/schemas.py` (~199) -- `TestAnswerIn {value: JsonValue, revision: int 1..1_000_000}`, `SavedAnswerOut`, `StoredAnswerOut`; `IndividualItemOut.options`, `.answer`.
- `backend/app/modules/tests/routes.py` (~249) -- `PUT {_TEST}/answers/{item_id}` `saveMyTestAnswer`, action `tests.take_own`.
- `backend/app/analysis/scoring.py` -- `ChoiceScore`, `score_choice`.
- `backend/app/platform/events/registry.py` (~166) -- `tests.save_answer: frozenset()`.
- `backend/app/modules/tests/README.md` -- save path.
- Tests: `backend/tests/individual_test/test_answer.py` (new; fixtures from `test_open.py`: `locked_session`, `replayed`, `path`, `call`, `clock`), `test_open.py` (item keys now include `options`, `answer`), `backend/tests/analysis/test_scoring*.py` (find existing; add choice cases).
- Frontend: `src/modules/tests/api.ts` (`saveMyTestAnswer`), new `src/modules/tests/autosave.ts` (pure state transitions: init/merge/draft/apply result) + `autosave.test.ts`, new `src/modules/tests/choice-item.tsx` (QuizChoice + status line, hook `useAutosave`), `individual-test-page.tsx` (`Items` renders choice items with it; needs `user.id`), `copy/nb.ts` (`tests.individual.saved(time)`, `notSaved`, `option(letter)`, `saveErrors`), `npm run api:generate`.
- Reuse: `components/quiz-choice.tsx` (no `marks`), `lib/drafts.ts`, `modules/sessions/dates.ts` `osloDayAndTime`.
- e2e: `frontend/e2e/individual-test.spec.ts` -- stand-in PUT route: idle, selected+saved, save-failed (500) then recovered, at 320/360/1440 with axe; 44 px rows; keyboard (Tab + arrows) choose; live test answers one choice and reload shows it.

## Tasks & Acceptance

**Execution:**
- Backend scoring, command, attempt read/save, schemas, route, registry, README.
- Backend tests: every matrix row, gather race, item keys (no score/key), `score_choice` right/wrong/unanswered.
- `npm run api:generate`; frontend autosave logic + Vitest; choice item; copy; page.
- e2e as mapped.

**Acceptance Criteria:**
- Given an open attempt with a choice item, when the Student picks an option, then the row shows chosen, «Lagret HH:MM» appears in a polite status region, and a reload shows the same choice without any right/wrong mark.
- Given the save fails, when the Student keeps working, then the failure line shows, the choice stays after a reload on the same device, and it is stored once the api answers again.
- Given 320/360/1440 px, then each option row is ≥ 44 px, operable by keyboard, and axe passes in idle, selected, saved and save-failed states.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four per the runbook, since the change adds a concurrent write path and a deadline refusal). Generated `openapi.json`/`schema.ts` and this spec left out of the review diff.
- verdicts: 30 findings — high 0, medium 0, low 22, false 7, maybe-false 1
- findings:
  - `[low]` `[reject]` Blind: two devices from the same stored revision both send stored+1; the first is kept and the second device shows it with «Lagret» — the page shows the answer that is stored (truthful), AD-10's rule is the highest revision; a notice per tie adds a state for a rare case.
  - `[low]` `[reject]` Blind: options read «Alternativ A/B/C» — the draft set has option ids only and real texts are issue #16's deliverable; recorded as a founder decision.
  - `[low]` `[reject]` Blind: radios stay enabled after a 409 refusal — each further pick is refused again and shows why; 11.10/11.11 give the page its handed-in state, which replaces the items.
  - `[false]` `[reject]` Blind: `attempt_submitted` for `auto_submitted` too — the only non-open statuses are `submitted` and `auto_submitted`, both handed in; `end_sitting` submits (status `submitted`), per the write-path decision.
  - `[low]` `[reject]` Blind: `JsonValue` unbounded, fixed 5 s retry storm — every JSON route parses its whole body before validation (pre-existing, no app-wide body cap); a retry only runs for an item with an unsent change, one at a time, as the spec sets (5 s and on `online`).
  - `[low]` `[patch]` Blind: every 4xx but 401/408/429 dropped the draft (400, 404, 413 too) — `refusedForGood` now only for 403, 409, 422 (the spec's list); Vitest covers 400, 404, 429.
  - `[low]` `[reject]` Blind: `merge` described as a live update while saves emit nothing — the test is read again on other events (`user` topic), focus and load; Design Notes record the no-event decision.
  - `[low]` `[patch]` Blind: test gaps — the stale-save test now moves the clock and asserts the whole stored answer, `saved_at` unchanged; the other gaps are covered (deadline mover in `test_open.py`), test-local (one held save at a time in the viewport test) or need no case (`score_choice` key is validated as an option at load).
  - `[false]` `[reject]` Blind: generated client missing — left out of the review diff on purpose; regenerated and committed in the tree.
  - `[false]` `[reject]` Blind: drafts kept on a shared machine — «Logg ut» runs `clearAllDrafts` (`lib/drafts.ts`), the same rule as every draft since 6.12.
  - `[false]` `[reject]` Blind: `__all__` order and one status region per item — `ruff check` passes; one polite region per item keeps the line beside the answer it describes, announced without moving focus.
  - `[low]` `[reject]` Edge: same-revision tie adopted silently — same as the first Blind row.
  - `[low]` `[reject]` Edge: refused item stays enabled — same as the Blind row.
  - `[low]` `[patch]` Edge: transient 4xx dropped the draft — same fix as the Blind row.
  - `[low]` `[reject]` Edge: retries forever every 5 s, also on an ended session — the copy promises «vi prøver igjen», and the draft survives a re-login; only items with an unsent change retry.
  - `[maybe-false]` `[reject]` Edge: an exception in the success handler counted as a failure — `setQueryData` and `update` do not throw on the api's shapes; would at most be low (a needless retry of a stored answer).
  - `[low]` `[reject]` Edge: a refusal line stays while a new save runs — replaced by the save's result a moment later; changing it adds a state.
  - `[low]` `[reject]` Edge: `JsonValue` unbounded — same as the Blind row.
  - `[low]` `[reject]` Edge: revision past 1 000 000 — a million changes to one item is not reachable in use.
  - `[low]` `[patch]` Edge (claim): code drops drafts for more 4xx than the spec says — same fix as the Blind row.
  - `[low]` `[patch]` Verification: the timed retry was unverified — new e2e with `page.clock`: a 503, no `online` event, `fastForward(5000)`, the same body sent again and «Lagret».
  - `[low]` `[patch]` Verification: a change during a running save was unverified — the same e2e picks B while A is held and asserts the second PUT `{b, 2}` after A returns.
  - `[low]` `[reject]` Intent: the live test runs at one width without failure states — the repo's pattern (stand-ins per width, one live test); failure states are network-level by nature.
  - `[low]` `[reject]` Intent: `save_answer` takes the user and Class session, not an attempt — the command resolves the attempt under the row lock, like `open_attempt`; the epic's signature names the arguments, not their shape.
  - `[low]` `[reject]` Intent: the two-device test is a repeated race, not deterministic — the `WHERE revision <` guard keeps the highest regardless of order, and the row lock serialises; three rounds run.
  - `[low]` `[patch]` Intent: no right/wrong assertion beyond idle — the e2e now asserts no «Riktig», «Ditt svar, ikke riktig» or `data-quiz-mark` after the saved and failed states.
  - `[low]` `[reject]` Intent: the hook has no unit test — its paths run in e2e (pick, coalesce, timed retry, online, reload draft, refusal).
  - `[false]` `[reject]` Intent: `score_choice` has no caller — the story asks for the pure scorer; Epic 12's assessment reads it.
  - `[false]` `[reject]` Intent: extra draft copy — the option label and refusals need words; marked `[ASSUMPTION]`.
  - `[false]` `[reject]` Intent: generated types not in the patch — same as the Blind row.

## Design Notes

- Option text: the draft question set stores option ids only (`a`, `b`, …); real option texts belong to the content deliverable (issue #16). The page labels them «Alternativ A» from copy; no text is invented in content.
- No event on save: the page that saved has the answer; another device reads it on its next load or `user` refetch. Emitting per click would refetch the whole test on the saving device.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/analysis -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Student answers the multiple-choice items of the open Individual test with Quizvalg (reused unchanged, no marks): each pick raises the item's revision by one, is kept on the device through `lib/drafts.ts` (field `test:<session>:<item>`, per User) and is sent to `PUT /api/me/class-sessions/{id}/test/answers/{item_id}`. `tests.commands.save_answer` locks the attempt row `FOR UPDATE` and upserts only a higher revision; the stored answer comes back either way, so a late or second-device save is no error. Under each item a polite status line reads «Lagret 21:14» (Europe/Oslo) or «Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.»; a failed save is retried every 5 s and at once when the device is back online, and an unsent draft is shown and sent after a reload. A 403/409/422 refusal drops the draft, shows the stored answer again with why, and reads the test again. The test's items now carry `options` and the saved `answer`; no weight, key, score or right/wrong state is sent or shown. `analysis.scoring.score_choice` is the pure scorer. No migration (the tables came with 11.3) and no event per save.

**Files.**
- `backend/app/modules/tests/commands.py`: `save_answer`, `AttemptSubmitted`, `UnknownItem`, `InvalidAnswer`, `_valid` (choice only until 11.5/11.6).
- `backend/app/modules/tests/{attempt,schemas,routes}.py`, `README.md`: items with `options`/`answer`, `save`, `TestAnswerIn`/`SavedAnswerOut`/`StoredAnswerOut`, route `saveMyTestAnswer`.
- `backend/app/analysis/scoring.py`: `ChoiceScore`, `score_choice`.
- `backend/app/platform/events/registry.py`: `tests.save_answer: frozenset()`.
- Tests: `backend/tests/individual_test/test_answer.py` (new, 6 tests), `test_open.py` (item keys), `tests/analysis/test_scoring.py`.
- Frontend: `src/modules/tests/{autosave.ts,autosave.test.ts,choice-item.tsx}` (new), `individual-test-page.tsx`, `api.ts`, `copy/nb.ts`; generated `lib/api/{openapi.json,schema.ts}`.
- e2e: `frontend/e2e/individual-test.spec.ts` (choice states per width with axe, coalescing and timed retry, draft through a reload, refusal, live pick + reload).

**Review.** Four sonnet reviewers, 30 findings: high 0, medium 0, low 22, false 7, maybe-false 1. Patched 5 low entries: refusals for good narrowed to 403/409/422 (others keep the draft and retry), the stale-save test asserts `saved_at` unchanged, a new e2e for a change during a running save and for the timed retry (`page.clock`), and no right/wrong marks asserted in the saved and failed states. Rejected 17 low, 7 false and 1 maybe-false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** No high or medium entry was patched (patched: high 0, medium 0, low 5).

**Verification.**
- Backend: full suite `--maxprocesses=8`: 3240 passed, 4 skipped. `ruff check` and `ruff format --check` clean. New tests over 1 s under parallel load: the `test_answer.py` tests run about 1.0–1.4 s each (a lock sweep and an open per test).
- Frontend: `tsc` clean, Vitest 1065 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081), 101 passed: individual-test (with the new states at 320/360/1440 and axe), homes, student-home, debrief-quiz, order-confirm, order-field, week-table, game-start, guided-week.
- Screenshots at 320 and 1440 of a saved and a failed item, checked by eye: one column, 44 px rows, no sideways scroll, the status line under its item.

**Decisions taken for the founder.**
- Options show as «Alternativ A/B/C» until the real question set (issue #16) gives option texts; the content model has option ids only.
- A save emits no event; another open device sees the answer when it reads the test again (load, focus, another `user` event).
- The status line shows only after a save in this visit; an answer stored on an earlier visit shows chosen with no time.
- Refusal copy «Testen er levert. Svaret ble ikke lagret.», «Testfristen er passert. Svaret ble ikke lagret.», «Svaret ble ikke lagret. Last siden på nytt.» is [ASSUMPTION] draft.
- A tie (two devices sending the same next revision) keeps the first stored; the second device then shows that answer.

**Personal data.** No new table. `test_answers` (answers a Student gave) and `test_attempts` (`user_id`) were noted by 11.3 for Story 15.2's registry.

**Residual risks.**
- Table, number and long answers are refused with 422 `invalid_answer` until 11.5/11.6 extend `commands._valid`.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
