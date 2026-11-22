---
title: 'Story 9.10: Exclude a quiz question and see quiz attempts'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '9dfae1f2b7ceeb21732fa1cd5127207f43b6a65d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot take a weak Debrief quiz question out, and staff cannot see how many attempts a Student used or when (FR-46, FR-47). The staff Debrief page (Story 9.8) also names no Student, so staff cannot tell whose summary they read.

**Approach:** `modules/debrief` owns a `quiz_exclusions` Class-session table, written only by `debrief.commands.set_quiz_exclusions` (audited, notifies affected Students); the quiz reads «asked = pinned questions minus exclusions». Two staff routes back a «Debrief-quiz» block on the Klasseøkt (answer keys plus a Bryter per question, own save). The staff Debrief summary answers the attempts list and the Student's Roster name.

## Boundaries & Constraints

**Always:**
- Table `quiz_exclusions(class_session_id, question_id)` PK, `quiz_version`, `excluded_by` (user id), `excluded_at` (db time); migration `0109_quiz_exclusions.py`. Lifting deletes the row. No edit of the `content` record.
- Staff read `GET /api/class-sessions/{id}/debrief-quiz` (new policy `debrief_quiz.read`: owners + Assistant lecturers) → `{version, placeholder, pinned, can_exclude, open, test_deadline, questions:[{id, prompt, choices, answer, excluded}]}`. `version` is the pinned one, the latest before the lock (`pinned` false). `can_exclude` = owner (new policy `debrief_quiz.exclude`) and Class not archived; `open` = no Test deadline or database time ≤ the Class session's Test deadline.
- Write `PUT /api/class-sessions/{id}/debrief-quiz/exclusions` body `{excluded: [question_id]}` (the whole wanted set; `debrief_quiz.exclude`). In one transaction holding the Class session's lock: 403 `forbidden` for non-owners/Assistants/outsiders; 409 `class_archived`; 409 `test_deadline_passed` when db now > Test deadline; 422 `validation_error` (`fields.excluded`: `unknown_question`); 409 `last_question` when nothing would be asked. Unchanged set → no write, no audit. Otherwise insert/delete rows, one `platform/audit` row `debrief_quiz.exclusions_changed` (target `class_session_id`, change `{excluded, lifted, quiz_version}` ids only), emit `session:<id>`, and `notify.enqueue(kind quiz_changed, ref=class_session_id, dedupe quiz_changed:<session>:<user>:<audit id>)` for every Student not passed whose last attempt's wrong answers are all now excluded. Answers the same shape as GET.
- Students: asked = pinned questions not excluded, in both GET's next questions and scoring. Answers sent for an excluded question are dropped before scoring (not stored); a still-asked question missing → 422 `incomplete`. No automatic pass; a passed attempt stays passed when an exclusion is lifted.
- Hjem: Stegene's current Quiz step carries `quiz_changed: true` when the Student has not passed and every wrong answer of their last attempt is now excluded (computed, provider registered by `debrief` in `sessions`, like `register_debrief_state`); the note reads «pågår, quizen er endret» (draft). Digest mail kind `quiz_changed` with template (context: Class name, reuse of `debrief_released_mail_context` rules).
- Staff summary (`GET …/students/{id}/debrief-summary`): adds `name` (the Student's Roster name now via `classes.student_names` through `sessions`; null when no longer a Student) and `quiz: {attempts:[{number, submitted_at, passed}], passed_at}`, read through `debrief.service`, also before the summary exists.
- UI: Klasseøkt block «Debrief-quiz» (`modules/debrief/quiz-exclusions.tsx`, after the Choices) for staff: each question with prompt, choices, «Riktig svar: …», and a Bryter «Med i quizen»/«Tatt ut» for owners while `open`; help text on scope; its own secondary button «Lagre quizvalg» (status line after save, ActionError on refusal). Assistants and a closed block show the state as text. Staff summary page shows the name as the page's lead line and a «Debrief-quiz» section: attempts count, each attempt's time and result, passed time or «ikke bestått».

**Never:** no change to a stored attempt or summary; no auto-pass; no LLM text; no name in audit, notices or facts sets; no growth of `tests/debrief/test_explanation.py` or the shared Debrief api test; no Group debrief behaviour (9.11).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Exclude | owner, `{excluded:[q2]}` | row stored, audit row, `session` event; Student's next GET omits q2; passing needs q1,q3 | — |
| Near-pass Student | last attempt wrong only on q2 | notice `quiz_changed`; Hjem Quiz step `quiz_changed`; not passed | — |
| Lift after pass | passed, then `{excluded:[]}` | still passed | — |
| All out | every question excluded | nothing stored | 409 `last_question` |
| Late | db now > Test deadline | nothing stored | 409 `test_deadline_passed` |
| Assistant | PUT | nothing stored | 403 `forbidden`; GET allowed, `can_exclude` false |
| Unknown id | `{excluded:["x"]}` | nothing stored | 422 `validation_error` |
| Stale form | Student answers q2 after it was excluded | q2 answer dropped, scored on rest | — |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/{models.py (quiz_attempts pattern), commands.py (submit_quiz: lock, db-time deadline; release: notify.enqueue), service.py (_quiz, _asked, _order, own_quiz, submit_quiz_mine, staff_summary, _attempts), schemas.py (StaffSummaryOut, Quiz* outs), routes.py (_answer map, staff summary route), rules.py (register_debrief_state pattern), README.md}`.
- `backend/app/analysis/quiz.py:199` `score(quiz, asked, answers)` -- asked set passed in; filter dropped answers in service.
- `backend/app/modules/sessions/service.py` -- `class_staff_may:1297`, `_writable:638`, `_class_for:646`, `register_debrief_state:1233` + `stegene:1199` + call at 1176 (pattern for a quiz-changed provider), `debrief_released_mail_context:2128`, `_names_in`/`classes.student_names`; `repo.session_pins:107`, `repo.session_row`. Add a `quiz_session(...)` read (class id, pins, Test deadline, archived) and `student_name(...)`.
- `backend/app/modules/sessions/schemas.py:564` `StepOut` -- add `quiz_changed: bool = False`.
- `backend/app/platform/{authz.py:119-144 (policies), audit.py:90 record, notify enqueue, events/registry.py (debrief.submit_quiz entry pattern)}`.
- `backend/app/modules/messaging/delivery.py:154-178` + `app/platform/email/templates/kinds/debrief_released.*.j2` -- new kind `quiz_changed`.
- `backend/migrations/versions/0108_debrief_quiz.py` -- pattern for 0109.
- Tests: `tests/debrief/test_quiz.py` (short played game helpers), `tests/test_migrations.py`, `tests/test_authz_rules.py`, `tests/messaging/test_delivery.py`.
- Frontend: `modules/sessions/class-session-page.tsx:407-416` (block placement), `components/switch.tsx`, `modules/debrief/{api.ts, summary-page.tsx, quiz-step.tsx (422 refetch)}`, `modules/games/home.ts:36` stepItems, `copy/nb.ts` (`homes.student`, `debrief.staffSummary`, new `debrief.quizExclusions`), `lib/api/topics.ts` (`session` → exclusions key), regenerated `lib/api/{openapi.json,schema.ts}`; e2e `frontend/e2e/{debrief-quiz.spec.ts, support/quiz.ts, debrief-bill.spec.ts, support/bill.ts}`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0109_quiz_exclusions.py`, `debrief/models.py` -- table.
- `backend/app/platform/authz.py` -- `debrief_quiz.read`, `debrief_quiz.exclude`.
- `backend/app/modules/sessions/{service,schemas}.py` -- `quiz_session`, `student_name`, quiz-changed provider and `StepOut.quiz_changed`, `quiz_changed_mail_context`.
- `backend/app/modules/debrief/{commands,service,schemas,routes,rules}.py`, `README.md`, `platform/events/registry.py` -- set exclusions, staff read, asked set, staff summary fields, provider.
- `backend/app/modules/messaging/delivery.py`, `platform/email/templates/kinds/quiz_changed.{txt,html}.j2` -- kind.
- Tests: new `tests/debrief/test_quiz_exclusions.py` (I/O matrix, notice, Hjem flag, staff summary attempts + name), `tests/test_migrations.py`, authz rules.
- Frontend: `modules/debrief/quiz-exclusions.tsx` (new), `api.ts`, `summary-page.tsx`, `quiz-step.tsx`, `sessions/class-session-page.tsx`, `games/home.ts`, `copy/nb.ts`, `lib/api/topics.ts`, regenerated types, Vitest cases.
- e2e: `frontend/e2e/debrief-quiz-exclusions.spec.ts` (new) -- owner excludes and saves, Assistant reads with no Bryter, staff summary shows name and attempts; axe at 320/360/1440.

**Acceptance Criteria:**
- Given an owner on the Klasseøkt, when the «Debrief-quiz» block shows, then each pinned question lists its choices and answer key with a Bryter and scope help text; an Assistant sees the same without a Bryter.
- Given an excluded question, when the Student opens a new attempt, then it is not asked and passing needs only the rest.
- Given a Student who would have passed without the excluded question, when the exclusion is saved, then they are not passed, a `quiz_changed` notice is enqueued, and Hjem's Quiz step says the quiz has changed.
- Given staff on a Student's Debrief summary page, when the Student has attempts, then the page names the Student and shows the number of attempts, each time and whether passed.
- Given 320, 360 and 1440 px, then axe passes on the Klasseøkt block and the summary page with no sideways page scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-10.md` and `review-edge-9-10.md` in the scratchpad. The review diff left out the generated `openapi.json`/`schema.ts` and `.docs` on purpose.
- verdicts: 32 findings — high 0, medium 0, low 25, false 7, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) Exclusion rows are matched by question id only; `quiz_version` is never read, so a row of another version applies to a same-id question or stays invisible. Needs a new content version published between a pre-lock exclusion and the lock; ids name the same concept across versions. The one harmful case (every question covered) is patched under edge 1.
  - `[false]` `[reject]` (blind 2) Staff and Student read different quiz versions. A Game's `session_runtime.pins` is the session's lock snapshot, so both resolve the same pinned version; before the lock no Student can take the quiz.
  - `[low]` `[reject]` (blind 3) Whole-set PUT is last-write-wins between two owners; a stale draft can undo another owner's change. Two owners editing the same block at once is rare; resetting the draft on every `session` event would discard edits on each Student step (progress emits `session`).
  - `[low]` `[reject]` (blind 4) An attempt committing during an exclusion change may miss the notice. Milliseconds window; Hjem's flag is computed live and stays right; only the digest mail can be missed.
  - `[low]` `[patch]` (blind 5) The `quiz_changed` digest is sent later even if the Student has retried, passed, or the exclusion was lifted. `quiz_changed_mail_context` now re-checks the registered rule and drops the mail when it no longer holds (tested).
  - `[low]` `[patch]` (blind 6) The mail says «et spørsmål» though several may be taken out. Now «tatt ut spørsmål». Draft-copy markers are the project's convention (rejected part).
  - `[false]` `[reject]` (blind 7) The Roster name to Assistant lecturers breaks a guarantee. FR-47 lets Assistant lecturers read every summary and they read the Class Roster; AD-14's "ids only" governs stored facts and links. The route checks `debrief_summaries.read` before `student_name` runs.
  - `[false]` `[reject]` (blind 8) A zero-question quiz refuses every PUT; check order. `DebriefQuiz.questions` is validated 1–20, so a quiz never has zero questions; refusing an invalid body before the deadline check is the house order.
  - `[low]` `[reject]` (blind 9) An open Student quiz form is not told of a change; a stale answer is dropped silently. The result shows «x av y riktige» for what was asked; a 422 now reads the quiz again; emitting every Debrief of the session adds broadcast for a rare case.
  - `[false]` `[reject]` (blind 10) The `["class-sessions", id]` prefix refetches unrelated queries. Only `sessionQuizKey` and `staffSummaryKey` live under it (searched).
  - `[low]` `[patch]` (blind 11) The block vanished while «Prøv igjen» refetched. The error block now stays while the retry runs.
  - `[low]` `[reject]` (blind 12) e2e skips the last-question refusal on phones; read-only states are stubbed. The refusal is one `role=alert` line already checked at 1440 px; the rules are pinned by the api test.
  - `[low]` `[patch]` (blind 13) The README left out "one of them in this change". README updated, with the lift event. The two equal copy strings are separate states (rejected part).
  - `[false]` `[reject]` (blind 14) The generated schema is missing. Regenerated and in the change; typecheck and build pass.
  - `[low]` `[reject]` (blind 15) Migration test checks only columns. Same depth as 0105–0108; `alembic check` in the walk compares the table to the model.
  - `[low]` `[reject]` (blind 16) Hjem makes one quiz-changed read per locked session. A Student has a handful of sessions and the read short-circuits unless the Debrief is done and the quiz not passed.
  - `[low]` `[reject]` (blind 17) `pinned`/`can_exclude` in the PUT answer are read before the lock. Only a lock in the same second differs; the next read (the `session` event) corrects it.
  - `[low]` `[patch]` (edge 1) Rows of another version covering every question would leave nothing asked and the quiz unpassable. `_asked` now asks every question then (unit test).
  - `[low]` `[reject]` (edge 2) Same as blind 1.
  - `[low]` `[reject]` (edge 3) Same as blind 4.
  - `[low]` `[reject]` (edge 4) Same as blind 17.
  - `[low]` `[patch]` (edge 5) Same as blind 5; same fix.
  - `[low]` `[patch]` (edge 6) A lift that ends «quizen er endret» emitted no `user` event, so Hjem kept the line until reload. The command now emits `user:<id>` for each Student whose flag a lift turns off (tested).
  - `[low]` `[reject]` (edge 7) The flag shows after the Test deadline. The Quiz step stays «pågår» then anyway; the attempt's refusal says why.
  - `[false]` `[reject]` (edge 8) Same as blind 8.
  - `[low]` `[reject]` (edge 9) Unbounded `excluded` list. Every id is checked against the version before any write; same as the other bodies.
  - `[low]` `[reject]` (edge 10) A session deleted between the read and the lock gives 500. Class sessions are not deleted in the product.
  - `[low]` `[reject]` (edge 11) Same as blind 3.
  - `[low]` `[patch]` (edge 12) After a `test_deadline_passed`/`class_archived` refusal the Bryters stayed. The block now reads the quiz again on those codes, so it shows its read-only state.
  - `[false]` `[reject]` (edge 13) The new e2e has no reflow check. `expectAccessible` runs `expectReflow` (support/classes.ts).
  - `[low]` `[reject]` (edge 14) No authz policy unit test. The api test pins owner, Assistant, Admin, another Lecturer and a Student on both routes.
  - `[low]` `[patch]` (edge 15) `_asked`'s "never empty" claim was not guaranteed. Made true by the edge 1 fix.

## Design Notes

Bryter in the Klasseøkt normally follows the Valgknapper rule (applies on «Lagre Klasseøkt», locks at the Start date). Exclusions must stay changeable after the lock until the Test deadline, when «Lagre Klasseøkt» no longer exists, so the block has its own secondary save («Lagre quizvalg»): still "applies on save", never on toggle. Roster name on the staff page: FR-47 lets Lecturers and Assistant lecturers read every summary, staff see names on the Roster, completion export and Oversikt; AD-14's "ids and Roles only" governs stored facts/links, not staff reads. The name is read at request time, never stored. «Quiz changed» on Hjem is derived (no read-state table): it vanishes on the Student's next attempt or when the exclusion is lifted.

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief/test_quiz_exclusions.py tests/debrief/test_quiz.py tests/test_migrations.py tests/test_authz_rules.py` -- pass
- full backend suite `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-quiz-exclusions`, `debrief-quiz`, `debrief-bill`, `homes`, play-screen specs `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Class session's owners can take Debrief quiz questions out, and the staff see each Student's attempts and name. `quiz_exclusions` (migration 0109, owned by `modules/debrief`) holds one row per question taken out, never an edit of the content record. `debrief.commands.set_quiz_exclusions` locks the Class session row, refuses an archived Class (409 `class_archived`), an unknown id (422), the last question (409 `last_question`) and a change after the Class session's Test deadline (409 `test_deadline_passed`, judged in database time); a change stores and deletes rows, writes one audit row `debrief_quiz.exclusions_changed` (ids only), emits `session:<id>`, and enqueues a `quiz_changed` digest notice for each Student not passed whose last attempt got wrong only questions now out (one of them in this change). Every attempt asks the pinned questions not taken out; a stale form's answer to an excluded question is dropped; nobody is passed by an exclusion, and a passed Student stays passed after a lift. Hjem's current Quiz step reads «pågår, quizen er endret» while that rule holds (`rules.quiz_changed`, registered with `sessions`). Routes: `GET /api/class-sessions/{id}/debrief-quiz` (owners and Assistant lecturers) and `PUT …/debrief-quiz/exclusions` (owners). The Klasseøkt gets a «Debrief-quiz» block: each question with its choices, «Riktig svar: …», a Bryter «Med i quizen»/«Tatt ut», scope help text and its own secondary «Lagre quizvalg»; Assistant lecturers and a closed block read the state as text. The staff Debrief summary answers the Student's Roster name (read now, never stored; null once removed) and every attempt's number, time and result, shown on `/klasseokter/[sessionId]/studenter/[studentId]/debrief`.

**Files.**
- `backend/migrations/versions/0109_quiz_exclusions.py` (new), `debrief/models.py`: the table.
- `backend/app/modules/debrief/{commands,service,schemas,routes,rules}.py`, `README.md`: command, staff reads, asked set, staff summary fields, quiz-changed rule.
- `backend/app/modules/sessions/{service,schemas}.py`: `quiz_session`, `lock_for_quiz_exclusions`, `student_name`, quiz-changed provider, `StepOut.quiz_changed`, mail context.
- `backend/app/platform/{authz.py, events/registry.py}`, `messaging/delivery.py`, `email/templates/kinds/quiz_changed.{txt,html}.j2` (new): policies, registry entry, digest kind.
- Tests: `tests/debrief/test_quiz_exclusions.py` (new); `test_migrations.py` (head 0109); one-line updates in `test_debrief.py`, `test_explanation.py` (the summary now has `name`), `sessions/test_student_home.py`.
- Frontend: `modules/debrief/quiz-exclusions.tsx` (new), `api.ts`, `summary-page.tsx`, `quiz-step.tsx` (a 422 reads the quiz again), `sessions/class-session-page.tsx`, `games/home.ts`, `copy/nb.ts`, `lib/api/topics.ts`, regenerated `lib/api/{openapi.json,schema.ts}`; Vitest in `debrief.test.ts`, `home.test.ts`, `topics.test.ts`.
- e2e: `frontend/e2e/debrief-quiz-exclusions.spec.ts` (new); `debrief-bill.spec.ts` + `support/bill.ts` (name and attempts on the staff page).

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), two review layers. (1) Roster name on the staff Debrief page: shown. FR-47 lets Lecturers and Assistant lecturers read every summary, staff already see names on the Roster and the completion export, and AD-14's "ids and Roles only" governs stored facts sets and link payloads, not staff reads; the name is read at request time and never stored («Studenten er ikke lenger i Klassen.» once removed). (2) The block has its own secondary save «Lagre quizvalg» instead of the Valgknapper rule «applies on Lagre Klasseøkt», because exclusions stay open after the lock until the Test deadline, when «Lagre Klasseøkt» no longer exists; it still applies only on save, never on toggle. (3) The cut-off is the Class session's own Test deadline (no per-Student extension yet). (4) «Hjem tells them»: a digest mail `quiz_changed` plus a derived Stegene note «pågår, quizen er endret» (no read-state table; it ends with the next attempt or a lift). Only Students whose last attempt is fully covered by the change are told, as the AC words it. (5) Before the lock the block shows the latest version with a line saying the lock pins it. (6) The staff see attempt times and pass/fail only, not the answers. (7) An answer sent for a question taken out meanwhile is dropped, not refused. All copy is draft `[ASSUMPTION]` (Issue #31 pattern).

**Review.** 32 findings (high 0, medium 0, low 25, false 7): patched 7 root causes, all low (`_asked` never empty; the digest re-checks the rule at send time; mail copy for several questions; the error block stays during retry; README; a lift emits `user`; the block reads again after a closed-refusal); nothing deferred; the rest rejected with reasons above. followup_review_recommended: false (no high or medium patched; patched counts: low 7).

**Verification.**
- Backend after the patches: full suite `--maxprocesses=8` 2940 passed; `ruff check`, `ruff format --check` clean. Migration 0109 applied to the lane's `olspillet`; test databases migrate per session.
- Frontend: typecheck, Vitest (55 files, 767 tests), `lint:colours`, `check:copy`, `next build` (in the lane's image build) pass.
- Playwright on the rebuilt lane stack (8081), after the patches, `--workers=4`: `debrief-quiz-exclusions` (axe and reflow at 320, 360, 1440 px; real save on a fresh session; last-question refusal), all `debrief-*`, `class-session*`, `homes`, `student-home`, `game-end`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`, `live-updates`, `test-game`: 259 of 259.
- Failed once, passed on rerun: none.
- Tests over 1 s: `tests/debrief/test_quiz_exclusions.py::test_exclusions_change_the_next_attempt_and_staff_see_attempts` about 3.4 s call plus about 3 s setup (one Class, a two-Week game, the shared fixture); `test_an_attempt_never_asks_nothing` under 1 s call. `test_explanation.py` did not grow (one assertion changed).

**Residual risks.** Exclusion rows are matched by question id across content versions (rare: a new version between a pre-lock exclusion and the lock). Two owners saving at once is last-write-wins. The quiz content is still the placeholder (issue #16).
