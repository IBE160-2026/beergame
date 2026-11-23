---
title: "Story 13.12: Staff download one Student's report at any time"
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '2f20c98f9f68779fe78c45acfddbeb227e784e06'
review_loop_iteration: 1
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-11-person-downloading-can-add-the-ai-assessment-section.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Only the Student can make their Student report, and only after their effective Test deadline. The Lecturers and Assistant lecturers of the Class cannot document a Student's work from the Studentside when the course needs it (FR-59, FR-63, FR-58, FR-56).

**Approach:** Staff routes beside the Student's own (`/api/class-sessions/{id}/students/{user_id}/report`, its `/file`) that record a request and defer the same `reports.render_report` job on `reports-single`: one pipeline. Staff downloads are their own variants, `staff` and `staff_ai`, shared by the staff of the Class and kept apart from the Student's own PDFs; `staff_ai` adds the AI assessment section and never the Indicative letter. The Studentside's empty report slot shows the same download block as Hjem, driven by a source per audience.

## Boundaries & Constraints

**Always:**
- Policy: new Class action `reports.download` (account roles Lecturer and Assistant; staff roles owner and assistant), reached only through `sessions.student_target(user, class_session_id, student_id, "reports.download")`. Any other caller (another Class's staff, an Admin without a staff role, a Student), a User who is no Student of the Class now and an unknown Class session all get the same 403 `forbidden`, and nothing is written: no request, no job, no snapshot.
- Open at any time: no deadline check and no lock check. The state answers `open: true`, `opens_at: null`.
- A Student the reports leave out (`scope.reporting_students`) → 409 `not_counted` on the press and the file, nothing written.
- AI section offered (`ai_available`) only while `tests.report_assessment(..., requested_by_student=False)` is ready and the caller may `ai_assessments.read`; an AI press/file otherwise → 409 `ai_assessment_unavailable`. Off by default, not remembered.
- `staff_ai` never carries the Indicative letter, whatever the Lecturer's setting or the Student's own choice: `ReportOptions.letter` is true for `ai_letter` only, and the render passes `requested_by_student=False` for any staff request.
- A staff press is recorded in `platform/audit` (`report.requested`, target Class session + Student, change `{variant}`), emits the requester's `user` topic; the render's end emits the requester's `user` topic and not the Student's for a staff variant.
- Steps not done read as not done (the existing completion section); the same snapshot, print route and converter; download name without a person's name.
- Migration `0307` (revises `0306`) widens `ck_report_requests_variant` with `staff`, `staff_ai`; downgrade deletes those rows first.

**Never:** no second pipeline or queue; no letter in a staff download; no change to the Student's own routes, state or PDFs (a staff render never replaces the Student's object, and vice versa); no ZIP or export (13.13/13.14); no new table; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Before the Test deadline | Lecturer or Assistant presses | 202 pending; job renders `staff` PDF; steps not done read «ikke gjort» | — |
| Shared among staff | Lecturer made it; Assistant opens | same state `ready`, same file | — |
| AI added | ready assessment, `ai: true` | `staff_ai`; section present, `letter` null even with setting `all` or Student's own choice on | — |
| Not ready | assessment not ready | `ai_available: false` | AI press/file → 409 `ai_assessment_unavailable` |
| Student apart | Student's own `standard` ready, staff `staff` ready | each serves its own object; Student's state unchanged by staff press | — |
| Outsider | other Lecturer, Admin w/o Class role, Student, unknown student id | 403 `forbidden` | no row, no job, no snapshot |
| Not counted | test Student | — | 409 `not_counted`, nothing written |
| No PDF yet | file before ready | — | 409 `report_not_ready` |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py:160,198,236` -- add `reports.download` to the account-role table and `CLASS_STAFF_ROLES`.
- `backend/app/modules/sessions/service.py:2596` -- `student_target(..., action)`; reuse, read only. `class_staff_may` (:2768) for `ai_assessments.read`.
- `backend/app/modules/reports/report.py` -- add `DOWNLOAD = "reports.download"`, `REQUESTED_AUDIT = "report.requested"`, `staff_state`, `request_staff`, `staff_file_url` beside the own ones; reuse `_status`, `object_path`, `download_name`, `repo.*`, `jobs.defer(RENDER_TASK, queue=REPORTS_SINGLE)`; `_staff_choice` → `staff`/`staff_ai`.
- `backend/app/modules/reports/report_data.py:83-103` -- `ReportVariant` gains `staff`, `staff_ai`; `assessment` true for `ai`, `ai_letter`, `staff_ai`; `letter` only `ai_letter`.
- `backend/app/modules/reports/render.py:100` -- `_emit`: Student's topic only for non-staff variants.
- `backend/app/modules/reports/models.py:48,75` + `backend/migrations/versions/0307_staff_report_variants.py`; `backend/tests/test_migrations.py:188,379` HEAD 0307 and a block.
- `backend/app/modules/reports/routes.py` -- `getStudentReport`, `requestStudentReport`, `downloadStudentReport` under `/class-sessions/{session_id}/students/{user_id}/report`; reuse `_state`, `AI_QUERY`, `ReportRequestIn`, `PERSONAL`.
- `backend/app/modules/reports/schemas.py:151,184` -- drop the `report: None` slot field from `StudentRecordOut` (the slot is filled in the frontend); `backend/tests/reports/test_studentside.py:65`, `frontend/e2e/support/record.ts:24` follow.
- `backend/app/modules/reports/README.md` -- the staff download section.
- `frontend/src/modules/reports/api.ts` -- a `ReportSource` (key, family, read, request, filePath) with `mySource(sessionId)` and `staffSource(sessionId, userId)`; staff keys under `["reports","staff",…]`; `useReport(source, ai, enabled)`.
- `frontend/src/lib/api/topics.ts:30` -- `user` case adds `staffReportsKey`.
- `frontend/src/modules/reports/report-download.tsx` -- body takes a source and copy overrides (note, ai help); `ReportDownload` (Hjem) unchanged in behaviour; new `StaffReportDownload`.
- `frontend/src/modules/reports/record-blocks.tsx:120` -- replace the slot with a «Studentrapport» Block holding `StaffReportDownload` (or the not-counted line when `record.completion` is null).
- `frontend/src/copy/nb.ts:4252,4396` -- `reports.download.staff` (note, ai help) and `reports.record.report` (title, not counted). Draft `[ASSUMPTION]`.
- `backend/app/platform/jobs/__init__.py:54` + `docker-compose.yml:112` -- queue `reports-bulk` (worker-batch runs it beside `reports-single`'s reserved slots; the ZIP job is 13.13's).
- `backend/app/modules/sessions/service.py` (`data_deleted(row, now)`, beside `report_opens_at`) -- the Class session's `deletion_date` (13.9) has come, Oslo day; `report.py` reads it from `student_target(...).row`; state `deleted`, press/file 409 `data_deleted`.
- Tests: `backend/tests/reports/test_staff_report.py` (reuse `test_student_report` `converter`, `files`, `run_reports`, `locked_session`; `test_report_assessment`/`test_letter` `locked`, `assessed`, `save`, `letter_url`; `test_staff.ASSISTANT`, `put_staff`; `test_studentside.ADMIN`/`OTHER_LECTURER` with `make`); `frontend/src/modules/reports/report-download.test.tsx`; e2e `frontend/e2e/studentside.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `authz.py`, migration 0307, `models.py`, `test_migrations.py` -- the action and the variants.
- `report_data.py`, `report.py`, `render.py`, `routes.py`, `schemas.py`, README -- the staff path.
- `backend/tests/reports/test_staff_report.py` -- matrix rows: before-deadline press and render (steps not done), shared state between Lecturer and Assistant, Student's own state and object untouched, `staff_ai` with no letter under `all` and under the Student's own choice, unavailable 409s, outsiders 403 with no rows/jobs/snapshots, not counted 409, audit row, emitted topics.
- `npm run api:generate`; frontend api, topics, download block, record block, copy; Vitest for the staff block (renders, AI Bryter only when available, staff note).
- `backend/tests/reports/test_staff_report.py` -- (amended) deleted data: state `deleted`, 409 `data_deleted`, nothing written; a slow test job on `reports-bulk` while a staff report is made within 30 s; the download's audit row `report.downloaded`.
- `frontend/e2e/studentside.spec.ts` -- a Lecturer opens a Student's Studentside before the Test deadline, makes the report, sees the link and downloads a PDF (status 200 through the redirect).

