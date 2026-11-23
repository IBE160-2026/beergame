---
title: 'Story 15.4: The Admin exports pseudonymised data for evaluation'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '5a6fd09b9207dc21bfeda1858fd5f4d77c4e93e0'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The deletion date, the Individual test answers and the Control test and test-Student scope are seams only.
    evidence: |-
      Story 15.3 (retention), Epic 11 (test answers) and Epic 12 (control_test, is_test_student) are not on this branch. ops.retention.deletion_date is a placeholder (Test deadline + 6 calendar months, Oslo); ops.evaluation.SECTIONS has no test-answer section; reports.scope narrows only Game purposes. Each later story must replace or extend these and the export test.
    location: >-
      backend/app/modules/ops/retention.py, backend/app/modules/ops/evaluation.py SECTIONS, backend/app/modules/reports/scope.py
    severity: medium
  - summary: >-
      The export reads every row into memory before the ZIP is streamed.
    evidence: |-
      _read materialises each section; zip_stream only encodes incrementally. Bounded by 20 Class sessions; a server-side cursor per section would bound memory. Not measured at pilot scale (Story 15.10 load test).
    location: >-
      backend/app/modules/ops/evaluation.py _read
    severity: low
---

<intent-contract>

## Intent

**Problem:** The founder needs the Decision log and Students' answers to evaluate AI players and learning outcomes (FR-71), but the Admin sees no Student answers (AD-12) and nothing may leave with names; there is no agreement record, no pseudonym key handling and no export.

**Approach:** A new Admin page «Pseudonymisert eksport» (`/admin/evaluering`) in `modules/ops`: record an Institution agreement per Class session (audited), run an export with a key typed in the form that streams a ZIP of CSV files in the request with every Student replaced by `HMAC-SHA256(key, user_id)`, store only the key's fingerprint (first run) and refuse a different key, replace the fingerprint as a separate audited action, and list every run (from the audit log) with each Class session's deletion date. `can(admin, "export_pseudonymised", class_session)` in `platform/authz` is the only gate. Rows are read through a new `reports.scope` (AD-13).

## Boundaries & Constraints

**Always:**
- `platform/authz`: action `export_pseudonymised` (role `admin`) holds for a resource only when `resource.agreement_recorded` is true; `evaluation.manage` (role `admin`) for agreements, key and list. A Lecturer gets 403 before anything is read; an Admin choosing any Class session without an agreement (or unknown) gets 403 `no_agreement` with `fields.class_session_ids`, and no Student data is read.
- The key: 32–512 characters after trimming outer whitespace; held in a pydantic `SecretStr`, used only in memory in that request; never in the database, a job, a log line, an env var, an error body or the audit. Fingerprint = `HMAC-SHA256(key, "olspillet:pseudonym-key-fingerprint:v1")` hex, stored in a one-row table. First export stores it; a later key with another fingerprint → 409 `pseudonym_key_changed`. «Bytt nøkkel» stores the new key's fingerprint (audited `pseudonym_key.replaced`, change: old and new fingerprint).
- Pseudonym = hex `HMAC-SHA256(key, str(user_id))`; the same Student gets the same pseudonym in every file and every run with the same key. An erased User (`deleted_at`) gets an empty pseudonym.
- ZIP contents: `decision_log.csv` (every `seat_weeks` column incl. `state_seen` as JSON, `llm_call_ids`, the Role, the game number, and the Student in force that Week as pseudonym), `llm_calls.csv` (metadata of the referenced calls: model, provider, version, effort, tokens, cost, latency, outcome, times — no bodies, no error text), `starting_task.csv`, `explanations.csv` (text as written, not scrubbed), `manifest.json` (time, Class session ids with deletion dates, key fingerprint, files). No name, e-mail, student number, AI assessment or Indicative letter.
- Scope: `reports.scope.reporting_games()` (excludes `lecturer_test` and `simulation`; seam for `control_test` Class sessions) and `reporting_students()` (seam for test Students) filter every section.
- Sections are a list `ops.evaluation.SECTIONS` of `(file, reader)`; each owning module provides its reader in its `service.py` (`games`, `tests`, `debrief`); Epics 11–14 append theirs (Individual test answers) there — the registration seam.
- Every run and every refusal (`no_agreement`, `pseudonym_key_changed`) writes one audit row `evaluation_export.run`: actor, time, change `{outcome, class_session_ids, key_fingerprint}`. Agreement recording writes `evaluation_agreement.recorded` (target `class_session_id`, change: agreed-on date). The export list reads these audit rows, newest first (100).
- Deletion date (seam for Story 15.3): Test deadline + 6 calendar months (placeholder), in `ops.retention.deletion_date`; none while the Test deadline is unset.
- All copy in `frontend/src/copy/nb.ts` marked `[ASSUMPTION] Story 15.4`; one primary button (the download); the key field is `type="password"`, `autocomplete="off"`, cleared after every run.

