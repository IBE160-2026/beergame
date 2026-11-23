---
title: 'Story 12.10: Compare human and AI scores and mark the Scoring guide as checked'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'f3ac81ce26456cb3254613a713cb765d0525b5d0'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 12.9 stores blind human scores, but nobody sees how they compare with the AI's, and `content.service.is_checked` still answers False for every Scoring guide, so «Ikke kontrollert med en Kontrolltest.» never goes away (FR-81, FR-82, AD-27).

**Approach:** A pure `analysis.agreement` computes the five FR-82 measures; an Admin-only results page under «Kontrolltest» shows every answer's human and AI scores side by side with the measures, preliminary while scores are missing. When the last named scorer's last score is submitted, `assessment` calls `content.service.mark_checked` in the same transaction, writing a `scoring_guide_checks` row that `is_checked` reads from now on.

## Boundaries & Constraints

**Always:**
- `backend/app/analysis/agreement.py` (pure, AD-1): `agreement(human_scores, ai_scores, *, words) -> Agreement`. `human_scores`: sequence of `(answer_key, step)`; `ai_scores`: `{answer_key: step}`; `words`: `{answer_key: word count}`. One pair per human score whose answer has an AI step. Measures: `pairs`; `exact` (share h == a); `within_one` (share |h − a| ≤ 1); `offset` (mean a − h, positive = AI higher); `compression` (population SD of the paired AI steps / that of the human steps; None when the human SD is 0); `by_length`: bands `short` (< 50 words), `medium` (50–149), `long` (≥ 150), each with `pairs`, `exact`, `within_one` (None for 0 pairs). Shares and means as floats rounded to 4 decimals; all None (and `pairs` 0) with no pairs. Steps outside 0–4 raise `ValueError`.
- Migration `0209` (Revises `0208`), table owned by `modules/content`: `scoring_guide_checks(scoring_guide_id FK content_records.id, model_config_id FK ai_model_configs.id, control_test_id uuid NOT NULL no FK, checked_at; PK (scoring_guide_id, model_config_id))`, a trigger refusing UPDATE. `content.service.mark_checked(s, scoring_guide_id, model_config_id, *, control_test_id, now) -> bool` (ON CONFLICT DO NOTHING; the first check stays). `is_checked(id, config, *, session=None)` reads it; None config → False.
- Completion, in `tests.blind.submit`'s transaction: `assessment.service.record_human_score(...)` first locks the Control test's `control_test_scorers` rows (`FOR UPDATE`), refuses (→ 403) a scorer no longer named, inserts, and then, when the Control test has ≥ 1 named scorer, ≥ 1 listed answer, no open attempt, and every named scorer has a score on every listed answer, calls `content.service.mark_checked(pinned guide id, session model_config_id)`. `assessment` is the only caller (import test allows `assessment` → `content.service`). Audit row `control_test.checked` (ids) when a row was written.
- `ControlTestFacts` gains `model_config_id`; the guide id is `guide.in_force(s, id).record.id` (pinned at creation, 12.7).
- Results: `GET /api/admin/control-tests/{session_id}/results` (policy `control_tests.manage`; 404 `not_found` for no Control test; audit `control_test.results_read`, ids). Body: test, pinned guide {version, edited}, model config {name, model_version} | null, scorers [{name}] in naming order, rows (the 12.9 entries: number, type, question, words, `human` list aligned to scorers with null for missing, `ai` step | null), `missing` (named scorers × listed answers − their scores), `ai_missing`, `open_attempts`, `complete`, `checked` (`is_checked` of the pair), `withheld`, `measures` (from `analysis.agreement` over named scorers' scores) | null. Before the Test deadline rows are empty. `withheld`: the reader is a named scorer with an unscored listed answer → every `ai` and `measures` null (blind, AD-27).
- Web: `/admin/kontrolltest/[sessionId]/resultater` «Resultater»: «Teller aldri med i en Klasseøkt.», pinned guide version and model config, status line (checked / preliminary with the missing count in words), the five measures as labelled numbers (`formatNumber`, percentages), a «Etter svarlengde» table, and the side-by-side HTML table (Svar, type, ord, one column per scorer, KI) in a horizontally scrollable region. Lenke to it from the «Sensorer» page and each Kontrolltest row. Copy in `nb.ts` marked `[ASSUMPTION]`. No chart.

**Never:** an agreement threshold for «checked» (AD-27: all scores submitted); unmarking a check; showing AI feedback; results for anyone but the Admin; `mark_checked` called outside `assessment`; changes to the demo Class, seeds or `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Offset | h [0,1,2,3], a [1,2,3,4] | exact 0, within 1, offset 1, compression 1 | — |
| Compressed | h [0,1,2,3,4], a [1,2,2,2,3] | exact 0.2, within 1, offset 0, compression 0.4472 | — |
| Flat humans | h [2,2], a [1,3] | compression None | — |
| Partial | 2 scorers × 3 answers, 4 scores | `missing` 2, preliminary, unchecked | — |
| Last score | 6th score submitted | check row, `is_checked` True for pair only | other config / newer version: False |
| Concurrent last | two scorers submit their last at once | exactly one check row | row lock serialises |
| Withheld | Admin is named and has unscored answers | `withheld`, no `ai`, no measures | — |
| Outsider | Lecturer, Student, non-Admin scorer GET results | — | 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/analysis/total.py` -- style of a pure module (Fraction, `SCALE_TOP`).
- `backend/app/modules/content/{models,service}.py` -- `content_records`; `is_checked` (~513) stub to replace; add table + `mark_checked`.
- `backend/app/modules/assessment/service.py` (~1540–1637) -- `insert_human_score`, `scorers_of`, `human_scores_by`, `score_counts`; add `record_human_score`, `scores_of(s, answer_ids) -> {answer: {scorer: step}}`; `assessment_of(s, attempt_id).scores` gives AI steps.
- `backend/app/modules/tests/blind.py` -- `_entries`, `_reader`, `submit`; new `backend/app/modules/tests/control_results.py` builds the results.
- `backend/app/modules/tests/guide.py` -- `in_force`; `_out` passes the session's `model_config_id` to `is_checked` (unchanged).
- `backend/app/modules/sessions/service.py` (~868) -- `ControlTestFacts`, `control_test_facts`.
- `backend/app/modules/tests/{routes,schemas}.py` (~658) -- `_SCORERS` routes pattern; add results route and `ControlResults*Out`.
- `backend/app/ai/config.py` -- `get(id)` for the config's name.
- `backend/tests/test_imports.py` (~109) -- allow `app.modules.content.service` from `assessment`.
- Tests: `backend/tests/assessment/test_human_scores.py` (fixtures, SQL-seeded attempts) → new `backend/tests/assessment/test_control_results.py`; new `backend/tests/analysis/test_agreement.py`; `backend/tests/scoring_guide/test_scoring_guide.py` (~151, the "never checked" test changes meaning); `backend/tests/test_migrations.py` (HEAD 0209).
- Frontend: `src/modules/admin/control-test-scorers-page.tsx` (page pattern), `src/modules/admin/control-tests-page.tsx` (row Lenke), `src/modules/assessment/scoring-api.ts` (hook), `src/modules/identity/homes.ts` (path), `src/lib/number-format.ts`, `src/copy/nb.ts` (`scoring`), new `src/modules/admin/control-test-results-page.tsx`, `src/app/(app)/admin/kontrolltest/[sessionId]/resultater/page.tsx`.
- E2E: `frontend/e2e/control-test-scoring.spec.ts` (route stand-in pattern) → new `frontend/e2e/control-test-results.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/agreement.py` + `backend/tests/analysis/test_agreement.py` -- measures with hand-worked golden cases (matrix rows 1–3, by-length bands, no pairs, multiple scorers on one answer, missing AI).
- `backend/migrations/versions/0209_scoring_guide_checks.py`, content models/service -- table, `mark_checked`, `is_checked`.
- `assessment/service.py`, `sessions/service.py`, `tests/blind.py`, new `tests/control_results.py`, routes, schemas, `test_imports.py` -- completion and results.
- `backend/tests/assessment/test_control_results.py` -- matrix rows 4–8; edited guide checked, Lecturer 403 on results and scoring; course session pinned to the checked version with the same config: guide `checked: true`, assessment `checked: true`; scores appear in no other response.
- Frontend files, `npm run api:generate`; Vitest for view helpers; `frontend/e2e/control-test-results.spec.ts` -- preliminary and complete at 320/360/1440 with axe.

**Acceptance Criteria:**
- Given every named scorer has scored every listed answer of a closed Control test, when the last score is submitted, then `is_checked(guide, config)` is True, False for another config and for a later guide version, and the Lecturer's «Sensorveiledning» api answer of a session pinning that pair has `checked: true`.
- Given the results page, when Playwright runs at 320, 360 and 1440 px, then preliminary and complete results pass axe and show the measures, the missing count and the side-by-side table.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment. Four sonnet reviewers ran, per the runbook's rule for data-model, access and concurrency changes. The builder did the implementation in its own context (the brief's rule), so patches were applied directly.
- verdicts: 38 findings — high 0, medium 4, low 22, false 8, maybe-false 4
- findings:
  - `[medium]` `[patch]` Blind: the status line said «kontrollert» from `checked` alone. A second Control test on a pair that was already checked therefore read as checked while scores were missing. The page now says «Kontrollert» only when `complete && checked`, and a new line says another Control test checked the pair. Vitest covers it.
  - `[medium]` `[patch]` Blind: completion was evaluated only when a score was stored. Removing the last scorer who still owed scores left a complete Control test unchecked for good. `remove_scorer` now holds the scorer rows and calls `assessment.settle_after_removal`, which applies the same rule; `assessment` is still the only caller of `mark_checked`. Test added.
  - `[low]` `[patch]` Blind: `listed` and `settled` were read before the scorer-row lock. `blind.submit` now takes `assessment.hold_scorers` first and reads the answers after it. `record_human_score` takes the held set. This lock does not cover an attempt that closes during the transaction (residual risk).
  - `[low]` `[reject]` Blind: a named Admin-scorer sees other scorers' steps in the human columns. AD-27 hides only the AI score, and in SM-7 the founder scores alone. Recorded as a founder decision.
  - `[low]` `[patch]` Blind: `ai_missing` showed whether the AI had scored while `withheld`. It is now 0 while withheld, and a test asserts it.
  - `[low]` `[reject]` Blind: `submit` duplicates `_entry`'s lookup, and `results` reads `assessment_of` once per attempt. A Control test has tens of answers, and the lock-first order needs the list in `submit`.
  - `[false]` `[reject]` Blind: one scorer and one answer mark a guide checked, with no threshold. Under AD-27, checked means every human score is submitted. The measures are shown, not used as a gate.
  - `[low]` `[reject]` Blind/Edge: the trigger refuses UPDATE but not DELETE. `content_records` and `human_scores` use the same UPDATE-only pattern, and no code path deletes.
  - `[low]` `[patch]` Blind/Verification: a second completion on a checked pair left no audit trace and had no test. `control_test.checked` is now written on every completion, with `first` set to true when that completion wrote the row. A test with two Control tests on one pair asserts one row and two audit rows.
  - `[low]` `[reject]` Blind: `# type: ignore` on the band literal, and `measures!`. These are narrow typing gaps, and tests cover the behaviour.
  - `[false]` `[reject]` Blind: `offsetText` can print «−0 trinn». The formatter drops the minus sign when no digit is non-zero, so −0.00001 prints «0 trinn».
  - `[low]` `[reject]` Blind: empty results have no back link. The breadcrumb leads back, so this is cosmetic.
  - `[low]` `[reject]` Blind: `__all__` order, and copy functions that take both a count and a text. ruff passes, and the pair keeps the singular/plural choice apart from the formatter.
  - `[low]` `[reject]` Blind: the band thresholds appear in the copy too. There are three fixed bands, with tests on both sides.
  - `[low]` `[reject]` Blind/Intent: Playwright uses stand-ins, and no browser test shows «Ikke kontrollert…» going away. Stories 12.2–12.9 use the same pattern. The api test asserts `checked: true` on «Sensorveiledning», and the existing components hide the line on `checked`.
  - `[medium]` `[patch]` Edge: completion was never re-evaluated after a removal. Same root and fix as the second Blind row.
  - `[low]` `[reject]` Edge: a 409 resubmit could repair a missed check. With the removal fix, the only path that misses one is a late attempt whose answers are all blank (residual risk).
  - `[low]` `[patch]` Edge: `listed` and `settled` were read before the lock. Same fix as the third Blind row.
  - `[low]` `[reject]` Edge: FOR UPDATE does not block a scorer who is named at the same moment. A scorer named after the last score joins a complete Control test, and the check reflects the scorers at that moment.
  - `[false]` `[reject]` Edge: `in_force` may fall back to the latest default. Every Control test pins its guide at creation (Story 12.7).
  - `[low]` `[reject]` Edge: other scorers' steps are shown while withheld. Same as the Blind row.
  - `[low]` `[patch]` Edge: `ai_missing` while withheld. Same fix as the Blind row.
  - `[low]` `[reject]` Edge: AI steps of an assessment that is not ready enter the measures. A stored item score is written once and never changes (the rule from Story 12.9).
  - `[false]` `[reject]` Edge: a step off the scale raises a 500. Both columns have a CHECK constraint of 0–4.
  - `[medium]` `[patch]` Edge: a complete but unchecked Control test reads as preliminary with no reason given. Fixed by the removal path. The status-line fix is the first Blind row.
  - `[false]` `[reject]` Edge: the FK RESTRICT on `content_records` blocks deleting a checked version. Content records are never deleted (AD-23).
  - `[false]` `[reject]` Edge: a DELETE silently unchecks a guide. No code path deletes.
  - `[maybe-false]` `[reject]` Edge (claim): `model_config_id` has no FK, although the spec names one. `test_imports` forbids any module other than `app/ai` from naming the config table, and `class_sessions.model_config_id` has no FK either. A referenced config is immutable and never deleted. AD-6 settles it; the deviation is recorded here.
  - `[low]` `[patch]` Edge (claim): completion by removal never marks the guide checked. Same fix as the second Blind row. Completion through a late attempt whose answers are all blank remains a residual risk.
  - `[low]` `[patch]` Verification: re-marking a checked pair was untested. Test added (see the Blind audit row).
  - `[low]` `[patch]` Verification: word counts were never checked from a stored answer. A test now seeds a 60-word and a 160-word answer and, through the route, asserts `words` and the medium and long bands.
  - `[maybe-false]` `[reject]` Verification: the concurrency test cannot force an interleave. A deterministic race needs a test hook in the request path, and the lock order is now explicit. It would be `low` at most.
  - `[low]` `[patch]` Verification: `ScorerNotNamed` was untested. A service-level test now asserts the refusal and that no row is written.
  - `[low]` `[patch]` Verification: the two new audit actions had no labels. They now have labels in `nb.ts`, and `audit.test.ts` asserts them.
  - `[false]` `[reject]` Verification (other): `settled` is read outside the lock. The lock is now taken first (patched above). An attempt closing is a separate transaction that the scorer lock never covered.
  - `[maybe-false]` `[reject]` Verification (other): `results.complete` and the record rule are written twice. Both are tested on the complete and incomplete paths, and a shared helper would cross module ownership (`tests` against `assessment`).
  - `[false]` `[reject]` Intent: the api-access AC is tested on one route only. Human scores are served only by `/api/scoring/*` (Story 12.9, tested) and by this route, and tests show both refuse outsiders.
  - `[maybe-false]` `[reject]` Intent: `mark_checked` takes a session, the Control test and the time as well as the AC's two ids. The AC names the pair. The extra arguments are the same transaction and the record the AC asks for.

