---
title: "Story 7.11: Act on the longest-waiting game from the Varselbånd"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e569cdbf97e5d21982152b88ed348c53b5ff4685'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Oversikt lists waiting games but names no single game to act on, and no row offers a Message (FR-39, FR-40, UX-DR41, UX-DR45).

**Approach:** The overview api names the longest-waiting Class game (`alert`); the page draws it as the Varselbånd with a primary «Send Melding» preset to the waited-for Student, tints that game's row in the wall, the table and the game list, leaves it out of «Venter ellers», and gives every row a «Melding» link to the Meldingsskjema preset to that Class game.

## Boundaries & Constraints

**Always:**
- **Api** `ClassOverviewOut.alert: OverviewAlertOut | None` = `{game_id, game_number, role, name, user_id, since}`, chosen in `sessions/overview.py` by a pure `_alert(games, names)`: among `waiting` games with at least one waited-for Seat, the earliest `wait_started_at` (else its earliest `since`), ties by game number then id; within it the waited-for Seat with the earliest `since`, ties in chain order. `name`/`user_id` only when the Student is still a Student of the Class (`user_id` null otherwise). None before the Start date and when nothing waits. Part of the ETag body. No new query, no migration. Epic 8 replaces the choice (seam: `_alert` docstring).
- **Band** (`overview-band.tsx`): only when `alert` is set and not before the Start date; above the headline counts; full-width `bg-restordre-fill text-ink`, text `font-semibold` «Spill 2 venter på Noah (Grossist) i 23 t.» (no name: «Spill 2 venter på Grossist i 23 t.»), duration from `since` at the server-clock `now`; primary «Send Melding» (a Lenke styled with `buttonClassName("primary")`) to `messagePath(sessionId, {game, student})` (`student` only when `user_id`). Below `lg` the action sits under the text at full width. A `<section>` with an accessible name. No band → nothing in its place.
- **Announcement**: a polite, always-mounted `sr-only` `role="status"` with `useThrottledAnnouncement` over the band's identity text without duration («Spill 2 venter på Noah (Grossist).»), so it is said at most once a minute, only when the band appears or changes game/Student; focus never moves. The band reads the shown answer, so with «Oppdater automatisk» off it holds until «Oppdater».
- **Rows**: every wall row, table row and game-list row has a Lenke «Melding» (accessible name `nb.messages.toGameLabel(n)`) to `messagePath(sessionId, {game})`. The band's game row is tinted `restordre-fill` with `ink` text and an `ink` underlined «Melding»; other rows' «Melding» is `lager` underlined. Wall: the link is the row's last `gridcell` at the drawing's right edge, reached by ArrowRight from the last Uke (and Up/Down between links; a not-started row is reachable by its link only); Enter or a click opens it via the router and never opens Spillinnsikt. Table: a column «Melding» (header visible text sr-only) after the extra columns; the target row's link is in the Tab order after its row header, Up/Down move link to link; a click never opens Spillinnsikt.
- **Rail**: «Venter ellers» leaves out the band's game; with the band set and no other waiting game it reads «Ingen andre spill venter.».
- Assistant lecturers see the same. Copy in `nb.ts`, new strings `[ASSUMPTION]`; text ≥ 13 px outside wall cells; no page-level horizontal scroll at 320 px.