**Never:**
- No job, no stored file, no key in a URL or query string.
- No scrubbing of free text (open assumption 15.4); no AI assessments, letters, reflection or follow-up text.
- No change to `seat_weeks` or other game rows; no new Student-data access path besides this gate.
- No build of Story 15.3 retention, Epic 11 test answers or Epic 14 reports beyond the seams.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First export | agreement recorded, no fingerprint, key K | 200 ZIP; fingerprint of K stored; audit `exported` | — |
| Same key later | fingerprint of K stored, key K | 200 ZIP, identical pseudonyms | — |
| Changed key | fingerprint of K stored, key L | 409 `pseudonym_key_changed`, audit refused | nothing read |
| No agreement | one chosen session without agreement | 403 `no_agreement`, audit refused | nothing read |
| Lecturer | any | 403 `forbidden` | no audit, nothing read |
| Short key | < 32 chars | 422 `fields.key` | no audit |
| Empty / too many sessions | `[]` or > 20 | 422 | — |
| Test Game | Lecturer test Game in the session | not in any file | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py:82` -- `POLICIES`, `can()`: add `export_pseudonymised` with a resource condition, `evaluation.manage`.
- `backend/app/platform/audit.py:90` -- `record`, `page(action=…)` for the export list; `register_labels` for `class_session_id`.
- `backend/app/modules/ops/` -- owns the feature (epic context). `sweep.py` shows the list-of-actions registry pattern (`DUE_ACTIONS`).
- `backend/app/modules/games/models.py:317` -- `seat_weeks`; `seat_occupancy` (`from_week`, newest by id in force, `repo.py:1023`); `games.purpose`, `class_session_id`, `game_number`.
- `backend/app/ai/calls.py:101` -- `get(ids)`; add `export_metadata(ids)` (only `app/ai` reads `llm_call`).
- `backend/app/modules/tests/models.py:33` -- `starting_task_answers`.
- `backend/app/modules/debrief/models.py:147` -- `debrief_explanations`.
- `backend/app/modules/sessions/models.py:34` -- `class_sessions` (`test_deadline`, `start_at`); `classes.models` (`name`, `course_code`, `institution_id`); `identity.models.institutions`, `users.deleted_at`.
- `backend/app/modules/identity/personal_data.py` -- registry: add the two new tables.
- `backend/app/main.py:104` -- router includes; `_invalid_request` echoes field names only (key safe).
- `backend/app/platform/logging.py` -- allowlist logging (key never a field).
- `backend/tests/sessions/test_play.py:58` -- `running(klass, students)`; `tests/identity/test_user_delete.py:56` `everywhere(...)` whole-DB search; `tests/classes/test_classes.py` `make`, `as_user`.
- `frontend/src/modules/admin/institutions-page.tsx`, `institution-form.tsx`, `api.ts`, `audit.ts` -- page, form and hook patterns; `modules/identity/home-page.tsx:52` `AdminSections`; `homes.ts` paths.
- `frontend/e2e/admin-institutions.spec.ts` -- axe at 320/1440 pattern.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0066_evaluation_export.py` -- tables `evaluation_agreements` (class_session_id PK FK cascade, agreed_by text, agreed_on date, controller text, recorded_by uuid, recorded_at) and `pseudonym_key_fingerprints` (one row, fingerprint, set_by, set_at).
- `backend/app/modules/reports/{__init__,scope}.py` -- `reporting_games()`, `reporting_students()` by table name only.
- `backend/app/modules/ops/{models,evaluation,retention,schemas,routes}.py` -- tables, agreement upsert, key fingerprint, export build (sections, pseudonymisation, ZIP stream), export list, deletion date, routes under `/api/admin/evaluation`.
- `backend/app/modules/{games,tests,debrief}/service.py`, `backend/app/ai/calls.py` -- section readers.
- `backend/app/platform/authz.py`, `backend/app/main.py`, `identity/personal_data.py` -- policy, router, registry.
- `backend/tests/ops/test_evaluation_export.py` -- matrix rows, pseudonym stability, scope, key search in DB and logs, audit rows, policy unit test.
- `frontend/src/copy/nb.ts`, `src/modules/admin/{evaluation-page.tsx,evaluation.ts,evaluation.test.ts,api.ts}`, `src/app/(app)/admin/evaluering/page.tsx`, `modules/identity/{homes.ts,home-page.tsx}`, `src/lib/api/*` (regenerated) -- page and link.
- `frontend/e2e/admin-evaluation.spec.ts` -- record agreement, export download, key change refusal, axe at 320/1440.

