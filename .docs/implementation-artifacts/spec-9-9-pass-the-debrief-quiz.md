---
title: 'Story 9.9: Pass the Debrief quiz'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '9a25f4e60675e0303e33441837315c0014bb572d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student who has finished the Debrief (`debrief` step) has no step 5: there is no Debrief quiz, no stored attempts and nothing records `quiz_passed`, so Stegene's Quiz step can never be done (FR-46, FR-47, UX-DR37).

**Approach:** A sixth content kind `debrief_quiz` (placeholder version 1, pinned at the lock) whose shape and pure scoring/rendering live in a new `analysis/quiz.py`. `debrief.commands.submit_quiz` stores one immutable `quiz_attempts` row per attempt and records `quiz_passed` in the same transaction when every asked question is right. Two routes (`GET /api/debriefs/{id}/quiz`, `POST /api/debriefs/{id}/quiz/attempts`) behind `progress.has_step(debrief)`; the web app shows step 5 under «Fullfør Debriefen» with a reusable Quizvalg component.

## Boundaries & Constraints

**Always:**
- Content `debrief_quiz` body: `placeholder: bool`, `questions` (1–20): `id` (key), `prompt`, `choices` (2–6, ids unique), `answer` (a choice id), `explanation` (text), optional `in_your_game` (template whose slots ⊆ `QUIZ_VALUES`). Validated on publish/read; no «!», no plain-text slot in `explanation`. Version 1 = three placeholder questions (Posisjon, Forsterkning, forsinkelse), `placeholder: true`. Pin provider `debrief_quiz_pin` registered in `sessions.service`.
- `QUIZ_VALUES` from the facts set of the Student's Seat: `weeks`, `chain_total_cost`, `own_amplification`, `factory_amplification`, `own_first_large_order_week`, `first_moment_week`. `analysis.quiz.render_in_your_game` returns None when a used value is None; amplification written with one decimal («7,6»), money as `format_money`. Pure (AD-1).
- Scoring only on the server (`analysis.quiz.score`); asked questions = every question of the pinned version (exclusions come with 9.10). The answer key never appears in GET's `questions`.
- Gate: 403 `debrief_required` until `progress.has_step(user, session, debrief)`; plus the Debrief's own availability/ownership (403 `debrief_not_open`/`debrief_held`/`forbidden`).
- POST body `answers: [{question_id, choice_id}]` in the order shown; 422 `validation_error` (`fields.answers`: `incomplete` when not exactly the asked set once each, `unknown_choice`). 409 `test_deadline_passed` when database time > `effective_test_deadline` (via `sessions.student_deadlines`), nothing stored. 409 `quiz_passed` once passed.
- `quiz_attempts(id, user_id, class_session_id, game_id, number, quiz_version, answers jsonb [{question_id, choice_id, correct}], passed, submitted_at db time)`, unique `(user_id, class_session_id, number)`, trigger refuses UPDATE. Debrief row locked; `progress.record_step(quiz_passed, submitted_at)` in the same transaction when passed; emits `debrief:<id>` (registry `debrief.submit_quiz`).
- GET answers `{version, placeholder, attempts, passed_at, questions, last}`: `questions` for the next attempt (content order for attempt 1, then a shuffle seeded by user id and attempt number; empty once passed), `last` the latest attempt re-rendered: per question in asked order its prompt, choices, `chosen`, `right_choice`, `correct`, and `explanation` (content text + rendered `in_your_game`) only when wrong.
- `SummaryOut` gains `quiz_attempts` (attempts until and with the passing one, or all while not passed) and `quiz_passed_at`, read at request time (the summary row stays immutable).
- UI: step 5 «Debrief-quiz» (section `#debrief-quiz`) under the finished line only once the summary exists. Quizvalg (`components/quiz-choice.tsx`): native radios in a `fieldset`/`legend`, full-width rows, idle `ink-muted` border, selected 1.4 px `ink` + dot, after submit wrong «Ditt svar, ikke riktig» (`restordre` border), right «Riktig» (`ink` border) in text, explanation under. Focus moves to the result summary after submit. «Prøv igjen» opens a new form. Placeholder note when `placeholder`. Stegene's current Quiz step links to `/debrief/{sid}#debrief-quiz`.

