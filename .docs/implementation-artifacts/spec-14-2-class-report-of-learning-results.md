---
title: 'Story 14.2: Class report of learning results'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'c162b138481446e2af23e9940d68f9e15e068c68'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-14-1-class-report-of-the-games.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The learning read's selection-in-force path after the Start-date lock (locked_pins, then selection_of) has no test of its own.
    evidence: |-
      Every learning test uses an unlocked session (effective selection). The call mirrors tests.commands.open_attempt, but a regression passing None for pins would go unnoticed. Settle with one test on a locked session (tests.individual_test.test_adapted.locked_with).
    location: >-
      backend/app/modules/tests/class_results.py class_results
    severity: low
  - summary: >-
      Still-to-submit with no Test deadline set (deadline None counts as still to submit) is untested.
    evidence: |-
      All learning tests use a session with the TEST deadline; the extension test covers deadline > now both ways. Whether a reporting session can lack a Test deadline at that point was not verified.
    location: >-
      backend/app/modules/reports/class_report_learning.py _still_to_submit
    severity: low
  - summary: >-
      The learning part uses a local stand-in for reports.scope.reporting_students(); relink at the Epic 13 merge.
    evidence: |-
      reports.scope exists only on epic-13. _reporting_students (registered Students less identity.test_students, none for a Control test) repeats its rule; at merge call scope.reporting_students(session, id) so one predicate holds it (AD-13).
    location: >-
      backend/app/modules/reports/class_report_learning.py _reporting_students
    severity: low
---

<intent-contract>

## Intent

**Problem:** The Klasserapport (Story 14.1) shows how the Class games went but not what the class learned: no Starting task results beside the matching test items, no results per Individual test question, and no view of the AI assessment totals (FR-64).

**Approach:** A learning part under the Klasserapport, fed by its own read `GET /api/class-sessions/{id}/class-report/learning` (`getClassLearningReport`, same `class_report.read` policy). `tests.service` gives one bulk read of the session's results (Starting task answers, attempts with frozen items, stored computed scores, AI steps through `assessment.service`, totals from `analysis.total_score` and a new pure `analysis.core_total_score`); `reports` aggregates it with no identifier in the response. The page refetches on `session:<id>` (prefix of the report key).

## Boundaries & Constraints

**Always:**
- Students: the reporting Students of the Class session (registered Students of the Class less test students; none for a Control test Class session), a local stand-in for `reports.scope.reporting_students()` documented for relink at the Epic 13 merge. Handed in = attempt status `submitted` or `auto_submitted`.
- Still to submit: reporting Students with an `open` attempt, or with no attempt whose effective Test deadline (`sessions.effective_test_deadline`, own extension included) is unset or in the future. Stated as a count.
- Starting task beside test items: for each question-set item with `starting_task_item` that is in force (not excluded), over Students who finished the Starting task (`played_before` row) and handed in an attempt holding that item: n, Starting task correct count and percent, test right count and mean credit percent. The overall «did both» count is stated.
- Results per question: every Core item of the selection in force (lock pin, else the selection in force), in set order; excluded items listed as «Tatt ut», with no figures and left out of every total. Computed items (choice, table, number, drawn): n handed-in attempts holding it, right/partly/wrong/not answered (credit ≥1 / between / ≤0 / no answer), mean credit percent. Long items: n and answered count only, marked as scored in the KI-vurdering. Replacement items and Adapted items are not per-question rows; a line states how many handed-in attempts had Adapted items and how many had replacement items, and that Adapted items differ between Students.
- AI part: `switched_off` when the pinned/unpinned switch is off; else per handed-in, closed attempt ready exactly as the Student's view reads it (status `ready`, every AI item scored; a stopped assessment counts only when ready); `not_ready` when none is ready, else `ready` with ready count of handed-in. Totals as percent of the frozen weights' sum; Core-only = same weighting over frozen items that are neither Adapted nor replacement, rescaled to 100 (`analysis.total.core_total_score`, pure, golden-tested). Distribution (median, quartiles, values sorted ascending) for both, plus counts per 10-point band (90–100 closed). Labelled AI-generated with «Teller ikke. Ingen karakter.»; never an Indicative letter.
- Small groups (decision): the live report shows figures at any group size, each with its n (AC: the 10-threshold is for stored aggregates and cross-Institution views, and these staff may read each answer, FR-63). It never sends a name, `user_id`, attempt id or per-Student row; score values go out sorted. Tested with a group of one.
- Every number from the api (AD-10); the page formats only. Fixed number of queries whatever the number of Students; the read writes nothing. `Cache-Control: no-store`.
- Merge layout as 14.1: new backend files `reports/class_report_learning*.py`, `tests/class_results.py` (re-exported in `tests/service.py` by an `import … as …` line near the imports, `__all__` untouched); new frontend files `class-report-learning*`, `class-report-parts.tsx`. Copy under `nb.classReport.learning`, drafts `[ASSUMPTION]`.