**Never:** no countdown, «Pause spillet», «Sett inn KI-spiller» or Takeover choice (Epic 8); the web app never picks the band's game; no `ink-muted` or `restordre` text in the band; no new endpoint.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One waits | game 1 waits for Noah since T | `alert` = game 1, Noah, `user_id`, `since` T | — |
| Two wait | game 2 since T−1h, game 1 since T | game 2 | — |
| Tie | same `wait_started_at` | lower game number | — |
| Several Seats | game waits for Wholesaler (T) and Retailer (T−5m) | Retailer | — |
| Former Student | waited-for Student left the Class | `name` null, `user_id` null; band by Role; preset to game | — |
| None waits | running/finished only | `alert` null; no band, no button | — |
| Waiting, no Seat | `waiting_for` empty | that game skipped | — |
| Before Start date | not locked | `alert` null | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/overview.py:62` `class_overview`, `_game_out` -- add `_alert`, set `alert`. `names` comes from `classes.student_names` (Students of the Class only).
- `backend/app/modules/sessions/schemas.py:767,854` `OverviewWaitOut`, `ClassOverviewOut` -- add `OverviewAlertOut`, field `alert`.
- `backend/app/modules/games/service.py:551-579` `SummaryWait`, `ClassGameSummary` (`waiting_for` in chain order).
- `backend/tests/sessions/test_overview.py:90` waiting test -- assert `alert`; new pure test file for `_alert`.
- `backend/app/openapi.py` -- `uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.
- `frontend/src/modules/games/overview-page.tsx:225` `OverviewBody`, `GameRow:391` -- band, list link and tint.
- `frontend/src/modules/games/overview.ts` -- `wallGroups:252`, `tableRows:379`, `waitingElsewhere:420`; add `bandText`, `bandSaid`.
- `frontend/src/modules/games/overview-wall.tsx` -- pass `alertId`, links, router follow.
- `frontend/src/modules/games/overview-rail.tsx:69` -- skip band game.
- `frontend/src/components/charts/matrix-wall.tsx`, `matrix-wall-layout.ts` (`wallSizes`, `moveFocus`, `WallPosition`) -- row `link`, `tint`; README Matrisevegg section.
- `frontend/src/components/charts/matrix-table.tsx` -- row `link`, `tint`, link column.
- `frontend/src/components/link.tsx` (`onTint`), `components/button.tsx` (`buttonClassName`), `lib/announce.ts`, `modules/games/seat-status.ts` (`waitDuration`), `modules/identity/homes.ts:59` `messagePath`.
- `frontend/e2e/overview.spec.ts` (`liveClassGame`, `orderByApi`, `VIEWPORTS`, `expectAccessible`) -- cell locator at line 80 must exclude the link cell.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/schemas.py`, `overview.py` -- `OverviewAlertOut`, `_alert`, field.
- `backend/tests/sessions/test_overview_alert.py` (new, pure) -- matrix rows; `test_overview.py` -- api answer with and without a waiting game.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/charts/matrix-wall-layout.ts`, `matrix-wall.tsx`, `matrix-table.tsx`, `README.md` -- link cell/column, tint, keyboard.
- `frontend/src/modules/games/{overview.ts,overview-band.tsx,overview-page.tsx,overview-wall.tsx,overview-rail.tsx}`, `copy/nb.ts`.
- Unit tests: `matrix-wall.test.tsx` (`moveFocus` with links, `wallSizes` with links), `matrix-table.test.tsx` (link column, click does not activate), `overview.test.ts` (`bandText`, `waitingElsewhere` skip, row links/tint).
- `frontend/e2e/overview.spec.ts` -- band for Lecturer and Assistant at 1440/320 px with axe, «Send Melding» lands on the Meldingsskjema titled for the Student, the band's game out of «Venter ellers», row «Melding» in wall (keyboard) and table, no band when nothing waits.