**Never:** no quiz exclusions or staff quiz UI (9.10); no LLM-worded explanations (9.14); no change of the step pointer; no score or grade from the quiz; no edit of `debrief_summaries` rows; no growth of `test_explanation.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Not finished | no `debrief` step | nothing stored | 403 `debrief_required` |
| Wrong attempt | one wrong answer | 201, `passed` false, explanation on the wrong one; no `quiz_passed` | — |
| Retry | after a wrong attempt | GET `attempts` 1, questions reshuffled set-equal | — |
| Pass | all right | 201 `passed`; `quiz_passed` at `submitted_at`; Stegene Quiz `done` | — |
| Again | passed | nothing stored | 409 `quiz_passed` |
| Late | db now > Test deadline | nothing stored | 409 `test_deadline_passed` |
| Bad body | missing/extra/duplicate question, unknown choice | nothing stored | 422 `validation_error` |

</intent-contract>

## Code Map

- `backend/app/analysis/{sentences.py (SentenceTemplate checks, format_number/format_money, _plain_slots), moments.py (_fill pattern), facts.py (FactSet: chain.weeks/total_cost/by_role amplification/first_large_order_week, seat.moments)}`; new `analysis/quiz.py`.
- `backend/app/modules/content/{models.py Kind, schemas.py, service.py (pattern: reflection_questions + _pin)}`; `sessions/service.py:2691-2698` register pins.
- `backend/migrations/versions/0106_moment_templates.py` -- pattern for `0108_debrief_quiz.py` (kind check, v1 literal, table + trigger).
- `backend/app/modules/debrief/{commands.py (finish: lock, deadline in db time), service.py (_own, require_explanation, _questions, _summary, finish_mine), schemas.py, routes.py (_answer error map), models.py, README.md}`; `platform/events/registry.py` (`debrief.finish` entry); `progress.Step.QUIZ_PASSED`; `sessions.service.STEGENE` maps quiz → `quiz_passed`.
- Tests: new `tests/analysis/test_quiz.py` (golden facts JSON in `tests/golden/facts/`), new `tests/debrief/test_quiz.py` (short played game: helpers in `tests/debrief/test_debrief.py`, `test_explanation.py:play_own_week`, `tests/games/helpers.py:play_week`), `tests/test_migrations.py`.
- Frontend: `modules/debrief/{api.ts, bill-step.tsx (Finish pattern, focus), debrief-page.tsx, debrief.test.ts}`, `components/components.test.tsx`, `copy/nb.ts` (`nb.debrief.quiz`), `modules/games/home.ts` stepItems href, `lib/api/{openapi.json,schema.ts}` regenerated; e2e `frontend/e2e/{debrief-bill.spec.ts, support/bill.ts}` pattern.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/quiz.py` (new), `__init__.py` -- `DebriefQuiz` shape, `QUIZ_VALUES`, `quiz_values(fact_set)`, `render_in_your_game`, `score`.
- `backend/app/modules/content/{models,schemas,service}.py`, `sessions/service.py` -- kind, reader, pin.
- `backend/migrations/versions/0108_debrief_quiz.py` (new), `debrief/models.py` -- kind constraint, v1 record, `quiz_attempts` + trigger.
- `backend/app/modules/debrief/{commands,service,schemas,routes}.py`, `README.md`, `platform/events/registry.py` -- submit, read, summary fields.
- Tests: `tests/analysis/test_quiz.py`, `tests/debrief/test_quiz.py`, `tests/test_migrations.py`, content validation cases.
- Frontend: `components/quiz-choice.tsx` (new), `modules/debrief/quiz-step.tsx` (new), `api.ts`, `debrief-page.tsx`, `copy/nb.ts`, `modules/games/home.ts`, regenerated api types, Vitest cases.
- e2e: `frontend/e2e/debrief-quiz.spec.ts` (new) + `support/quiz.ts` -- stubbed wrong attempt, retry, pass, keyboard-only, focus on result, axe at 320/360/1440.

