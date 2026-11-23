---
title: 'Story 13.14: Export the Completion status'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '2f275f4ee947b496eacd96c373ed0f1917ff690b'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-13-download-all-student-reports-as-one-zip.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer must approve the course requirement in the course's own system, but the Completion status of a Class session can only be read Student by Student on the Studentside (FR-60).

**Approach:** In the Klasseøkt's «Eksport» block, «Last ned fullføringsliste (CSV eller Excel)» opens a choice of two downloads (CSV, Excel .xlsx). One GET route builds the file at request time from `reports.service.completion_status` for every Student in `reporting_students()`, names and emails from `identity.service`, and streams it without storing it.

## Boundaries & Constraints

**Always:**
- New Class action `completion.export`: account role Lecturer, staff role owner only. An Assistant lecturer, another Class's staff, an Admin without a staff role, a Student and an unknown Class session get one 403 `forbidden`.
- Fixed column allow-list `COLUMNS` (order fixed; a test asserts it equal to a literal tuple and that no header names AI/KI, score, feedback or letter): Navn, E-post, Klassespill, Debrief, Quiz, Replay, Individuell test (each: the Oslo date the step was done), Bestilte uker (%), Kravet (%), Utspilling (%), Oppfølgingsspill (date given), Rettet av faglærer (Ja/Nei), Krav oppfylt (Ja/Nei/«Ikke obligatorisk»).
- Every status value comes from one `completion_status` per Student (the share figures, the required share, `done`, `corrected`, `requirement_met`), so the file agrees with the Studentside. A step not done reads «ikke gjort»; a step done without a recorded date (a correction) reads «gjort».
- Names and emails read at export time through a new `identity.service.student_contacts(class_id, ids)` (Students of the Class now only); rows sorted by name in Norwegian order (`nb_sort_key`).
- CSV: UTF-8 with BOM, `;` separator, CRLF, dates `dd.mm.yyyy`, numbers with a decimal comma. Excel: real date cells (`dd.mm.yyyy`) and number cells; every text cell written as text.
- A text cell starting with `=`, `+`, `-`, `@`, tab or CR is prefixed with `'` in the CSV, and stored as a string (never a formula) in the .xlsx.
- `Content-Disposition: attachment`, file name `fullforingsliste-klasseokt-<n>.csv|.xlsx` (no person's name), `Cache-Control: no-store`; nothing written to storage or the database apart from one audit row `completion_export.downloaded` (target Class session, change `{format}`).
- The block shows the action and the note «Ingen av filene har KI-vurderinger.» only when the read of the ZIP state says `completion_export: true` (the caller holds `completion.export`); an Assistant lecturer sees only the ZIP part.

**Never:** no AI score, AI feedback or Indicative letter, nor any column outside the allow-list; no stored copy of the file; no new table or migration; no change to the ZIP job or the single report; no Game data export (FR-88, later); no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| CSV | Lecturer, 2 Students, one with every step | 200 `text/csv; charset=utf-8`, BOM, header + 2 rows | — |
| Excel | `format=xlsx` | 200 xlsx; openpyxl reads the same rows, dates as dates | — |
| Not obligatory | session not obligatory | Krav oppfylt «Ikke obligatorisk» | — |
| Corrected | a step corrected done | date «gjort» or its date, Rettet av faglærer «Ja» | — |
| Playout | Weeks played out | Utspilling (%) holds the share | — |
| Make-up | an Oppfølgingsspill given | its column holds the date given | — |
| Formula-like name | name `=HYPERLINK(...)` | CSV `'=HYPERLINK(...)`; xlsx string cell | — |
| No Students | none in scope | header only | — |
| Assistant / outsider | Assistant, other Lecturer, Admin w/o role, Student, bad id | — | 403 `forbidden`, no audit row |
| Bad format | `format=pdf` | — | 422 (query validation) |
| Deleted | deletion date has come | — | 409 `data_deleted` |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py:175,226` -- add `completion.export` to the account-role map (LECTURER) and `CLASS_STAFF_ROLES` (OWNER), beside `completion.correct`.
- `backend/app/modules/identity/repo.py:1100` `student_names` -- add `student_contacts` (id, name, email) with the same Roster filter; `identity/service.py:2281` -- `student_contacts` returning `Person`.
- `backend/app/modules/reports/service.py` -- add `completion_statuses(class_session_id, session)`: `{user_id: CompletionStatus}` over `scope.reporting_students` via `_status` (as `requirement_not_met` does), reading the scope once.
- `backend/app/modules/reports/completion_export.py` (new) -- `EXPORT`, `COLUMNS`, `export_rows(user, class_session_id)` (None → 403; `ReportRefused("data_deleted")`), pure `row_values(status, contact, makeup_at)`, `to_csv(rows) -> Iterator[bytes]`, `to_xlsx(rows) -> bytes`, `file_name(number, fmt)`. Reuses `sessions.staff_session_row`, `sessions.data_deleted`, `sessions.report_heading` (number), `sessions.class_id_of`, `repo.makeup_of`, `audit.record`, `OSLO` dates (`sessions.dates` / `zoneinfo`).
- `backend/app/modules/reports/routes.py` -- `GET /class-sessions/{session_id}/completion-export?format=csv|xlsx`, `operation_id="downloadCompletionExport"`, `StreamingResponse`; `_zip_state` adds `completion_export`.
- `backend/app/modules/reports/bundle.py:79` `ZipState`, `schemas.py` `ZipStateOut` -- `completion_export: bool` (`sessions.class_staff_may(user, id, EXPORT)`).
- `backend/app/modules/reports/README.md` -- a «Completion export» section.
- `frontend/src/modules/reports/api.ts:254` -- `completionExportPath(sessionId, format)`.
- `frontend/src/modules/reports/export-block.tsx` -- the action (a disclosure button with `aria-expanded`/`aria-controls` revealing two download links) and the note, when `state.completion_export` and not `deleted`.
- `frontend/src/copy/nb.ts:4296` -- `reports.export.completion` (spine strings verbatim, the rest `[ASSUMPTION]` draft).
- Tests: `backend/tests/reports/test_completion_export.py` (reuse `test_corrections` imports: `short_game`, `obligatory`, `every_later_step`, `play_weeks`, `call`, `ASSISTANT`, `put_staff`, `ADMIN`, `OTHER_LECTURER`, `email`); existing ZIP state tests in `test_reports_zip.py` assert the state dict (add the field); `frontend/src/modules/reports/export-block.test.tsx`; e2e `frontend/e2e/class-session-export.spec.ts`.

## Tasks & Acceptance

**Execution:**
- authz, identity repo/service -- the action and the contact read.
- `reports/service.py`, `completion_export.py`, routes, schemas, bundle state, README; `npm run api:generate`.
- `backend/tests/reports/test_completion_export.py` -- matrix rows; column allow-list; agreement with `completion_status` and the Studentside record; both formats decoded with æøå, dates and decimal comma; formula guard; no storage object and one audit row.
- frontend api, block, copy; Vitest for the block with and without `completion_export`.
- e2e: on a fresh Class session the Lecturer opens the choice and downloads both files (CSV begins with BOM and the header; xlsx begins `PK`); an Assistant lecturer sees no completion action; axe at each width.

**Acceptance Criteria:**
- Given a Lecturer of the Class on the Klasseøkt, when the «Eksport» block shows, then it has «Last ned fullføringsliste (CSV eller Excel)» and «Ingen av filene har KI-vurderinger.»; pressing it offers CSV and Excel, each a download.
- Given the file, then it has one row per Student in `reporting_students()` with exactly the allow-listed columns, values agreeing with the Studentside's Completion status.
- Given an Assistant lecturer, then the block shows only the ZIP part and the endpoint answers 403.
- Given the block at 320 px and 200 % text, then it reflows and axe reports no violations.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 36 findings — high 0, medium 3, low 21, false 8, maybe-false 4
- findings:
  - `[low]` `[reject]` Blind: a Student in scope without a Roster contact gets a blank row — `reporting_students` and `student_contacts` read the same Roster (registered, not removed); only a removal between two reads in one request reaches it, and the row still carries the status.
  - `[medium]` `[patch]` Blind: the Oppfølgingsspill column ran only against a fake `repo` — the test now inserts a real `makeup_games` row (and a `makeup` Game) and asserts its date in both formats.
  - `[low]` `[reject]` Blind: `makeup_of` once per Student (N+1) — `completion_status` itself reads per Student by design (the one assembler); one more indexed read per Student is negligible at 250.
  - `[low]` `[reject]` Blind: the CSV apostrophe changes the value for a name beginning with `+`/`-`/`@` — the OWASP CSV-injection guard; Excel shows the text without the apostrophe as a text prefix; the .xlsx keeps the raw text as a string cell. `\n` added to the prefixes (patch below).
  - `[false]` `[reject]` Blind: float formatting inconsistent — no float reaches the file: the shares are `int` (`CompletionStatus`), the float branch only formats the comma.
  - `[medium]` `[patch]` Blind: the audit row is written before the file is built, without a count — the body is now built first, then `record_download` writes `{format, students}`; tests updated.
  - `[low]` `[reject]` Blind: a refused download (403/409 after the page loaded) saves a JSON body — the same plain-link pattern as the ZIP and the single report (13.12/13.13); only reachable when the deletion date passes with the page open.
  - `[medium]` `[patch]` Blind: unrelated Prettier reformatting in `api.ts`, `export-block*.tsx`, the e2e spec — reverted; the four files now carry only this story's lines (92 lines instead of 262).
  - `[low]` `[reject]` Blind: the flag on `ZipStateOut` couples two features and costs a policy read per poll — the poll runs only while a ZIP is pending; a separate read would be a second request for one bool (Design Notes).
  - `[false]` `[reject]` Blind: tap-target height not met — `LINK` already has `min-h-tap-target-min`; axe and the reflow check pass at every width.
  - `[low]` `[reject]` Blind: no Escape or focus management in the disclosure — a native button with `aria-expanded`; the links follow it in tab order; same pattern as `archive-class.tsx`.
  - `[low]` `[reject]` Blind: draft copy without an issue — marked `[ASSUMPTION]` as the project convention for draft copy; listed in the report.
  - `[low]` `[reject]` Blind: the banned-word test is weak — the column tuple is compared with a literal first; the word list is a second guard only.
  - `[false]` `[reject]` Blind: docstring "one row per Student reports count" garbled — the module's own idiom («the Students reports count»); "owners" is the staff role of Lecturers.
  - `[low]` `[reject]` Blind: `format` shadows the builtin — the query parameter's public name; local to the handler.
  - `[low]` `[patch]` Blind: `StreamingResponse` gives no benefit over built rows — now one `Response` with the built body (and a Content-Length), see the audit patch.
  - `[low]` `[patch]` Blind: meaningless `assert seated` — removed.
  - `[false]` `[reject]` Blind: fixtures re-exported through `__all__` — the suite's pattern for pytest fixtures (as `test_reports_zip.py`).
  - `[false]` `[reject]` Blind: regenerated client missing — regenerated with `npm run api:generate` and left out of the review diff on purpose; typecheck passes.
  - `[low]` `[patch]` Edge: `\n` missing from the formula prefixes — added; the e-mail part of the claim as Blind's apostrophe row (rejected).
  - `[false]` `[reject]` Edge: floats with more decimals or NaN — no float reaches the file (see above).
  - `[medium]` `[patch]` Edge: audit before build — same patch as Blind's row.
  - `[low]` `[reject]` Edge: missing Roster contact — as Blind's row.
  - `[low]` `[reject]` Edge: N+1 reads — as Blind's row.
  - `[low]` `[reject]` Edge: link after expiry/deletion saves an error body — as Blind's row.
  - `[low]` `[reject]` Edge (claim): the spec's e2e line promises an Assistant lecturer check the spec does not run — the Assistant's view is pinned by Vitest (`completion_export: false`) and the api by `test_only_the_lecturers_of_the_class_may_export_and_the_block_says_so` (403 and the flag false); an Assistant in e2e needs an Invitation flow for a fresh Class. Recorded as a residual gap.
  - `[medium]` `[patch]` Verification: the POST answer's `completion_export` never asserted — `test_reports_zip.py` now asserts it True for the Lecturer and False for the Assistant lecturer.
  - `[low]` `[patch]` Verification: only «=» of the formula guard tested — `test_every_text_a_spreadsheet_reads_as_a_formula_is_written_as_text_in_the_csv` covers all seven prefixes and an ordinary name.
  - `[medium]` `[patch]` Verification: the real Oppfølgingsspill read only ran with no rows — same patch as Blind's row.
  - `[low]` `[reject]` Verification (other): the guard alters fixed values and e-mails — fixed values never begin with a prefix character; e-mails as Blind's row.
  - `[maybe-false]` `[reject]` Intent: the decimal comma never occurs in real output — the shares are whole percents to agree with the Studentside (Design Notes); the CSV formatter is tested with a decimal, the .xlsx holds number cells Excel shows in the reader's locale. At most low.
  - `[maybe-false]` `[reject]` Intent: the make-up date not from `completion_status` — `CompletionStatus` holds no date of the Oppfølgingsspill; the status values (shares, done, met) all come from it. At most low.
  - `[low]` `[reject]` Intent: missing Roster contact — as Blind's row.
  - `[maybe-false]` `[reject]` Intent: browser behaviour of refused links and the toggle only in e2e — the e2e ran and passed; refused links as Blind's row. At most low.
  - `[low]` `[reject]` Intent: the guard changes `+`/`-` texts — as Blind's row.
  - `[maybe-false]` `[reject]` Intent: the allow-list test guards the header only — values come from the one assembler, which holds no AI input (`analysis.completion`, AD-1). At most low.

## Design Notes

Shares are whole percents rounded down, as the Studentside shows them («Bestilte i 70 % av ukene»), so the file agrees with it (AD-16); a number cell is still a number, so Excel shows it in the reader's locale, and the CSV formats numbers with a comma for Norwegian Excel. The format choice is a disclosure rather than two buttons from the start, to keep the spine's one action label. The make-up column holds the date the Oppfølgingsspill was given [ASSUMPTION]; whether it counted shows in the share and «Krav oppfylt». The ZIP state read carries `completion_export` so the block needs no second request to know whether to offer it.

## Verification

**Commands:**
- `uv run pytest tests/reports tests/identity -n 8` -- pass
- `npm run typecheck && npx vitest run src/modules/reports && npm run check:copy && npm run lint:colours` -- pass
- `npx playwright test e2e/class-session-export.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary:** The Klasseøkt's «Eksport» block offers the Lecturers of the Class «Last ned fullføringsliste (CSV eller Excel)», a disclosure with two download links (CSV, Excel .xlsx) and the note «Ingen av filene har KI-vurderinger.». `GET /api/class-sessions/{id}/completion-export?format=csv|xlsx` (new Class action `completion.export`, owners only) builds one row per Student in `reporting_students()` from `reports.service.completion_statuses` (the one assembler per Student), names and e-mails from `identity.service.student_contacts` at download time, and sends the file without storing it. The columns are the fixed allow-list `COLUMNS`: name, e-mail, the Oslo date of each of the five steps («ikke gjort» / «gjort»), ordered share, required share, playout share, the date the Oppfølgingsspill was given, «Rettet av faglærer», «Krav oppfylt». CSV: UTF-8 with BOM, `;`, CRLF, `dd.mm.yyyy`, decimal comma, formula-like text prefixed with `'`; .xlsx: date and number cells, all text as string cells. One audit row `completion_export.downloaded` (format, number of Students). Assistant lecturers get 403 and see only the ZIP part (`ZipStateOut.completion_export`). The implementation ran in the builder's own context, as the orchestrator directed, not in a separate subagent. No migration and no new table.

**Files:**
- `backend/app/modules/reports/completion_export.py` (new): the columns, the rows, CSV and .xlsx writers, the audit.
- `backend/app/modules/reports/routes.py`: `downloadCompletionExport`; the ZIP state carries `completion_export`.
- `backend/app/modules/reports/service.py`: `completion_statuses`.
- `backend/app/modules/reports/bundle.py`, `schemas.py`: `completion_export` on `ZipState`/`ZipStateOut`.
- `backend/app/modules/identity/repo.py`, `service.py`: `student_contacts`.
- `backend/app/platform/authz.py`: `completion.export` (Lecturer / owner).
- `backend/app/modules/reports/README.md`: the section.
- Frontend: `export-block.tsx`, `api.ts` (`completionExportPath`), `nb.ts` (spine strings; `choose`, `csv`, `xlsx` draft), regenerated client.
- Tests: `backend/tests/reports/test_completion_export.py` (7), `test_reports_zip.py` (the flag in GET and POST), `export-block.test.tsx` (+2), e2e `class-session-export.spec.ts` (both downloads, axe per width with the choice open).

**Review:** four layers, 36 findings (see the triage log). Patched: 4 medium (audit after the file is built, with a count; unrelated Prettier churn reverted; the POST flag asserted; the Oppfølgingsspill column tested on a real row) and 4 low (a newline in the formula prefixes and a test of all prefixes; one `Response`; a stray assert). Deferred: none. Rejected with reasons in the log.

**Follow-up review recommended:** true (4 medium patched). Unverified risk: the Assistant lecturer's view is checked by Vitest and the api only, not in e2e; and the reverted frontend files were re-applied by script, reviewed only by the author.

**Verification:**
- Backend: full suite 4043 passed (`-n 8 --maxprocesses=8`, 3 min 52 s); ruff passes.
- Frontend: typecheck, Vitest (1286), `check:copy`, `lint:colours` pass; the frontend image built.
- Playwright `--workers=4`: 172 passed (every `class-session*` spec, homes, order-confirm, guided-week, chain-band); axe and reflow per width in the export spec.
- New tests over 1 s: the two played-out export tests (about 3–4 s each, from the `_played_out` fixture) and the two others (about 1.5 s).

**Residual risks:**
- A Student removed from the Roster between the scope read and the contact read in one request gets a row with no name or e-mail.
- A download link pressed after the deletion date passed with the page open saves the 409 body as a file (the same pattern as the ZIP).
- The CSV apostrophe guard changes a name or address that begins with `+`, `-` or `@`; the .xlsx keeps it unchanged.
- Decisions taken without the founder: the make-up column holds the date given; shares are whole percents rounded down (as the Studentside); «Kravet (%)» is an extra column; the format choice is a disclosure; no `no_students` refusal (an empty file has the header).
- New personal data: no new table. The file holds names and e-mails but is never stored.


## Epic 13 close-out: follow-up review

Access, formula-injection guards, BOM/CRLF and scope are clean. Added the promised e2e check: an Assistant lecturer of the Class sees the ZIP but not the Completion export, and the export route answers 403 (`class-session-export.spec.ts`).
