---
title: 'Story 9.6: Answer the reflection questions'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '4b2082071510c795cb290ad9be478e73a476b237'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['multiple-goals', 'oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** After step 3 the Debrief goes nowhere: there are no reflection questions (FR-45), so the Student never thinks through feelings, evidence and structure before their own moments (Story 9.7). Also, at 1280 px step 3's four-Role Kjedebånd stops at 56 rem while the Ordrestolper under it span the column (9.5 visual check, `screenshots/9.5/debrief-step3-last-uke-1280.png` vs `07-debrief.png`).

**Approach:** A new content kind `reflection_questions` (immutable, versioned, pinned at `sessions.lock` like `sentence_templates`), version 1 seeded by migration 0105 with three placeholder questions in the order feelings → evidence → structure (issue #16 delivers real content). A new table `debrief_reflection_answers` keyed by `user_id`, Class session and question id. `GET /api/debriefs/{id}/reflection` (behind `require_explanation`) answers the pinned questions with the caller's own answers; `POST /api/debriefs/{id}/reflection/{question_id}` saves one answer through new `debrief.commands.complete_step`. The web app shows the reflection section under step 3, one question at a time, the answered ones read-only above, drafts kept in `lib/drafts.ts`. The band drops its 56 rem cap.

## Boundaries & Constraints

**Always:**
- Gate: both reflection routes keep the 9.2/9.3 refusals (`debrief_not_open`, `debrief_held`, `forbidden`, `explanation_required`) with the envelope only.
- Questions come from `content.reflection_questions(pinned_version(pins, REFLECTION_QUESTIONS))`, latest for a session locked before the pin. Content schema `ReflectionQuestions`: 1–12 questions, each `{id (key pattern), kind: feelings|evidence|structure, prompt ≤500, hint ≤500 | null}`; ids unique; kinds in non-decreasing order feelings → evidence → structure with each kind present; no `!` in any text.
- Answers: keyed by `user_id` + `class_session_id` + `question_id`, with `game_id`, `questions_version`, `text`, `length`, `saved_at` (DB time). Text non-blank, ≤ 2000 chars (422 `validation_error`, `fields.text` = `blank`/`too_long`). Stored once and never changed (trigger refuses UPDATE). A repeat POST of an answered question returns the stored answer unchanged (200, idempotent: a lost response retried, a second device). The next question only: POSTing a question after the first unanswered one answers 409 `reflection_out_of_order`; an id not in the pinned version answers 404 `not_found`.
- `complete_step` locks the Debrief row, writes the answer and emits `debrief:<id>`; registry entry `debrief.complete_step` → `{debrief}`.
- Each Student reads only their own answers (another Student of the same game sees none of them, FR-43, AD-14).
- UI: section «Spørsmål til ettertanke» under step 3 (unnumbered: it sits between steps 3 and 4), «Spørsmål 2 av 3», one open question as a labelled text area with hint and «Fortsett»; earlier answers shown read-only above; after the last, a status line. Unsent text per question in `lib/drafts.ts` (field `debrief-reflection:<classSessionId>:<questionId>`), cleared on save. A failed save shows «Det ble ikke lagret. Prøv igjen.» and keeps the text. After a save focus moves to the next question's heading (or the done line). Copy in `nb.debrief.reflection`, draft copy marked `[ASSUMPTION]`.
- Band: `FourRoleBand` spans the step's full width (no `max-w-[56rem]`); the scrubber row keeps its own layout.

**Never:** no AI text or follow-up field (Story 9.15); no step-pointer move or Group sync (9.11); no staff read route (Student report, Epic 13); no editing of a stored answer; no import of `modules/players`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Read | `GET …/reflection` with Explanation | 200 `{version: 1, questions:[{id, kind, prompt, hint, answer: null | {text, length, saved_at}}]}` in content order | — |
| No Explanation | none saved | 403 `explanation_required` | envelope only |
| Save next | POST first unanswered, `{text}` | 200 the question with its answer; row stored; `debrief:<id>` emitted | — |
| Repeat | POST an answered question, other text | 200 stored answer unchanged | — |
| Out of order | POST question 3 with 2 unanswered | 409 `reflection_out_of_order`, nothing stored | — |
| Unknown id | POST `nope` | 404 `not_found` | — |
| Blank / long | `"  "` / 2001 chars | 422 `validation_error` `{text: blank | too_long}` | — |
| Save fails (UI) | network / 5xx | «Det ble ikke lagret. Prøv igjen.», text kept in field and draft | — |

</intent-contract>

## Code Map

- `backend/app/modules/content/{models.py Kind, schemas.py, service.py}` -- add `REFLECTION_QUESTIONS`, `ReflectionQuestions`, `reflection_questions(version)`, `reflection_questions_pin`; pattern = `sentence_templates`.
- `backend/app/modules/sessions/service.py:2682` -- `register_pin_provider(...)` beside the other content pins.
- `backend/migrations/versions/0104_sentence_templates.py` -- pattern for 0105 (kind check + seeded literal v1); `0103_debrief_explanations.py` -- immutable-table trigger pattern.
- `backend/app/modules/debrief/{models.py, commands.py save_explanation, service.py _own/require_explanation, routes.py _answer, schemas.py, README.md}` -- add answers table, `complete_step`, service read/save, two routes.
- `backend/app/platform/events/registry.py:106` -- add `debrief.complete_step`.
- Tests touching pins/heads: `tests/content/test_content.py:74`, `tests/sessions/test_lock.py:90`, `tests/test_migrations.py` (HEAD, tables, downgrade walk).
- `backend/tests/debrief/test_explanation.py` -- module played game; extend with a `reflected(...)` helper called from the main test (gate before send, flow after, mate isolation).
- `frontend/src/modules/debrief/{explanation-step.tsx (Write/Sent pattern), chain-step.tsx FourRoleBand, debrief-page.tsx Steps, api.ts, debrief.test.ts}`, `frontend/src/lib/drafts.ts`, `frontend/src/copy/nb.ts` `debrief`.
- `frontend/e2e/{debrief-chain,debrief-reveal,debrief-explanation}.spec.ts` -- stub `reflection` too (else the stubbed page reads the stack).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/content/*` + `sessions/service.py` -- kind, schema with validators, reader, pin provider registered.
- `backend/migrations/versions/0105_reflection_questions.py` -- kind check, v1 literal, `debrief_reflection_answers` with length check and immutable trigger.
- `backend/app/modules/debrief/*`, `platform/events/registry.py` -- table, `complete_step`, service, routes, schemas, README.
- `backend/tests/{content/test_content.py, sessions/test_lock.py, test_migrations.py, debrief/test_explanation.py}` -- pins, schema rejects, migration walk, the I/O matrix rows.
- `frontend/src/modules/debrief/{reflection-step.tsx (new), api.ts, debrief-page.tsx, chain-step.tsx, debrief.test.ts}`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts`.
- `frontend/e2e/debrief-reflection.spec.ts` (new) -- stubbed: one at a time in order, keyboard-only answering, draft kept over reload, failed save keeps text, focus move, axe at 320/360/1440; other debrief specs stub the route.

**Acceptance Criteria:**
- Given a saved Explanation, when the Debrief shows, then the reflection section shows under step 3 with only the first unanswered question open, in the order feelings, evidence, structure.
- Given a typed answer, when the Student presses «Fortsett», then it is saved, shown read-only and the next question opens with focus on its heading; when the save fails, the failure line shows and the text stays.
- Given text typed and not sent, when the page reloads, then the text is back in the field.
- Given 320, 360 and 1440 px, when the reflection step shows, then axe passes, no sideways page scroll, and it is operable by keyboard alone.
- Given 1280 px, when step 3 shows, then the band's right edge reaches the bars region's right edge (±2 px).

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-6.md` and `review-edge-9-6.md` in the scratchpad.
- verdicts: 28 findings — high 0, medium 0, low 21, false 7, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) The privacy line names the Class's staff as readers, but no staff read route exists. The line states the permission (AD-12, AD-14: Assistant lecturers may read); the reader comes with the Student report (Epic 13), as FR-58 plans.
  - `[low]` `[patch]` (blind 2) A question answered first on another device swapped in the stored text and cleared the draft without a word. The page now says «Spørsmålet var allerede besvart på en annen enhet …» (also after the last question); e2e case added.
  - `[low]` `[reject]` (blind 3) A session locked before the pin reads the latest version, so a version 2 could move ids under a Student. Only sessions locked before migration 0105 (local/test data, no production yet) take that path; same rule as 9.4's templates.
  - `[false]` `[reject]` (blind 4) Reflection not recorded as progress / step pointer not moved. The spec excludes the pointer (9.11); `debrief` completion is 9.8's; 9.7 can read the stored answers.
  - `[low]` `[reject]` (blind 5) The questions open once the Explanation is saved, not after step 3 was viewed. Same gate as steps 2 and 3; no «viewed» record exists and the page shows them under step 3.
  - `[low]` `[reject]` (blind 6) Input hardening: NUL character gives 500, no body size cap, no exact-2000 test. Rare, and the Explanation shares the behaviour; a fix adds branches for no everyday user.
  - `[low]` `[patch]` (blind 7) A blank or long repeat of an answered question answered 422, against «repeat returns the stored answer». `answer_mine` now answers the stored answer before judging the text; test added.
  - `[low]` `[patch]` (blind 8) Drafts of questions answered elsewhere stayed in localStorage. The step clears the draft of every answered question; e2e asserts none is left. (Logout already clears all drafts.)
  - `[low]` `[reject]` (blind 9) Concurrency untested; `_locked` with no row. The row exists (`_own` read it) and `.one()` would raise; the lock and primary key are the same pattern as `save_explanation`.
  - `[low]` `[reject]` (blind 10) Kinds listed three times. The Literal feeds the OpenAPI type; the tuple gives the order; all three are in two files and tested.
  - `[false]` `[reject]` (blind 11) Tests break when version 2 is published. Tests run on the migrated database with version 1 only; `only_version_1` removes later versions.
  - `[low]` `[reject]` (blind 12) Placeholder prompts presuppose amplification. Placeholder content until issue #16; copy review is Issue #31.
  - `[low]` `[reject]` (blind 13) No loading line, permanent empty-field reason, status + focus on the closing line, no counter at 2000. Same patterns as steps 1–3 (the notice part is patched with blind 2).
  - `[false]` `[reject]` (blind 14) The band change is out of scope. The run's intent asks for it.
  - `[false]` `[reject]` (blind 15) Downgrade deletes later versions, no IF EXISTS, DELETE not refused. Same as 0103/0104; cascades must delete; the trigger guards changes, not deletion.
  - `[low]` `[patch]` (edge 1) Same as blind 2; same fix.
  - `[low]` `[patch]` (edge 2) The 409 path cannot be reached from the page, and the e2e tested an answer the api never gives. The e2e now tests the reachable case (blind 2); the 409 handling stays as a guard.
  - `[low]` `[patch]` (edge 3) Same as blind 7; same fix.
  - `[low]` `[reject]` (edge 4) NUL / lone surrogate gives 500. Same as blind 6.
  - `[low]` `[reject]` (edge 5) Version drift for unpinned sessions. Same as blind 3.
  - `[low]` `[reject]` (edge 6) Answers to ids missing from the version read are invisible. Only through blind 3's path.
  - `[low]` `[reject]` (edge 7) After a 409, a failed refetch leaves the notice on the same question. Needs the unreachable 409 plus a failed read.
  - `[low]` `[patch]` (edge 8) Same as blind 8; same fix.
  - `[false]` `[reject]` (edge 9) A failed background refetch is invisible. Deliberate, as in step 3: the read data stays; only a first read that fails shows the error.
  - `[false]` `[reject]` (edge 10) Pasted text over 2000 is cut and UTF-16 differs from code points. UTF-16 units are never fewer than code points, so the browser limit is the stricter one; same as the Explanation.
  - `[low]` `[reject]` (edge 11) Downgrade leaves pins to a deleted version. Downgrade is a developer path; a re-upgrade stores version 1 again under the same number.
  - `[low]` `[patch]` (edge 12, claim) Repeat with changed text not idempotent. Same as blind 7; same fix.
  - `[false]` `[reject]` (edge 13, claim) The second-device case is not announced. True before the patch (blind 2); announced now.

## Design Notes

Store-once with idempotent repeat (not 409) because a Student never edits an answer and a retry after a lost response must not show an error. Out-of-order refusal keeps «one at a time» true in the api, not only in the UI. Heading «Spørsmål til ettertanke» is unnumbered so the spine's five numbered steps stay intact. Placeholder questions (v1, migration literal, draft until issue #16):
- feelings: «Hvordan opplevde du det å bestille uke for uke uten å vite hva kundene ville bestille?»
- evidence: «Hva i tallene fra hele kjeden viser at svingningene vokste oppover i kjeden?»
- structure: «Hvorfor svinger nesten alle kjeder slik, uansett hvem som spiller dem?» (hint: «Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.»)

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief tests/content tests/sessions/test_lock.py tests/test_migrations.py` -- pass
- full `uv run pytest`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-reflection`, `debrief-chain`, `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, play-screen specs -- pass

## Auto Run Result

Status: done

**Summary.** The Debrief asks the reflection questions between steps 3 and 4. New content kind `reflection_questions` (immutable, versioned, pinned at `sessions.lock` under `pins["reflection_questions"]`), version 1 from migration 0105 with three placeholder questions in the order feelings, evidence, structure (issue #16 delivers real ones). `GET /api/debriefs/{id}/reflection` answers the pinned questions with the caller's own answers; `POST /api/debriefs/{id}/reflection/{question_id}` stores one answer through the new `debrief.commands.complete_step` (Debrief row locked, `debrief:<id>` emitted) in `debrief_reflection_answers`, keyed by `user_id`, Class session and question, stored once (trigger), in order (409 `reflection_out_of_order`), a repeat answering the stored answer. Both behind the Explanation gate. The web app shows «Spørsmål til ettertanke» under step 3: one question at a time with «Spørsmål n av 3», the answered ones read-only above, drafts per question in `lib/drafts.ts`, «Det ble ikke lagret. Prøv igjen.» keeping the text, focus to the next question's heading or the closing line. Step 3's four-Role Kjedebånd now spans the step's width (the 56 rem cap is gone); an e2e at 1280 px checks its edges match the bars region within 2 px.

**Files.**
- `backend/app/modules/content/{models,schemas,service}.py`, `sessions/service.py`: kind, `ReflectionQuestions` (order, ids, no «!»), reader, pin provider.
- `backend/migrations/versions/0105_reflection_questions.py` (new): kind check, version 1, answers table and trigger.
- `backend/app/modules/debrief/{models,commands,service,routes,schemas}.py`, `README.md`; `platform/events/registry.py` (`debrief.complete_step`).
- `backend/tests/{content/test_content.py, sessions/test_lock.py, test_migrations.py, debrief/test_explanation.py}`.
- `frontend/src/modules/debrief/{reflection-step.tsx (new), api.ts, debrief-page.tsx, chain-step.tsx, debrief.test.ts}`, `copy/nb.ts` (`debrief.reflection`), regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/{debrief-reflection.spec.ts (new), support/reflection.ts (new), debrief-chain.spec.ts (1280 px band), debrief-reveal.spec.ts, debrief-explanation.spec.ts}`.

**Decisions for the founder.** The builder implemented in its own context (orchestrator rule) and ran two review layers. Placeholder questions written fresh in Norwegian (Design Notes) and draft UI copy marked `[ASSUMPTION]`; the section heading «Spørsmål til ettertanke» is unnumbered so the five numbered steps stay. Answers must be non-blank, at most 2000 characters, and are never edited; a repeat answers the stored one; the api refuses any question but the next. The privacy line names the Class's teachers as readers (the reader itself comes with the Student report). No AI text or follow-up field yet (9.14/9.15).

**Review.** 28 findings (high 0, medium 0, low 21, false 7): patched 4 root causes (second-device answer announced, stored answer before judging a repeat, drafts of answered questions cleared, e2e moved to the reachable case); nothing deferred; the rest rejected with reasons in the triage log. followup_review_recommended: false (no high or medium patched).

**Verification.**
- Full backend suite after the patches: 2886 passed in 70 s; `ruff check`, `ruff format --check` clean.
- Frontend: typecheck, Vitest (55 files, 750 tests), `lint:colours`, `check:copy`, `next build` pass.
- Playwright on the rebuilt lane stack (8081): `debrief-reflection`, `debrief-chain`, `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`: 129 of 129 passed (and 32 of 32 debrief specs before the patches). axe at 320, 360, 1440 px for the reflection step. No flaky reruns.
- Tests over 1 s: none new; `test_step_one_the_one_send_the_gate_and_the_readers` grew from about 3 s to about 4 s (reflection checks on the same played game).

**Residual risks.** Placeholder questions and draft copy await issue #16 and Issue #31. A session locked before migration 0105 reads the latest question version (only local/test data). The 409 out-of-order path cannot be reached from the page today; it stays as a guard.