## Design Notes

- Pairs are per human score: with two scorers an answer gives two pairs. Measures use only currently named scorers (a removed scorer's kept scores are left out) and only answers with an AI step.
- Length bands are fixed word counts so results compare across Control tests; the AI scores blank answers 0 by code and they are not listed (12.9).
- `control_test_id` has no FK: a check outlives the Control test's retention, as `content_records.class_session_id` does.
- Completion is settled where it can change: on each stored score and (after review) on a scorer's removal, both under the held scorer rows. `control_test.checked` is audited on every completion, `first` false when another Control test checked the pair before.
- `model_config_id` has no foreign key (only `app/ai` names its tables, AD-6; `test_imports` enforces it), as `class_sessions.model_config_id`.

## Verification

**Commands:**
- `uv run pytest tests/analysis/test_agreement.py tests/assessment/test_control_results.py tests/assessment/test_human_scores.py tests/scoring_guide tests/test_migrations.py tests/test_imports.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/control-test-results.spec.ts e2e/control-test-scoring.spec.ts e2e/control-test.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** `analysis.agreement` (pure, AD-1) computes the five FR-82 measures over each pair of a human step and the AI's step for the same answer: exact, within one step, offset (AI minus human), compression (SD ratio, None when the human steps do not vary) and agreement by answer length (under 50 / 50–149 / 150+ words). Golden cases were worked by hand (constant offset, compressed scale, flat humans, two scorers, bands, thirds). Admin-område → «Kontrolltest» → «Resultater» (`/admin/kontrolltest/[id]/resultater`, `GET /api/admin/control-tests/{id}/results`, `control_tests.manage`, each read audited `control_test.results_read`) shows:
- «Teller aldri med i en Klasseøkt.»;
- the pinned guide version and model config;
- checked, or preliminary with the missing scores, open attempts and missing AI steps in words;
- the measures as labelled numbers through `formatNumber`;
- the length table;
- an HTML table with every answer's per-scorer steps and the AI step.

An Admin who is a named scorer with answers still to score gets no AI step and no measures. Migration 0209 adds `scoring_guide_checks` (owned by `content`, update refused by a trigger). `content.mark_checked` is called only by `assessment`, in the transaction of the last stored score or of a removal that completes the Control test, under the held scorer rows (`hold_scorers`). `content.is_checked` reads the table, so «Ikke kontrollert med en Kontrolltest.» goes away on «Sensorveiledning» and feedback for exactly that guide version and model config.

**Files.**
- `backend/app/analysis/agreement.py` (new), `backend/tests/analysis/test_agreement.py` (new): the measures.
- `backend/migrations/versions/0209_scoring_guide_checks.py` (new), `backend/app/modules/content/{models,service}.py`: the table, `mark_checked`, `is_checked`.
- `backend/app/modules/assessment/service.py`: `hold_scorers`, `record_human_score`, `settle_after_removal`, `scores_of`.
- `backend/app/modules/tests/blind.py`: lock-first submit, removal settling, `control_test.checked` audit, word counts.
- `backend/app/modules/tests/control_results.py` (new), `routes.py`, `schemas.py`: the results.
- `backend/app/modules/sessions/service.py`: `ControlTestFacts.model_config_id`.
- `backend/tests/assessment/test_control_results.py` (new), `tests/test_imports.py`, `tests/test_migrations.py` (head 0209), `tests/scoring_guide/test_scoring_guide.py`.
- `frontend/src/modules/admin/control-test-results-page.tsx` (new), `src/app/(app)/admin/kontrolltest/[sessionId]/resultater/page.tsx` (new), `src/modules/assessment/{results.ts,results.test.ts}` (new), `scoring-api.ts`, `admin/{control-tests-page,control-test-scorers-page}.tsx`, `identity/homes.ts`, `admin/audit.test.ts`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}` (generated).
- `frontend/e2e/control-test-results.spec.ts` (new).

**Review.** 38 findings from four sonnet reviewers.
- Patched:
  - 2 medium entries:
    - the status line read «kontrollert» while this Control test was still incomplete;
    - a removal that completed the Control test never marked it.
  - 6 low entries:
    - lock before reading answers;
    - `ai_missing` hidden while withheld;
    - completion audited with `first`;
    - tests for a second Control test on a checked pair, `ScorerNotNamed`, and real word counts in the bands;
    - audit labels.
- Deferred: none.
- Rejected: 26 low, false and maybe-false entries, each with its reason in the triage log.

**Follow-up review: recommended.** Two medium entries were patched (counts: high 0, medium 2, low 6). The specific unverified risk is the completion path under concurrency. The concurrent-last-score test cannot force an interleave, and the new removal path settles under the same lock but has no race test.

**Verification.**
- Backend: full suite with `--maxprocesses=8`:
  - Before review: 3869 passed. One failure came from stale test databases that had migrated an earlier draft of 0209 with a config FK. The FK was dropped there, the file was fixed, and the test reran green.
  - After review: 3873 passed, 1 failed (`tests/debrief/test_explanation.py::test_step_one_the_one_send_the_gate_and_the_readers`). That test passes when rerun on its own and is unrelated to this story.
  - One run made at the same time as the stack rebuild errored on connections. It is not counted.
- `ruff check` and `ruff format` are clean. No new test call is over 1 s (the slowest is 0.97 s; the ~1 s setups are the shared first setup).
- Frontend: `tsc` clean, Vitest 1199 passed, `lint:colours` and `check:copy` pass, `next build` ok (`/admin/kontrolltest/[sessionId]/resultater`).
- Playwright on the lane-3 stack (8082) after the patches covered `control-test-results` (preliminary and complete at 320/360/1440 with axe, withheld, the links), `control-test-scoring`, `control-test`, `homes`, `game-start`, `order-field`, `week-table`, `guided-week`, `scoring-guide`, `ai-assessment` and `admin-audit`: 127 passed.

**Decisions taken in place of the founder.**
1. «Checked» means every named scorer scored every listed answer and no attempt is open. There is no agreement threshold (AD-27). The first check of a pair stays, and a check is never taken back.
2. Each human score is one pair. Only currently named scorers count, and only answers with an AI step.
3. Length bands are fixed at under 50, 50–149 and 150+ words.
4. The results are for the Admin only. A named Admin who is still scoring sees no AI step or measures, but does see the other scorers' steps.
5. No chart is shown, only tables.
6. All new copy is [ASSUMPTION] draft: the «Resultater» page, the measure labels and help texts, and two audit labels.

**Residual risks.**
- A late attempt (an extension) whose answers are all blank, closing after every score is in, leaves the Control test complete but unchecked until another score or removal.
- An attempt closing in the same instant as the last score is not held by the scorer lock.
- Personal data: no new table holds a `user_id` or User text. `scoring_guide_checks` holds ids only.