**Acceptance Criteria:**
- Given a waiting Class game, when the Oversikt renders, then the band shows «Spill n venter på Name (Rolle) i d.» on `restordre-fill` with `ink` text and «Send Melding» opens «Melding til Name, Spill n».
- Given no waiting game, then no band and no primary button in its place.
- Given wall and table, then every row has «Melding» to that Class game, and the band's row is tinted with an `ink` underlined «Melding».
- Given several waiting games, then «Venter ellers» lists all but the band's game.
- Given 320 CSS px, then the band text comes first, «Send Melding» wraps under it at full width, no page-level horizontal scroll, axe passes.
- Given the band appears or changes, then it is announced politely at most once a minute and focus does not move; with «Oppdater automatisk» off it does not change until «Oppdater».
- Given an Assistant lecturer, then the same band and «Send Melding».

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment skipped on that instruction. Both hand-backs dropped; findings read from `review-blind-7-11.md` and `review-edge-7-11.md` in the session scratchpad.
- verdicts: 20 findings — high 0, medium 0, low 13, false 7, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) Generated api types missing from the diff — the review diff left out the generated `openapi.json`/`schema.ts` on purpose; both are regenerated in the change (`OverviewAlertOut`, `alert`).
  - `[false]` `[reject]` (blind 2) Table rows re-sort under a keyboard user on a «Melding» link — the hold uses `inside` (focus anywhere in the region), not `rowFocused`, which only puts focus back on a row header.
  - `[low]` `[reject]` (blind 3) `restordre-fill` also means backorder in charts — DESIGN.md and the AC name `restordre-fill` for the Varselbånd and its row; cells keep their own fills with a `paper` stroke.
  - `[low]` `[reject]` (blind 4) The tint is the only cue in wall/table/list — the band's text names the game in words above the wall (WCAG 1.4.1 met by text); a row word adds copy and parameters.
  - `[low]` `[reject]` (blind 5) `expectReflow` skips every SVG control — the only SVG control is the wall's «Melding», whose equivalent full-size link stands in the game list (WCAG 2.5.8 equivalent exception), recorded in the helper.
  - `[low]` `[patch]` (blind 6) `_alert` fallbacks untested — added a test for a game with no stored `wait_started_at` (its earliest Seat counts) and an unnumbered game after a numbered one; an unknown Role cannot reach it (DB enum).
  - `[low]` `[reject]` (blind 7) Api choice and Venter group order are two rules — intended: the AC wants the api to choose (AD-10); the group order is presentation.
  - `[low]` `[reject]` (blind 8) Focus on «Send Melding» drops when the band goes away; the end is not announced — needs a Student to order in the instant the lecturer sits on the button; a fix adds focus-management state.
  - `[low]` `[reject]` (blind 9) «Melding» does not remember the wall position for Back — not asked; Back returns to the Oversikt.
  - `[low]` `[reject]` (blind 10) Thin unit coverage of interaction code — covered end to end by `varselband.spec.ts` (keyboard to the wall link, table link, band live).
  - `[low]` `[reject]` (blind 11) Link column narrows cells at phone width — cells keep `minCell`; the wall region scrolls, as before.
  - `[low]` `[reject]` (blind 12) Hard-coded colours in the e2e — the values are the tokens; a palette change should fail a colour assertion.
  - `[low]` `[patch]` (blind 13) Tinted list row's `px-2` shifted its columns 8 px — the tint now uses `-mx-2 px-2`, so columns stay in line.
  - `[low]` `[patch]` (blind 14) Import order in `overview-page.tsx` — `cn` moved after `page-state`. The rest (three ways to build the target) rejected: band and row links go to different recipients.
  - `[false]` `[reject]` (blind 15) Table link behaviour undocumented — the README «Row links» paragraph names the table column and its Tab stop; draft copy is recorded under Decisions.
  - `[low]` `[reject]` (edge 1) Table link header empty when `copy.link` is omitted — the one caller passes it.
  - `[false]` `[reject]` (edge 2) First band after the Start date not announced — at that moment no game can wait (nobody has ordered yet), so the band mounts empty.
  - `[low]` `[reject]` (edge 3) A band that leaves and returns with the same text inside a minute is not re-announced — the text is the one last announced; a reset adds timing state.
  - `[false]` `[reject]` (edge 4) Enter on a link cell whose row lost its link opens Spillinnsikt — `target` is a link only when the row has one (`active.link && row.link`, or a row with no Uker, reachable only by a link).
  - `[false]` `[reject]` (edge 5) Table link focus then switch to wall lands on a Uke — the shared position is the game, as for row headers; the wall starts on that game's Uke by design (one Tab stop on cells).
- Matrix audit: One waits, Two wait, Tie, Several Seats, Former Student, None waits, Waiting no Seat — `test_overview_alert.py` (pure, ran); Before Start date — `test_overview.py::test_before_the_start_date…` (`alert` null); api answer with names and Assistant — `test_staff_see_whom…`. All ran and passed.

## Design Notes