**Acceptance Criteria:**
- Given a Lecturer of the Class on a Student's Studentside before the Test deadline, when they press «Lag Studentrapport», then the report is made by the `reports-single` job and «Last ned Studentrapporten (PDF)» appears without a reload.
- Given the Student's AI assessment is ready, when staff turn on the Bryter and make the report, then the PDF holds the «KI-vurdering» section and never the Indicative letter.
- Given an outsider, when they ask for the state, the press or the file, then they get 403 and no request, job or snapshot exists.
- Given a slow job holds `reports-bulk`, when a single report is requested, then it is ready within 30 s on `reports-single`'s reserved slots.
- Given the Class session's deletion date has come, when staff open the report block, then it says the data is deleted and the press/file answer 409 `data_deleted` with nothing built.

## Spec Change Log

### 2026-11-23 — iteration 1 (review: intent alignment)
- Trigger: the story's last two acceptance blocks (the `reports-bulk` isolation test; «a Student whose data has been deleted») were missing from the plan.
- Amended: Code Map, Tasks and Acceptance Criteria (queue `reports-bulk`, `sessions.data_deleted`, state `deleted`, 409 `data_deleted`, the two tests). The intent contract is unchanged.
- Known-bad state avoided: a story marked done without two of its acceptance criteria.
- KEEP: everything already built and verified (variants `staff`/`staff_ai`, `_press`, routes, policy, audit, the `ReportSource` block, the record block, the tests). The change is additive, so the code was extended in place rather than re-derived.
- Reading chosen: "data deleted" means the Class session's `deletion_date` has come (the deletion itself is Epic 15's). A deleted User is no Student of the Class and gets the usual 403.

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 34 findings — high 0, medium 3, low 18, false 9, maybe-false 4
- findings:
  - `[medium]` `[bad_spec]` Intent: block 4 (`reports-bulk` isolation test) not built — spec amended; queue `reports-bulk` added (jobs, compose) and `test_a_single_report_meets_its_target_while_a_slow_job_holds_reports_bulk`.
  - `[medium]` `[bad_spec]` Intent: block 5 (deleted data) not built — spec amended; `sessions.data_deleted`, state `deleted`, 409 `data_deleted`, copy, `test_once_the_students_data_is_deleted_the_action_says_so_and_builds_nothing`, Vitest.
  - `[low]` `[reject]` Intent: no UI test turns the staff Bryter on — the variant choice and the no-letter rule are pinned at the api; Vitest renders the Bryter off.
  - `[low]` `[reject]` Intent: denial asserted only at the api — the page's denial is 13.2's (`getStudentRecord` 403), unchanged.
  - `[false]` `[reject]` Intent: removing `StudentRecordOut.report` breaks the contract — it was a `None` placeholder; client regenerated, fixtures updated, typecheck and build pass.
  - `[medium]` `[patch]` Blind/edge: a staff download (signed URL) is not audited — `staff_file_url` writes `report.downloaded`; asserted in the first test.
  - `[low]` `[reject]` Blind/edge: a second press that joins the pending render writes no audit row — nothing is made; the download row records who got the PDF.
  - `[low]` `[reject]` Blind: file name `studentrapport-klasseokt-N.pdf` repeats across Students — AD-14 keeps names out of file names; browsers number duplicates.
  - `[low]` `[reject]` Blind/edge: GET state of a left-out Student reads open — the block is not shown for them (`record.completion` null, now tested); press and file answer 409.
  - `[low]` `[reject]` Blind: `staff_state(ai=True)` does not swallow an assessment fault — same as the Student's own (13.11); asked only after the Bryter was offered.
  - `[low]` `[reject]` Blind/edge: other staff get no live update when the shared report is ready — they poll while pending and read it on load; a Class-wide topic would refetch every staff page.
  - `[low]` `[reject]` Blind: variant lists repeated (Literal, tuple, check, set) — one line each; the migration test pins the constraint.
  - `[false]` `[reject]` Blind/verification: the render's `and variant not in STAFF_VARIANTS` is redundant — a deliberate second guard on the letter gate; harmless.
  - `[maybe-false]` `[reject]` Blind/edge: requester loses the staff role between press and render — the PDF is served only to who passes the policy at download; a role-removal test would settle it; at most low.
  - `[low]` `[reject]` Blind: no test of `reports.download` without `ai_assessments.read` — both grant the same roles today, so no user reaches that branch.
  - `[maybe-false]` `[reject]` Blind/verification: 0307 downgrade DELETE untested with rows — developer rollback path only, as 13.11's deferred row; at most low.
  - `[low]` `[reject]` Blind: PDFs of deleted rows left in storage after a downgrade — retention deletes objects (Epic 15).
  - `[false]` `[reject]` Blind: timing assertions are slow or flaky — the 30 s bound is the story's own criterion; renders take under a second on the mock.
  - `[false]` `[reject]` Blind: no regenerated schema — regenerated with `npm run api:generate`, left out of the review diff on purpose.
  - `[low]` `[reject]` Blind: the staff press reuses the `reports.request_report` registry entry — same topic set (`user`), asserted.
  - `[low]` `[reject]` Blind: error copy written for the Student — staff never get `report_not_open`; `not_counted` and `data_deleted` read neutrally.
  - `[low]` `[patch]` Edge: the Bryter state carries over to another Student on client navigation — the block is keyed by session and Student.
  - `[false]` `[reject]` Edge: a press on an unlocked session — "at any time" is the story; the report marks every step not done; `NotReportable` fails the render with a code.
  - `[maybe-false]` `[reject]` Edge (claim): "every staff press is audited" — the spec says a press is recorded; a joined press makes nothing.
  - `[maybe-false]` `[reject]` Edge (claim): "shared, updates without reload" — the AC's live update is the requester's, which the e2e shows.
  - `[low]` `[patch]` Verification: the left-out Student's block is asserted nowhere — Vitest renders `RecordBlocks` with `completion: null`: the not-counted line, no button.
  - `[low]` `[patch]` Verification: the audit row's `request_id` not asserted — now asserted against the request row.
  - `[low]` `[reject]` Verification: 0307 downgrade with rows — as above (developer rollback only).
  - `[false]` `[reject]` Verification (other): the render guard is unpinned — see the redundant-guard row.
  - `[false]` `[reject]` Intent: the e2e covers one Student only — the matrix is at the api.
  - `[false]` `[reject]` Intent: 30 s only on the mock — the e2e measures it on the real stack with WeasyPrint.
  - `[false]` `[reject]` Intent: the slot replaced rather than filled — the slot was an empty div meant for this block.
  - `[low]` `[reject]` Intent: choices beyond the ACs (audit, variants, refactor) — implementation choices within the story.
  - `[low]` `[reject]` Intent: `student_target` and deleted Users — a deleted User is off the Roster, so 403 like any non-Student.