**Acceptance Criteria:**
- Given the Admin on «Pseudonymisert eksport», when they record an agreement for a Class session, then the session becomes choosable for export and the audit has `evaluation_agreement.recorded`.
- Given an allowed run, when the ZIP is opened, then the same Student has one pseudonym across `decision_log.csv`, `starting_task.csv` and `explanations.csv`, and none of the files holds a Student's name or e-mail.
- Given any run, when the database (every table) and the captured logs are searched for the key, then it is found nowhere.
- Given an export or refusal, when the Admin reads the export list, then it shows the time, actor, Class sessions with their deletion dates, fingerprint and outcome.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- verdicts: 50 findings — high 0, medium 9, low 26, false 6, maybe-false 0 (verification-gap ordering finding counted under its filed disposition)
- findings:
  - `[medium]` `[patch]` Blind: key not Unicode-normalised (NFC vs NFD «ø») gives `pseudonym_key_changed` or new pseudonyms — the route now NFC-normalises the trimmed key; tested with an NFD key that exports and replaces as a no-op.
  - `[low]` `[reject]` Blind: a mistyped first key becomes the stored one, no double entry — «Bytt nøkkel» replaces it; a confirm field adds UI for a rare slip.
  - `[low]` `[reject]` Blind: key-holder separation not enforced, any Admin can replace the key and record agreements — the story makes the key holder an organisational role who types the key at run time; the system cannot tell who types; every action is audited.
  - `[medium]` `[patch]` Blind: fingerprint in `manifest.json` lets a ZIP holder test keys offline — removed from the manifest (kept in the database, audit and list, which the ZIP holder does not see); copy now asks for 32 random characters. A KDF/entropy check was rejected: a fixed-message HMAC of a 32+-character random key is not guessable, and a KDF adds a parameter to manage.
  - `[low]` `[reject]` Blind: all erased Users share the empty pseudonym — intended: an erased User has no pseudonym so nothing links their rows; `occupant_kind` tells them from AI Seats.
  - `[medium]` `[patch]` Blind: CSV formula injection in Explanation text — `cell()` prefixes `'` to text starting with `= + - @` tab or CR; manifest states it; unit-tested.
  - `[medium]` `[patch]` Blind: page copy says no names while Explanations are unscrubbed — lead and manifest notice now say the Explanations stand as written and can name people.
  - `[medium]` `[patch]` Blind: one bind parameter per LLM call id can exceed the driver limit — `export_metadata` now binds one array (`= ANY`). In-memory build and the key-row lock held during the read: deferred (memory) / rejected (exports are rare, a second export waits seconds).
  - `[low]` `[reject]` Blind: no agreement revoke, audit lacks old agreed_by/controller, draft sessions accept agreements, no check on past deletion date — not asked by the story; the audit holds ids and codes only by rule (AD-14); a draft session has no data to export.
  - `[low]` `[reject]` Blind: a future section could leak raw user ids if its column is not in `student_columns` — the seam's docstring states the rule; Epic 11 extends the no-id assertion of the export test with its section.
  - `[low]` `[reject]` Blind: audit says exported before the bytes are delivered — the data left the database for that request; a broken download is retried by the Admin and audited again.
  - `[low]` `[reject]` Blind: export list capped at 100 without paging — the Revisjonslogg keeps every row; exports are rare.
  - `[false]` `[reject]` Blind: unrelated sprint-status and Story 11.3 log hunks — the orchestrator's commits after the baseline, not this change.
  - `[false]` `[reject]` Blind: migration 0066 may clash with the other lane — the orchestrator relinks numbers at merge (brief).
  - `[low]` `[reject]` Blind: forbidden/expired session words as the generic failure; Blob in memory; no component tests for focus — the page's guard handles an ended session; the e2e covers the visible flow.
  - `[low]` `[patch]` Blind: `del key` does nothing — removed.
  - `[low]` `[patch]` Blind: file name with minute resolution — now to the second.
  - `[medium]` `[patch]` Edge: CSV injection — same fix as above.
  - `[medium]` `[patch]` Edge: bind-parameter limit — same fix as above.
  - `[low]` `[reject]` Edge: Starting task answers of a Student with no Seat in a reporting Game are left out — by design the Class session's Students are its seat holders (`reports.scope.reporting_seat_holders`); every allocated Student holds a Seat.
  - `[medium]` `[patch]` Edge: NFC/NFD key — same fix as above.
  - `[low]` `[reject]` Edge: low-entropy 32-character keys accepted — copy asks for random characters; see fingerprint row.
  - `[low]` `[patch]` Edge: a run that fails while reading leaves no audit row — any other exception now writes the run with outcome `failed` (copy «Feilet») and re-raises.
  - `[low]` `[defer]` Edge: whole export held in memory — deferred (frontmatter).
  - `[low]` `[reject]` Edge: agreement for an unsaved session; replaced agreement loses old text — as the Blind row.
  - `[low]` `[reject]` Edge: `agreed_on` may be any past date — the Admin records the date on the document; no rule bounds it.
  - `[low]` `[reject]` Edge: erased Users collapse into one value — as the Blind row.
  - `[false]` `[reject]` Edge: lone surrogates abort the stream; no BOM — Postgres text cannot hold lone surrogates; UTF-8 without BOM is stated in the manifest for R/pandas.
  - `[medium]` `[patch]` Edge (claim): page promises no names while free text is exported — same fix as the Blind copy row.
  - `[low]` `[patch]` Edge (claim): not every run is audited — same fix as the failed-run row.
  - `[low]` `[reject]` Edge (claim): «streams» while rows are materialised — Design Notes state it; the request, not a job, is the requirement.
  - `[false]` `[reject]` Edge (claim): Starting task ignores `in_scope`, so control_test narrowing will not reach it — `reporting_seat_holders` is built on `reporting_games()`, so a narrowing there reaches it.
  - `[medium]` `[patch]` Verification gap: `llm_calls.csv` path never ran with an id — a test runs `export_metadata` with an id (the query compiles against the real columns) and asserts no body, caller reference or error column.
  - `[medium]` `[patch]` Verification gap: Student per Week not checked across an occupancy change — a staff Takeover in Week 3; the test asserts the pseudonym per (Role, Week): the Student for Weeks 1–2, none in Week 3.
  - `[low]` `[patch]` Verification gap: Oslo conversion of the deletion date untested — 22:30 UTC on 31 Aug gives 1 Mar.
  - `[low]` `[patch]` Verification gap: audit label registration untested — the test reads `/api/admin/audit` and finds the Class session label.
  - `[low]` `[patch]` Verification gap: agreement replacement and same-key no-op untested — both asserted (two audit rows; same key: no row, same `set_at`).
  - `[low]` `[patch]` Verification gap: newest-first order unobserved — the outcome sequence of five runs is asserted.
  - `[medium]` `[patch]` Verification gap (other): CSV formula cells — same fix as above.
  - `[low]` `[reject]` Verification gap (other): Starting task of unseated Students — as the Edge row.
  - `[false]` `[reject]` Verification gap (other): `simulation` exclusion unobserved — not a finding by its own account; a simulation Game has no Class session.
  - `[low]` `[reject]` Intent: «streams» is in-request, not incremental — as above.
  - `[low]` `[reject]` Intent: no key-holder concept in code — as the Blind row.
  - `[false]` `[reject]` Intent: LLM metadata as a side file, not inline columns — the Decision log carries `llm_call_ids` and the metadata file is joined by them; descriptive.
  - `[low]` `[defer]` Intent: Individual test answers absent; deletion date a placeholder; scope comments for Epic 12 — deferred seams (frontmatter).
  - `[low]` `[reject]` Intent: Starting task scope rests on seat holders — as the Edge row.
  - `[false]` `[reject]` Intent: erased User's empty pseudonym departs from «same pseudonym» — an erased User is no longer a Student to evaluate; descriptive.
  - `[low]` `[reject]` Intent: Lecturer denials not audited — the policy refuses before any export runs; the story audits runs and refusals of the export.
  - `[low]` `[reject]` Intent: browser-side key (mutation cache) not inspected — the cache lives in that tab's memory only; nothing is stored.
  - `[false]` `[reject]` Intent: whole-branch hygiene hunks — orchestrator commits.