- The choice lives in the api (AD-10) as a pure function so Epic 8 swaps the rule (earliest `takeover_due_at`) without touching the page; the page only reads `alert`.
- A game waiting for several Students names one in the band (the longest wait); the game list and wall still name all. «Send Melding» goes to that Student, as the AC says.
- The wall link is a grid cell, not a second Tab stop, so the wall stays one Tab stop (Story 7.2); the table is a plain table with a roving row header, so its link joins that roving pattern.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/sessions/test_overview_alert.py tests/sessions/test_overview.py` -- pass
- `cd frontend && npx vitest run src/components/charts src/modules/games/overview.test.ts` -- pass
- Before commit: backend full suite `--maxprocesses=8`; `npm run typecheck`, `npx vitest run`, `npm run lint:colours`, `npm run build`; stack rebuilt; Playwright `--workers=4` `overview`, `messages`, `homes`, `live-updates`, play-screen specs.

## Auto Run Result

Status: done

**Summary.** The overview api now names the Varselbånd's game (`alert`: game, Role, name, `user_id`, `since`), chosen in `sessions/overview.py` by a pure `_alert`: the waiting Class game whose wait started first, then the lowest game number; within it the Seat waited for longest, then chain order; the Student's name and id only while they are a Student of the Class. The Oversikt draws it as a full-width `restordre-fill` band, «Spill 2 venter på Noah (Grossist) i 23 t.», with the primary «Send Melding» to the Meldingsskjema preset to that Student (to the Class game when the Student has left). No band and nothing in its place when nothing waits. The band is announced politely (game and Student, not the ticking time) at most once a minute without moving focus, and follows the shown answer, so it holds while «Oppdater automatisk» is off. Every wall, table and game-list row has «Melding» to its Class game; the band's row is tinted with an `ink` link. In the wall the link is the row's last grid cell (Right from the last Uke; Up/Down link to link); in the table it is a column after the extra columns, the row's second Tab stop. «Venter ellers» leaves the band's game out («Ingen andre spill venter.»). No migration, no new query.

**Files.**
- `backend/app/modules/sessions/{schemas.py,overview.py}` -- `OverviewAlertOut`, `ClassOverviewOut.alert`, `_alert`.
- `backend/tests/sessions/test_overview_alert.py` (new, pure), `test_overview.py` -- choice matrix; api answer, before start, Assistant.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated.
- `frontend/src/components/charts/{matrix-wall-layout.ts,matrix-wall.tsx,matrix-table.tsx,README.md}` (+ tests) -- row link cell/column, tint, keyboard stops.
- `frontend/src/modules/games/{overview-band.tsx (new),overview-band.test.ts (new),overview.ts,overview-page.tsx,overview-wall.tsx,overview-rail.tsx,api.test.ts}`, `copy/nb.ts` -- band, row links, rail.
- `frontend/e2e/varselband.spec.ts` (new); `overview.spec.ts`, `game-insight.spec.ts` (Uke cells by `data-week`; rail with the band); `e2e/support/classes.ts` (tap-target check skips SVG controls).

**Review.** 20 findings (blind 15, edge case 5; Sonnet): 0 high, 0 medium, 13 low, 7 false. Patched (low): `_alert` fallback tests, tinted list row alignment, import order. Rejected the rest with the reasons above. Deferred: none. Follow-up review: not recommended (patched: high 0, medium 0, low 3).

**Verification.** After the patches: backend full suite 2857 passed (`--maxprocesses=8`); ruff check and format; frontend typecheck, Vitest 829 passed, `lint:colours`, `check:copy`, `next build`; stack rebuilt, then Playwright `--workers=4` `varselband`, `overview`, `game-insight`, `messages`, `homes`, `student-home`, `game-card`, `live-updates`, `order-confirm`, `week-advance`: 69 passed; axe on the Oversikt with the band at 1440 px and 320 px. New tests over 1 s: `varselband.spec.ts` (about 6 s, one live e2e). No test failed once and passed on rerun; the first `varselband` failure was a real selector clash with the median graph's `data-band`, fixed by naming the band `data-attention-band`.

**Decisions taken instead of the founder.**
- A game waiting for several Students names one in the band: the Seat waited for longest, then chain order (downstream first); «Send Melding» goes to that Student. The game row still lists all.
- Ties between games go to the lower game number; a game with no stored wait start counts from its earliest Seat.
- A waited-for Student no longer in the Class: the band names the Role and «Send Melding» goes to the Class game.
- The band stands above the headline counts, across the page; its accessible name is «Spillet som har ventet lengst» (draft).
- The announcement says «Spill 2 venter på Noah (Grossist).» without the duration, so only a new game or Student is read out.
- «Melding» also on the game list under the wall (besides wall and table), tinted the same for the band's game.
- Wall keyboard: the link is reached by Right from the last Uke; Home/End stay on the Uker; a not-started row is reached by its link.
- Table: the «Melding» column stands after Status, Venter på and Kjedekost (not after the Uker), with a read-only header «Melding».
- The e2e tap-target check skips SVG controls (the wall link's equivalent full-size link is in the game list).
- «Venter ellers» reads «Ingen andre spill venter.» when only the band's game waits.
- Assistant lecturer checked in the api test (same answer), not in a separate e2e.
- Draft copy `[ASSUMPTION]`: `nb.overview.band.label`, `band.said`, `rail.waiting.noneOther`, `wall.table.link`.
- Implemented in the builder's own context and reviewed by two Sonnet layers, as the orchestrator instructed.

**Residual risks.**
- Focus on «Send Melding» is lost if the band disappears while it has focus (rare; rejected above).
- «Venter ellers» with several waiting games is unit-tested only (one e2e game per Class session).
- Verification-gap and intent-alignment reviews skipped by instruction; the visual check is left to the separate visual agent.
