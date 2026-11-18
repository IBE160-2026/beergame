---
title: 'Story 4.2: Upload a Roster file and pick the e-mail column'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '62f6f74d3693eacf0101a7f6d65c3871ff32a27f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer who owns a Class has no way to bring in the student list: there is no upload, no staging and no way to say which column holds the addresses, so a Canvas export would have to be edited by hand.

**Approach:** Add Roster upload staging in `identity` (tables `roster_uploads`, `roster_upload_rows`, in-memory .xlsx/.csv parsing, expiry purge), Class-scoped routes in `classes` that reach it only through `identity.service`, and on the Class page the Filopplasting box with file name, «N rader lest», «Bytt fil», the «E-postkolonne» select with its reason, and a short preview of the file.

## Boundaries & Constraints

**Always:**
- The file is parsed in memory and never written to disk or a bucket; only cell values are staged, in `identity` tables reached through `identity.service` (AD-14). `identity` imports nothing from `classes`.
- One staged upload per Class: a new upload replaces the old one in one transaction; a refused upload leaves the earlier staging untouched and stages nothing new.
- `identity.service.purge_expired_roster_uploads(now)` is idempotent and runs on every upload and every staging read; an upload whose `expires_at <= now` is never returned. `now` is the api's clock.
- Logs, job args and audit rows hold ids and counts only — never file names, cells or addresses.
- Limits are configuration: `ROSTER_MAX_FILE_MB` (placeholder 5), `ROSTER_MAX_ROWS` (placeholder 5000), `ROSTER_STAGING_TTL_HOURS` (placeholder 24). The body is read with a hard cap, never unbounded.
- Every new route declares a policy (`classes.manage`, owner only via `CLASS_STAFF_ROLES`); a Class outside the User's scope gives the same 403 `forbidden` as an unknown one.
- UI copy only in `nb.ts`; reuse `SelectField`, `Button`, `Link`, `ActionError` patterns; errors and result lines clear when a new action starts.
- New dependency `openpyxl==3.1.5` (2024-06-28), with `et-xmlfile==2.0.0`, pinned exactly.

**Never:** address validation reasons, invalid-row list, paste staging (Story 4.3); Roster table, Invitations, Send button (4.4); archive checks (4.10); reading real Canvas exports; comparing DB time with host time or ordering by timestamps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Canvas people .xlsx | fixture: Name, Login ID, SIS User ID, E-post, Section; 12 rows | 201; row_count 12; columns A–E with headers; suggested/chosen D, reason «alle rader» | – |
| Canvas grade-book .csv | fixture: Student, ID, SIS User ID, SIS Login ID (addresses), Section, assignments; a «Points Possible» row | 201; chosen = SIS Login ID column; reason «alle rader unntatt én» | – |
| Semicolon CSV, Windows-1252 | `Navn;E-post` with «Ørjan» in cp1252 | parsed with `;`, «Ørjan» intact | – |
| No header row | first row holds an address | every row is data; columns labelled by letter only («Kolonne B») | – |
| No e-mail column | no cell looks like an address | 201; `suggested_column` null, chosen null; page says so and points to «Lim inn adresser i stedet» | – |
| Choose column | PUT column index | chosen stored; answer re-evaluated from staged cells (address count of that column) | out-of-range → 422 `invalid_request`, `fields.column = column_unknown` |
| Unreadable | empty, header only, binary garbage, .pdf/.txt, broken .xlsx, > max MB, > max rows | 422 `roster_unreadable`; nothing staged, earlier staging kept | page: «Filen kunne ikke leses. Bruk .xlsx eller .csv, eller lim inn adressene.» |
| Replace | second upload for same Class | only the second staging exists | – |
| «Bytt fil» | DELETE | 204; GET then returns `upload: null` | – |
| Expired | staging with `expires_at` in 2000 | GET → `upload: null`, rows purged; column PUT → 404 `not_found` | – |
| Scope | other Lecturer / unknown Class / non-Lecturer | 403 `forbidden`, nothing staged | – |

</intent-contract>

## Code Map

