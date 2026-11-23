---
title: 'Story 13.11: The person downloading can add the AI assessment section'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '811cab780651ee9205185693851c21cbf9f9d254'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-10-student-report-documents-the-debrief-the-replay-and-the-test.md'
warnings: ['oversized']
deferred:
  - summary: >-
      No test renders a report requested by someone other than the Student through the job.
    evidence: |-
      render.py sets requested_by_student from requested_by == user_id; only the Student's own
      routes exist until Story 13.12, so no such request can be made yet. The gate itself is pinned
      at build_report_data. Story 13.12 should add the staff-download case.
    location: >-
      backend/app/modules/reports/render.py
    severity: low
  - summary: >-
      The 0306 downgrade's DELETE of AI-variant rows runs only against an empty table in tests.
    evidence: |-
      test_migrations.py downgrades 0306 with no report_requests rows; a seeded-row test settles it.
    location: >-
      backend/migrations/versions/0306_report_variants.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** The Student report (13.7–13.10) never carries the AI assessment. A Student who wants their «KI-vurdering» documented has no way to add it, and the report meant for approval must stay free of AI scores unless the Student chooses otherwise (FR-58, FR-55, FR-56, FR-61, C-2).

**Approach:** An opt-in Bryter under «Rapport» on Hjem, offered only while the Student's own AI assessment is `ready`. The choice is a report *variant*: `standard` (default), `ai`, or `ai_letter`, each its own request row and its own object name, so a download without the option never serves a PDF with the section. `build_report_data` gets the option and adds an `assessment` section; the Indicative letter goes in only through `assessment.letter_for(reader="report", requested_by_student=…)`, the one gate.

## Boundaries & Constraints

**Always:**
- The Bryter is off on every visit (not remembered); off means the `standard` variant, exactly as today.
- Offered only when the Student's own view (`tests.assessed._view`) reads `ready` (every item scored, a total). `not_ready`, `incomplete`, `failed`, `switched_off`, `no_test`: no Bryter, and the api refuses an AI variant with 409 `ai_assessment_unavailable`; a `GET` for the AI variant then answers the standard state with `ai: false`.
- Letter: the variant is `ai_letter` when, at the press, `letter_for(rules, …, opted_in=<Student's choice>, reader="report", requested_by_student=True)` gives a letter (shown to all, or the Student turned it on for their own view), else `ai`. The render calls `letter_for` again with `requested_by_student = (requested_by == user_id)` and the choice then; it puts in a letter only for `ai_letter` and only if the gate still gives one. Unavailable for the Class session (Institution's no-letter mark, setting `unavailable`) → never.
- The section: «KI-vurdering» heading, first line «KI-generert, kan ta feil. Teller ikke. Ingen karakter.», «Ikke kontrollert med en Kontrolltest.» when unchecked, each item in test order with its question, points of weight, and its score in words (AI step with label, or the computed result); an AI item's written feedback as `{text, ai_generated}` with the prefix «KI-generert, kan ta feil:», or the dropped-feedback note; the weighted total with its note; the letter line with its label. No flags, no other Student's anything.
- Every AI text in the section (AI score lines, feedback, total, letter) is on a `p`/`span` with `data-ai-generated="true"`, so `pdf_marks` gives it `/UserProperties ai_generated`. PDF/UA-1 stays compliant (veraPDF).
- The render fails with code `ai_unavailable` (nothing stored) when an AI variant is built and the assessment is no longer `ready`.
- The Student's own `getMyReport` / `requestMyReport` / `downloadMyReport` take the choice as `?ai=true` (GET) and a JSON body `{ai}` (POST); the state answers `ai` (this state's variant carries the section) and `ai_available`.