## Design Notes

Export list from audit rows, not a new table: the AC asks `platform/audit` to record each run, and one source avoids drift. Fingerprint with a fixed domain message differs from every pseudonym (messages are UUID strings). The 32-character minimum makes brute force of the stored fingerprint impractical. Rows are fetched in one read transaction after the gate, then written into a ZIP whose bytes are yielded as they are produced (`zipfile` on an unseekable writer).

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_evaluation_export.py tests/identity/test_personal_data_registry.py tests/test_authz_rules.py -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-evaluation homes --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** «Pseudonymisert eksport» (`/admin/evaluering`, linked from the Admin-område). The Admin records an Institution agreement per Class session (who agreed, the date, the controller; `PUT /api/admin/evaluation/class-sessions/{id}/agreement`, audited `evaluation_agreement.recorded`). `can(admin, "export_pseudonymised", resource)` in `platform/authz` holds only with an agreement (new `RESOURCE_CONDITIONS`). The run form takes the key holder's key (password field, cleared after every run) and `POST /api/admin/evaluation/exports` streams a ZIP from the request: `decision_log.csv` (every `seat_week` column, Role, game number, the Student in force that Week), `llm_calls.csv` (call metadata, no bodies or error text), `starting_task.csv`, `explanations.csv` (text as written, formula-safe) and `manifest.json` (Class sessions with deletion dates). Each Student is hex `HMAC-SHA256(key, user_id)`; an erased User has none. The key is trimmed and NFC-normalised, never stored; the first run stores `HMAC(key, fixed message)` as fingerprint, a different key gets 409 `pseudonym_key_changed`, «Bytt nøkkel» replaces it (audited `pseudonym_key.replaced`). Every run and refusal writes `evaluation_export.run` (actor, time, Class sessions, fingerprint, outcome); the export list reads those rows with each Class session's deletion date. Rows are read through the new `reports.scope` (Lecturer test Games and simulations out; the Class session's Students are its seat holders in reporting Games).

**Seams.** `ops.evaluation.SECTIONS` (Epic 11 appends Individual test answers; a reader returns columns and rows with User ids in `student`), `reports.scope` (Story 12.7 `control_test`, 12.8 test Students), `ops.retention.deletion_date` (placeholder Test deadline + 6 calendar months; Story 15.3 replaces it).

**New personal-data tables** (listed in `identity/personal_data.py`, handling `keep`): `evaluation_agreements` (`recorded_by` id; `agreed_by` and `controller` are the Admin's text about the Institution, which may name a person there), `pseudonym_key_fingerprints` (`set_by` id).

**Files.**
- `backend/migrations/versions/0066_evaluation_export.py` — the two tables.
- `backend/app/modules/ops/{models,schemas,evaluation,retention,routes}.py` — feature, routes, deletion-date seam.
- `backend/app/modules/reports/{__init__,scope}.py` — the AD-13 scope.
- `backend/app/modules/{games,tests,debrief}/service.py`, `games/repo.py`, `backend/app/ai/calls.py` — section readers.
- `backend/app/modules/{sessions,classes,identity}/{repo,service}.py` — Class session names, erased Users.
- `backend/app/platform/authz.py`, `backend/app/main.py`, `identity/personal_data.py` — policy, router and audit label, registry.
- `backend/tests/ops/test_evaluation_{export,rules}.py`, `tests/test_migrations.py`, `tests/test_imports.py` (main may mount `ops.routes`).
- `frontend/src/modules/admin/{evaluation-page.tsx,evaluation.ts,evaluation.test.ts,api.ts}`, `src/app/(app)/admin/evaluering/page.tsx`, `modules/identity/{homes.ts,home-page.tsx}`, `src/copy/nb.ts`, `src/lib/api/*` (regenerated), `e2e/admin-evaluation.spec.ts`, `e2e/homes.spec.ts`.

**Review.** Four sub-agent reviewers (blind, edge case, verification gap, intent alignment), model sonnet. 50 findings: 9 medium, 26 low, 6 false (rest rejected with reasons). Patched: 9 medium rows and 10 low rows (7 root causes plus 5 test gaps). Deferred: 2 (seams; in-memory build). Rejected: the rest, each with its reason above.

**Follow-up review: recommended.** Patched medium entries: 6 groups (CSV formula prefix, NFC key, array-bound call ids, copy on free text, two test gaps); patched low: 6. Unreviewed new behaviour: the `failed` audit path on an unexpected exception, and the `'` prefix that changes Explanation text starting with `-` in the exported file.

**Verification.**
- Backend full suite (`-n 8 --maxprocesses=8`, DB `olspillet_e15`): 3448 passed; ruff check and format clean.
- Frontend: typecheck ok; Vitest 1127 passed; `lint:colours`, `check:copy` passed; `next build` compiled.
- Playwright (`--workers=4`, stack on `olspillet_e15stack`): `admin-evaluation`, `admin-audit`, `admin-institutions`, `admin-delete`, `homes`, `order-field`, `playout` — 50 passed; axe at 320 and 1440 px in `admin-evaluation`. Screenshots at 360 and 1440 px checked: one column on phone, tables become labelled blocks, one primary button.
- Matrix: every row is covered by `test_evaluation_export.py` (first export, same key, changed key, no agreement, Lecturer, short key, empty and 21 sessions, test Game).
- New slow tests: `test_an_agreed_export_gives_each_student_one_pseudonym_and_no_name` about 3.7 s (a started Class game played two Weeks, a Takeover, a test Game played out, three exports); `test_a_changed_key_is_refused_until_the_fingerprint_is_replaced` and `test_without_an_agreement_or_as_a_lecturer_nothing_is_read` about 1 s each.

**Residual risks.**
- The key holder's separation from the founder is organisational; any Admin can type or replace a key (audited).
- Explanations are exported as written and can name people (stated on the page and in the manifest).
- The export is built in memory per request (bounded by 20 Class sessions).
