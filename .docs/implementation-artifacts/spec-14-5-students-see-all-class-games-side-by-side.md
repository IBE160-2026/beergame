---
title: 'Story 14.5: Students see all Class games side by side'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'b156e68909bd0dd902df854cffd78cc41d60fefb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-14-1-class-report-of-the-games.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The view's scope uses 14.1's stand-in class_report._class_games; relink to reports.scope.reporting_games at the Epic 13 merge.
    evidence: |-
      reports.scope exists only on epic-13. class_report_all_games imports the private _class_games so one predicate holds the rule on this branch; the merge must point both reads at scope.reporting_games(purposes={class}).
    location: >-
      backend/app/modules/reports/class_report_all_games.py class_games
    severity: low
  - summary: >-
      Make-up games do not exist yet; the own game is games.student_game, which must keep returning the allocated Class game once they do.
    evidence: |-
      Purpose.MAKEUP is unused. A Student who later plays a make-up game would get own_game null if student_game returned the make-up game. Settle with a test when make-up games are built.
    location: >-
      backend/app/modules/games/service.py student_game
    severity: low
---

<intent-contract>

## Intent

**Problem:** After their Debrief a Student cannot see whether the other teams of the Class behaved as theirs did; the bullwhip pattern is only shown to them in their own game (FR-86).

**Approach:** A Student page «Alle spill side om side» at `/alle-spill/{sessionId}`, fed by one anonymised read `GET /api/me/class-sessions/{id}/all-games` (`getMyClassGames`) that returns, per Role, every Class game's Orders per Week keyed by game number, with the Student's own game marked. Hjem shows the entry under Stegene, locked with «Åpnes når Debriefen din er ferdig og Spillfristen er passert.» until the api's `all_games_open` says both conditions hold.

## Boundaries & Constraints

**Always:**
- Gate (api): the Class session is one of the Student's own locked ones (`sessions.enrolled_locked_row`), else 403 `forbidden` (same body for unknown or malformed ids); then `progress.has_step(user, session, debrief)` and the session's Play deadline set and passed (`sessions.play_deadline_passed(row, now)`), else 403 `all_games_locked`. Hjem's `EnrolledSessionOut.all_games_open` uses the same two conditions (Debrief step in the steps already read, `play_deadline_passed`).
- Scope: the Class games (`purpose=class`) of that Class session only, through 14.1's scope stand-in `class_report._class_games` (none for a Control test session; relinked to `reports.scope.reporting_games` at the Epic 13 merge). Lecturer test Games, simulations, make-up games and Replays never appear. Games without a number are left out.
- Own game: `games.service.student_game` (the Seat held now, else the one held last: a taken-over Student keeps the Class game they were allocated to). Marked only when it is one of the listed Class games; at most one game is marked.
- Response: `roles` in chain order, each with `games` in game-number order, each `{number, own, orders}` where `orders[i]` is the Order of Uke `i+1` or null; `weeks` = the highest Week with an Order; `own_game` the number or null. No names, `user_id`, Seat or Game id, occupant data, cost, Total cost, decided-by or any result. A test asserts the schema's field names hold no identifying or cost field. `Cache-Control: no-store`. A fixed number of queries whatever the number of games; the read writes nothing.
- Page: one Ordrelinjer chart per Role, Fabrikk at the top, all on one shared y-scale; every game a thin line, the own game a thick line with a point at each Week, and named in text above the charts («Ditt spill er Spill 3. Det er tegnet med tykk strek og punkter.»). Under each chart «Vis som tabell»: rows in game-number order, columns Uke 1…n, own row's header «Spill 3 (ditt spill)». Nothing sorts, ranks or highlights by cost or result. The chart is a new hand-made SVG in `frontend/src/components/charts/order-lines.tsx` (`aria-hidden`, `<title>`), sized by its caller; on phones the chart and the table scroll sideways inside their own region, the page does not.
- Copy under a new top-level `nb.allGames` (and the Hjem entry there); drafted strings `[ASSUMPTION]`. Numbers through `formatNumber`. Merge layout: new backend files `reports/class_report_all_games*.py`, route in `class_report_routes.py`, `games/class_figures.py` read `class_orders` (re-exported in `games/service.py`).