- `backend/app/modules/classes/routes.py` -- route/`error_response`/`documented` pattern; class id parsing → `authz.Forbidden`. Add the four roster-upload routes after `/{class_id}`.
- `backend/app/modules/classes/service.py` -- `get_class`, `_StaffOf`, `authz.can(user, action, resource)`. Add a `_managed(user, class_id)` check with `classes.manage`, then delegate to `identity.service`.
- `backend/app/modules/identity/models.py` -- table style (`metadata`, CheckConstraint). Add `roster_uploads`, `roster_upload_rows` (FK by name to `classes.id`, CASCADE).
- `backend/app/modules/identity/schemas.py:246` -- `email_is_valid`: the shape check used to judge "looks like an address" in 4.2 (4.3 adds reasons).
- `backend/app/modules/identity/service.py` / `repo.py` -- public functions other modules call; add staging functions.
- `backend/app/platform/config.py` -- `Settings`; add the three `roster_*` fields.
- `backend/migrations/versions/0023_classes.py` -- migration style; new `0024_roster_uploads.py`.
- `backend/tests/conftest.py:129` `IDENTITY_TABLES`; `tests/test_migrations.py` HEAD/HEAD_TABLES; `tests/classes/test_classes.py` + `tests/identity/helpers.py` for api tests.
- `frontend/src/modules/classes/{class-page.tsx,api.ts}` -- Class page and hooks to extend; `frontend/src/components/select-field.tsx` (`hint`).
- `frontend/src/lib/api/{client.ts,mutation.ts}` -- `api`, CSRF middleware, `request`, `useAction`.
- `frontend/e2e/classes.spec.ts` -- `freshLecturer`, `expectAccessible`, viewports.
- No `platform/storage` exists; none is needed since the file is never stored.

## Tasks & Acceptance

**Execution:**
- `backend/pyproject.toml`, `uv.lock` -- add `openpyxl==3.1.5`, `et-xmlfile==2.0.0`.
- `backend/app/platform/config.py` -- `roster_max_file_mb`, `roster_max_rows`, `roster_staging_ttl_hours`.
- `backend/migrations/versions/0024_roster_uploads.py`, `backend/app/modules/identity/models.py` -- `roster_uploads` (id, class_id UNIQUE FK classes CASCADE, uploaded_by FK users CASCADE, file_name, headers JSONB, has_header, column_count, row_count, chosen_column NULL, created_at, expires_at) and `roster_upload_rows` (upload_id FK CASCADE, row_number, cells JSONB; PK upload_id+row_number).
- `backend/app/modules/identity/roster_file.py` -- pure parser: type by name + content, CSV encoding/delimiter detection, xlsx read-only, header detection, limits, `RosterUnreadable`; column letters; suggestion and reason data.
- `backend/app/modules/identity/{repo,service,schemas}.py` -- `stage_roster_upload`, `roster_upload`, `choose_roster_column`, `delete_roster_upload`, `purge_expired_roster_uploads`, `RosterUploadOut`.
- `backend/app/modules/classes/{service,routes}.py` -- `POST/GET/DELETE /api/classes/{class_id}/roster-upload`, `PUT /api/classes/{class_id}/roster-upload/column`; raw body upload with `X-File-Name` (URL-encoded) and a capped read.
- `backend/app/modules/classes/README.md` -- staging decision, open point on real Canvas exports.
- `backend/tests/classes/test_roster_upload.py` + `tests/identity/test_roster_file.py`, reading the fixtures under `frontend/e2e/fixtures/roster/` -- api tests for the matrix; parser unit tests.
- `frontend/src/modules/classes/{api.ts,roster-upload.tsx,roster.ts,roster.test.ts,class-page.tsx}`, `frontend/src/copy/nb.ts` -- UI and copy.
- `frontend/e2e/roster-upload.spec.ts` + `frontend/e2e/fixtures/roster/*` (shared with the api tests) + `frontend/e2e/support/classes.ts` (helpers moved out of `classes.spec.ts`) -- keyboard-only flow, axe at 320 px, 200 % text, 1440 px.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.

