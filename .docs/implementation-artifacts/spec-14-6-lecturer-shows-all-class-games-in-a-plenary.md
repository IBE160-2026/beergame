---
title: 'Story 14.6: The Lecturer shows all Class games in a plenary'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '723a2c7b714d4a1ebef0bb48af6abac233426723'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-14-5-students-see-all-class-games-side-by-side.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Lecturer has no view of all Class games that can go on the projector: the Oversikt carries Student names, «Venter …», the Varselbånd and Spillstyring, so it cannot be shown to the class (FR-86, UX-DR42).

**Approach:** A secondary button «Vis i plenum» on the Oversikt opens `/klasseokter/{id}/oversikt/plenum`, a display-mode page fed only by a new anonymised read `GET /api/class-sessions/{id}/plenary` (`getClassPlenary`) that returns, per Role, every Class game's Netto lager and Orders per Week keyed by game number. The page shows the Matrisevegg (Netto lager, larger cells, no figure/detail/link columns) with a Rolle filter, its legend and caption, and a Visningsbryter to «Vis som tabell» and to the per-Role Orders charts of Story 14.5 (no game marked).

## Boundaries & Constraints

**Always:**
- Access follows the Oversikt's policy: `authz.require("class_sessions.overview")` and `sessions.staffed_session(user, id, "class_sessions.overview")` (Lecturers and Assistant lecturers of the Class); every other User, an unknown or malformed id answer 403 `forbidden` alike. No new policy.
- Scope: the Class games of the session through 14.1's stand-in `class_report._class_games` (none for a Control test session; relinked to `reports.scope.reporting_games` at the Epic 13 merge), games without a number left out, in game-number order. Values from `games.class_played(s, ids, with_orders=True)`: per opened Week `inventory − backlog` per Role, and the placed Order.
- Response `{weeks, roles:[{role, games:[{number, net, orders}]}]}`: `roles` in chain order; `net[i]` = Netto lager of Uke i+1 for the game's opened Weeks only (an unstarted game has `[]`); `orders` has length `weeks`, null where none; `weeks` = the highest opened Week of any listed game. No name, `user_id`, Seat or Game id, occupant, status, wait, cost, chain cost, decided-by, Varselbånd or Spillstyring field; a test holds the schema's field names to an allow-list. `Cache-Control: no-store`; a fixed number of queries whatever the number of games; no write.
- Page: display mode like `/delt-skjerm` (no `user` in `PageShell`, the projector text scale), title «Alle spill i plenum», the line «Mønsteret går igjen, uten navn og uten rangering.», a Lenke back to the Oversikt. Wall: one group, rows «Spill n» in game-number order, cells Netto lager on the `net` scale, the legend always visible (MatrixWall's own), caption «Rødt: restordre, under null. Blått: lager, over null. Tallet i cellen er netto lager.» in `body` under the wall; cells at 1.5× the Oversikt's wall font size. Rolle filter (Fabrikk default, the Oversikt's text-button group) drives wall and table. «Vis som tabell»: `MatrixTable` with no extra columns and no sortable header, rows in game-number order. Orders view: 14.5's per-Role charts and tables (Fabrikk first, one scale), every game `own: false`. Focus stays on the same game across refetches (row id = game number).
- Live: the query key sits under `classReportKey(id)`, so `session:<id>` refetches it (no new topic).
- The page calls only `getClassPlenary` (never `getClassOverview`, `getWallAggregates`, `getGameWeeks`).
- Copy under `nb.plenary`; drafted strings `[ASSUMPTION]`; the three story strings exact; numbers through the shared formatter.

**Never:** no names, occupants, status groups, waits, cost, chain-cost figure, median rows, near-Takeover tint, Melding links or Spillinnsikt navigation; no sorting by cost or any column; no new event topic, migration or table; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Owner | Lecturer of the Class, played games | 4 roles × N games; net and orders per Week | — |
| Assistant | Assistant lecturer of the Class | same answer | — |
| Outsider | Student, Lecturer of another Class, Admin, unknown/malformed id | — | 403 `forbidden` |
| Other purposes | lecturer test Game and Replay in the session | not listed | — |
| Unstarted game | numbered Class game not started | `net: []`, orders all null | — |
| Partial game | stopped at Uke 4 of 6 | `net` length 4; `orders` length `weeks`, null after | — |
| Control test | Control test session (staff) | `roles` with empty `games`, `weeks` 0 | — |
| No games / no Weeks | nothing opened | page says «Ingen klassespill har startet ennå.» | — |
| Many games | 2 vs 6 Class games | same query count | — |

</intent-contract>

## Code Map

- `backend/app/modules/reports/class_report_all_games.py` -- 14.5's read; pattern for gate, `_class_games`, chain-order roles. `class_report_all_games_schemas.py` -- schema pattern.
- `backend/app/modules/reports/class_report_routes.py` -- add the route (`_id` → `authz.Forbidden`, `no-store`).
- `backend/app/modules/reports/class_report.py:95` `_class_games`; `:283` `sessions.staffed_session(user, id, action)`; `sessions.kind_of`, `CONTROL_TEST`.
- `backend/app/modules/games/service.py:1422` `class_played(session, ids, with_orders)` -- `PlayedGame.states` (WeekState, `.seat(role)`, `.finished`) and `.orders[(week, role)]`.
- `backend/app/platform/authz.py:110,221` `class_sessions.overview` (Lecturer + Assistant, owner + assistant staff).
- Tests: `backend/tests/reports/test_class_report_all_games.py` (fixtures `klass`, `short_game`, `play_weeks`, query counting) and `test_class_report.py`; `backend/tests/games/helpers.py`.
- Frontend: `modules/games/overview-page.tsx:196` `OverviewHeader` (button goes here); `modules/games/overview-wall.tsx` (wall + table wiring); `components/charts/matrix-wall.tsx` (`MatrixWall`, groups/rows, legend), `matrix-table.tsx` (`MatrixTable`, no columns → no sort); `modules/games/wall-copy.ts` `wallCopy`, `formatCell`; `modules/games/wall-filters.tsx` (`Group` → export a `RoleFilter`); `components/view-toggle.tsx`; `modules/reports/all-games-page.tsx` (`RoleSection`/`Chart` → export an `OrdersByRole` block), `all-games.ts`; `modules/debrief/shared-screen.tsx` (`PROJECTOR_SCALE`, no-user `PageShell`); `modules/reports/class-report-api.ts` `classReportKey`; `modules/identity/homes.ts` (paths); `components/button.tsx` `buttonClassName`; `copy/nb.ts`.
- e2e: `frontend/e2e/all-games.spec.ts` (stub + axe + reflow pattern), `e2e/support/classes.ts`, `e2e/support/auth.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/reports/class_report_plenary{,_schemas}.py` (new) -- `plenary(user, id)` and `PlenaryOut`.
- `backend/app/modules/reports/class_report_routes.py` -- `GET /api/class-sessions/{id}/plenary`.
- `backend/tests/reports/test_class_report_plenary.py` (new) -- matrix rows, schema allow-list, fixed query count.
- `frontend/src/lib/projector.ts` (new) -- `PROJECTOR_SCALE` moved from `shared-screen.tsx` (re-imported there).
- `frontend/src/modules/reports/plenary-api.ts`, `plenary.ts` (+ `plenary.test.ts`), `plenary-page.tsx` (new); `app/(app)/klasseokter/[sessionId]/oversikt/plenum/page.tsx` (new); `homes.ts` `plenaryPath`; `overview-page.tsx` button; `wall-filters.tsx` `RoleFilter`; `all-games-page.tsx` exported `OrdersByRole`; `nb.ts` `plenary`; `npm run api:generate`.
- `frontend/e2e/plenary.spec.ts` (new) -- stubbed at 320/1440 with axe and reflow; the three views; no `aria-sort`, no names; the page requests no staff overview endpoint; live: the Oversikt's button opens the page for a fresh Lecturer, and a Student gets the permission-denied page.

**Acceptance Criteria:**
- Given the Oversikt after the Start date, when the Lecturer presses the secondary button «Vis i plenum», then the plenary page opens with the Matrisevegg on `paper`, larger cells, no figure, detail or link column, the line «Mønsteret går igjen, uten navn og uten rangering.», the legend and the caption «Rødt: restordre, under null. Blått: lager, over null. Tallet i cellen er netto lager.».
- Given the plenary page, when its data is fetched, then the only api read is `getClassPlenary`, whose answer holds game numbers and per-Week values only.
- Given the Visningsbryter, when «Vis som tabell» is chosen, then the table lists the games in game-number order with a number in every played Uke, no names and no sortable header; the Rolle filter changes wall and table.
- Given the Visningsbryter, when the Orders view is chosen, then four per-Role Orders charts (14.5's) are shown with no game marked, each with «Vis som tabell».
- Given 320 and 1440 px, when Playwright and axe run, then no horizontal page scroll and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 16 findings — high 0, medium 0, low 9, false 7, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) Button comment says "when there are games to show" but the guard is only the Start date — comment corrected; a session with no opened Uke gets the page's «Ingen klassespill har startet ennå.» (truthful).
  - `[false]` `[reject]` (blind) Raw `NextLink` + `buttonClassName` is a second idiom — it is the codebase's pattern for a link drawn as a button (`game-action.tsx`, `briefing-page.tsx`); the design asks for a secondary button.
  - `[false]` `[reject]` (blind) Live refresh not wired — the key sits under `classReportKey`, which `session:<id>` invalidates; the Oversikt's own wall refreshes on the same topic.
  - `[low]` `[patch]` (blind) `net` docstring says "end of Uke" — reworded to "as the Oversikt's Matrisevegg shows it (the stored Week state)"; the values are the wall's own (`class_game_weeks`).
  - `[low]` `[reject]` (blind) Reads every Week state per refetch — the same read as the Oversikt's aggregates (`class_played`), two queries; size is small (60×36 states) and an ETag would add surface.
  - `[low]` `[patch]` (blind) Positional alignment of `listed`/`played`/`net` and a dead second number filter — now one `zip(..., strict=True)` of game and play, `_net` per pair.
  - `[false]` `[reject]` (blind) `game_id not in text` TypeError — `short_game` returns the id as `str` (same assertion passes in 14.5's test); other test-gap notes rejected (401 is the platform's, unnumbered games filtered by the same predicate as 14.5).
  - `[low]` `[patch]` (blind) Unit test relied on `-0` vs `0` — test data no longer produces `-0`.
  - `[false]` `[reject]` (blind) Orders view has no reflow at 320 px — `expectAccessible` includes `expectReflow`, and it runs after the Orders view at 320 px.
  - `[false]` `[reject]` (blind) Caption names colours — the caption is the story's exact text, the legend and the signed number carry the meaning too.
  - `[low]` `[reject]` (blind) `PROJECTOR_SCALE` rendered in children — same pattern as Delt skjerm; the `<style>` leaves with the page.
  - `[false]` `[reject]` (edge) `net` positional over sorted states could shift Uker — every opened Week has one stored state from Uke 1 (the Oversikt's wall indexes values from Uke 1 the same way).
  - `[low]` `[reject]` (edge) Zero games run fewer queries — fewer, never more; the bound is what NFR-3 asks.
  - `[low]` `[patch]` (edge) Button gating comment — as the blind row.
  - `[low]` `[patch]` (edge) Student page-level denial untested — the live e2e now opens the page as a Student and sees «Du har ikke tilgang til denne siden.».
  - `[low]` `[reject]` (edge) "Fixed number of queries" claim — as the zero-games row.

## Design Notes

Decisions the founder would otherwise take (`[ASSUMPTION]`):
- No gate beyond the Oversikt's policy (the story names none); the button shows once the Start date has passed.
- Cells at 1.5× the Oversikt's wall font (DESIGN.md's "≥ 2× cell" assumption is met on a projector through the projector text scale on top of it).
- One wall group titled «Alle spill, 24» style count; third Visningsbryter segment «Ordre per rolle».
- Unstarted games are rows without cells (as on the Oversikt), so the class sees how many games exist.

## Verification

**Commands:**
- `uv run pytest tests/reports -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/reports src/modules/games && npm run lint:colours && npm run check:copy` -- pass
- `npx playwright test e2e/plenary.spec.ts e2e/all-games.spec.ts --workers=4` (lane stack) -- pass

## Auto Run Result

Status: done

Summary: «Alle spill i plenum». A secondary button «Vis i plenum» in the Oversikt's header (after the Start date) opens `/klasseokter/{id}/oversikt/plenum`, a display-mode page (no name in the header, the Delt skjerm projector text scale) fed only by the new anonymised `GET /api/class-sessions/{id}/plenary` (`getClassPlenary`, Oversikt policy `class_sessions.overview`, `no-store`): per Role in chain order, every Class game by number with its Netto lager per opened Uke and its Orders per Uke; no name, id, occupant, status, wait or cost (schema allow-list test). The page shows the Matrisevegg (1.5× the Oversikt's font, only the game column, one group), the always-visible legend, the line «Mønsteret går igjen, uten navn og uten rangering.» and the caption «Rødt: restordre, under null. Blått: lager, over null. Tallet i cellen er netto lager.»; a Rolle filter; a Visningsbryter «Vegg» / «Vis som tabell» (MatrixTable, game-number order, nothing sortable) / «Ordre per rolle» (14.5's charts via the extracted `OrdersByRole`, no game marked). Live through `session:<id>` (key under `classReportKey`). No migration, no table, no new topic, no new policy.

Files: backend `reports/class_report_plenary{,_schemas}.py` (new), route in `class_report_routes.py`; test `tests/reports/test_class_report_plenary.py` (new). Frontend `modules/reports/plenary{,-api,-page}.ts(x)` + `plenary.test.ts` (new), route `app/(app)/klasseokter/[sessionId]/oversikt/plenum/page.tsx`, `lib/projector.ts` (moved from `shared-screen.tsx`), `all-games-page.tsx` (`OrdersByRole`), `wall-filters.tsx` (`RoleFilter`), `view-toggle.tsx` (three segments allowed), `overview-page.tsx` (button), `homes.ts` `plenaryPath`, `nb.ts` `plenary`, regenerated `openapi.json`/`schema.ts`; `e2e/plenary.spec.ts` (new).

Review: two layers (blind, edge case; Sonnet, per the orchestrator's brief; implementation in the builder's own context per the brief; no access change). 16 findings: 6 patched (all low), 0 deferred, 10 rejected with reasons above. followup_review_recommended: false.

Verification: backend full suite 3921 passed, 4 skipped (before the low patches; `tests/reports` 30 passed after); ruff check/format; frontend typecheck, Vitest 1244 passed, lint:colours, check:copy, frontend image build (Next build) passed; Playwright plenary, all-games, overview, debrief-shared, homes, order-field, game-card 52 passed with axe at 320/360/1440 px; plenary + overview rerun after patches 11 passed. Screenshots of wall, table and Orders at 320 and 1440 px checked. New backend tests take 1.6–2.3 s each (the played short-game fixture, as in 14.1/14.5).

Residual risks: scope stand-in `_class_games` to relink to `reports.scope.reporting_games` at the Epic 13 merge (as 14.5); `nb.ts`, `overview-page.tsx` and `view-toggle.tsx` touch lines other lanes may touch (small mechanical conflicts).