## Design Notes

Variants as the unit (13.11) carry over: `staff`/`staff_ai` give the staff their own pending lock, ready lookup and object without touching the Student's, and keep a staff-made PDF from ever reaching the Student's own download (or a Student's `ai_letter` PDF from reaching staff). Shared among the Class's staff: the content does not depend on which staff member asked.

## Verification

**Commands:**
- `uv run pytest tests/reports tests/platform/test_authz.py tests/test_migrations.py -n 8` -- pass
- `npm run typecheck && npx vitest run src/modules/reports && npm run check:copy && npm run lint:colours` -- pass
- `npx playwright test e2e/studentside.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary:** Lecturers and Assistant lecturers of the Class can make and download one Student's report from the Studentside's «Studentrapport» block. This works at any time, before or after the Test deadline.
- The same press (`report._press`), snapshot, print route and `reports-single` job are used as for the Student's own report.
- Staff downloads are their own variants, `staff` and `staff_ai`. They are shared by the staff of the Class and kept apart from the Student's own PDFs.
- The AI section is off by default. It is offered while the AI assessment is ready and the reader may read it. A staff download never holds the Indicative letter.
- Outsiders get one 403 and nothing is written.
- A Student whose Class session's deletion date has come gets «data deleted» (state `deleted`, 409 `data_deleted`) and nothing is built.
- The queue `reports-bulk` now exists. A test shows a single report is made while a slow job holds it.

**Files:**
- `platform/authz.py`: the `reports.download` action.
- `platform/jobs/__init__.py`, `docker-compose.yml`, `railway/worker-batch/railway.toml`, `tests/test_railway_config.py`: the queue `reports-bulk`.
- Migration `0307_staff_report_variants.py` and `reports/models.py`: the variants. `test_migrations.py` HEAD is 0307.
- `sessions/service.py`: `data_deleted`.
- `reports/report.py`: `_press`, `staff_state`, `request_staff`, `staff_file_url`, and the audit rows `report.requested` and `report.downloaded`.
- `report_data.py`: `STAFF_VARIANTS` and the section option.
- `render.py`: no letter and no Student topic for staff variants.
- `routes.py` and `schemas.py`: `getStudentReport`, `requestStudentReport`, `downloadStudentReport`, and `deleted` in the state. The `report: None` placeholder is dropped from the record.
- README.
- Frontend:
  - `api.ts`: `ReportSource`, `useReport`, staff keys.
  - `topics.ts`.
  - `report-download.tsx`: one block for both; `StaffReportDownload`; the deleted view.
  - `record-blocks.tsx`: the block in 13.2's slot.
  - `nb.ts`: draft copy.
  - The regenerated client.
- Tests:
  - `tests/reports/test_staff_report.py` (8 tests), plus updates to `test_student_report.py` and `test_studentside.py`;
  - `report-download.test.tsx` (5 new);
  - e2e `studentside.spec.ts`, where the Assistant makes and downloads the PDF before the Test deadline;
  - `e2e/support/record.ts`.

**Review:** four layers (blind, edge case, verification gap, intent), 34 findings.
- Two bad_spec findings: the story's two last acceptance blocks were missing from the plan. The spec was amended outside the intent contract (iteration 1), and the code was extended in place, keeping all the verified work.
- Patched: 1 medium (the download is audited) and 3 low (the Bryter keyed per Student, the left-out Student's block tested, the audit `request_id` asserted).
- Deferred: none.
- Rejected: the rest, with reasons in the triage log.

**Follow-up review recommended:** true. Two medium entries were taken in this pass: the two acceptance blocks built after review, and the download audit. The new `reports-bulk` test and the deleted-data path were reviewed only by the author.

**Verification:**
- Backend:
  - The full suite (`-n 8 --maxprocesses=8`) gave 4020 passed and 1 failed. The failure was `test_railway_config` (the worker command), now fixed and passing (19/19).
  - Ruff passes.
  - `tests/reports` passes (64).
- Frontend:
  - Typecheck, Vitest (1276), `check:copy` and `lint:colours` pass.
  - The build passes (in the frontend image).
  - Playwright `--workers=4`: studentside, student-report, homes, ai-assessment, ai-assessment-letter and the play-screen specs order-confirm, guided-week and chain-band passed (110 tests), with axe per width.
- New tests over 1 s: the `test_staff_report.py` tests take 1.2–4.5 s each, because of the locked-session and assessment fixtures.

**Decisions taken for the founder:**
- "Data deleted" means the Class session's `deletion_date` has come. The deletion itself is Epic 15's. A deleted User is no Student of the Class and gets 403.
- The staff's PDFs are shared by all staff of the Class, never by the Student. The Student's Hjem is not told of a staff render.
- A staff press and a staff download are both audited.
- The Bryter is offered only for `ready`, and it is not remembered.
- The file name has no name in it (AD-14).
- The record's `report` placeholder field is removed. The block reads its own endpoint.
- All the copy is a draft.

**Residual risks:**
- Other staff with the page open see a new staff PDF only on load or by the 15 s poll while pending.
- The 0307 downgrade's DELETE is untested with rows.
- New personal data: no new table. `report_requests` gains staff-requested rows (`user_id`, `requested_by`), and `audit_events` gains rows naming the Student.

## Epic 13 close-out: follow-up review

Fixed (medium): `reports-bulk` shared `worker-batch`'s one main slot with the sweep, mail and LLM batches, so a ZIP of many minutes held them. Beside other queues it now runs in a worker of its own (one slot), as `reports-single` does (`test_worker.py`; `docs/ops/connection-budget.md` updated: worker-batch 10, pool size at least 57). The download audit: one row per file call, actor the staff user, none on 403/409. Left (low): the audit is written when the signed URL is minted, not on delivery. Registry: staff ids in `report_requests.requested_by` and `audit_events.actor_user_id` (`report.requested`, `report.downloaded`).
