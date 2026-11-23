---
title: 'Story 14.8: Export a Class session''s Game data (cut list)'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'f51a95f56a07de0fcc382421b7ca31549d550dc0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-14-export-the-completion-status.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer who wants to analyse a Class session's games in their own tools has no way to get the week-by-week play out of the product (FR-88).

**Approach:** Behind `FEATURE_GAME_DATA_EXPORT`, the Klasseøkt's «Eksport» block (13.13/13.14) gets «Last ned spilldata (CSV)», a plain download of `GET /api/class-sessions/{id}/game-data-export`. The file has one row per Game, Week and Seat of the Decision log, for every Game `scope.reporting_games()` counts (Class games, make-up games, Replays), built at request time and streamed, never stored.

## Boundaries & Constraints

**Always:**
- Flag off: the route answers what an unknown route answers (FastAPI's plain 404 `{"detail":"Not Found"}`, before any policy or read), and `ZipStateOut.game_data_export` is false, so the block has no action.
- New action `game_data.export`: account role Lecturer; Class staff role owner only. An Assistant lecturer, another Class's Lecturer, an Admin without a staff role, a Student, an unknown or malformed id: one 403 `forbidden`, nothing recorded.
- Scope: `scope.reporting_games(s, id)` with the default purposes (class, makeup, replay); lecturer test Games, simulations and every Game of a Control test Class session never appear.
- Fixed column allow-list `COLUMNS` (a test holds it to a literal tuple; no header names AI/KI, score, feedback, letter, name, e-mail or user): `purpose`, `game`, `week`, `role`, `incoming_order`, `incoming_delivery`, `inventory`, `backlog`, `order`, `cost`, `decided_by`, `mark`, `occupant`.
- Values: `purpose` the Game's purpose code; `game` the game number for a Class game, and for a make-up game or a Replay its ordinal 1, 2, … within its purpose in creation order (UUIDv7 id); `role` the Role code; the four quantities and `cost` from the Decision log row's `state_seen` (the Week's cost on end-of-Week balances); `order`, `decided_by` from the row; `mark` = `games.seat_mark(decided_by, fallback, occupant_kind, reason)` (the one AD-15 mapping) or empty; `occupant` `student` or `ai` (llm, rule_based, scripted). Rows sorted by purpose (class, makeup, replay), game, week, Role in chain order.
- CSV dialect as 13.14: UTF-8 with BOM, `;`, CRLF, decimal comma; formula-like text guarded. `Content-Disposition: attachment; filename="spilldata-klasseokt-<n>.csv"`, `Cache-Control: no-store`; one audit row `game_data_export.downloaded` (target the Class session, change `{games, rows}`), written once the rows are read; 409 `data_deleted` once the Class session's deletion date has come.
- The block shows the link and «Ingen av filene har KI-vurderinger.» when `game_data_export` is true and the state is not `deleted`; the note appears once whether one or both CSV actions show.

**Never:** no AI score, AI feedback, Indicative letter, `user_id`, seat id, game id, name or e-mail in the file; no stored copy, no new table, no migration; no change to the ZIP job or the Completion export's file; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Played Class game | flag on, Lecturer, a 2-Student game played 3 Weeks | 200 `text/csv`, BOM, header + 12 rows (3 Weeks × 4 Roles), values equal to `seat_weeks` | — |
| Make-up and Replay | a given make-up game and a Replay with Orders | their rows with `purpose` makeup/replay and `game` 1 | — |
| Out of scope | a lecturer test Game; a Control test session | never in the file; Control test: header only | — |
| Fallback / switch | a row with `fallback=timeout` | `mark` `fallback_timeout` | — |
| No Orders yet | session with no Decision log row | header only | — |
| Flag off | `FEATURE_GAME_DATA_EXPORT=false` | 404 identical to an unknown route; state flag false | — |
| Refused | Assistant, other Lecturer, Admin w/o role, Student, bad id | — | 403 `forbidden`, no audit row |
| Deleted | deletion date has come | — | 409 `data_deleted` |

</intent-contract>

## Code Map

- `backend/app/platform/config.py:65` `feature_game_data_export` (default True) -- the flag, read through `get_settings()`; tests flip it with `tests/sessions/test_test_game.py:flag` pattern (`flag(monkeypatch, False, "FEATURE_GAME_DATA_EXPORT")` + `get_settings.cache_clear()`).
- `backend/app/platform/authz.py` -- beside `completion.export`: `"game_data.export"` in the account map (LECTURER) and `CLASS_STAFF_ROLES` (OWNER).
- `backend/app/modules/reports/scope.py` `reporting_games(session, id)` -- `SessionGame(game_id, purpose, number, end_reason)`, ordered by id; `[]` for a Control test.
- `backend/app/modules/games/class_figures.py` -- add `GameDataRow` and `game_data_rows(session, game_ids)`: one read of `seat_weeks ⋈ seats` (pattern `repo.placed_orders_of`, `repo.py:1064`) giving game_id, week, role, `state_seen` (a `SeatState` dump: `incoming_order`, `incoming_delivery`, `inventory`, `backlog`, `cost`; `engine/state.py:13`), order, decided_by, fallback, occupant_kind, reason; export via `games/service.py` `__all__` and import block (`:23`, `:228`). `seat_mark` is `games.service.seat_mark` (`marks.py:32`).
- `backend/app/modules/reports/completion_export.py` -- reuse its CSV writer: factor `to_csv` into `csv_lines(columns, rows)` and let `_csv_cell` write a `Decimal` with a decimal comma; `to_csv(rows)` keeps its output byte for byte.
- `backend/app/modules/reports/game_data_export.py` (new) -- `EXPORT`, `COLUMNS`, `DOWNLOADED_AUDIT`, `export(user, id) -> GameData | None` (`sessions.staff_session_row`, `sessions.data_deleted`, `ReportRefused`, `sessions.report_heading` for the number, as `completion_export.export`), pure `game_keys(games)`, `row_values(...)`, `to_csv(rows)`, `file_name(number)`, `record_download`.
- `backend/app/modules/reports/routes.py:408` -- after the Completion export: `GET /class-sessions/{session_id}/game-data-export`, `operation_id="downloadGameDataExport"`, a first dependency that raises `HTTPException(404)` while the flag is off, then `authz.require(game_data_export.EXPORT)`; `StreamingResponse(to_csv(rows))`.
- `backend/app/modules/reports/bundle.py:83,165,211` `ZipState` and `schemas.py:228` `ZipStateOut`, `routes.py:_zip_state` -- `game_data_export: bool` = flag on and `sessions.class_staff_may(user, id, "game_data.export")`.
- `backend/app/modules/reports/README.md` -- a «Game data export» section.
- `frontend/src/modules/reports/api.ts:263` -- `gameDataExportPath(sessionId)`; `export-block.tsx` -- the link (Lenke look `LINK`) in the owners' part, shared note; `frontend/src/copy/nb.ts` `reports.export.gameData.action` «Last ned spilldata (CSV)» (spine, EXPERIENCE.md:507).
- Tests to extend: `backend/tests/reports/test_completion_export.py` (fixtures, `call`, `ASSISTANT`, `put_staff`, `ADMIN`, `OTHER_LECTURER`), `test_reports_zip.py` (state dict gains the field), `tests/reports/test_class_report.py:add_game` (out-of-scope Games), `tests/reports/test_makeup.py:give`; `frontend/src/modules/reports/export-block.test.tsx`; e2e `frontend/e2e/class-session-export.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `authz.py`, `games/class_figures.py`, `games/service.py` -- the action and the bulk read.
- `completion_export.py` -- the shared CSV writer and Decimal cell.
- `game_data_export.py`, `routes.py`, `bundle.py`, `schemas.py`, `README.md` -- the export, the route, the state flag; `uv run python -m app.openapi ../frontend/src/lib/api/openapi.json` then `npm run api:generate`.
- `backend/tests/reports/test_game_data_export.py` -- every matrix row; the column literal and banned words; values equal to the stored `seat_weeks`; one query count for the rows whatever the number of Games; no storage object and one audit row.
- `test_reports_zip.py` -- the state carries `game_data_export` (True for the Lecturer, False for the Assistant and with the flag off).
- frontend api, block, copy; Vitest with and without `game_data_export`; e2e: the Lecturer downloads the CSV on a fresh Class session (begins with BOM and the header), axe at each width.

**Acceptance Criteria:**
- Given the flag on and a Lecturer of the Class on the Klasseøkt, when the «Eksport» block shows, then it has «Last ned spilldata (CSV)» and «Ingen av filene har KI-vurderinger.», and pressing it downloads the CSV.
- Given the flag off, when the block shows, then the action is absent and the route answers as an unknown route.
- Given an Assistant lecturer of the Class, then the block has no game data action and the route answers 403.
- Given the block at 320 px and 200 % text, then it reflows and axe reports no violations.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 36 findings — high 0, medium 1, low 26, false 9, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind) Regenerated client missing — regenerated with `npm run api:generate`; `openapi.json`/`schema.ts` were left out of the review diff on purpose; typecheck passes.
  - `[low]` `[reject]` (blind) Rows are materialised before streaming — at 100 Class games x 50 Weeks x 4 Seats plus Replays the rows are tens of thousands of small tuples; only the body is streamed; not worth a cursor.
  - `[low]` `[reject]` (blind) A Class game without a number is dropped silently — every Class game is numbered at allocation; 14.5/14.6 apply the same rule; a guard for a state not shown reachable.
  - `[low]` `[reject]` (blind) One `state_seen` failing validation gives a 500 — the rows are written by the same `SeatState` model and older versions read as the current one (as `games.facts` reads them); a loud failure on corrupt data is correct.
  - `[low]` `[patch]` (blind) `PURPOSE_ORDER.index` raises for a new reporting purpose — now a rank dict with a fallback; the ordinal-stability part is rejected: Replays and make-up games are never deleted, so creation order is stable.
  - `[low]` `[patch]` (blind) `cost` semantics undocumented — README now says the quantities and `cost` are what the Seat saw when it ordered; a codebook or dot-decimal variant rejected (one dialect, the Completion export's).
  - `[false]` `[reject]` (blind) Decimal formatting unquantised / NaN — `week_cost` is the engine's `_Money` Decimal, never NaN; numeric columns get only ints and that Decimal.
  - `[low]` `[patch]` (blind) The link lacks `min-w-tap-target-min` — added; error handling for a stale link rejected (the 13.13/13.14 plain-link pattern).
  - `[low]` `[reject]` (blind) Shared note copy — the spine's note (EXPERIENCE.md:507) covers all files of the block.
  - `[false]` `[reject]` (blind) The state flag is true while data is deleted — `zip_state` returns early with `deleted=True` and the default `game_data_export=False`; `request_zip` refuses on deleted.
  - `[low]` `[reject]` (blind) Tests depend on the flag's default — the default is `True` in `config.py`; the flag-off case is its own test.
  - `[low]` `[reject]` (blind) Audit before streaming — the 13.14 rule ("once the file is built"); the rows are read and the body is deterministic.
  - `[low]` `[reject]` (blind) Test gaps for `file_name(None)` and `occupant` variants — the variants are now covered by the mark test; `file_name(None)` is a two-branch literal.
  - `[false]` `[reject]` (blind) Ordering redundant in SQL and Python — the Python sort orders across Games; the SQL order only makes the read deterministic.
  - `[low]` `[reject]` (edge) `SeatState` validation 500 — as the blind row.
  - `[low]` `[reject]` (edge) Class game without a number — as the blind row.
  - `[low]` `[reject]` (edge) Ordinals change between downloads — as the blind row (append-only Games).
  - `[low]` `[patch]` (edge) `PURPOSE_ORDER.index` ValueError — same patch as the blind row.
  - `[low]` `[reject]` (edge) Audit before the stream ends — as the blind row.
  - `[low]` `[reject]` (edge) Memory grows with rows — as the blind row.
  - `[false]` `[reject]` (edge) Bind-parameter limit — a Class session has at most a few hundred Games; the driver is psycopg.
  - `[low]` `[reject]` (edge) Stale link after the flag goes off — the plain-link pattern; the flag is a deploy-time setting.
  - `[low]` `[patch]` (edge) Docstring says three reads — now "a fixed number of reads"; the constant-count test holds it.
  - `[medium]` `[patch]` (verification) The `mark` column's occupancy branches are untested — `copied()` takes `kind`/`reason`; `test_the_mark_is_the_one_ad15_mapping_of_each_row` pins Takeover, guard switch (Rule-based and LLM), cost limit, playout, reclaim, and the fallback winning over a Takeover.
  - `[low]` `[patch]` (verification, other) A taken-over Seat's mark repeats on every Week, unlike Spillinnsikt — intended for row-level data; README states it.
  - `[low]` `[reject]` (verification, other) The Decimal assertion mirrors `_csv_cell` — it still catches a fall-through to text; the dialect is pinned by 13.14's tests.
  - `[false]` `[reject]` (verification, other) The e2e may not run — it ran and passed.
  - `[low]` `[reject]` (intent) The flag-off block is not run in a browser — the api answers `game_data_export=false` (tested) and Vitest pins the block without it.
  - `[low]` `[reject]` (intent) The route stays in OpenAPI while "not existing" — the flag is read at runtime (AD-17's pattern, as `startTestGame`); at runtime it answers exactly as an unknown route.
  - `[low]` `[reject]` (intent) Open Weeks have only the Orders placed so far — a row is a Decision log row (Design Notes).
  - `[low]` `[reject]` (intent) Rows materialised before streaming — as the blind row.
  - `[false]` `[reject]` (intent) Client not regenerated — as the blind row.
  - `[false]` `[reject]` (intent) Deleted-data hiding and the audit row go beyond the ACs — they follow the spec's Always rules (13.14's pattern).
  - `[low]` `[reject]` (intent) A Class game without a number dropped — as the blind row.
  - `[low]` `[reject]` (intent) Make-up and Replay numbering, mark as one column, Decision-log rows only (readings C1–C3) — choices recorded in the Design Notes and the report.
  - `[false]` `[reject]` (intent) Only the flag-on browser case and the api tested — the api tests cover flag-off, refusals and deletion; see the rows above.

## Design Notes

The file is for analysis in the Lecturer's own tools, so headers and enum values are stable codes (the stored values and the AD-15 marks), not display text; only the dialect follows Norwegian Excel, as the Completion export does. A row is a Decision log row: every Week a Seat ordered in. The open Week of a running Game has no Order yet and is left out, so every row has every column. Make-up games and Replays have no game number; their ordinal within the purpose keys them without exposing an id.

```
purpose;game;week;role;incoming_order;incoming_delivery;inventory;backlog;order;cost;decided_by;mark;occupant
class;1;1;retailer;4;4;12;0;4;6;student;;student
replay;1;3;factory;4;4;8;0;6;4,5;llm;fallback_timeout;ai
```

## Verification

**Commands:**
- `uv run pytest tests/reports tests/test_imports.py -n 8` -- pass
- `npm run typecheck && npx vitest run src/modules/reports && npm run check:copy && npm run lint:colours` -- pass
- `npx playwright test e2e/class-session-export.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary:** Behind `FEATURE_GAME_DATA_EXPORT`, the Klasseøkt's «Eksport» block offers the Lecturers of the Class «Last ned spilldata (CSV)». `GET /api/class-sessions/{id}/game-data-export` (new Class action `game_data.export`, owners only) writes one row per Decision log row (Game, Week, Seat) of every Game `scope.reporting_games()` counts: Class games, make-up games and Replays, the purpose in its own column, make-up games and Replays numbered within their purpose. The columns are the fixed allow-list `COLUMNS`; `mark` is the one AD-15 mapping; `occupant` is `student` or `ai`. The Completion export's CSV dialect, streamed, never stored; one audit row with counts. With the flag off the route answers as an unknown route, before any policy, and the block has no action. One bulk read (`games.game_data_rows`). No migration, no new table. Implemented in the builder's own context, as the orchestrator directed.

**Files:**
- `backend/app/modules/reports/game_data_export.py` (new): columns, keys, rows, audit, CSV.
- `backend/app/modules/reports/routes.py`: `downloadGameDataExport` with the flag dependency; `_zip_state` carries `game_data_export`.
- `backend/app/modules/reports/bundle.py`, `schemas.py`: `game_data_export` on `ZipState`/`ZipStateOut`.
- `backend/app/modules/reports/completion_export.py`: shared `csv_lines`; a `Decimal` cell (the Completion file is unchanged).
- `backend/app/modules/games/class_figures.py`, `service.py`: `GameDataRow`, `game_data_rows`.
- `backend/app/platform/authz.py`: `game_data.export` (Lecturer / owner).
- `backend/app/modules/reports/README.md`: the section.
- Frontend: `export-block.tsx`, `api.ts` (`gameDataExportPath`), `nb.ts` (`reports.export.gameData.action`, spine), regenerated client.
- Tests: `backend/tests/reports/test_game_data_export.py` (10), `test_reports_zip.py` (the flag), `export-block.test.tsx` (+1), e2e `class-session-export.spec.ts`.

**Review:** four layers (Sonnet, per the orchestrator's brief), 36 findings. Patched: 1 medium (the mark branches tested) and 6 low (purpose rank fallback, docstring, tap target, README on cost and repeated marks). Deferred: none. Rejected with reasons in the log.

**Follow-up review recommended:** false (one medium patched, test coverage only).

**Verification:**
- Backend: full suite 4088 passed before the review patches (`-n 8 --maxprocesses=8`, 4 min 10 s); after them the export tests 16 passed; ruff passes.
- Frontend: typecheck, Vitest 1309, `check:copy`, `lint:colours`, build pass.
- Playwright `--workers=4` on the lane-3 stack: class-session-export, all-games, class-report, plenary, homes, order-confirm, guided-week, chain-band: 81 passed; the export spec again after the patches; axe per width.
- New tests over 1 s: the played tests in `test_game_data_export.py` (about 1 to 3.3 s each, from `short_game`/`play_weeks`).

**Residual risks:**
- Rows are built in memory before the body streams (fine at pilot size).
- A link pressed after the deletion date or with the flag turned off saves the error body as a file (the 13.13/13.14 pattern).
- Decisions taken without the founder: stable codes (English snake_case headers, stored enum values) in the Completion export's Norwegian-Excel dialect; one row per Decision log row (the open Week holds only Orders placed); make-up games and Replays keyed by their ordinal within the purpose; `occupant` collapses LLM, Rule-based and scripted into `ai`; flag off = plain 404 identical to an unknown route; 409 `data_deleted` after the deletion date; the note shown once for both CSV actions.
- New personal data: no new table; the file has no name, e-mail or id.