**Never:** no Indicative letter or letter setting read; no aggregates table or migration (14.3); no change to 14.1's response; no new event topic; no human scores; no answer text in the response; no web-app arithmetic beyond bar widths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Nobody handed in | attempts open or none | `submitted=0`, questions listed with n 0, AI `not_ready`, still-to-submit count | — |
| Did both | 2 Students finished Starting task, 1 of them handed in | Starting-task row n=1 | — |
| Excluded item | selection excludes item X | X listed `excluded`, no figures; totals use frozen weights | — |
| Extension | Class deadline passed, Student with own later deadline and no attempt | counted in still to submit | — |
| AI off | switch disabled | `ai.state=switched_off`, computed parts shown | — |
| AI partial | 1 of 2 closed attempts ready | `ready=1`, distributions of 1 value | — |
| Core-only | weights core 60 + adapted 40, core credit full, adapted step 0 | total 60, core 100 | — |
| Group of one | one Student | figures with n=1, no identifier in JSON | — |
| Assistant / other / Admin / bad id | GET | — | 403 `forbidden` |
| Control test | Control test session | empty learning part (0 Students) | — |

</intent-contract>

## Code Map

- `backend/app/analysis/total.py` -- `total_score` (Fraction loop, SCALE_TOP); add `core_total_score(computed, ai_items, weights, core)` sharing an exact helper.
- `backend/app/modules/tests/assessed.py:296` `_state_of`, `:315` `_view` -- the readiness rules to mirror; `_computed` credit/result rule (`right`≥1, `wrong`≤0).
- `backend/app/modules/tests/models.py` -- `starting_task_answers` (`played_before`), `test_attempts` (`items` `[{id,type,weight,replaces?}]`, `status`, `closed_at`, `effective_deadline`), `test_answers` (`score.{answered,credit}`, `value`).
- `backend/app/modules/tests/commands.py:151` `selection_of(s, id, pins)`; `sessions.locked_pins`; `selection.Selection.excluded`; `tests/service.py` `_has_content` rule (redo in SQL with `jsonb_typeof`).
- `backend/app/modules/assessment/service.py:238` `switch_of`, `:1536` `summaries_for_session`; add `item_scores_for_session(s, id) -> {attempt_id: {item_id: step}}` (one query) beside it.
- `backend/app/modules/sessions/service.py:2431` `own_test_deadlines`; add `effective_test_deadlines(s, id, user_ids)` right after it (Epic 13 inserts before it) via `repo.session_row`, `_with_own_deadlines`, `effective_test_deadline`.
- `backend/app/modules/identity/service.py:2721` `test_students(s, ids)`; `classes.service.registered_students`.
- `backend/app/modules/reports/class_report.py` -- `READ`, `distribution`, `percent`, `staffed_session`/`kind_of` pattern; `class_report_routes.py` route pattern; `class_report_schemas.DistributionOut`.
- Tests: `backend/tests/reports/test_class_report.py` (`call`, `execute`, `rows`, `klass`, `confirmed`); `tests/individual_test/test_adapted.py` `locked_with`.
- Frontend: `frontend/src/modules/reports/class-report-page.tsx` (Section, Toggled, Table, Bars, Distribution → move to `class-report-parts.tsx`), `class-report-api.ts` (key prefix `["reports","class",id]`, invalidated by `topics.ts`), `class-report.ts` formatters, `components/charts/cost-distribution.tsx`, `copy/nb.ts` `classReport`.
- e2e: `frontend/e2e/class-report.spec.ts` (stubbed report pattern, axe, reflow).

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/total.py` -- add `core_total_score`; `backend/tests/analysis/test_core_total.py` golden cases (rescale, missing share → None, zero core weight → None, ignores adapted/replacement ids).
- `backend/app/modules/assessment/service.py` -- `item_scores_for_session`.
- `backend/app/modules/sessions/service.py` -- `effective_test_deadlines`.
- `backend/app/modules/tests/class_results.py` (new) + re-export line in `tests/service.py` -- `class_results(s, class_session_id, students) -> ClassResults` (question set, selection, per-Student starting answers, attempt status/items/credits/answered, AI total and core, switch state, effective deadline).
- `backend/app/modules/reports/class_report_learning.py`, `class_report_learning_schemas.py` (new); route in `class_report_routes.py`.
- `backend/tests/reports/test_class_report_learning.py` (new) -- matrix rows, no identifiers, query count constant, access.
- Frontend: `class-report-parts.tsx` (moved shared parts), `class-report-learning.ts` (+ `.test.ts`), `class-report-learning.tsx`, hook/type in `class-report-api.ts`, page renders the learning part, `nb.ts` copy; `npm run api:generate`.
- `frontend/e2e/class-report.spec.ts` -- stubbed learning part at 320/1440 with axe and reflow, table toggles, AI off state.

**Acceptance Criteria:**
- Given a Lecturer owner with handed-in tests, when they open the Klasserapport, then «Læringsresultater» shows the Starting-task comparison, results per question and the AI distribution, each chart with «Vis som tabell».
- Given AI assessment off or not ready, when the report is shown, then the AI part states it and the computed parts are shown.
- Given 320 and 1440 px, when Playwright and axe run, then there is no horizontal page scroll and no violation.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 36 findings — high 0, medium 0, low 25, false 11, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) Total rounded twice (total_score to 2 decimals, then rescaled) — `_scores` now takes the total from `core_total_score` over every frozen item: exact rescale, one rounding.
  - `[low]` `[patch]` (blind) `ready` with `core` null hides the total chart too — the page shows each distribution that is present (`ai.total || ai.core`, null spreads filtered).
  - `[false]` `[reject]` (blind) Total and Core-only distributions of different n unmarked — each chart title carries its own count (`chartTitle(title, values.length)`).
  - `[false]` `[reject]` (blind) Assessment reads load test students' rows / query count not pinned — the reads are per Class session and fixed in number; test students are dropped by the Student list; the count test compares 2 and 12 Students.
  - `[false]` `[reject]` (blind) Several assessments or score rows per item, last wins — `uq_ai_assessments_attempt` and `pk_ai_item_scores (assessment_id, item_id)` make each unique.
  - `[low]` `[reject]` (blind) `effective_test_deadlines` has no direct test — covered through the route's extension test; a two-read helper over the one sanctioned rule.
  - `[false]` `[reject]` (blind) Still-to-submit counts no-deadline and open-past-deadline Students — that is the spec's rule (Always): an open attempt is still to submit until the sweep closes it.
  - `[false]` `[reject]` (blind) Per-question weight from the selection vs frozen weights — the selection is pinned at the Start-date lock and attempts open only after it.
  - `[low]` `[patch]` (blind) Golden test passes `"abc"` as `core` — now a list.
  - `[low]` `[reject]` (blind) `out == out | {...}` subset assertion style — readable enough; the excluded row's figures are asserted.
  - `[low]` `[patch]` (blind) No test of the SQL content rule (and stopped assessment) — test added for blank text, JSON null and an all-empty table; the stopped case is rejected (as the Student's view, ready only).
  - `[low]` `[patch]` (blind) Screen reader reads «0 av 0 (0,0 %)» for an item no Student reached — reads «Ingen har levert ennå.»; the «Ikke svart» column for long answers is correct (rejected part).
  - `[low]` `[patch]` (blind) Adapted line shown with weight 0 — rendered only when the Adapted weight is above 0; the AI label in the off state is kept (harmless).
  - `[false]` `[reject]` (blind) Generated api contract missing — `openapi.json`/`schema.ts` were regenerated with `npm run api:generate` and only left out of the review diff.
  - `[low]` `[patch]` (blind) Garbled docstring, duplicated AI_TYPES, no tracking marker — docstring fixed; the constant stays (reports may import only `tests.service`); the stand-in is in `deferred`.
  - `[low]` `[reject]` (blind) Test helpers imported from other test modules, weak «bokstav» check — the suite's own pattern (14.1 does the same); the response has no letter field.
  - `[low]` `[patch]` (verification) SQL `_has_content` not pinned — test added (`test_blank_long_answers_and_empty_tables_are_not_answered`).
  - `[low]` `[patch]` (verification) Replacement items' exclusion from Core-only never tested on a ready assessment — test added (`test_a_ready_test_with_replacement_items_scores_them_in_the_total_only`).
  - `[low]` `[defer]` (verification) Lock-pin path of the selection untested — deferred.
  - `[low]` `[patch]` (verification) Live refetch rests on an untested key prefix — Vitest case asserts `classLearningKey` starts with `classReportKey`.
  - `[low]` `[defer]` (verification) No-Test-deadline branch of still-to-submit untested — deferred.
  - `[low]` `[reject]` (verification) ADAPTED/AI_TYPES duplicated across modules — `reports` may only import `tests.service`; the type names are fixed content values.
  - `[low]` `[patch]` (verification) Rounding of total vs subscore — same fix as the first blind row.
  - `[low]` `[patch]` (edge) Core-only empty hides the page's total — same fix as the second blind row.
  - `[low]` `[patch]` (edge) Bands counted on raw values, distribution on 0.1 values — bands now count the values the distributions show.
  - `[low]` `[reject]` (edge) Session locked before the pin existed may list another version — legacy sessions only; attempts and list then share `selection_of`'s fallback.
  - `[false]` `[reject]` (edge) Starting task item without an answer counted wrong — `finish` refuses the final question while any item is open (`ItemsOpen`).
  - `[low]` `[patch]` (edge) Screen-reader text for null percents — same fix as the blind row.
  - `[low]` `[reject]` (edge) Unicode whitespace: SQL `\s` vs Python `strip()` — rare characters only; the count is the staff's overview, not a score.
  - `[false]` `[reject]` (edge) Race between status and score reads — scores are written once and `ready` is set only when every item has one, so a later read can only see more.
  - `[low]` `[reject]` (edge) Stopped switch reads «ikke klare» while the Student's view says switched off — wording only; the assessments are not ready and resume.
  - `[false]` `[reject]` (edge) Session deleted between reads — every read returns empty for a gone session; no 500.
  - `[false]` `[reject]` (edge) Corrupt credit raises — credits are written by `tests` in 0..1 and steps are checked 0..4 by the database.
  - `[low]` `[reject]` (intent) No minimum group size in code (reading "protective threshold") — the story's AC settles it: figures at any n for the Class's own staff (FR-63); recorded as a founder decision.
  - `[low]` `[reject]` (intent) Backend tests seed rows; page tests use stubs — the live e2e reads the real api; the hand-in path that writes the rows has its own tests (Epic 11/12).
  - `[false]` `[reject]` (intent) Generated client absent — regenerated, excluded from the review diff only.

## Design Notes

Founder decisions taken here (`[ASSUMPTION]`, in the report):
- Core-only leaves out replacement items as well as Adapted items: replacements stand in for Adapted items for some Students only, so keeping them would break comparability.
- «Did the Starting task» = finished it (final question answered); test credit of an unanswered item counts 0.
- No minimum group size in the live report (see Always).
- A stopped assessment's not-ready attempts count as not ready (as the Student's view reads them).

## Verification

**Commands:**
- `uv run pytest tests/reports tests/analysis/test_core_total.py -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/reports && npm run lint:colours && npm run check:copy` -- pass
- `npx playwright test e2e/class-report.spec.ts --workers=4` (lane stack) -- pass

## Auto Run Result

Status: done

Summary: the Klasserapport's learning part «Læringsresultater» under the games part, fed by `GET /api/class-sessions/{id}/class-report/learning` (`getClassLearningReport`, `class_report.read`, `no-store`): Starting task beside the matching test items over the Students who did both, results per question of the selection in force (taken-out questions listed «Tatt ut», out of every figure), still-to-submit count with extensions, and the AI totals with the Core-only subscore (new pure `analysis.total.core_total_score`, golden-tested) as distributions and 10-point bands, labelled «KI-generert. Teller ikke. Ingen karakter.», with switched-off and not-ready states. No letter, no identifiers, values sorted. Fixed number of queries; refetched on `session:<id>` through the report's key prefix.

Files: `backend/app/analysis/total.py` (`core_total_score`, shared exact helper); `backend/app/modules/tests/class_results.py` (bulk read, re-exported in `tests/service.py`); `assessment/service.py` (`item_scores_for_session`); `sessions/service.py` (`effective_test_deadlines`); `reports/class_report_learning{,_schemas}.py`, route in `class_report_routes.py`; tests `tests/analysis/test_core_total.py`, `tests/reports/test_class_report_learning.py`; frontend `class-report-parts.tsx` (shared parts moved from the page), `class-report-learning.ts` (+ test), `class-report-learning-part.tsx`, `class-report-api.ts` hook, page renders the part, `nb.ts` `classReport.learning`, regenerated `openapi.json`/`schema.ts`; `e2e/class-report.spec.ts` (learning part at 320/1440 with axe and reflow, AI off, live real-api status line).

Review: four layers (blind, edge case, verification gap, intent alignment; Sonnet per the orchestrator's brief). 36 findings: 14 patched (all low), 2 deferred (low), 20 rejected with reasons in the triage log. followup_review_recommended: false (no high or medium patched). The step-03 implementation subagent was not used: the orchestrator's brief requires the builder to implement in its own context.

Verification: backend full suite 3912 passed before the review patches (`--maxprocesses=8`), touched tests 28 passed after; frontend typecheck, Vitest 1234 passed, lint:colours, check:copy, build (frontend image) passed; Playwright class-report, homes, order-field 37 passed after the patches. New test over 1 s: `test_the_read_takes_a_fixed_number_of_queries_whatever_the_number_of_students` (about 1.4 s, 12 Students).

Residual risks: the Students stand-in must be relinked to `reports.scope.reporting_students` at the Epic 13 merge; `tests/service.py`, `sessions/service.py`, `nb.ts` touch lines near Epic 13's (small mechanical conflicts possible). Pre-existing on the branch: `backend/tests/reports/test_class_report.py` (14.1) fails `ruff check` (import line too long); left untouched.

## Close-out of Epic 14 (2026-11-23)

Both deferred test gaps are closed: `test_a_locked_session_reads_the_selection_its_lock_pinned` and `test_with_no_test_deadline_everyone_who_has_not_handed_in_is_still_to_submit`. The live report still has no minimum group size (the 10-Student rule is for stored aggregates), recorded as a founder decision.
