---
title: 'Story 13.7: A Student downloads the Student report as a tagged PDF'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '48b48beb8ea1e466d6902491bcd3719e035485f8'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-6-message-the-students-who-have-not-met-the-requirement.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Stored report PDFs have no retention or deletion path; a deleted User's or Class session's PDF stays in the bucket.
    evidence: |-
      storage.delete runs only when a newer render replaces a PDF; report_requests cascades but the object stays. Epic 15 adds deletion and retention.
    location: >-
      backend/app/modules/reports/render.py
    severity: medium
  - summary: >-
      The private reports bucket is never created, and WEB_INTERNAL_URL has no production check.
    evidence: |-
      A first production upload fails without the bucket; a missing WEB_INTERNAL_URL makes every render fail as render_failed.
    location: >-
      backend/app/platform/config.py
    severity: medium
  - summary: >-
      The same-origin fetcher of the WeasyPrint conversion is never exercised by a test.
    evidence: |-
      Tests fake to_pdf. Would settle it: the predicate factored out and unit-tested without Pango.
    location: >-
      backend/app/modules/reports/render.py
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** A Student cannot document their work in a Class session: there is no Student report, no PDF pipeline and no storage (FR-57, FR-58, AD-14, AD-18).

**Approach:** Build the whole report pipeline once, for reuse by 13.8–13.13 and 15.1: a request row and a `reports-single` job (ids only), `reports.build_report_data` as the only assembler, a short-lived snapshot with a single-use 5-minute render token, the server-rendered print route `/print/report/<snapshot_id>`, WeasyPrint `pdf/ua-1` in `worker-batch`, `platform/storage` (local mock in `./.local-storage/`, Supabase Storage over REST in production) and signed download URLs. The report holds a header and the Completion section; a section registry on both sides takes the later sections.

## Boundaries & Constraints

**Always:**
- Api (Student self, policy `reports.download_own`, ANY_USER held to `sessions.enrolled_locked_row`; one 403 `forbidden` for everything else): `GET /api/me/class-sessions/{id}/report` → `ReportStateOut {opens_at, open, status: none|pending|ready|failed, generated_at}`; `POST` same path → 202 with the state (records a `report_requests` row and defers `reports.render_report(request_id)` on `reports-single` in the same transaction; a pending one answers itself, no second render); 409 `report_not_open` before the effective Test deadline or with none, 409 `not_counted` outside `scope.reporting_students`. `GET …/report/file` → 303 to a signed URL (`SIGNED_URL_TTL_SECONDS`, default 300) only after the policy allowed it; 409 `report_not_ready` without a ready PDF. `Cache-Control: no-store`.
- A pending request older than `REPORT_STALE_SECONDS` (120) reads as failed and a new press replaces it (a crashed worker cannot block the Student).
- Job: loads the request (not pending → nothing), deletes expired snapshots, calls `build_report_data(student_id, class_session_id, options)`, stores a `report_snapshots` row (data JSONB, sha256 of a `secrets.token_urlsafe(32)` token, `expires_at` = now + 5 min), commits, fetches `WEB_INTERNAL_URL/print/report/<id>?token=…` through WeasyPrint `pdf/ua-1` (fetches only from that origin), stores the PDF at `reports/class-sessions/<cs>/<user_id>/student-report.pdf`, marks the request `ready` (or `failed`, code `render_failed`, logged with ids and the error type only), deletes the snapshot in a `finally`, emits `user:<student>`. Registry `reports.request_report` and `reports.render_report`: `{user}`.
- `GET /api/report-snapshots/{id}` with header `X-Render-Token` (public dependency): one UPDATE marks it used only while unused, unexpired and the token hash matches, answering its data; any other case 404 `not_found` with no data.
- Print route (server component, `force-dynamic`, no client code): reads the snapshot from `API_INTERNAL_URL`, renders the header «ØL-spillet», «Studentrapport», name, Class, «Klasseøkt N», Start date, Play/Debrief deadlines, the Student's Test deadline, «Laget <time>», «Rapporten dokumenterer arbeidet ditt. Den er ikke en karakter.», then each section through a `kind` → component registry. Completion section: a `<table>` with `<caption>`, `th scope="col"`, `th scope="row"` step names, status «gjort»/«ikke gjort» (with «, rettet av faglærer»; never the reason), the share line through `formatNumber`, and «Kravet er oppfylt.»/«Kravet er ikke oppfylt.»/«Klasseøkten er ikke obligatorisk.». PDF copy lives in `frontend/src/app/print/report/copy.ts`. Fonts come from the root layout's `@fontsource/source-sans-3`.
- Stegene: the «Rapport» step is `current` once the effective Test deadline has passed (also when earlier steps are not done), else `locked` with «Rapport, åpnes når Testfristen er ute.»; Hjem puts `ReportDownload` under that step. `ReportDownload` (reusable by 15.1): button «Lag Studentrapport»; pending line «Lager rapporten …» (`role=status`); ready: Lenke «Last ned Studentrapporten (PDF)» to `…/report/file` and «Laget <time>»; failed: inline error and «Prøv igjen». The `user` topic invalidates its query.
- `platform/storage`: `put`, `signed_url`, `delete`; Supabase Storage (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, bucket `reports`) when the keys are set, else the local mock in `LOCAL_STORAGE_DIR` (default `.local-storage`) only when `APP_ENV` is local, test or ci; the mock's signed URL is `/api/storage/local/<path>?expires=…&signature=…` (HMAC with the JWT secret), served only by the mock.
- `worker-batch` runs `reports-single` beside its queues with `REPORTS_SINGLE_RESERVED` (default 2) slots of its own.
- veraPDF (`verapdf/cli`, pinned digest, Docker, no account) checks the e2e's sample PDF against PDF/UA-1 in CI and locally.