**Acceptance Criteria:**
- Given a finished Debrief, when the page shows, then step 5 «Debrief-quiz» lists the pinned questions as Quizvalg rows, with the placeholder note.
- Given a wrong answer, when the result shows, then the chosen row reads «Ditt svar, ikke riktig», the right one «Riktig», followed by the explanation, and focus is on the result summary.
- Given a passing attempt, when Hjem shows, then Stegene's Quiz step is done.
- Given 320, 360 and 1440 px, when the quiz shows, then axe passes, there is no sideways page scroll, and the quiz is operable by keyboard alone.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-9.md` and `review-edge-9-9.md` in the scratchpad. The review diff left out the generated `openapi.json`/`schema.ts` and `.docs` on purpose.
- verdicts: 23 findings — high 0, medium 0, low 17, false 6, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) The regenerated `openapi.json`/`schema.ts` are missing. They are regenerated and in the change; only the review diff leaves them out; typecheck and build pass.
  - `[false]` `[reject]` (blind 2) A failed attempt shows the right choice, so the quiz can be passed by copying it. The AC requires «Riktig» on the right one after every attempt (UX-DR37, FR-46); the quiz counts toward no score.
  - `[low]` `[patch]` (blind 3) `submit_quiz` stores a caller-supplied `passed`. The command now derives `passed` from the answers' `correct` (all, and at least one); the parameter is gone.
  - `[low]` `[patch]` (blind 4) A 409 `quiz_passed` from another device leaves the form standing. The web app now reads the quiz again on that refusal, so the passed result replaces the form. A deadline flag in GET was rejected: the 409 states the reason beside the button.
  - `[low]` `[reject]` (blind 5) «10 eller mer» is a literal in the content. Content is versioned and LARGE_ORDER is analysis-versioned; a change is a new version of both.
  - `[low]` `[reject]` (blind 6) After a pass the earlier explanations are not shown again. They were shown on the attempt that missed; the AC asks for the latest result.
  - `[low]` `[reject]` (blind 7) `now()` is the transaction start, before the row lock. Same pattern as 9.8's finish; the skew is the wait for one other attempt's insert, milliseconds; numbers stay ordered under the lock.
  - `[low]` `[reject]` (blind 8) No length bounds on the attempt body. Anything but the asked set once is refused 422 `incomplete` before storing; same as the other Debrief bodies.
  - `[low]` `[reject]` (blind 9) Test gaps (another Game's Debrief id, double submit, Group debrief, pre-pin session, staff summary fields, 409 `quiz_passed` in e2e). `_own` refuses another Game's id for every Debrief route (9.2 to 9.8 tests); the staff read uses the same `_summary`; `STAFF_SUMMARY` spreads `SUMMARY`, so it has the new fields (that part false); the Group debrief does not exist yet (9.11).
  - `[low]` `[patch]` (blind 10) The pure test rounded the expected Forsterkning half-even. It now rounds half up as the code does. The `__all__` fixture list is the repo's pattern (rejected).
  - `[false]` `[reject]` (blind 11) Placeholder content ships everywhere. The AC asks for exactly that, clearly marked; the downgrade mirrors 0105 to 0107.
  - `[low]` `[reject]` (blind 12) `analysis/quiz.py` imports `sentences`' private helpers; `question()` raises StopIteration on an unknown id. Same layer, one owner; the id always comes from the same version (scored or stored with it), so the StopIteration is unreachable.
  - `[low]` `[reject]` (blind 13) The scored fieldset is `disabled`; the summary line is focused and `role="status"`. The marks are text in each row's name and pass axe at three widths; the focused status line is 9.8's pattern.
  - `[false]` `[reject]` (blind 14) `_result` refetches the facts set when it is None. `games.fact_set` never returns None (it creates or raises).
  - `[low]` `[patch]` (edge 1) Same as blind 4; same fix.
  - `[false]` `[reject]` (edge 2) Focus may run before the result renders. `setQueryData` renders the result in the same pass; the e2e asserts the focus after both sends at three widths.
  - `[low]` `[reject]` (edge 3) A facts-set failure after the attempt is stored answers 5xx. A finished Game always has its facts set (step 4 already read it); failing loudly is the 9.1 rule.
  - `[low]` `[reject]` (edge 4) Same as blind 8.
  - `[low]` `[reject]` (edge 5) Same as blind 7.
  - `[low]` `[reject]` (edge 6) A double POST stores two attempts. The button is unavailable while sending; attempts are unlimited and count toward nothing.
  - `[false]` `[reject]` (edge 7) Same as blind 12's StopIteration: unreachable.
  - `[low]` `[patch]` (edge 8) Stegene's `#debrief-quiz` link lands before the section renders. `QuizStep` now scrolls to it once the quiz has answered when the hash names it.
  - `[low]` `[patch]` (edge 9) The spec names `quiz_values(fact_set)` and an `__init__.py` entry. The `analysis` package docstring now lists `quiz`; the values are the `QUIZ_VALUES` mapping (no separate function needed, rejected).