**Never:** no cost, result or ranking in the response or the page; no colour-only marking; no live topic or new event topic; no migration or table; no change to the demo Class; no web-app arithmetic beyond chart scales.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Debrief not done | Play deadline passed, no `debrief` step | Hjem entry locked | GET → 403 `all_games_locked` |
| Deadline ahead | `debrief` step, Play deadline in the future (or unset) | Hjem entry locked | 403 `all_games_locked` |
| Open | both hold | `all_games_open: true`; 4 roles × N games, own marked once | — |
| Not own session | other Student's/unknown/malformed id, Lecturer | — | 403 `forbidden` |
| Other purposes | lecturer test Game and Replay in the session | not listed | — |
| Taken over | Student's Seat held by AI since Week 3 | that Class game marked own | — |
| Unplayed weeks | a game stopped at Week 4 of 6 | `orders` of length `weeks`, null after Week 4 | — |
| Control test | Control test session | `roles` with empty `games` | — |
| Many games | 2 vs 6 Class games | same query count | — |

</intent-contract>

## Code Map

- `backend/app/modules/reports/class_report.py:95` `_class_games` -- scope stand-in to reuse; `sessions.kind_of` for control test (`:287`).
- `backend/app/modules/reports/class_report_routes.py` -- route pattern (`_id` → `authz.Forbidden`, `no-store`); stable codes via `app.platform.errors.error_response(403, code, message)` as in `debrief/routes.py:85`.
- `backend/app/modules/sessions/service.py:2103` `enrolled_locked_row` (membership); `:1953` `test_deadline_passed` -- add `play_deadline_passed(row, now)` beside it; `:1699` `enrolled_sessions` (`done` steps at `:1727`, construct at `:1760`) -- add `all_games_open`.
- `backend/app/modules/sessions/schemas.py:889` `EnrolledSessionOut` -- add `all_games_open: bool = False`.
- `backend/app/modules/games/service.py:527` `student_game`; `games/repo.py:1041` `placed_orders_of` (the SQL to mirror); `games/class_figures.py` -- add `class_orders(session, game_ids)`; re-export block `games/service.py:23,214`.
- `backend/app/modules/progress/service.py:79` `has_step`, `Step.DEBRIEF`.
- `backend/app/platform/authz.py:160` -- add `"all_games.own": frozenset({ANY_USER})` beside `debriefs.own`.
- Tests: `backend/tests/reports/test_class_report.py` (`klass`, `short_game`, `play_weeks`, `call`, `execute`, query counting with `event`), `backend/tests/games/helpers.py`.
- Frontend: `frontend/src/modules/games/student-hjem.tsx:201` (Stegene; entry goes under it); `components/stegene.tsx` (locked style); `modules/assessment/assessment-page.tsx` (Student page/guard/403 pattern); `app/(app)/ki-vurdering/[sessionId]/page.tsx` (route pattern); `modules/reports/class-report-parts.tsx` (`Toggled`, `Table`, `Section`, `REGION`); `components/charts/cost-area.tsx` (hand-made SVG pattern, `palette.ts`); `lib/box-size.ts`; `modules/sessions/sessions.ts` `roleName`; `modules/identity/homes.ts` (paths); `copy/nb.ts`.
- e2e: `frontend/e2e/class-report.spec.ts` (stub + axe + reflow), `e2e/support/classes.ts` (`expectAccessible`, `expectReflow`, `test`), `e2e/support/auth.ts` `loginByApi`.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/authz.py` -- policy `all_games.own`.
- `backend/app/modules/sessions/{service,schemas}.py` -- `play_deadline_passed`; `all_games_open` on Hjem's sessions.
- `backend/app/modules/games/class_figures.py` + `games/service.py` -- `class_orders` (one query: game id, week, role, order).
- `backend/app/modules/reports/class_report_all_games.py`, `class_report_all_games_schemas.py` (new) + route in `class_report_routes.py`.
- `backend/tests/reports/test_class_report_all_games.py` (new) -- matrix rows, schema has no identifying field, fixed query count, Hjem flag.
- Frontend: `components/charts/order-lines.tsx` (+ test in `charts.test.tsx` or own test), `modules/reports/all-games-api.ts`, `all-games.ts` (+ `.test.ts`), `all-games-page.tsx`, `app/(app)/alle-spill/[sessionId]/page.tsx`, `homes.ts` `allGamesPath`, Hjem entry in `student-hjem.tsx`, `nb.ts` `allGames`; `npm run api:generate`.
- `frontend/e2e/all-games.spec.ts` (new) -- stubbed view at 320/360/1440 with axe and reflow (only chart and table regions scroll), table toggle with own row named, Hjem entry locked and open (stubbed sessions), live api: a fresh Student whose Debrief is not done gets 403 `all_games_locked`.

**Acceptance Criteria:**
- Given a Student with the Debrief done and the Play deadline passed, when they follow «Alle spill side om side» on Hjem, then the page shows four Role charts (Fabrikk first) with every Class game's Orders and their own game named in text and drawn thick with points, each with «Vis som tabell».
- Given either condition missing, when the Student opens Hjem, then the entry reads «Åpnes når Debriefen din er ferdig og Spillfristen er passert.» and is no link; opening the page directly shows that line instead of charts.
- Given 320, 360 and 1440 px, when Playwright and axe run, then no horizontal page scroll and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 24 findings — high 0, medium 0, low 17, false 7, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) An Order between two empty Weeks draws no mark on another game's line — round caps on the thin lines (1.5 px) draw it as a dot.
  - `[false]` `[reject]` (blind) Other lines unidentifiable; chart aria-hidden with a focusable region — by design (anonymous, no game singled out, UX-DR72); «Vis som tabell» names every game; the focusable region lets a keyboard scroll the wide chart (axe passes).
  - `[low]` `[patch]` (blind) Hjem's flag does not check the lock the read checks — the flag now also requires `is_locked`. Opening live when the deadline passes on an open Hjem is not added (Design Notes: next read).
  - `[false]` `[reject]` (blind) A 403 `all_games_locked` could be cached — the client fetches with `cache: "no-store"` and the response has no validator; the envelope is the documented 403 like every other code.
  - `[low]` `[reject]` (blind) Unfinished games listed with partial Orders — the AC asks for every Class game of the session; after the Play deadline the playout finishes them, and the Orders carry no identity.
  - `[low]` `[reject]` (blind) Private `_class_games` import — kept so 14.1 and 14.5 share one predicate until the Epic 13 relink (deferred).
  - `[low]` `[reject]` (blind) Entry on a Control test session leads to «Klasseøkta har ingen klassespill.» — rare (test students only) and the page says so truthfully.
  - `[low]` `[patch]` (blind) Unused copy `allGames.showTable`/`showChart` — removed; `axis` is the page's unit line; `lastLabel` and the chart's Week count both follow the api's `weeks`.
  - `[low]` `[patch]` (blind) No check that outsiders get `forbidden` while locked — added (outsider and Lecturer before the Debrief); the other test-gap notes rejected (the e2e Hjem stub follows the suite's pattern).
  - `[low]` `[patch]` (edge) One-point line invisible — same fix as the first blind row.
  - `[low]` `[patch]` (edge) Games listed but no Order at all shows an empty axis — the page shows «Klasseøkta har ingen klassespill.» when `weeks` is 0.
  - `[false]` `[reject]` (edge) `top` below the highest Order — the page computes `top` from the same data (`sharedTop`).
  - `[low]` `[patch]` (edge) Flag vs read lock — same fix as the blind row.
  - `[low]` `[reject]` (edge) Control test link — as the blind row.
  - `[low]` `[reject]` (edge) In-progress Orders of other games — as the blind row.
  - `[low]` `[reject]` (edge) No live e2e reaches `all_games_locked` — the backend tests call the real route for every gate case; a live e2e would need a played game and a moved Play deadline (no dev route) for no further coverage.
  - `[low]` `[patch]` (verification) Play-deadline boundary not pinned — the test now asserts locked one second before and open at the deadline itself.
  - `[low]` `[patch]` (verification) Empty state rendered by no test — e2e case added.
  - `[false]` `[reject]` (intent) Scope is not `reporting_games` — not on this branch; the stand-in is documented and deferred.
  - `[low]` `[defer]` (intent) Make-up Student marking untested — make-up games do not exist yet; deferred.
  - `[false]` `[reject]` (intent) Entry only with a game card — a Student without one has no Debrief to finish; the locked line would never open.
  - `[false]` `[reject]` (intent) Flag and gate are two implementations — both use `play_deadline_passed` and the Debrief step; the backend test reads both sides.
  - `[false]` `[reject]` (intent) Phone table scroll not asserted — the table sits in its own scroll region (`REGION`) and `expectAccessible` asserts no page scroll after the table opens.
  - `[low]` `[reject]` (intent) Live e2e of `all_games_locked` — as the edge row.

## Design Notes

Decisions the founder would otherwise take (`[ASSUMPTION]`, in the report):
- Own-game marking: thick line plus a point per Week, and the game named in text above the charts and in its table row; other games thin lines in one neutral colour (no per-game colours, so no game stands out).
- All four Roles shown (Fabrikk first) on one shared scale, matching «samme skala» in `09-alle-sider.png`; the own Role is not singled out.
- Make-up games do not exist yet (`Purpose.MAKEUP` unused): "allocated game" = `student_game`, which covers a taken-over Seat. When make-up games are built, `student_game` must keep returning the allocated Class game.
- Hjem entry shows once the Student has a game card; the Play deadline passing does not push a live update (Hjem shows it on the next read).

## Verification

**Commands:**
- `uv run pytest tests/reports -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/reports src/components/charts && npm run lint:colours && npm run check:copy` -- pass
- `npx playwright test e2e/all-games.spec.ts e2e/homes.spec.ts --workers=4` (lane stack) -- pass

## Auto Run Result

Status: done

Summary: «Alle spill side om side» for Students. `GET /api/me/class-sessions/{id}/all-games` (`getMyClassGames`, policy `all_games.own`, `no-store`) returns, per Role in chain order, every Class game's Orders per Week keyed by game number, with only the Student's own game marked (`games.student_game`, so a taken-over Seat keeps its game); no names, ids, occupants, cost or result (schema field allow-list test). Gate: own locked session else 403 `forbidden`; Debrief step (`progress.has_step`) and Play deadline passed (`sessions.play_deadline_passed`) else 403 `all_games_locked`. Hjem gets `all_games_open` and shows the entry under Stegene: a Lenke, or locked with «Åpnes når Debriefen din er ferdig og Spillfristen er passert.». Page `/alle-spill/{id}`: one Ordrelinjer chart per Role (new hand-made SVG `components/charts/order-lines.tsx`, reusable by 14.6), Fabrikk first, one shared scale, own game thick with a point per Week and named in text, «Vis som tabell» in game-number order; on phones only the chart and table scroll. Fixed number of queries; no write, no migration, no new table.

Files: backend `reports/class_report_all_games{,_schemas}.py` (new), route in `class_report_routes.py`, `games/class_figures.py` `class_orders` (+ re-export in `games/service.py`), `sessions/{service,schemas}.py` (`play_deadline_passed`, `all_games_open`), `platform/authz.py`; tests `tests/reports/test_class_report_all_games.py` (new), `tests/sessions/test_dates.py` (field list). Frontend `components/charts/order-lines.tsx`, `modules/reports/all-games-api.ts`, `all-games.ts` (+ `all-games.test.tsx`), `all-games-page.tsx`, `all-games-entry.tsx`, route `app/(app)/alle-spill/[sessionId]/page.tsx`, `homes.ts` `allGamesPath`, Hjem entry in `student-hjem.tsx`, `nb.ts` `allGames`, regenerated `openapi.json`/`schema.ts`; `e2e/all-games.spec.ts`.

Review: four layers (blind, edge case, verification gap, intent alignment; Sonnet per the orchestrator's brief; implemented in the builder's own context per the brief). 24 findings: 9 patched (all low), 1 deferred (low; plus the scope relink recorded), 14 rejected with reasons above. followup_review_recommended: false (no high or medium patched).

Verification: backend full suite 3919 passed before the patches (one field-list test then updated); touched backend tests 55 passed after the patches; ruff check and format; frontend typecheck, Vitest 1240 passed, lint:colours, check:copy, frontend image build passed; Playwright all-games, homes, order-field, game-card, class-report 49 passed with axe at 320/360/1440 px. Screenshots checked at 1440 px and Hjem at 320 px. New backend tests take about 2.5 s each (the played short-game fixture, as in 14.1).

Residual risks: scope stand-in to relink at the Epic 13 merge; make-up games not built; Hjem does not open the entry live when the Play deadline passes (next read); `sessions/service.py`, `nb.ts`, `authz.py` touch lines near Epic 13's (small mechanical conflicts possible).