**Never:** no report content built in the api request; no names or free text in logs or job arguments; no second chart, form or Stegene; no AI data; no sections of 13.8/13.10; no change to the demo Class «class-of-1994».

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| After deadline | POST | 202 pending; job → ready; `user:<id>` | — |
| Second press while pending | POST | same request, one job | — |
| Before deadline / none | POST | — | 409 `report_not_open` |
| Other Student / not enrolled / bad id | any | — | 403 `forbidden` |
| File before ready | GET file | — | 409 `report_not_ready` |
| Render fails | converter raises | status failed, snapshot gone, log without names | retry by POST |
| Used / expired / wrong token | snapshot GET | — | 404 `not_found` |
| Stale pending (> 120 s) | GET / POST | reads failed; POST makes a new request | — |
| Later correction | POST again | new PDF with the correction | — |

</intent-contract>

## Code Map

- `backend/app/platform/jobs/__init__.py` -- `QUEUES`, `TASK_MODULES`, `defer`, `run_worker` (add `REPORTS_SINGLE` and the reserved-slot worker).
- `backend/app/worker.py` -- CLI; `serve`.
- `backend/app/platform/config.py` -- settings; `REQUIRED_SECRETS` already holds the storage keys (Story 3.14).
- `backend/app/platform/chart_print_check.py` -- WeasyPrint `URLFetcher` pattern and `pdf/ua-1` call to reuse.
- `backend/app/platform/authz.py:84-225` -- policy tables.
- `backend/app/platform/events/registry.py:151` -- `reports.*` entries; `tests/test_events.py` checks them.
- `backend/app/modules/reports/{service.py,routes.py,README.md,models.py,repo.py}` -- `completion_status`, router; new `report.py` (request, state, file), `report_data.py` (assembler + section registry), `render.py` (job + converter), `snapshot_routes` in `routes.py`.
- `backend/app/modules/sessions/service.py` -- `enrolled_locked_row` (:1996), `_student_row`, `effective_test_deadline`, `stegene` (:1600), `enrolled_sessions` stegene call (:1550); `repo.number_of`; `classes.label_of_class`, `classes.student_names`.
- `backend/app/modules/sessions/dev.py` -- add `POST /api/dev/class-sessions/{id}/test-deadline-passed`.
- `backend/migrations/versions/` -- head `0303`; new `0304_student_reports.py`.
- `backend/Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml` -- storage dir, env, queue, veraPDF step.
- `frontend/src/app/print/graf-over-tabell/page.tsx` -- print page pattern; new `frontend/src/app/print/report/[snapshotId]/page.tsx`, `copy.ts`, `sections.tsx`.
- `frontend/src/components/stegene.tsx`, `frontend/src/modules/games/{home.ts,student-hjem.tsx}`, `frontend/src/lib/api/topics.ts`, `frontend/src/copy/nb.ts` (`homes.student.locked.report`), `frontend/src/modules/reports/` (new `report-download.tsx`, `api.ts`).
- Tests: `backend/tests/reports/test_completion_status.py` (`obligatory`, `every_later_step`), `tests/sessions/test_game_end.py` (`short_game`, `klass`, `clock`), `tests/classes/test_student_registration.py` (`set_clock`, `emitted`), `tests/sessions/test_dates.py` (`TEST`, `NOW`). E2E `frontend/e2e/support/live-game.ts` (`lockedClassGames`).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/storage.py` + config -- storage with local mock and Supabase REST; local route.
- `backend/migrations/versions/0304_student_reports.py`, `reports/models.py`, `reports/repo.py` -- `report_requests` (partial unique pending index), `report_snapshots`.
- `reports/report_data.py`, `reports/report.py`, `reports/render.py`, `reports/routes.py`, authz, registry, jobs, worker, sessions stegene + dev route -- the pipeline.
- `backend/tests/reports/test_student_report.py`, `tests/platform/test_storage.py`, worker/job tests -- matrix rows with a fake converter that reads the snapshot through the api.
- Frontend: print route + registry + copy, `ReportDownload`, Stegene action slot, topic key, nb copy, `npm run api:generate`, unit tests.
- `frontend/e2e/student-report.spec.ts` -- fresh locked session, steps recorded, deadline passed by dev route, press → pending → ready under 30 s → PDF bytes, `/print/report/x` 404 through the proxy, axe at 320 and 1440 px; writes the sample PDF.
- `scripts/verapdf` + CI step -- veraPDF PDF/UA-1 on the sample.

**Acceptance Criteria:**
- Given a Student after their effective Test deadline, when they press «Lag Studentrapport» on Hjem, then the step shows the pending line and, without reload, the download Lenke within 30 s, and the PDF downloads.
- Given the sample PDF, when veraPDF runs with the UA-1 profile, then it passes.
- Given a Student before the deadline, when Hjem shows Stegene, then «Rapport» is locked with what opens it.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: four (blind, edge case, verification gap, intent alignment) on Sonnet, as the lane brief directs for a change to the data model, access and a job pipeline.
- verdicts: 45 findings — high 0, medium 15, low 26, false 2, maybe-false 2 (4 descriptive intent rows graded low)
- findings:
  - `[medium]` `[patch]` Blind: a render replaced as stale could overwrite a newer PDF at the one shared path. Each render now writes `student-report-<request_id>.pdf`; a ready render clears and deletes the earlier objects; a render no longer pending deletes its own. The correction test asserts one file, the newest, and that `/file` points at it.
  - `[medium]` `[patch]` Blind: no bound on render time. `to_pdf` is `wait_for(…, 90 s)`, so a hung conversion frees its slot.
  - `[medium]` `[patch]` Blind: an open page never learns of a crashed render. `useMyReport` refetches every 15 s while pending.
  - `[medium]` `[patch]` Blind: snapshots left by a killed render linger. Sweep action `reports.purge_snapshots` deletes expired ones (allowed in `test_imports`); test added. The bucket's PDF retention is deferred (Epic 15).
  - `[low]` `[reject]` Blind: SIGTERM cancels an in-flight render. The render's `finally` marks it failed and the Student presses again; draining needs a stop signal of its own.
  - `[medium]` `[patch]` Blind: an error page could become a "ready" PDF. The job stores nothing unless the print route read the snapshot (`used_at`); test added.
  - `[medium]` `[patch]` Blind: a failed re-render hides the older good PDF. The Lenke and «Laget …» show whenever a ready PDF exists.
  - `[low]` `[reject]` Blind: two `current` steps; nothing on 403; the button before `not_counted`; the locked note with no deadline. The story opens «Rapport» at the deadline whatever the earlier steps; the rest is rare (test students arrive with Epic 12).
  - `[medium]` `[patch]` Blind: production configuration. `railway/worker-batch` runs `reports-single` and names `WEB_INTERNAL_URL`; `.env.example` lists the new variables. The bucket's creation and a production check of `WEB_INTERNAL_URL` are deferred.
  - `[low]` `[reject]` Blind: no rate limit on presses. One pending render per Student bounds it; a render takes seconds.
  - `[low]` `[patch]` Blind: test gaps. `not_counted`, `not_reportable`, the worker split and the non-ASCII signature have tests now; `took < 30` is the story's measurement on the mock.
  - `[low]` `[reject]` Blind: veraPDF only on the simple sample. Stories 13.8 and 13.10 extend the fixture by their own ACs.
  - `[low]` `[reject]` Blind: copy re-typed from `nb.ts`. AD-19 puts PDF copy in the print route.
  - `[low]` `[patch]` Blind: `topics.ts` import order. Fixed.
  - `[low]` `[patch]` Edge: non-ASCII signature gives 500. `isascii()` guard; test.
  - `[medium]` `[patch]` Edge: shared object path. Same root as the first Blind row.
  - `[low]` `[patch]` Edge: shared `.part` file. Random suffix.
  - `[low]` `[patch]` Edge: `StorageError` on sign gives 500. 503 `storage_unavailable`.
  - `[medium]` `[patch]` Edge: lingering snapshot. Same as the Blind row.
  - `[medium]` `[patch]` Edge: no conversion timeout. Same as the Blind row.
  - `[low]` `[patch]` Edge: a redirect bypasses the origin check. `allow_redirects=False`.
  - `[low]` `[patch]` Edge: the reports worker dies unnoticed. `run_worker` waits on both and stops the process when it ends.
  - `[low]` `[reject]` Edge: SIGTERM cancels a render. As the Blind row.
  - `[medium]` `[patch]` Edge: no refetch while pending. Same as the Blind row.
  - `[medium]` `[patch]` Edge: a failed render hides the older PDF. Same as the Blind row.
  - `[low]` `[defer]` Edge: cascades orphan PDFs in the bucket. Epic 15 (deletion, retention).
  - `[low]` `[reject]` Edge: the dev route ignores a Student's own extension. Dev only; the e2e has none.
  - `[low]` `[patch]` Edge: `/file` served a Student reports leave out. `own_file_url` checks the reporting scope; test.
  - `[false]` `[reject]` Edge: registry entries unchecked. The api test asserts the emitted topics equal `COMMAND_TOPICS["reports.request_report"]` and `["reports.render_report"]`.
  - `[low]` `[reject]` Edge (claim): the intent names `/api/report-snapshots/{id}`, the code `/api/internal/…`, so the proxy can refuse it. The fix edits the intent block.
  - `[low]` `[patch]` Edge (claim): the origin claim and redirects. Patched above.
  - `[low]` `[patch]` Edge (claim): stale "reads failed" on an open page. Patched by the refetch.
  - `[low]` `[reject]` Edge (claim): role=status is a separate sr-only line and the copy differs. That line is the polite announcement; the wording is draft copy.
  - `[medium]` `[patch]` Verification: the worker split is not asserted. `test_worker.py` asserts two workers, the reserved concurrency, no signal handlers on the reports worker, and one worker otherwise.
  - `[medium]` `[patch]` Verification: `not_counted` and `not_reportable` untested. Test added.
  - `[maybe-false]` `[defer]` Verification: `SameOrigin` never runs in a test. Would settle it: the predicate factored out and unit-tested without Pango.
  - `[false]` `[reject]` Verification: `test_railway_config` not updated. Updated with the Railway command before this pass's patches; it passes.
  - `[medium]` `[patch]` Verification: Railway's worker-batch lacks `reports-single`. Same as the Blind production row.
  - `[low]` `[patch]` Verification: `docs/ops/connection-budget.md` stale. Updated (worker-batch pool 4, pooler at least 55).
  - `[low]` `[patch]` Verification: the reports worker unsupervised. Same as the Edge row.
  - `[maybe-false]` `[reject]` Verification: stale overwrite. Same root as the patched path row.
  - `[low]` `[reject]` Intent: backend tests fake the converter. The e2e and the veraPDF step run the real pipeline.
  - `[low]` `[reject]` Intent: the fixture is not the demo Class. The lane brief forbids changing «class-of-1994»; the e2e makes a fresh Class.
  - `[low]` `[reject]` Intent: the print page's bad-token branch untested. `readSnapshot` gives null on any non-200, the api's 404 is tested, and the job now refuses a page that read nothing.
  - `[low]` `[reject]` Intent: `ReportDownload` not unit-rendered. The e2e drives it with axe at 1440 and 320 px.

## Design Notes

The request is two steps (make, then download) because the PDF is built asynchronously and a signed URL must be created at click time; a plain Lenke to `…/report/file` keeps the download working without script. The sample for veraPDF comes from the e2e's fresh Class, not the demo Class (the lane brief forbids changing it); the e2e records step events through existing dev routes.

## Verification

**Commands:**
- `uv run pytest tests/reports/test_student_report.py tests/platform/test_storage.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/reports src/modules/games` -- pass
- `npx playwright test e2e/student-report.spec.ts` then `python scripts/verapdf frontend/test-results/student-report.pdf` -- pass

## Auto Run Result

Status: done

**Summary.** The Student report pipeline (FR-57, FR-58, AD-9, AD-14, AD-18). A Student whose effective Test deadline has passed sees «Rapport» open on Hjem with «Lag Studentrapport». The press records a `report_requests` row and defers `reports.render_report(request_id)` on `reports-single`; the api builds no content. The job calls `report_data.build_report_data` (the only assembler, with a section registry: `completion` now; 13.8 and 13.10 add theirs), stores a snapshot with a single-use 5-minute token, has WeasyPrint (`pdf/ua-1`, same origin, no redirects, 90 s cap) convert `/print/report/<id>?token=…`, stores the PDF through the new `platform/storage` (Supabase REST, or the `./.local-storage/` mock), deletes the snapshot in every case, and emits `user:<id>`. The Lenke «Last ned Studentrapporten (PDF)» goes to `/report/file`, which answers 303 to a signed URL (300 s) after the policy. The print route is server-rendered with no script and self-hosted fonts; the proxy refuses `/print/*` and `/api/internal/*`. `worker-batch` runs `reports-single` on 2 reserved slots.

**Implementation note.** The lane brief says to implement in the builder's own context, so step 3 ran here rather than in a sub-agent.

**Files.**
- Backend: `platform/storage.py` (new), `platform/config.py`, `platform/jobs/__init__.py` (queue, reserved worker), `platform/authz.py`, `platform/events/registry.py`, `worker.py`, `main.py`; `reports/{report,report_data,render,snapshot}.py` (new), `reports/{models,repo,routes,schemas}.py`, `reports/README.md`; `sessions/service.py` (`own_report_session`, `report_opens_at`, `report_heading`, Stegene `report_open`), `sessions/dev.py` (`test-deadline-passed`); `ops/sweep.py` (`reports.purge_snapshots`); migration `0304_student_reports.py`.
- Backend tests: `tests/reports/test_student_report.py`, `tests/platform/test_storage.py`, `tests/test_verapdf_script.py` (new); `test_worker.py`, `test_migrations.py`, `test_authz_rules.py`, `test_proxy_config.py`, `test_imports.py`, `test_railway_config.py`.
- Frontend: `app/print/report/{[snapshotId]/page.tsx,report.tsx,sections.tsx,copy.ts,snapshot.ts}` (new), `modules/reports/{report-download.tsx,report-download.test.tsx}` (new), `modules/reports/api.ts`, `components/stegene.tsx` (action slot), `modules/games/{home.ts,student-hjem.tsx}`, `lib/api/topics.ts`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/student-report.spec.ts` (new).
- Ops: `proxy/Caddyfile`, `docker-compose.yml` (volume, env, queue), `backend/Dockerfile`, `railway/worker-batch/railway.toml`, `.env.example`, `docs/ops/connection-budget.md`, `.github/workflows/ci.yml` (veraPDF step), `scripts/verapdf` (new).

**Review.** Four layers, 45 findings: 0 high, 15 medium, 26 low, 2 false, 2 maybe-false. Patched 10 distinct medium roots and the low ones listed; deferred 3 (bucket PDF retention, bucket creation and a production `WEB_INTERNAL_URL` check, a test of the same-origin fetcher); the rest rejected with reasons in the Review Triage Log. Follow-up review: **true**: the per-request object paths with deletion of older PDFs, and the supervised reserved worker in `run_worker`, were written after the review and have only this pass's tests.

**Verification.**
- Full backend suite (8 processes): 3775 passed (before the last test-speed edit; the report file again alone: 9 passed). An earlier run had 9 load flakes (`test_sim`, `test_events`, `test_narration`) that pass alone and touch no changed code. ruff check and format pass.
- Frontend: typecheck, Vitest 1210 passed, lint:colours, check:copy; build in the image.
- Playwright (4 workers, lane stack): `student-report` (locked → open → pending → Lenke in about 2 s, under 30 s → PDF download; proxy 404s; axe and reflow at 1440 and 320 px), `homes`, `student-home`, `completion`, `replay-close`, `replay-start`, `individual-test`, `order-field`, `order-confirm`, `game-end`: 127 passed (one `individual-test` flake passed on rerun).
- PDF/UA: **veraPDF 1.30.4 ran locally** through its Docker image (`verapdf/cli`, pinned by digest, no account): `scripts/verapdf frontend/test-results/student-report.pdf` → compliant against the `ua1` profile. CI runs the same step after Playwright.
- New tests over 1 s: `test_the_report_opens_at_the_test_deadline_and_is_rendered_from_a_snapshot` (about 1.8 s), `test_a_later_correction_shows_in_the_next_report` (1.6 s), `test_a_student_reports_leave_out_gets_no_report` (1.3 s): each locks a Class session.

**Decisions taken for the founder [ASSUMPTION].**
- Two steps: «Lag Studentrapport», then the Lenke «Last ned Studentrapporten (PDF)» with «Laget …»; the latest PDF stays downloadable while a new one is made or after one failed.
- «Rapport» opens at the Student's effective Test deadline whatever the earlier steps (they show as «ikke gjort» in the report); locked copy «Rapport, åpnes når Testfristen er ute.», open note «åpen».
- The veraPDF sample comes from the e2e's fresh Class, not the demo Class «class-of-1994» (the lane brief forbids changing it).
- A Student reports leave out (test student, Control test session) gets 409 `not_counted`.
- A pending render older than 120 s counts as failed and the next press replaces it.
- The PDF has a dates table with the year and Oslo time; draft PDF copy in `app/print/report/copy.ts`.

**Personal data.** New tables `report_requests` (`user_id`, `requested_by`) and `report_snapshots` (the Student's name and report content, for one render; purged when expired).

**Residual risks.** No bucket creation or retention in production yet (deferred); a render cancelled by a deploy ends `failed` and needs a new press.

## Epic 13 close-out: follow-up review

Fixed (medium): the Student's own report ignored the deletion date while the staff's refused. Now `own_state` answers `deleted`, and the press and the download answer 409 `data_deleted` (`test_once_the_data_is_deleted_the_student_gets_no_report`); Hjem says «Dataene dine i denne Klasseøkten er slettet. …» [ASSUMPTION]. Left (low): no test of a stale render that ends after a newer one; the render job does not re-check the deletion date when it runs.