**Never:** no AI data in a `standard` report, a staff download, a ZIP or an export (13.12–13.14 build on `letter_for`'s `report`/`zip`/`export` readers); no letter the gate refuses; no change to the AI assessment itself or to flags; no new chart; no client-side code in the print route; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Default | ready assessment, Bryter untouched | `standard` PDF, no «KI-vurdering» section anywhere | — |
| Added | Bryter on, letter not shown to the Student | `ai` variant; section with items, feedback, total; no letter | — |
| Added with letter | Bryter on; letter `all`, or `student_choice` and chosen | `ai_letter`; letter line with «KI-generert indikasjon…» | — |
| Letter turned off after the press | `ai_letter` pending, Student turns letter off | built without the letter | — |
| Letter unavailable | Institution forbids | `ai` variant, no letter | — |
| Not ready / off | `not_ready`, `incomplete`, `switched_off`, `failed`, `no_test` | `ai_available: false`, no Bryter | POST/file with ai → 409 `ai_assessment_unavailable` |
| Switched off between press and render | AI variant pending, view no longer `ready` | request `failed`, code `ai_unavailable`, nothing stored | Student may press again |
| Separate objects | standard ready, then ai ready | two objects (`student-report-…`, `student-report-ai-…`); `file` without ai serves the standard one | — |
| Dropped feedback | item `feedback_dropped` | the note in place of feedback | — |

</intent-contract>

## Code Map

- `backend/app/modules/tests/assessed.py` -- `_view` (:315) builds the Student's `MyAssessmentOut` (state, items, total, `letter` via `_own_letter`); `sessions.letter_rules`; record's `letter_chosen`. Add `report_assessment(user_id, class_session_id) -> ReportAssessment | None` (ready only: the view plus `rules` and `chosen`), exported from `tests/service.py` (reports may import only `service`).
- `backend/app/modules/assessment/service.py:407` -- `letter_for` (reader `report`, `requested_by_student`). Read only.
- `backend/app/modules/reports/report_data.py` -- `ReportOptions` (:77) gains the variants; `SECTIONS` (:515) gains `("assessment", _assessment_section)` after `test`; new models in `AnySection`; `ReportTextOut` reused for feedback; `NotReportable`-like `AssessmentUnavailable`.
- `backend/app/modules/reports/report.py` -- `own_state`/`request_own`/`own_file_url` take `ai: bool`; choose the variant (`_variant`); `ReportState` gains `ai`, `ai_available`; `object_path` already names non-standard variants apart.
- `backend/app/modules/reports/render.py` -- `ReportOptions(variant, by_student=…)`; catch the unavailable case → `failure="ai_unavailable"`.
- `backend/app/modules/reports/models.py` + `backend/migrations/versions/0306_report_variants.py` -- `REPORT_VARIANTS` and `ck_report_requests_variant` gain `ai`, `ai_letter` (revises 0305); `backend/tests/test_migrations.py` HEAD 0306.
- `backend/app/modules/reports/routes.py`, `schemas.py` -- `?ai` query on GET/file, `ReportRequestIn {ai: StrictBool = False}` optional body on POST, `ReportStateOut.ai`, `ai_available`; 409 `ai_assessment_unavailable`.
- `frontend/src/modules/reports/{api.ts,report-download.tsx}` -- key and paths per `ai`; Bryter (`components/switch.tsx`, as `assessment/letter-control.tsx` uses it) when `ai_available`, labelled «KI-vurdering i rapporten», off by default, help line; the state query follows the Bryter.
- `frontend/src/app/print/report/{sections.tsx,copy.ts}` + new `assessment-section.tsx` -- renderer; reuse `nb.assessment.student` lines and `modules/assessment/assessment.ts` helpers (`pointsText`, `scoreText`, `totalText`) and `nb.assessment.letter`.
- `frontend/src/copy/nb.ts` -- `reports.download.ai` (control, on/off, help, error).
- Tests: `backend/tests/reports/test_student_report.py` (`locked_session`, `press`, `file`, `run_reports`, `converter`), `test_report_test_section.py` for a submitted test; `tests/assessment` helpers for a ready assessment; e2e `frontend/e2e/student-report.spec.ts` (`everyStep`, dev `test/close`).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/tests/assessed.py`, `service.py` -- `report_assessment` -- the report's one read of the Student's own view.
- `backend/migrations/versions/0306_report_variants.py`, `reports/models.py`, `tests/test_migrations.py` -- variants.
- `backend/app/modules/reports/report_data.py` -- options, section, builder.
- `backend/app/modules/reports/report.py`, `render.py`, `routes.py`, `schemas.py` -- variant choice, refusals, state fields.
- Backend tests `tests/reports/test_report_assessment.py`: default has no section; ai without letter; ai_letter with `all` and with the Student's choice; the gate refusing a non-student requester; unavailable refusals (409) and the render failure; separate objects; dropped-feedback note; snapshot JSON of `standard` holds no AI key.
- `npm run api:generate`; frontend api, Bryter, print section, copy; Vitest for the download view and the section render.
- `frontend/e2e/student-report.spec.ts` -- after the test deadline: close the test, wait for the ready assessment, make the default report (no Bryter state change), then turn the Bryter on, make and download the AI report; sample `test-results/student-report-ai.pdf` for veraPDF.

**Acceptance Criteria:**
- Given a ready assessment, when the Student opens «Rapport», then a Bryter for the AI section shows, off, and «Lag Studentrapport» makes the standard report.
- Given the Bryter on, when the report is made and downloaded, then the PDF holds the «KI-vurdering» section with the disclosure and AI-marked text, and veraPDF reads it PDF/UA-1 compliant.
- Given an AI report ready, when the Bryter is off again, then the link serves the standard PDF, never the AI one.

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 27 findings — high 0, medium 3, low 12, false 10, maybe-false 2
- findings:
  - `[low]` `[patch]` Blind/edge/verification: `staff_assessment`'s docstring sat under the new alias in `tests/service.py` — moved back.
  - `[medium]` `[patch]` Blind/edge: `ReportDownload` returned null while the AI state loaded (Bryter unmounted, focus lost; a failed read left no way back) — renders from the standard state, keeps the Bryter, shows only it while loading and «ble ikke laget» on a failed read.
  - `[low]` `[reject]` Edge: `withAi` stays true while unavailable — `ai = withAi && available` keeps it off; reappearing needs the assessment to go and come back in one visit.
  - `[medium]` `[patch]` Edge: no refetch after 409 `ai_assessment_unavailable` — invalidates `["reports","mine"]` on that refusal.
  - `[medium]` `[patch]` Edge/blind: the standard report read the AI assessment, so a fault there broke it — press/download without `ai` no longer read it; the state's `ai_available` goes through `_available` (logs, hides the Bryter on a fault); test `test_a_fault_reading_the_assessment_never_stops_the_standard_report`.
  - `[low]` `[reject]` Edge: extra read sessions inside `request_own`'s transaction — now only for an AI press; read-only.
  - `[maybe-false]` `[reject]` Edge: torn read between press and render — the render recomputes and can only drop the letter or fail; at most low.
  - `[low]` `[patch]` Edge: AI item points line unmarked — marked `data-ai-generated`.
  - `[low]` `[reject]` Edge: malformed `?ai=` 422 undocumented — FastAPI's standard answer.
  - `[low]` `[reject]` Blind: full view built on every call — now only for AI and availability.
  - `[false]` `[reject]` Blind: a stale letter can be served — `ai_letter` is served only while the gate gives a letter (tested).
  - `[low]` `[reject]` Blind: AI PDF drops out when the letter choice changes — by design (Design Notes).
  - `[false]` `[reject]` Blind: migration test never returns to head — same chain pattern as every revision block.
  - `[maybe-false]` `[defer]` Blind/verification: 0306 downgrade DELETE untested with rows — deferred.
  - `[low]` `[reject]` Blind: AI PDFs left after a downgrade — developer path; retention deletes objects.
  - `[false]` `[reject]` Blind: no regenerated schema — regenerated with `npm run api:generate`, left out of the review diff on purpose.
  - `[false]` `[reject]` Blind: key readers unaudited — only `topics.ts`, by prefix; Vitest asserts both variants under it.
  - `[low]` `[reject]` Blind: no tests for body validation, 403 with `?ai`, per-variant lock — lock is 13.7's variant index; 403 precedes `ai`.
  - `[false]` `[reject]` Blind: e2e runs no axe — `expectAccessible` runs with the Bryter shown.
  - `[low]` `[reject]` Blind: long draft help copy — `[ASSUMPTION]` for review.
  - `[low]` `[patch]` Verification: CI veraPDF only checks the standard sample — second step for `student-report-ai.pdf`.
  - `[maybe-false]` `[defer]` Verification: no render of a non-Student request — deferred to 13.12.
  - `[false]` `[reject]` Verification/intent: no Bryter component test — the e2e drives it on the real stack.
  - `[false]` `[reject]` Intent: «not offered» asserted only at the api — the component renders the Bryter from `ai_available` only.
  - `[false]` `[reject]` Intent: «no AI data in default PDF» only on snapshot JSON — PDF text also read (pypdf): standard has no «Vektet sum»/«KI-vurdering:»/disclosure; AI sample has them.
  - `[false]` `[reject]` Intent: letter not a separate download choice — reading chosen: letter follows the Student's own view through `letter_for`; founder decision.
  - `[false]` `[reject]` Intent: only Student routes — staff downloads are 13.12; its gate is in place.

## Design Notes

Variant as the unit: the request row, the pending lock, the ready lookup and `object_path` are already keyed by variant (13.7), so a separate name and a separate state per choice come for free; the letter in the variant name means a later change of the Student's letter choice reads as «no PDF yet» for the new variant instead of serving a stale letter.

## Verification

**Commands:**
- `uv run pytest tests/reports tests/assessment tests/test_migrations.py -n 8` -- pass
- `npm run typecheck && npx vitest run && npm run check:copy && npm run lint:colours && npm run build` -- pass
- `npx playwright test e2e/student-report.spec.ts` then `python scripts/verapdf frontend/test-results/student-report-ai.pdf` -- compliant

## Auto Run Result

Status: done

**Summary:** A Bryter under «Rapport» on Hjem lets the Student add a «KI-vurdering» section to their own Student report.
- It is offered only while their AI assessment is `ready`, and it is off on every visit.
- Each choice is its own report variant (`standard`, `ai`, `ai_letter`), with its own request, pending lock and stored object. The standard download never serves the AI PDF.
- The Indicative letter goes in only through `assessment.letter_for(reader="report", requested_by_student=…)`. The gate is checked at the press and again at the render.
- An AI render whose assessment stopped being ready fails with `ai_unavailable` and stores nothing.

**Files:**
- Migration `0306_report_variants.py` and `reports/models.py`: the two new variants.
- `tests/assessed.py` and `tests/service.py`: `report_assessment`.
- `reports/report_data.py`: the options, the section model and its builder.
- `reports/report.py`, `render.py`, `routes.py` and `schemas.py`:
  - choosing the variant, and `ai` / `ai_available` in the state;
  - `?ai` on the reads and the `{ai}` body on the press;
  - the 409 `ai_assessment_unavailable` and the render failure `ai_unavailable`.
- `frontend/src/modules/reports/api.ts` and `report-download.tsx`: the Bryter, and the state per variant.
- `frontend/src/app/print/report/assessment-section.tsx`, `sections.tsx` and `copy.ts`: the print section, with every AI text marked.
- `nb.ts`: the copy.
- `.github/workflows/ci.yml`: a second veraPDF step.
- Tests:
  - `tests/reports/test_report_assessment.py` (7 tests), plus updates to `test_student_report.py` and `test_migrations.py`;
  - `assessment.test.tsx` and `report-download.test.tsx`;
  - the e2e `student-report.spec.ts`, which writes the sample `student-report-ai.pdf`.

**Review:** four layers (blind, edge case, verification gap, intent).
- Patched: 3 medium and 4 low findings.
- Deferred: 2 findings.
- Rejected: everything else, with reasons in the triage log.

**Follow-up review recommended:** true. Two medium findings were patched in `ReportDownload` (the loading/failed paths and the refetch after a refusal), and the e2e covers only the happy path of those branches.

**Verification:**
- Backend: the full suite passed (4012), except one test under load, `test_pause_view`, which passes alone and is unrelated to this change. Ruff passes.
- Frontend:
  - Vitest passed (1271).
  - Typecheck, `check:copy`, `lint:colours` and the build pass.
  - Playwright at `--workers=4` passed: student-report, homes, studentside, ai-assessment, ai-assessment-letter, completion and the play-screen specs.
- veraPDF `ua1`: both samples are compliant.
- The PDF text was read with pypdf. The standard sample has no AI text; the AI sample has the disclosure, the scores, the feedback and the total.
- New tests over 1 s: the `test_report_assessment.py` tests take 2.4–3.6 s each, because of the shared locked-and-assessed fixture.

**Decisions taken for the founder:**
- The letter follows the Student's own view. There is no separate letter choice at download.
- The Bryter is offered for `ready` only, not for `incomplete`.
- An AI press while the assessment is not ready gets a 409. It never falls back quietly to the standard report.
- The Bryter is not remembered between visits.
- All the copy is a draft.

**Residual risks:**
- Prettier reformatted `report-download.tsx`.
- Stories 13.12–13.14 must pass `requested_by_student=False` and use the `zip` / `export` readers.

## Epic 13 close-out: follow-up review

Access and variant isolation are clean. Left (low): an `ai_letter` request whose letter was turned off before the render is stored as `ai_letter` without a letter; `ai`/`staff_ai` PDFs are not invalidated when the assessment is rescored (each press makes a new PDF).
