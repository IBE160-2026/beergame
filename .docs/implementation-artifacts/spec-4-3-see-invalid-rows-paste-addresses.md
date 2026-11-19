---
title: 'Story 4.3: See invalid rows and paste addresses instead'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: 'd15604b612f552fc7d1a694e0341493e04f6b9d6'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** After Story 4.2 the Lecturer sees which column holds the addresses, but not which rows cannot be used or why, and the «Lim inn adresser i stedet» panel cannot be sent. Two visual defects from 4.2 remain (Issue #85): the chosen preview header reads «E-post (e-post)», and the reason for a column with no addresses is grey.

**Approach:** One address-validation function in `identity` gives each staged row a reason or none; the staging answer carries the valid count and the invalid rows (number, value, reason, first row for duplicates). A paste route splits pasted text into one-column rows staged in the same tables. The Class page shows «Ugyldige rader: N av M», one line per invalid row with «Registrer manuelt», the line «Ugyldige rader får ingen e-post før de er rettet.» and the primary «Send N Invitasjoner», unavailable when nothing is valid.

## Boundaries & Constraints

**Always:**
- One function `identity.schemas.address_problem(value) -> code | None` decides validity; `email_is_valid(v)` is `address_problem(v) is None`, so login, access-request and Roster agree. `identity.service` evaluates staged rows with it.
- Addresses compared trimmed and lower-cased; duplicates only among valid addresses; the first occurrence (lowest row number) is valid.
- Paste is staged in `roster_uploads`/`roster_upload_rows` (source `paste`, one column, no header), replacing any staging, through `classes.service` → `identity.service`; same limits (`ROSTER_MAX_ROWS`, text ≤ `ROSTER_MAX_FILE_MB`).
- Logs hold ids and counts only, never pasted text, cells or addresses.
- Reasons are text, never colour alone; copy in `nb.ts`; errors and result lines clear when a new action starts.

**Never:** sending Invitations or writing a Roster (4.4 — «Send N Invitasjoner» has no action yet); the «Registrer manuelt» form (4.8 — the link has no action yet); comparing against an existing Roster (no Roster table before 4.4); comparing DB time with host time or ordering by timestamps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Reasons | cells `a@stud`, `a(at)x.no`, `a@@x.no`, `a@b@x.no`, ``, `a b@x.no`, `@x.no` | `missing_domain`, `missing_at`, `two_at`, `two_at`, `empty`, `whitespace`, `missing_name` | – |
| Duplicate | rows 2 `Ola@X.no`, 5 ` ola@x.no ` | row 2 valid; row 5 `duplicate`, `first_row` 2 | – |
| Counts | 250 rows, 4 invalid | `valid_count` 246, 4 `invalid_rows` in row order | – |
| No column chosen | `chosen_column` null | `valid_count` 0, `invalid_rows` [] | – |
| Column change | PUT column | answer re-evaluated with the new column's reasons | – |
| Paste | `a@x.no, b@x.no;c@x.no\nOla Nordmann <d@x.no>  e@x.no` | 201; source `paste`; 5 one-column rows numbered 1–5, all valid | – |
| Paste quoted name | `"Nordmann, Ola" <d@x.no>` | one row `d@x.no` | – |
| Empty paste | `""` or only separators | 201; 0 rows; `valid_count` 0 | – |
| Paste too long | more tokens than `ROSTER_MAX_ROWS` or text over the byte cap | 422 `roster_paste_too_long`; earlier staging kept | page line under the field |
| Scope | other Lecturer / unknown Class | 403 `forbidden`, nothing staged | – |

</intent-contract>

## Code Map

- `backend/app/modules/identity/schemas.py:246` -- `email_is_valid`; add `address_problem`, reason codes, `RosterInvalidRow`, `source`/`valid_count`/`invalid_rows` on `RosterUploadOut`, `RosterPasteIn`.
- `backend/app/modules/identity/roster_file.py` -- `looks_like_address` (keep, via `email_is_valid`); add pure `split_paste(text)`.
- `backend/app/modules/identity/service.py:1304-1460` -- `stage_roster_upload`, `_roster_upload_out`, `_staged_out`, `choose_roster_column`; add `evaluate_roster_rows`, `stage_roster_paste`, `RosterPasteTooLong`.
- `backend/app/modules/identity/repo.py:724` -- `roster_rows` returns unordered cells; return `(row_number, cells)` ordered by row number (row order is a business key, not a timestamp). `insert_roster_upload` gains `source`.
- `backend/app/modules/identity/models.py`, new `backend/migrations/versions/0025_roster_upload_source.py` -- `source` text NOT NULL default `'file'`, CHECK in (`file`,`paste`).
- `backend/app/modules/classes/{service,routes}.py` -- `may_manage` pattern; add `POST /api/classes/{class_id}/roster-paste` (`classes.manage`).
- `backend/tests/classes/test_roster_upload.py` -- `klass`, `upload`, `settings_env` fixtures; add tests. `backend/tests/test_migrations.py:65` HEAD → 0025.
- `frontend/src/modules/classes/roster-upload.tsx` -- paste panel (line 138), `Preview` header suffix (line 326); `roster.ts` `columnReason`; `api.ts` add `pasteRoster`.
- `frontend/src/components/select-field.tsx` -- `error` prop gives the restordre style and `aria-invalid`.
- `frontend/src/copy/nb.ts:336` -- `classes.roster` copy; `previewChosen` becomes screen-reader text.
- `frontend/e2e/roster-upload.spec.ts` -- `classPage`, `tabTo`, `chooseFile`; fixtures in `frontend/e2e/fixtures/roster/`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0025_roster_upload_source.py`, `identity/models.py` -- add `source`.
- `identity/schemas.py` -- `address_problem` (order: empty, whitespace/control, no `@`, more than one `@`, empty name, domain not two non-empty labels), `email_is_valid` on it; response fields.
- `identity/roster_file.py` -- `split_paste`.
- `identity/repo.py`, `identity/service.py` -- ordered rows, evaluation, paste staging.
- `classes/service.py`, `classes/routes.py` -- paste route.
- `backend/tests/identity/test_roster_file.py`, `backend/tests/classes/test_roster_upload.py`, `backend/tests/test_migrations.py` -- matrix tests.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/modules/classes/{api.ts,roster.ts,roster.test.ts,roster-upload.tsx}`, `frontend/src/copy/nb.ts` -- invalid rows, send area, paste continue, Issue #85 fixes.
- `frontend/e2e/fixtures/roster/ugyldige-rader.csv`, `frontend/e2e/roster-upload.spec.ts` -- invalid-row and paste flows by keyboard, axe.
- `backend/app/modules/classes/README.md` -- validation and paste decisions.

**Acceptance Criteria:**
- Given a staged upload with a chosen column, then the page shows «Ugyldige rader: N av M» with the api's counts and one line per invalid row: row number, cell value and reason in text («Domene mangler», «Mangler @», «To @», «Tom celle», «Dublett av rad 12», …), each with «Registrer manuelt».
- Given valid rows, then the primary button reads «Send N Invitasjoner» (singular «Invitasjon» for one) and «Ugyldige rader får ingen e-post før de er rettet.» stands by it.
- Given no valid row (all invalid, no column, or empty paste), then the primary button is primary but unavailable (`aria-disabled`) and the page says there is no valid address to invite.
- Given the paste panel, when text is entered and «Fortsett» pressed, then the staging shows «Innlimte adresser», «N adresser lest», the same invalid-row list and send area, with no column select or preview; a refusal shows under the field and clears as the user types.
- Given a staged file, then the chosen column in the preview is marked by its tint and screen-reader text, with no visible suffix; given a chosen column with no address, its reason line is in the error style.
- Given Playwright with axe, then the invalid-row and paste flows pass by keyboard with no page-level horizontal scroll at 320 px, 200 % text and 1440 px.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 32 findings — high 0, medium 7, low 20, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) `classes/README.md` lacks the validation and paste decisions — section «Invalid rows and pasted addresses» added.
  - `[false]` `[reject]` (blind) `identity.RosterPasteTooLong` and friends may not be exported — `identity` is `identity.service` imported as a module; the names are module attributes, and the api tests reach the route and the 422.
  - `[medium]` `[patch]` (blind) Paste leftovers `<a@x.no`, `'a@x.no'`, `(a@x.no)`, `mailto:a@x.no` count as valid — `split_paste` strips brackets, quotes and `mailto:` around a piece; unit case added.
  - `[low]` `[patch]` (blind) `ola@x.no <ola@x.no>` gives a false duplicate — a name piece equal to the bracketed address is dropped; unit case added.
  - `[low]` `[patch]` (blind) «Rad»/«E-post i fila» make no sense for a paste — paste rows read «Nr.» and «Innlimt verdi».
  - `[medium]` `[patch]` (blind) The invalid-row list is unbounded (5000 list items and buttons) — the page draws the first 100 with «Viser de første 100 av N ugyldige radene.»; the heading counts all.
  - `[low]` `[patch]` (blind) Schema cap 5 Mi chars disagrees with a `ROSTER_MAX_FILE_MB` above 5 — schema cap raised to 50 MiB (the setting's maximum), so the service answers `roster_paste_too_long`.
  - `[low]` `[patch]` (blind) `split_paste` builds every piece before the row check — it takes `limit` and stops one piece past it; unit test added.
  - `[low]` `[patch]` (blind) `_staged_out` evaluates on the event loop — counts and evaluation run through `asyncio.to_thread`.
  - `[medium]` `[patch]` (blind) The "keeps the staging" test never checks the staging — a GET after both refusals asserts the earlier paste; the byte cap is now tested with multi-byte text.
  - `[low]` `[reject]` (blind) No api test reaches `missing_name`/`whitespace` — each reason is unit-tested on the one function the api calls; a pasted whitespace is a separator by design.
  - `[low]` `[patch]` (blind) A late column answer can overwrite a paste in the cache — a successful paste clears `latestColumn` and `pending`.
  - `[false]` `[reject]` (blind) A duplicate without `first_row` shows «rad 0» — `evaluate_roster_rows` is the only producer and always sets `first_row` for `duplicate`.
  - `[low]` `[patch]` (blind) The reason has no screen-reader label; the buttons do nothing — «Hva er galt:» added as sr-only text; the inactive «Registrer manuelt» and «Send» are the story's (forms and sending are 4.8 and 4.4).
  - `[medium]` `[patch]` (edge) A NUL in pasted text reaches JSONB and fails with a 500 — NUL is a separator; api and unit tests added.
  - `[low]` `[reject]` (edge) A piece over 1000 chars is cut silently — no address comes near 1000 characters; a reason for it adds a code for a case no Lecturer meets.
  - `[low]` `[reject]` (edge) Addresses over 254 chars count as valid — rare in a roster; a length reason would change the login check too; delivery failures surface as bounces (4.6).
  - `[low]` `[reject]` (edge) A quoted name holding `<…>` leaves junk rows — rare; the junk is listed as invalid, never mailed.
  - `[low]` `[reject]` (edge) A single-quoted name leaves `'Nordmann` as a row — rare; it is listed as invalid, never mailed.
  - `[medium]` `[patch]` (edge) Up to 5000 invalid rows in every response and on the page — grouped with the unbounded-list row: the page is capped; the api answer stays complete (a few hundred kB at the limit).
  - `[low]` `[reject]` (edge) While a column answer is pending, the list describes the old column — lasts one request; the answer replaces it.
  - `[false]` `[reject]` (edge) `first_row` null shows «rad 0» — same refutation as the blind row.
  - `[low]` `[patch]` (edge) The 1 s wall-clock bound may flake on a loaded machine — bound raised to 5 s (quadratic splitting would take minutes).
  - `[low]` `[patch]` (edge) Text over 5 MiB chars gets `invalid_request`, not `roster_paste_too_long` — same fix as the blind schema-cap row.
  - `[low]` `[patch]` (edge) README not updated — same fix as the blind README row.
  - `[medium]` `[patch]` (verification-gap) The paste refusal test never checks the earlier staging — same fix as the blind test row.
  - `[medium]` `[patch]` (verification-gap) The paste refusal line and its clearing are not exercised — e2e `a refused paste says so under the field and the line clears as the user types` added (422 faked with `page.route`).
  - `[low]` `[patch]` (verification-gap) `ck_roster_uploads_source` is not compared with `RosterSource` — entry added to `test_the_check_constraints_list_exactly_the_enum_values`.
  - `[false]` `[reject]` (intent) The validation function lives in `identity.schemas`, not `identity.service` — the story's "one validation function in `identity.service`" is met at module level: `identity.service.evaluate_roster_rows` applies `address_problem`, and no other check exists.
  - `[low]` `[reject]` (intent) The note sits under the button, not beside the list — mockup 02 puts it under the button, next to the list at 1440 px.
  - `[false]` `[reject]` (intent) «Registrer manuelt» is a button, not a link — it will open an in-place form (4.8, EXPERIENCE.md), not navigate; it looks like a link, as 4.2's «Lim inn adresser i stedet».
  - `[low]` `[reject]` (intent) The column tint is not asserted — checked on screenshots at 1440 and 320 px; the screen-reader marking is asserted.

## Design Notes

- Reason codes → copy: `empty` «Tom celle», `missing_at` «Mangler @», `two_at` «To @», `missing_name` «Mangler navn før @», `missing_domain` «Domene mangler», `whitespace` «Mellomrom i adressen», `duplicate` «Dublett av rad N».
- Paste split: first replace each `Name <addr>` (name may be quoted, contains no `@`, starts at a separator boundary) with ` addr `, then split on `[\s,;]+`, drop empty tokens; rows are numbered 1…n.
- Layout: the invalid-row list goes in the right column above the preview (mockup 02); at 320 px each row stacks (number + reason, value wrapping with `overflow-wrap:anywhere`, link). The send area sits under «E-postkolonne» in the left column.
- «Send N Invitasjoner» and «Registrer manuelt» render now and act from 4.4 and 4.8.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes/test_roster_upload.py tests/identity/test_roster_file.py tests/test_migrations.py -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt compose stack -- pass.

## Auto Run Result

Status: done

**Summary.** Story 4.3 is built. One check, `identity.schemas.address_problem`, gives each staged row a reason or none. `email_is_valid` is built on it. `identity.service.evaluate_roster_rows` applies it to the chosen column, and repeated addresses name their first row. The staging answer carries `source`, `valid_count` and `invalid_rows`. `POST /api/classes/{id}/roster-paste` stages pasted addresses in the same tables (`source = 'paste'`, migration 0025). The Class page shows «Ugyldige rader: N av M», one line per row with its reason in text and «Registrer manuelt», and the primary «Send N Invitasjoner». The button is unavailable, with «Ingen gyldige adresser å invitere.», when nothing is valid. The paste panel gets «Fortsett». Issue #85: the chosen preview column is marked by its tint plus screen-reader text, with no visible suffix. A chosen column with no address shows its reason in the error style with `aria-invalid`.

**Process note.** The caller required the implementation to run in the orchestrating context. The four review layers ran as sub-agents; their reports were read from their transcripts.

**Files changed**
- `backend/migrations/versions/0025_roster_upload_source.py`, `identity/models.py`: the `source` column and CHECK.
- `identity/schemas.py`: `AddressProblem`, `address_problem`, response fields, `RosterPasteIn`, `RosterPasteTooLong`.
- `identity/roster_file.py`: `split_paste`.
- `identity/repo.py`, `identity/service.py`: ordered rows, evaluation, paste staging.
- `classes/service.py`, `classes/routes.py`, `classes/README.md`: the paste route and the decisions.
- `backend/tests/classes/test_roster_upload.py`, `tests/identity/test_roster_file.py`, `tests/test_migrations.py`: tests.
- `frontend/src/modules/classes/{roster-upload.tsx,roster.ts,roster.test.ts,api.ts}`, `frontend/src/copy/nb.ts`: the UI and copy.
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `frontend/e2e/roster-upload.spec.ts`, `frontend/e2e/fixtures/roster/ugyldige-rader.csv`: e2e and the shared fixture.

**Review findings.** 32 findings: 7 medium, 20 low, 5 false.
- Patched: 7 medium and 13 low (grouped into 5 medium and 11 low entries).
- Deferred: none.
- Rejected: 7 low and 5 false, each with its reason in the Review Triage Log.

**Follow-up review recommended: true.** Five medium entries were patched. The named unverified risk: the 100-line cap on the invalid-row list has no test, and the api still returns every invalid row (up to `ROSTER_MAX_ROWS`).

**Verification**
- Backend: `ruff check` and `format` are clean. The full `pytest` suite passes (2077, about 75 s).
- Frontend: `typecheck`, `npm test` (344), `check:copy`, `lint:colours` and `build` pass. Playwright passes 139 against the rebuilt compose stack.
- No new test takes over 1 s.
- Shared test databases: revision 0025 was added and migrated. It was not changed after it ran.
- Checks that would otherwise fall to the founder were done by the independent review layers above.
- Layout was checked on screenshots at 1440 and 320 px. This found and fixed two problems: a horizontal scroll caused by the screen-reader text, and the sticky «Rad» header being overlapped by the chosen column's header.

**Decisions taken in place of the founder**
- «Send N Invitasjoner» and «Registrer manuelt» are drawn now and act from 4.4 and 4.8.
- An empty paste stages no rows, so the page shows the unavailable button and «Ingen gyldige adresser å invitere.»
- A paste is «Innlimte adresser» with «Start på nytt» and has no column select or preview. Its rows read «Nr.» and «Innlimt verdi».
- Reasons beyond the epic's four: «Mellomrom i adressen» and «Mangler navn før @». Two or more `@` read «To @».
- Duplicates count only among valid addresses.
- The «Navn» column from mockup 02 is not shown in the invalid-row list.
- The page lists at most 100 invalid rows.
- Pastes have the same size and row limits as files.
- Brackets, quotes and `mailto:` around a pasted piece are dropped.
- All new copy except the story's own wording is [ASSUMPTION].

**Residual risks**
- Real Canvas exports are still untested (open point from 4.2).
- The invalid-row cap is untested (see the follow-up recommendation).