**Acceptance Criteria:**
- Given the Class page of a Class the Lecturer owns with no staging, then the Filopplasting box shows «Velg fil» and the link «Lim inn adresser i stedet», and the file input accepts .xlsx and .csv.
- Given a readable file is chosen, then the page shows its name, «N rader lest» with the real number and «Bytt fil», and «E-postkolonne» lists every column by letter and header with the suggested one preselected and its reason under it.
- Given another column is chosen, then the reason line updates from the api's re-evaluation without a new upload.
- Given an unreadable file, then the page shows «Filen kunne ikke leses. Bruk .xlsx eller .csv, eller lim inn adressene.», and the line clears when the next file is chosen.
- Given «Bytt fil» is pressed, then the staging is deleted and the empty box returns with focus on «Velg fil».
- Given a reload after upload, then the staging is shown again from the api.
- Given Playwright with axe, then the whole flow passes by keyboard only at 320 px, 200 % text and 1440 px with no page-level horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 37 findings — high 0, medium 6, low 19, false 12, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) Two uploads for one Class at once break `UNIQUE(class_id)` with a 500 — `repo.lock_roster_staging` takes a transaction-scoped advisory lock before the delete and insert; `test_two_uploads_at_once_leave_one_staging` added.
  - `[medium]` `[patch]` (blind) Parsing blocks the event loop — `parse` and `address_counts` now run through `asyncio.to_thread`.
  - `[low]` `[patch]` (blind) The whole body is read before ownership is checked — the route now checks `may_manage` first.
  - `[medium]` `[patch]` (blind) An xlsx with a far-away row makes read-only `iter_rows` walk every empty row — scanning stops at `(max_rows + 1) * 20` rows; unit test added.
  - `[false]` `[reject]` (blind) Every refusal shares one message — the story's AC requires exactly that line for the size limit too.
  - `[false]` `[reject]` (blind) «Bytt fil» deletes before a new file is picked — the AC says «Bytt fil» deletes the staged upload and returns to the empty box.
  - `[low]` `[reject]` (blind) The paste field does nothing — paste is Story 4.3's; the panel and its way back are this story's; recorded as a decision.
  - `[low]` `[patch]` (blind) Column answers can arrive out of order — only the latest choice's answer is stored, and `pending` clears only for it.
  - `[low]` `[patch]` (blind) `repo.roster_column_values` is unused — removed; recounting up to 5000 rows per read is cheap and stays.
  - `[false]` `[reject]` (blind) GET runs the purge as a write — the AC requires the purge on every staging read.
  - `[false]` `[reject]` (blind) The check and the write are in separate transactions — no Class delete or ownership change exists before 4.9/4.10; the lock fix covers the concurrent case.
  - `[low]` `[reject]` (blind) UTF-16 is not tried — the AC names UTF-8 and Windows-1252 only.
  - `[low]` `[patch]` (blind) The `identity` table has a foreign key to `classes` — recorded in the module README as the one deliberate tie; no code import.
  - `[low]` `[reject]` (blind) Dates read as ISO and uncached formulas read empty — not an e-mail concern, rare in Canvas exports.
  - `[low]` `[reject]` (blind) The grade-book «Points Possible» row counts as a row — it is a row of the file; Story 4.3 lists it as invalid with its number; skipping it needs a Canvas-specific rule.
  - `[low]` `[reject]` (blind) `roster_max_rows` and the TTL have no upper bound — operator configuration with sane placeholders.
  - `[low]` `[patch]` (blind) Missing tests — a streamed body with no Content-Length and concurrent uploads added; a Class deleted mid-request (no such path) and a failed column PUT in the UI (generic `ActionError`) rejected.
  - `[medium]` `[patch]` (edge) A UTF-8 BOM before bytes that are not UTF-8 gives a 500 — now refused as unreadable; unit test added.
  - `[low]` `[patch]` (edge) Cutting a long file name drops its extension — the stem is cut instead; test added.
  - `[medium]` `[patch]` (edge) Concurrent uploads give a 500 — same fix as the first blind row.
  - `[false]` `[reject]` (edge) A Class deleted between check and insert — no Class delete path exists.
  - `[low]` `[reject]` (edge) `ClientDisconnect` while streaming — the client is gone; only log noise.
  - `[low]` `[patch]` (edge) Out-of-order column answers — same fix as the blind row.
  - `[low]` `[patch]` (edge) A late column answer after «Bytt fil» restores the upload — «Bytt fil» clears the latest choice, so a late answer is ignored.
  - `[low]` `[patch]` (edge) Paste pressed while a file uploads — `startPaste` does nothing while the upload is pending.
  - `[low]` `[patch]` (edge) A quoted multi-line record stores its last line number — now its first; unit test added.
  - `[low]` `[patch]` (edge) `str.splitlines` splits the header on `\x0b` — lines are split as csv does; unit test added.
  - `[medium]` `[patch]` (verification-gap) The preview from GET and PUT is not asserted — assertions added to the column test.
  - `[medium]` `[patch]` (verification-gap) The streaming size cap never runs in a test — `test_a_streamed_file_over_the_size_limit_is_refused` added.
  - `[low]` `[patch]` (verification-gap) The access check on the early-refusal path is untested — the path now runs after the check; a nameless upload by another Lecturer added to the 403 test.
  - `[low]` `[patch]` (verification-gap) Batches over 1000 rows are untested — `test_more_rows_than_one_insert_batch_are_all_staged_and_evaluated` (1200 rows) added.
  - `[false]` `[reject]` (intent) The upload is on the Class page, not inside the «Lag Klasse» form — the AC is "«Lag Klasse» for a Class the Lecturer owns" and staging is keyed by Class id, so the Class must exist; «Lag Klasse» lands on the Class page (4.1), which holds the upload. Recorded as a decision.
  - `[false]` `[reject]` (intent) Filopplasting is not a shared component — one consumer; module-local until a second appears.
  - `[false]` `[reject]` (intent) The decision is only in `classes/README.md` — it is also in this spec (the story's notes), which is committed.
  - `[false]` `[reject]` (intent) The grade-book and paste e2e run at 1440 px only — the NFR-6 matrix runs the main flow at all three viewports.
  - `[false]` `[reject]` (intent) «Lim inn adresser i stedet» is a `<button>` — it opens a panel and never navigates, which the Lenke rule allows; it looks like a link.
  - `[false]` `[reject]` (intent) The row count includes «Points Possible» — same reading as the blind row.

## Design Notes

- Header rule: the first non-empty row is a header unless one of its cells looks like an address. Empty rows are skipped; `row_number` is the row's number in the file, so 4.3 can name it. `row_count` counts data rows.
- Suggestion: the column with the largest share of address-looking cells among data rows (leftmost on a tie); none when no cell matches. Reason (web, from counts): all → «Valgt fordi alle rader ser ut som adresser.»; ≥ half → «… alle rader unntatt fire …» (number words to twelve); fewer → «Valgt fordi 3 av 250 rader ser ut som adresser.» A chosen (not suggested) column shows «N av M rader ser ut som adresser.».
- CSV decode: UTF-8 BOM → utf-8-sig; else strict UTF-8; else cp1252; a NUL char → unreadable. Delimiter: the one of `,` `;` `\t` most frequent in the first line outside quotes; tie → `,`.
- Caps: 200 columns, 1000 chars per cell (longer cells truncated), rows stop at `ROSTER_MAX_ROWS + 1` → unreadable.
- The upload lives on the Class page under «Klasseliste» (4.1 sends the Lecturer there after «Lag Klasse»).
- «Lim inn adresser i stedet» opens a multi-line Tekstfelt panel with «Velg fil i stedet»; its continue action is Story 4.3's.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes tests/identity/test_roster_file.py tests/test_migrations.py tests/test_authz_rules.py -q` -- pass.
- `cd backend && uv run pytest -q` and `uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt compose stack -- pass.

## Auto Run Result

Status: done

**Summary.** Story 4.2 is built. The owner of a Class uploads a .xlsx or .csv Roster on the Class page («Klasseliste»). The api reads the file in memory and never stores it. It stages the cell values in the new `identity` tables `roster_uploads` and `roster_upload_rows` (migration 0024), with expiry `ROSTER_STAGING_TTL_HOURS` and a purge on every upload and read. It preselects the column with the most address-shaped cells and gives the reason. A column change is evaluated again from the staged cells. «Bytt fil» deletes the staging. Unreadable files answer 422 `roster_unreadable` and stage nothing.

**Process note.** As in 4.1, the caller required the implementation to run in the orchestrating context, not in an implementation subagent. The four review layers ran as subagents, and their reports were read from their transcripts.

**Files changed**
- `backend/pyproject.toml`, `uv.lock`: `openpyxl==3.1.5`, `et-xmlfile==2.0.0`.
- `backend/app/platform/config.py`: `roster_max_file_mb` (5), `roster_max_rows` (5000), `roster_staging_ttl_hours` (24).
- `backend/migrations/versions/0024_roster_uploads.py`, `backend/app/modules/identity/models.py`: the staging tables.
- `backend/app/modules/identity/roster_file.py`: the in-memory parser.
- `backend/app/modules/identity/{repo,service,schemas}.py`: staging, purge, column choice and the advisory lock.
- `backend/app/modules/classes/{service,routes}.py`: four routes under `/api/classes/{id}/roster-upload`, with an owner check and a capped body.
- `backend/app/modules/classes/README.md`: the staging decision and the open point on real Canvas exports.
- `backend/tests/classes/test_roster_upload.py`, `backend/tests/identity/test_roster_file.py`: new. `tests/test_migrations.py` and `tests/conftest.py` updated.
- `frontend/src/modules/classes/{roster-upload.tsx,roster.ts,roster.test.ts,api.ts,class-page.tsx}`, `frontend/src/copy/nb.ts`, `frontend/src/components/button.tsx` (`ref`): the UI.
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `frontend/e2e/roster-upload.spec.ts`, `frontend/e2e/support/classes.ts` (helpers moved out of `classes.spec.ts`), `frontend/e2e/fixtures/roster/*`: synthetic fixtures, shared with the api tests.

**Review findings.** 37 findings.
- Patched: 6 medium and 13 low.
- Deferred: none.
- Rejected: 6 low and 12 false, each with its reason in the Review Triage Log.

**Follow-up review recommended: false.** Six medium entries were patched, and each one has its own new test, which passes. No specific unverified risk remains.

**Verification**
- Backend: `ruff check` and `format` are clean. The full `pytest` suite passed: 2042 tests in about 70 s.
  - One timing test, `tests/players/test_rescue.py`, failed once while Docker was rebuilding and passed on rerun. It is unrelated to this story.
  - No new test takes over 1 s; the slowest takes 0.36 s.
- Frontend: `typecheck`, `npm test` (341), `check:copy`, `lint:colours` and `build` all pass. Playwright passes 135 tests against the rebuilt compose stack. The roster flow also passed three repeats in a row.
- Shared test databases: revision 0024 was added and migrated. It was not changed after it ran.
- Checks that would otherwise fall to the founder were done by the independent review layers above. The check against real Canvas exports stays open for the founder (see the module README).

**Decisions taken in place of the founder**
- The upload lives on the Class page under «Klasseliste»; «Lag Klasse» lands there after a create. Only the owner sees it.
- Placeholder limits: 5 MB, 5000 rows and 24 h staging.
  - A workbook that unpacks to more than 200 MB is refused.
  - Columns beyond 200 are dropped.
  - Cells are cut to 1000 characters.
- Header rule: the first non-empty row is the header unless it holds an address. Empty rows are skipped, and rows keep their file numbers. «Points Possible» counts as a row.
- Transport: the file is the raw body with `X-File-Name`, so no multipart dependency is needed.
- Copy ([ASSUMPTION]):
  - «Klasseliste», the lead and «Canvas-eksport».
  - The line naming the accepted file types.
  - The reason wording for other shares, with counts as words up to twelve.
  - The no-column line and the failure lines.
  - The preview texts. The five-row preview follows the mockup.
- «Lim inn adresser i stedet» opens the multi-line field with «Velg fil i stedet». Continuing from it is Story 4.3's.
- A refused file keeps the earlier staging.

**Residual risks**
- Real Canvas exports are untested (open point for the founder).
- The paste panel has no continue action until Story 4.3.