## Design Notes

The Debrief summary row is immutable (9.8 trigger), so «the number of attempts is added to the summary» is read at request time from `quiz_attempts` into `SummaryOut`, never written into the row. Reshuffling is done in `debrief.service` (not in pure `analysis`) with `random.Random(f"{user_id}:{n}")`, so the order a Student sees is stable across reloads of the same attempt. The explanation's own-game sentence is a separate optional template: when the Student's game lacks a value (no moments, no large Order, flat demand), only the general explanation shows, never a gap.

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis/test_quiz.py tests/debrief/test_quiz.py tests/test_migrations.py tests/content` -- pass
- full backend suite `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-quiz`, `debrief-bill`, `homes`, play-screen specs with `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** Step 5 «Debrief-quiz» now follows «Debriefen er fullført». A sixth content kind `debrief_quiz` (shape, scoring and own-game sentences in the pure `analysis/quiz.py`) ships version 1 as a marked placeholder (three questions: Posisjon, forsinkelse, Forsterkning; `placeholder: true`, issue #16) and is pinned at the lock (`debrief_quiz_pin`). `GET /api/debriefs/{id}/quiz` and `POST /api/debriefs/{id}/quiz/attempts` answer 403 `debrief_required` until `progress.has_step(debrief)`. GET gives the next attempt's questions without the answer key (content order, then a shuffle seeded by the Student and the attempt number; none once passed) and the latest result. POST scores on the server by the answer key (422 `validation_error` unless every asked question is answered once), then `debrief.commands.submit_quiz` locks the Debrief row and stores one immutable `quiz_attempts` row (number, quiz version, answers with `correct`, `passed`, database time); every answer right records `progress.record_step(quiz_passed, submitted_at)` in the same transaction; 409 `quiz_passed` once passed, 409 `test_deadline_passed` past the effective Test deadline (judged in the database). A wrong answer's result carries the content's explanation followed by the own-game sentence rendered from the Seat's facts set («Ditt første øyeblikk var Uke 11. Det står i kolonne 11 i din egen tabell.»), left out when the Game lacks the value. The Debrief summary answers `quiz_attempts` and `quiz_passed_at`, read at request time. The web app adds Quizvalg (`components/quiz-choice.tsx`: native radios covering full-width rows, selected state, «Ditt svar, ikke riktig» / «Riktig» in text and border), the quiz step (focus to the result summary after a send, «Prøv igjen» opens a new attempt), and Stegene's current Quiz step links to `/debrief/{id}#debrief-quiz`.

**Files.**
- `backend/app/analysis/quiz.py` (new), `analysis/__init__.py`: `DebriefQuiz`, `QUIZ_VALUES`, `render_in_your_game`, `score`.
- `backend/app/modules/content/{models,schemas,service,__main__}.py`, `sessions/service.py`: kind, reader, pin.
- `backend/migrations/versions/0108_debrief_quiz.py` (new); `debrief/models.py` (`quiz_attempts`).
- `backend/app/modules/debrief/{commands,service,schemas,routes}.py`, `README.md`; `platform/events/registry.py` (`debrief.submit_quiz`).
- Tests: `tests/analysis/test_quiz.py` (new), `tests/debrief/test_quiz.py` (new), `tests/content/test_content.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py`.
- `frontend/src/components/quiz-choice.tsx` (new), `modules/debrief/quiz-step.tsx` (new), `modules/debrief/{api.ts, debrief-page.tsx, debrief.test.ts}`, `components/components.test.tsx`, `copy/nb.ts` (`debrief.quiz`, `quizChoice`), `modules/games/{home.ts, home.test.ts}`, regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/{debrief-quiz.spec.ts (new), support/quiz.ts (new)}`, `debrief-bill.spec.ts` + `support/bill.ts` (quiz stub, summary fields).

**Deviations from the epic's wording.** «The number of attempts is added to the Student's Debrief summary»: the summary row is immutable (9.8), so the count is read from `quiz_attempts` into the summary's answer at request time, not written into the row. The own-game values come from `analysis.quiz.render_in_your_game` (the architecture's `analysis.render` name for code rendering). The Group debrief does not exist yet (9.11); nothing in the quiz is shared, so each Student takes it on their own device.

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), two review layers. Placeholder questions and copy are draft (`[ASSUMPTION]`, Issue #31; content issue #16): «Posisjon» uses the journey's −13 / 3 example. The explanation shows only under a wrong answer; a right one is marked «Riktig» alone. The first attempt asks in the content's order; retries are shuffled (questions only, not choices) with a seed of the Student and attempt number, so a reload shows the same order. After a pass no further attempt is taken (409 `quiz_passed`) and the passing result stays shown. An attempt must answer every question (the web app says so before sending). The placeholder line reads «Spørsmålene er foreløpige og byttes ut før kurset tar dem i bruk.». The wrong row keeps an `ink` dot inside a `restordre` ring (the theme has no text pair on `restordre`). Staff quiz UI and exclusions are left for 9.10.

**Review.** 23 findings (high 0, medium 0, low 17, false 6): patched 5 root causes, all low (`passed` derived in the command; a 409 `quiz_passed` reads the quiz again; the pure test rounds half up; the `#debrief-quiz` link scrolls once the step renders; the `analysis` docstring lists `quiz`); nothing deferred; the rest rejected with reasons above. followup_review_recommended: false (no high or medium patched; patched counts: low 5).

**Verification.**
- Backend, after the patches: full suite `--maxprocesses=8` 2932 passed, 4 skipped; `ruff check`, `ruff format --check` clean (a docstring reflow after the suite; the quiz tests rerun, 19 passed). Migration 0108 applied to the lane's `olspillet`; test databases migrate per session.
- Frontend: typecheck, Vitest (55 files, 763 tests), `lint:colours`, `check:copy`, `next build` (in the lane's image build) pass.
- Playwright on the rebuilt lane stack (8081), after the patches, `--workers=4`: `debrief-quiz` (axe at 320, 360, 1440 px; keyboard-only send; focus on the result), all other `debrief-*`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`: 149 of 149.
- Failed once, passed on rerun: none. Before the first green run, the quiz spec failed the 44 px tap-target check at 320/360 px (the radio sat inside the row's border); fixed by letting the radio cover the border.
- Tests over 1 s: `tests/debrief/test_quiz.py` about 2.5 s call plus 2.9 s setup (one Class, a two-Week game: the shared Class fixture); `tests/analysis/test_quiz.py` under 1 s per test. `test_explanation.py` did not grow.

**Residual risks.** The quiz is placeholder content until issue #16; a course locked before then pins version 1. The shuffle reorders questions only.
