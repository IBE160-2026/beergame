---
title: 'Story 13.13: Download all Student reports as one ZIP'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '687d75000d66124f8ebd8454f72fc918c133d5ba'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-12-staff-download-one-students-report-at-any-time.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Staff can download Student reports only one at a time from each Studentside; filing a course of up to 250 Students means 250 downloads (FR-59).

**Approach:** An «Eksport» block on the Klasseøkt screen whose action «Last ned alle Studentrapporter (ZIP)» records a ZIP request and defers one `reports.build_zip(bundle_id)` job on `reports-bulk`. The job renders one standard report per Student in `reporting_students()` through the same assembler, snapshot, print route and converter as the single report, with the AI section forced off, zips them, stores the ZIP through `platform/storage`, and tells the requester through `platform/notify`; the block then offers a signed-URL download.

## Boundaries & Constraints

**Always:**
- Policy: the existing Class action `reports.download` (Lecturer and Assistant lecturer of the Class). Anyone else (another Class's staff, an Admin without a staff role, a Student) and an unknown Class session get one 403 `forbidden`, with nothing written.
- The job builds with `ReportOptions(variant="staff")` (no AI section, no letter) whatever the request body says; a test opens the ZIP and finds no AI score, feedback or Indicative letter in any file (C-2).
- One ZIP request pending per Class session (partial unique index): a second press, by any staff member, answers the pending one. A pending request older than `REPORT_ZIP_STALE_SECONDS` (default 900, above the 10-minute target) reads as failed and the next press replaces it.
- Idempotent on Class session and request: the job skips a request no longer pending; the object path is keyed by the request (`class-sessions/<id>/bundles/student-reports-<request_id>.zip`), so a retried job overwrites its own object; once ready, the Class session's earlier ZIP objects are deleted, so one ZIP stays.
- Files inside are named by the Student's Roster name (`Kari Nordmann.pdf`, unsafe characters replaced; a name that repeats gets the first 8 hex digits of the `user_id`), so a Lecturer can find a Student. Object path and download name (`studentrapporter-klasseokt-<n>.zip`) carry no name (AD-14).
- Every snapshot is deleted when its render ends; a Student who stops being reportable while the job runs (`NotReportable`) is left out; any other failure fails the whole request with code `render_failed` (never a partial ZIP).
- On ready: one `reports_zip_ready` notice to the requester (immediate mail, dedupe key per request), emitting their `user` topic. Press and job end emit the requester's `user` topic; registry entries `reports.request_zip`, `reports.build_zip`.
- Press and download recorded in `platform/audit` (`report_zip.requested`, `report_zip.downloaded`, target Class session + request).
- The signed URL is made only after the policy allowed the caller (NFR-7, AD-12).
- Renders run with bounded concurrency (`REPORT_ZIP_CONCURRENCY`, default 3) so 250 Students fit 10 minutes; a timed test with 250 generated Students on the fake converter shows it.
- Migration `0308` (revises `0307`): table `report_zips`; `report_snapshots.request_id` nullable plus `zip_id` (FK, cascade) with a check that exactly one is set.

**Never:** no AI section or letter in the ZIP; no second assembler or converter; no change to the single-report routes, variants or objects; no Completion or Game data export (13.14, later); no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| First press | Lecturer, 2 Students | 202 `pending`; one job on `reports-bulk`; ZIP of 2 PDFs; notice + `user` topic | — |
| AI asked | body `{"ai": true}`, assessment ready, letter setting `all` | ZIP files hold no assessment section/letter | — |
| Shared | Lecturer pressed; Assistant opens | same state, same file | — |
| Second press | while pending | answers pending, one job | — |
| Failure | converter raises | `failed`, `render_failed`, no object, no snapshot | «Prøv igjen» presses anew |
| Retry | job delivered twice | second run skipped; one object | — |
| Outsider | other Lecturer, Admin w/o role, Student, unknown id | — | 403, no row/job |
| No Students | Control test session or none counted | — | 409 `no_students` |
| Deleted | deletion date has come | state `deleted` | press/file 409 `data_deleted` |
| No ZIP yet | file before ready | — | 409 `zip_not_ready` |

</intent-contract>

## Code Map

- `backend/app/modules/reports/models.py` -- add `report_zips` (id, class_session_id FK cascade, requested_by FK set null, status, requested_at, finished_at, object_path, failure, students int); `report_snapshots.request_id` nullable, `zip_id`, check `ck_report_snapshots_owner`.
- `backend/migrations/versions/0308_report_zips.py`; `backend/tests/test_migrations.py:126,189,380` -- HEAD 0308, `REPORT_ZIP_TABLES`, a downgrade block.
- `backend/app/modules/reports/repo.py` -- zip reads/writes beside the request ones (`latest_zips`, `insert_zip`, `finish_zip`, `release_older_zips`); `insert_snapshot(request_id=None, zip_id=None)`.
- `backend/app/modules/reports/bundle.py` (new) -- `zip_state`, `request_zip`, `zip_file_url`, the task `reports.build_zip` on `jobs.REPORTS_BULK`. Reuses `report._status`-style staleness, `scope.reporting_students`, `report_data.build_report_data`, `render.to_pdf`/`print_url`/`token_hash`/`TOKEN_LIFETIME`, `repo.snapshot_used`, `storage`, `notify.enqueue`, `audit.record`, `sessions.data_deleted`, `sessions.report_heading` (number).
- `backend/app/modules/sessions/service.py:2776` -- `staff_session_row(user, class_session_id, action)` beside `class_staff_may`; `reports_zip_mail_context` (Class name, number; None once the User is no staff of the Class).
- `backend/app/modules/messaging/delivery.py:270` -- `REPORTS_ZIP_READY_KIND`, immediate; `backend/app/platform/email/templates/kinds/reports_zip_ready.{html,txt}.j2`.
- `backend/app/platform/jobs/__init__.py:62` -- `app.modules.reports.bundle` in `TASK_MODULES`.
- `backend/app/platform/config.py` -- `report_zip_stale_seconds` (900), `report_zip_concurrency` (3).
- `backend/app/platform/storage.py:209` -- the mock serves `.zip` as `application/zip`.
- `backend/app/platform/events/registry.py:160` -- `reports.request_zip`, `reports.build_zip`: `{"user"}`.
- `backend/app/modules/reports/routes.py`, `schemas.py` -- `getReportsZip`, `requestReportsZip` (202), `downloadReportsZip` (303) under `/class-sessions/{session_id}/reports/zip`; `ZipStateOut` (status, generated_at, deleted).
- `backend/app/modules/reports/README.md` -- the ZIP section.
- `frontend/src/modules/reports/api.ts` -- `zipKey` under `staffReportsKey` (the `user` topic reads it again), `useReportsZip` (15 s poll while pending), `requestReportsZip`, `reportsZipFilePath`.
- `frontend/src/modules/reports/export-block.tsx` (new) -- «Eksport» section; `zipView(state, pressed)` pure; hidden on 403.
- `frontend/src/modules/sessions/class-session-page.tsx:558` -- render `ExportBlock` after `TestGameBlock`.
- `frontend/src/copy/nb.ts` -- `reports.export` copy (UX-DR49 strings verbatim; the rest draft).
- Tests: `backend/tests/reports/test_reports_zip.py` (reuse `test_staff_report`/`test_letter` `locked`, `assessed`, `save`, `letter_url`; `test_student_report` `files`, `code`; `test_staff` `ASSISTANT`, `put_staff`, `call`; `test_studentside` `ADMIN`, `OTHER_LECTURER`); `frontend/src/modules/reports/export-block.test.tsx`; e2e `frontend/e2e/class-session-export.spec.ts`.

## Tasks & Acceptance

**Execution:**
- models, migration 0308, `test_migrations.py` -- the table and the snapshot owner.
- config, repo, `bundle.py`, jobs, registry, storage mock type, sessions helpers, delivery kind + templates -- the job and the notice.
- routes, schemas, README; `npm run api:generate`.
- `backend/tests/reports/test_reports_zip.py` -- the matrix rows; the ZIP opened and checked for no AI data; names inside; a timed run with 250 generated Students (< 600 s on the fake converter); idempotent retry; notice row and mail kind.
- frontend api, `export-block.tsx`, Klasseøkt page, copy; Vitest for `zipView` and the block states.
- e2e: a Lecturer opens a fresh Klasseøkt with Students, presses the ZIP action, sees the pending line, then the download link; the download answers 200 with a ZIP; axe at 320 px and desktop with 200% text reflow.

**Acceptance Criteria:**
- Given staff of the Class on the Klasseøkt screen, when the «Eksport» block shows, then it has «Last ned alle Studentrapporter (ZIP)» and «ZIP-filen har aldri med KI-vurderingen.».
- Given staff press the action, then the block reads «ZIP-filen lages. Du får beskjed når den er klar, innen 10 minutter.» and, once the job ends, offers the download without a reload; the requester gets a notice.
- Given the job fails, when the block is shown, then it reads «ZIP-filen kunne ikke lages.» with «Prøv igjen».
- Given 250 Students, when the job runs, then it is ready within 10 minutes (timed test).
- Given the block at 320 px and 200% text, then it reflows, the status line is polite, and axe reports no violations.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 44 findings — high 0, medium 4, low 28, false 6, maybe-false 6
- findings:
  - `[low]` `[reject]` Intent: block states tested by static render, not clicks — the e2e presses, waits and downloads on the real stack; the rest are pure views.
  - `[low]` `[reject]` Intent: the e2e checks the status node, not its text — the announcement is the same effect as 13.12's block; asserted presence only.
  - `[maybe-false]` `[reject]` Intent: AI-free check is on the snapshot data, not the rendered PDF — the print route renders only the sections in the data; a PDF text check would need WeasyPrint in the unit suite. At most low.
  - `[low]` `[reject]` Intent: the 250 test times everything but real conversion — real conversion is bounded by concurrency 3 × the single report's 30 s target; the e2e runs the real converter.
  - `[medium]` `[patch]` Intent/verification/blind: the ready mail never rendered or asserted — added `test_the_ready_notice_is_an_immediate_mail_without_a_link_or_student_data` and `test_the_mail_context_names_the_class_session`.
  - `[low]` `[reject]` Intent: the signed URL's expiry not asserted — `storage` tests own the TTL (13.7).
  - `[false]` `[reject]` Intent/blind: generated client missing from the diff — regenerated with `npm run api:generate`, left out of the review diff on purpose; typecheck passes.
  - `[false]` `[reject]` Intent: extra copy beyond the spine — marked `[ASSUMPTION]` as the spec says.
  - `[medium]` `[patch]` Blind/edge (×2): duplicate-name suffix uses `hex[:8]`, the timestamp of a UUIDv7, so batch-made namesakes clash — now `hex[-8:]` (random part); unit test updated.
  - `[low]` `[reject]` Blind/edge: whole ZIP read into memory before `put` — `Storage.put` takes bytes; 250 PDFs are tens of MB; streaming would change the storage api.
  - `[low]` `[patch]` Blind: DEFLATE on PDFs costs CPU in the event loop — now `ZIP_STORED`.
  - `[maybe-false]` `[reject]` Blind/edge: a slow healthy job read as stale after 900 s spawns a second build — 900 s is above the 10-minute target; the first job then removes its own object (now tested). Settled by a job timing on real data; at most low.
  - `[low]` `[reject]` Blind: other staff get no live update — as 13.12: they poll while pending and read it on load.
  - `[low]` `[patch]` Blind: any read error hides the block — only a 403 hides it now; other errors show a line (`nb.reports.export.zip.unread`).
  - `[low]` `[reject]` Blind: a stale link answers a JSON error — same plain-link pattern as 13.7/13.12.
  - `[maybe-false]` `[reject]` Blind: ZIP objects not purged at the deletion date — the deletion is Epic 15's; the object sits under `class-sessions/<id>/`, the prefix the retention deletes. At most low here.
  - `[low]` `[reject]` Blind/edge: `count == 0` shows the generic failure — only reachable when every Student left the Class during the job.
  - `[low]` `[patch]` Blind/verification: no tests for left-out, partial failure and stale-job cleanup — added `test_one_failed_report_fails_the_whole_zip_and_a_student_left_out_is_skipped` and `test_a_job_replaced_as_stale_removes_its_own_zip`.
  - `[low]` `[reject]` Blind: the 250 test is slow (15 s) — the story's own acceptance; reported.
  - `[low]` `[reject]` Blind: the migration test does not re-upgrade — the suite's own pattern (one downgrade walk).
  - `[low]` `[reject]` Blind: the e2e hard-codes «med 2 Studentrapporter.» — a readable literal for a known count.
  - `[false]` `[reject]` Blind: `REQUESTED` unused — the registry name, as `report.REQUESTED`; the test reads `COMMAND_TOPICS` by it.
  - `[low]` `[reject]` Blind: loose type hints and positional dataclass build — mirrors `ReportRequest`.
  - `[low]` `[reject]` Blind: only the first concurrent failure raised — the log keeps the type; one failure fails the ZIP.
  - `[low]` `[reject]` Blind: download name has no Class — AD-14 keeps names out; as 13.12.
  - `[low]` `[reject]` Blind: entry order is completion order — file managers sort by name.
  - `[low]` `[reject]` Blind/edge: no list of left-out Students — `students` gives the count; a left-out Student is no longer in the Class.
  - `[false]` `[reject]` Blind: templates not in any registry test — now tested (see above).
  - `[low]` `[patch]` Blind: the HTML template lacks `[ASSUMPTION]` — added.
  - `[low]` `[reject]` Blind: duplicated copy string — two keys for two places, as 13.12.
  - `[low]` `[reject]` Blind: copy promises 10 minutes, failure shows at 15 — the target and the stale threshold are different things; draft copy.
  - `[medium]` `[patch]` Verification: earlier ZIP's `generated_at` kept while pending/failed untested — added `test_while_a_new_zip_is_made_or_failed_the_earlier_one_stays_downloadable` and a Vitest case.
  - `[low]` `[patch]` Verification: mixed outcomes untested — see the added test above.
  - `[low]` `[patch]` Verification: stale job's own object cleanup untested — see the added test above.
  - `[low]` `[reject]` Verification (other): the 250 test uses a fake converter — as above.
  - `[low]` `[reject]` Verification (other): the press flow only in e2e — as above.
  - `[false]` `[reject]` Edge (claim): the suffix "never clash" claim — fixed by the `hex[-8:]` patch.
  - `[maybe-false]` `[reject]` Edge: staleness from `requested_at` — as above.
  - `[medium]` `[patch]` Edge: the deletion date passing while the job waits still builds the ZIP — `build` reads the row again and fails with `data_deleted`; `test_a_zip_whose_data_is_deleted_while_it_waits_is_never_built`. (A ZIP already ready is Epic 15's deletion.)
  - `[maybe-false]` `[reject]` Edge: a ready row whose object is gone — as 13.12; only by manual cleanup.
  - `[false]` `[reject]` Edge: Supabase retry without upsert — `SupabaseStorage` sends `x-upsert: true` on every put.
  - `[maybe-false]` `[reject]` Edge: a snapshot delete error masks the result — the sweep purges expired snapshots; a DB error then fails the ZIP, which is correct.
  - `[low]` `[patch]` Edge: NFC/NFD names collapse on a normalising file system — names are NFC-normalised. Reserved device names rejected: no Student is called CON.
  - `[low]` `[patch]` Edge: after a 409 press the block keeps offering the action — the state is read again after a refused press.

## Design Notes

A table of its own (`report_zips`) rather than a `report_requests` variant: a request row names one Student, while a ZIP names a Class session; mixing them would break the per-Student pending lock and the release of older objects. Snapshots gain a second owner so the print route, token and `snapshot_used` check stay one path. The ZIP is built in a temporary file (`SpooledTemporaryFile`), PDFs written as they finish, so memory holds at most the concurrent PDFs plus the spool.

## Verification

**Commands:**
- `uv run pytest tests/reports tests/test_migrations.py tests/messaging -n 8` -- pass
- `npm run typecheck && npx vitest run src/modules/reports && npm run check:copy && npm run lint:colours` -- pass
- `npx playwright test e2e/class-session-export.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary:** The Klasseøkt has an «Eksport» block for the staff of the Class (policy `reports.download`). «Last ned alle Studentrapporter (ZIP)» records a `report_zips` request and defers `reports.build_zip` on `reports-bulk`. The job renders every Student of `reporting_students()` through `build_report_data` with the variant `staff`, so the ZIP never holds the AI section or the letter, whatever the press sent. It uses the snapshot, print route and converter of the single report, three at a time, stores one ZIP per Class session under `class-sessions/<id>/bundles/`, and sends the requester a `reports_zip_ready` mail (immediate). The block shows the pending line, the download (a signed URL after the policy), «ZIP-filen kunne ikke lages.» with «Prøv igjen», and the deleted state.

**Files:**
- `reports/bundle.py` (new): the state, the press, the file and the job.
- `reports/models.py`, migration `0308_report_zips.py`: `report_zips`, and `report_snapshots.zip_id` with an owner check.
- `reports/repo.py`: the ZIP reads and writes.
- `reports/routes.py`, `schemas.py`: `getReportsZip`, `requestReportsZip`, `downloadReportsZip`, `ZipStateOut`.
- `sessions/service.py`: `staff_session_row`, `session_row`, `REPORTS_ZIP_READY_NOTICE`, `reports_zip_mail_context`.
- `messaging/delivery.py` and the two `reports_zip_ready` templates.
- `platform/config.py` (`REPORT_ZIP_STALE_SECONDS` 900, `REPORT_ZIP_CONCURRENCY` 3), `jobs` (task module), `events/registry.py`, `storage.py` (the mock serves `.zip`).
- README.
- Frontend: `export-block.tsx` (new), `api.ts`, `class-session-page.tsx`, `nb.ts` (draft copy beyond the spine strings), and the regenerated client.
- Tests: `tests/reports/test_reports_zip.py` (15), `test_migrations.py`, `export-block.test.tsx` (8), e2e `class-session-export.spec.ts`.

**Review:** four layers, 44 findings (see the triage log).
- Patched, 4 medium: the namesake suffix (`hex[-8:]`), the ready mail is now tested, the earlier ZIP is kept while a new one is made (tested), and no ZIP is built once the deletion date has come while the job waits.
- Patched, low: `ZIP_STORED`, NFC names, only a 403 hides the block, the state is read again after a refused press, `[ASSUMPTION]` in the template, and tests for partial failure, a left-out Student and the stale job's cleanup.
- Deferred: none. The rest were rejected with reasons in the log.

**Follow-up review recommended:** true. Four medium entries were patched in this pass. The risk not yet checked by a second reviewer: the `data_deleted` re-read in `build` and the block's error state were reviewed only by the author.

**Verification:**
- Backend: full suite 4036 passed (`-n 8 --maxprocesses=8`); ruff passes.
- Frontend: typecheck, Vitest (1284), `check:copy`, `lint:colours` and the build (frontend image) pass.
- Playwright `--workers=4` passed 172 tests: every `class-session*` spec (the new export spec included), homes, and the play-screen specs order-confirm, guided-week and chain-band. Axe and reflow ran per width. After the patches, export, class-session and homes passed again (32).
- New tests over 1 s: the 250-Student timing (about 15 s), and the locked-session tests (1–3 s each, from the fixtures).

**Residual risks:**
- The 10-minute target is shown with a fake converter. The real conversion is bounded by concurrency 3 × the single report's time.
- The whole ZIP is held in memory for `put` (tens of MB for 250 Students).
- Other staff see a new ZIP only on load or by the 15 s poll while it is pending.
- Ready ZIP objects are removed by Epic 15's retention, under the Class session's prefix.
- New personal data: the table `report_zips` (`requested_by`), and ZIP objects holding Student names and work.
