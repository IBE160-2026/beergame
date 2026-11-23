---
title: 'Story 12.9: Score Control test answers blind'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '2eaa20ec3fdb197646648625d19f2a9ae325a1ef'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Control test (12.7, 12.8) produces AI scores, but nobody can score the same answers by hand, so 12.10 has nothing to compare against; and no rule says who may read a Control test's answers (FR-82, AD-12, AD-27).

**Approach:** The Admin names scorers (existing Users) per Control test. After its Test deadline a named scorer reads a neutral list of every non-blank long-answer and Adapted answer of the closed attempts, opens one (question, original answer, Adapted facts, the pinned Scoring guide entry and scale, no AI score), picks a step and submits once into `human_scores`; only then that item's AI score shows to them. The Admin reads the same list and items (audited) but does not score unless named.

## Boundaries & Constraints

**Always:**
- Migration `0208` (Revises `0207`), tables owned by `modules/assessment`: `control_test_scorers(class_session_id FK class_sessions cascade, user_id FK users cascade, named_by FK users set null, named_at; PK both ids)`; `human_scores(answer_id FK test_answers cascade, scorer_id FK users cascade, score smallint CHECK 0–4, submitted_at; PK (answer_id, scorer_id))` with a trigger refusing every UPDATE. No update function exists.
- authz: `control_test_answers.read` and `control_test_answers.score` (`ANY_USER`, held to `authz.control_tests_scored_by(user)`: the sessions the User is named on); `read` also holds for a User with `control_tests.manage` (Admin). A refusal is 403 `forbidden` the same whether the session, answer or Control test exists. `control_tests.manage` guards naming.
- Naming (`GET/POST /api/admin/control-tests/{id}/scorers`, `DELETE …/scorers/{user_id}`): by e-mail of an active existing User; refused 422 `invalid_request` `fields.email` = `unknown` (no active User) or `test_student`; 404 `not_found` for no Control test of that id; naming one already named writes nothing (200). Each naming and each removal is one audit row (`control_test.scorer_named` / `control_test.scorer_removed`, ids only). Removal keeps the scorer's submitted scores. GET lists name, e-mail, `scored` count.
- Reads (`GET /api/scoring` → the caller's named Control tests {id, name, test_deadline, open}; `GET /api/scoring/{session_id}`; `GET /api/scoring/{session_id}/answers/{answer_id}`): list `open` = now ≥ the session's `test_deadline`; before that `entries: []`. Entries = every long/Adapted item of each **closed** attempt with non-blank saved text, ordered by item id then SHA-256 of the answer id, numbered «Svar N» from 1; each carries `answer_id`, `number`, `type`, `question`, `scored` (by the reader). No name, e-mail, user id or attempt id anywhere in these responses. Each read by a User with the Admin role is an audit row `control_test.answers_read` (session id, and the answer id for an item).
- Item: number, type, question, original answer text, Adapted fact lines, the pinned guide entry (title, guide text, criteria code/weight/text) and the five-step scale, `own_score` {score, submitted_at} | null, `can_score`, and `ai` {step, label} only when the reader's own score exists and the AI stored one; otherwise the key is null. No AI feedback ever.
- Submit (`POST /api/scoring/{session_id}/answers/{answer_id}` `{score: 0–4}`): named scorers only (an Admin not named: 403); 201 with the item (AI score now included); a second submit → 409 `human_score_exists`, nothing written; before the deadline/unknown answer → 404 `not_found` for a scorer.
- Web: a Lenke «Sensur av Kontrolltest» on the User's own home (Lærerhjem, Hjem or Admin-område) only while `GET /api/scoring` lists a test; pages `/sensur`, `/sensur/[sessionId]`, `/sensur/[sessionId]/[answerId]` (guard `any`, the api decides). The item page: Valgknapper (`SegmentedChoice`) for the scale, «Kan ikke endres etterpå.»-style consequence line above the primary button «Lagre vurdering» (labelled by effect), no dialog; rejected resubmit shown in words. Admin: Kontrolltest row Lenke → `/admin/kontrolltest/[sessionId]` «Sensorer» (list, add by e-mail, «Fjern», Lenke to the answers). Scored state in text («Vurdert», «Ikke vurdert»). New copy in `nb.ts` marked `[ASSUMPTION]`.

**Never:** agreement measures, results page or `mark_checked` (12.10); showing AI feedback to scorers; editing a human score; names in audit rows or logs; a test student as scorer; changes to the demo Class, seeds or `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Name | Admin POST e-mail of active User | row, audit row | unknown/test student: 422 `fields.email` |
| Outsider | Lecturer/Student/not-named User reads list/item | — | 403 `forbidden` |
| Before deadline | scorer GET list | `open: false`, no entries | item: 404 |
| List | 2 test students × (2 long + 1 Adapted), one blank | 5 entries «Svar 1…5», no name | — |
| Item blind | scorer GET item, not scored | no `ai` | — |
| Submit | score 3 | row (answer, scorer, 3, now); `ai` shown on that item only | resubmit: 409 `human_score_exists` |
| Admin read | Admin GET list/item | 200, audit row per read, `can_score: false` | Admin submit when not named: 403 |
| Removed scorer | removed, then reads | — | 403; scores kept |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- POLICIES (~82–189), add two actions; scope `control_tests_scored_by` (pattern `control_test_classes` ~351) over `control_test_scorers` by name.
- `backend/app/modules/assessment/{models,service}.py` -- new tables; `name_scorer`, `remove_scorer`, `scorers_of`, `scored_sessions`, `is_scorer`, `insert_human_score` (ON CONFLICT DO NOTHING → False), `human_scores_by(scorer, answer_ids)`, `score_counts`; AI step via `assessment_of(s, attempt_id).scores`.
- `backend/app/modules/tests/blind.py` (new; `tests/scoring.py` is Story 11.5's computed scoring) -- access, list, item, submit, naming; reuses `assessed.read_for_assessment(attempt_id)` for question/answer/facts/guide entry/scale; `AI_TYPES`; `test_answers`/`test_attempts`.
- `backend/app/modules/sessions/service.py` -- `control_test_facts(s, id) -> (name, test_deadline) | None` for kind `control_test` (uses `repo.session_row`, `classes.class_facts`).
- `backend/app/modules/tests/{routes,schemas}.py` -- routes and `Scoring*Out` (answers addressed by `ref`, a keyed hash of the answer id, after review), `ScorerOut`, `ScoreIn`, `ScorerIn`.
- `backend/app/modules/identity/service.py` -- `active_user_for_email`, `is_test_student`, `people`.
- `backend/app/platform/audit.py` -- `record(s, actor, action, target, change, at)`.
- `backend/migrations/versions/0208_human_scores.py`; `backend/tests/test_migrations.py` (HEAD).
- Tests: new `backend/tests/assessment/test_human_scores.py`, fixtures from `tests/sessions/test_control_test.py` (`people`, `control`, `ADMIN`) and `tests/sessions/test_test_students.py` (`enrol`); attempts seeded by SQL (closed, items JSON, answers), `at(monkeypatch, when)` clock.
- Frontend: `src/modules/assessment/{scoring-api.ts,scoring.ts,scoring-pages.tsx}` (new), `src/app/(app)/sensur/...` (new), `src/modules/admin/{control-test-scorers-page.tsx (new),control-tests-page.tsx,api.ts}`, `src/app/(app)/admin/kontrolltest/[sessionId]/page.tsx` (new), `src/modules/identity/{home-page.tsx,homes.ts}`, `src/copy/nb.ts`, `src/components/segmented-choice.tsx` (reuse), generated `src/lib/api/{openapi.json,schema.ts}`.
- E2E: new `frontend/e2e/control-test-scoring.spec.ts` with route stand-ins (pattern `e2e/ai-assessment.spec.ts`).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0208_human_scores.py` -- tables, trigger -- storage.
- `backend/app/platform/authz.py`, `assessment/*`, `sessions/service.py`, `tests/scoring.py`, routes, schemas -- as above -- ACs 1–5.
- `backend/tests/assessment/test_human_scores.py` -- every matrix row; blind both directions; no name/e-mail/user id in list or item JSON; audit rows; UPDATE refused by trigger; migrations head.
- Frontend files, `npm run api:generate` -- screens.
- `frontend/e2e/control-test-scoring.spec.ts` -- list, item, submit, rejected resubmit at 320/360/1440 with axe; keyboard on the scale.

**Acceptance Criteria:**
- Given a named scorer after the deadline, when they open an item, submit a step, and open it again, then the first response has no AI score and the second has it, while another unscored item still has none (api test).
- Given the scoring screens, when Playwright runs at 320, 360 and 1440 px, then list, item, submit and rejected resubmit pass axe and the scale is operable by keyboard.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (four sonnet reviewers, per the runbook's rule for access and data-model changes). The implementation ran in the builder's own context (the brief's rule), so patches were applied directly.
- verdicts: 34 findings — high 0, medium 4, low 25, false 5, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind: `answer_id` (a UUIDv7 carrying its save time) was served in the list, the item and the URL, so a scorer could link one student's answers — scorers now get only `ref`, a keyed HMAC of the answer id (app secret), which also orders answers within a question; the answer id never leaves the server; tests assert no answer, attempt or user id in list or item.
  - `[low]` `[reject]` Blind: «Svar N» renumbers when a late attempt closes — documented decision (Design Notes); the page and URL key on `ref`, which never changes; freezing numbers needs a stored numbering for a rare extension case.
  - `[low]` `[reject]` Blind: every item read and submit rebuilds the whole list — a Control test has tens of answers; a targeted query adds a second definition of "listed answer" to keep in sync.
  - `[false]` `[reject]` Blind: `next(...)` in `_item` can raise StopIteration — `read_for_assessment` returns every frozen long/Adapted item, and the entry comes from the same frozen list; the second connection is the pattern `tests.assessed` already uses.
  - `[low]` `[patch]` Blind: the AI step shows without the assessment's state, and «har ingen vurdering» reads as final — a stored item score is written once and never changes, so showing it is right; the missing case now reads «KI-vurderingen av dette svaret er ikke klar ennå.». (The "adjustment tables" claim is unrelated: `student_adjustments` is Tilrettelegging.)
  - `[low]` `[reject]` Blind: a malformed scorer id on DELETE answers "No such Control test" — Admin-only route fed by the page's own ids; cosmetic.
  - `[false]` `[reject]` Blind: no confirmation before an irreversible submit — the AC requires the consequence stated above the button and no dialog (UX-DR9, UX-DR78).
  - `[low]` `[reject]` Blind: every home fetches `/api/scoring` — one indexed query per home load; a flag on `/me` would couple `identity` to `assessment`.
  - `[low]` `[patch]` Blind: missing tests (non-Control session, removed scorer's scores, `control_test_facts`) — tests added (ordinary Class session refused on every route, scores kept after removal); openapi/schema were regenerated (left out of the review diff on purpose); e2e error states are worded by Vitest.
  - `[low]` `[reject]` Blind: personal-data and audit gaps — FK cascades follow the identity tables' rule; both tables are reported for the 15.2 registry; scorer reads need no audit (AC: the Admin's reads).
  - `[low]` `[patch]` Blind: dead `assessment.scored_sessions` — deleted. `__all__` order: ruff passes; not changed.
  - `[low]` `[patch]` Blind: the scale shows twice under two «Skala» labels — the Valgknapper legend now reads «Velg trinn». The breadcrumb tap-target change only widens crumbs under 44 px.
  - `[low]` `[reject]` Blind: a student may name themselves in free text, and Adapted facts can fingerprint a game — inherent in reading answers; listed as a residual risk for the founder.
  - `[medium]` `[patch]` Edge: UUIDv7 answer ids in list and URL — same root and fix as the first Blind row.
  - `[low]` `[reject]` Edge: the list opens at the deadline while extended attempts are still open, and numbers shift — same as the Blind numbering row; only closed attempts are listed by design.
  - `[low]` `[patch]` Edge: AI step state — same fix as the Blind AI-state row.
  - `[low]` `[patch]` Edge: a submit returns the answer to an Admin scorer with no audit row — `submit` now writes the `answers_read` row too; the test counts it.
  - `[low]` `[patch]` Edge: a non-UUID answer id answered 403 to a named scorer — the path now takes `ref` (text) and an unknown one answers 404 after the access check; same root as the UUIDv7 row.
  - `[low]` `[reject]` Edge: the scorers page counts answers before the deadline — Admin-only and true (closed attempts); harmless.
  - `[false]` `[reject]` Edge: a large IN clause exceeds the bind limit — Postgres allows 65 535 parameters; a Control test has tens of answers.
  - `[false]` `[reject]` Edge: a scorer with no user row shows blank — `control_test_scorers.user_id` cascades with the User, so a named scorer always has a row; `people` reads inactive Users too.
  - `[low]` `[patch]` Verification: no test that an ordinary Class session is refused — test added (403 on the list for Admin and scorer, 404 on the scorers routes, no scorer row).
  - `[low]` `[patch]` Verification: no test of the within-question order — the list test asserts the order follows `ref`.
  - `[low]` `[patch]` Verification: no test that removal keeps scores — the removed scorer now scores first and the row is asserted after removal.
  - `[medium]` `[patch]` Verification (other): UUIDv7 `answer_id` served — same root and fix as the first Blind row.
  - `[low]` `[reject]` Verification (other): `_picked` refactor not asserted line by line — behaviour-preserving on every branch (the edge reviewer checked); the assessment tests send the fact line in the request.
  - `[low]` `[reject]` Intent: the two policies are `ANY_USER` and the gate is in `tests.blind` through `authz` helpers — the pattern of `tests.take_own` and `games.read_own` (policy plus `authz` scope); api tests prove it.
  - `[low]` `[reject]` Intent: the Lenke is tested only on Hjem — it is one component in the shared `HomePage` of all three homes.
  - `[low]` `[reject]` Intent: Playwright uses stand-ins — the pattern of the 12.2–12.5 specs; behaviour is proved by the api tests.
  - `[low]` `[reject]` Intent: one entry per saved non-blank answer, not per item — recorded decision (Design Notes), listed for the founder.
  - `[low]` `[patch]` Intent: the item response was not checked for ids — the item test now asserts no student, attempt or answer id and no address.
  - `[medium]` `[patch]` Intent: UUIDv7 `answer_id` — same root and fix as the first Blind row.
  - `[false]` `[reject]` Intent: extras beyond the story — removal makes "shown only while they are a named scorer" reachable; the trigger backs "no update path"; refusing test students keeps answers away from participants.
  - `[low]` `[reject]` Intent: backend tests seed attempts by SQL — keeps the tests under a second; the attempt and assessment pipelines have their own tests.

## Design Notes

- Blank answers are not listed: the AI scores them 0 by code (`source='blank'`), so a human score there compares nothing; `human_scores.answer_id` then always names a stored `test_answers` row.
- Numbering groups answers by question (scorers usually score one question across answers) and orders within by a hash, not by opening time or name; a late-closed attempt (an extension) may shift numbers, the URL uses the answer id.
- The Admin reads but scores only when named; reads are audited, not the scorer's own.

## Verification

**Commands:**
- `uv run pytest tests/assessment/test_human_scores.py tests/test_migrations.py tests/test_authz_rules.py tests/test_imports.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/control-test-scoring.spec.ts e2e/control-test.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Admin names scorers among existing Users for each Control test (Admin-område → «Kontrolltest» → «Sensorer og svar i …», `/admin/kontrolltest/[id]`; by e-mail, refused `unknown` or `test_student`; «Fjern» keeps their scores; each naming and removal audited). A named scorer, with no Admin role, sees «Sensur av Kontrolltest» on their own home (any of the three) while `GET /api/scoring` lists a test. After the Test deadline `/sensur/[id]` lists every long-answer and Adapted answer with text of the closed attempts as «Svar N» with type, question and «Vurdert»/«Ikke vurdert», no name, address or id; each answer is addressed by `ref`, a keyed hash of its id. An answer shows the question, the original text, an Adapted item's facts, and the pinned guide entry with its criteria and scale. The AI's step is absent until the scorer's own score is stored. The scorer picks a step on Valgknapper, reads «Vurderingen kan ikke endres etter at den er lagret.» and presses «Lagre vurdering»; one `human_scores` row (migration 0208, owned by `assessment`, update refused by a trigger) is written; a second is 409 `human_score_exists`; then «Din vurdering» and «KI-vurderingen: n av 4» show for that answer only. Access is decided by `platform/authz` (`control_test_answers.read`/`.score`, scope `control_tests_scored_by`, or `control_tests.manage`); the Admin reads (each read, also through a submit, audited `control_test.answers_read`) and scores only when named.

**Files.**
- `backend/migrations/versions/0208_human_scores.py` (new): `control_test_scorers`, `human_scores`, the update trigger.
- `backend/app/modules/assessment/{models,service}.py`, `README.md`: the tables; naming, removal, the once-only insert, reads and counts.
- `backend/app/platform/authz.py`: two policies, `control_tests_scored_by`, `reads_control_test_answers`.
- `backend/app/modules/sessions/service.py`: `control_test_facts`.
- `backend/app/modules/tests/blind.py` (new), `routes.py`, `schemas.py`, `assessed.py` (`adapted_facts`), `README.md`: the scorer and Admin routes.
- `backend/tests/assessment/test_human_scores.py` (new), `tests/test_migrations.py` (head 0208).
- `frontend/src/modules/assessment/{scoring-api.ts,scoring.ts,scoring.test.ts,scoring-pages.tsx,scoring-link.tsx}` (new), `src/app/(app)/sensur/**` (new), `src/modules/admin/control-test-scorers-page.tsx` and `src/app/(app)/admin/kontrolltest/[sessionId]/page.tsx` (new), `admin/control-tests-page.tsx`, `identity/{home-page.tsx,homes.ts}`, `components/breadcrumb.tsx` (44 px crumbs), `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}` (generated).
- `frontend/e2e/control-test-scoring.spec.ts` (new).

**Review.** 34 findings from four sonnet reviewers. Patched: 1 medium entry (UUIDv7 answer ids served to scorers: four rows, one root) and 9 low entries (AI step wording while not ready, Admin submit audited, missing tests for ordinary sessions, within-question order, kept scores and ids in the item response, dead `scored_sessions`, the duplicate «Skala» label). Deferred: none. Rejected: 15 low and 5 false, each with its reason in the triage log.

**Follow-up review: not recommended.** No high entry, and one medium entry was patched (counts: high 0, medium 1, low 9).

**Verification.**
- Backend: full suite with `--maxprocesses=8`: 3846 passed, 4 skipped before the review patches, and 3847 passed, 4 skipped after them. `ruff check` is clean. The new tests' slowest call is under 0.5 s. The 2 s first setup is the shared migration, so no new test is over 1 s.
- Frontend: `tsc` clean, Vitest 1196 passed, `lint:colours` and `check:copy` pass, `next build` ok (`/sensur`, `/sensur/[sessionId]`, `/sensur/[sessionId]/[answerId]`, `/admin/kontrolltest/[sessionId]`).
- Playwright on the lane-3 stack (8082), after the patches: `control-test-scoring`, `homes`, `control-test`, `classes` and `class-session`: 58 passed. Before the patches, the same specs plus `student-home`, `test-student`, `ai-assessment`, `game-start`, `order-field`, `week-table`, `guided-week` and `admin-institutions`: all passed.

**Decisions taken in place of the founder.**
1. Blank and unsaved answers are not listed: the AI scores them 0 by code. Only closed attempts are listed. An attempt closing late (an extension) can shift «Svar N»; the `ref` stays.
2. Numbers group answers by question, ordered within by the keyed hash.
3. Scorers are any active User but a test student. The Admin reads every Control test's answers (audited) but scores only when named. Removal keeps scores.
4. After their own score the scorer sees only the AI's step, never its feedback.
5. All new copy is [ASSUMPTION] draft: the «Sensur» pages, the scale and consequence lines, the «Sensorer» page and three audit action names.

**Residual risks.** A student can identify themselves in free text, and an Adapted item's facts may let a scorer who knows the games recognise one. Personal data: new tables `control_test_scorers` (`user_id`, `named_by`) and `human_scores` (`scorer_id`, a User's judgement) belong in the 15.2 registry.
