---
title: 'Story 7.7: Open one Game week by week in Spillinnsikt'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '45e481ef4f751bae9f3cb7bc99d2877d102a1940'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer on the Oversikt sees every game's wall row but cannot open one game and read, per Week and Seat, what came in, what was held, what was ordered, what it cost and who played it (FR-62, FR-34, UX-DR55). There is no staff insight endpoint and the AD-15 mark mapping knows only `guard_switch`.

**Approach:** A staff-only `GET /api/games/{id}/insight` (new `games.insight` policy, Class staff scope, ETag) returns the game head, its four Seats with names and an empty `links` slot, the customer demand series, the number of Weeks and, per Role, one row per opened Week built from the stored Week states, the Decision log and the occupancy history, with marks from the one `seat_mark`. A new Spillinnsikt page under the Oversikt renders it, opened by activating a wall or table row (or the game's name in the list), refetches on `game:<id>`, and Back lands focus on the same game.

## Boundaries & Constraints

**Always:**
- **Endpoint** `GET /api/games/{game_id}/insight` → `GameInsightOut`: `game_id`, `class_session_id`, `class_id`, `class_name`, `session_number`, `game_number`, `status` (`game_summaries`), `version`, `weeks_total` (snapshot `settings.weeks`), `demand: [{week, demand}]` (stored Detaljist `incoming_order` per opened Week), `seats` in chain order (Detaljist first) each `{role, holder: student|ai|free, name, links: [{kind, href}]}`, and `roles` in chain order each `{role, weeks: [{week, holder, name, incoming_order, incoming_delivery, inventory, backlog, order|null, cost, marks: [SeatMark]}]}`. Integers for units, decimal strings for money. Opened Weeks only (the finished state is no Week). Strong ETag of the body; `If-None-Match` → 304. Fixed number of queries.
- **Authz:** new action `games.insight` in `POLICIES` (Lecturer, Assistant) and `CLASS_STAFF_ROLES` (owner, assistant); a Game the Lecturer overview does not list (test, simulation), a Game of another Class, a missing Game, a bad id and any Student get the same 403 body (FR-5). Only this endpoint serves `weeks_total` and `demand` to staff.
- **Who played Week w:** the Seat's occupancy row in force (latest by id with `from_week ≤ w`): Student → name now (`classes.student_names`), name missing → `name` null; AI kinds → `ai`; none → `free`. Kind and reason for marks come from the Week's Decision log row when it exists, else the occupancy row in force.
- **Marks (AD-15):** extend `games/marks.py` `seat_mark` and `SeatMark` only. Seat marks from (`occupant_kind`, `reason`): `guard_switch` (rule_based + guard_switch, unchanged), `cost_limit`, `takeover_inactivity`, `takeover_staff`, `takeover_peer`, `reclaim`, `playout`; `initial`, `moved` → none. Order marks from (`decided_by`, `fallback`): `fallback_timeout`, `fallback_invalid_output`, `fallback_budget_exhausted`, `fallback_provider_error`; `none` → none. The insight calls it twice per row (seat args, then order args); the seat mark appears only in the Week where the Seat's (kind, reason) first appears, the order mark in every Week it applies.
- **Links:** `games.service.register_insight_links(provider)`; a provider `(session, game_id) -> Sequence[InsightLink(role, kind, href)]`; links go only on Student-held Seats; none registered; `modules/games` imports no later module.
- **Page** `/klasseokter/[sessionId]/oversikt/spill/[gameId]` (`frontend/src/modules/games/insight-page.tsx`): breadcrumb to Oversikt, h1 «Spill n», status word, four Seats upstream first (Fabrikk left) each with name, «KI-spiller» or «Ledig», and per Student Seat the link slot (empty list → «Forklaring og Debrief-sammendrag kommer når studenten har kommet dit.» [ASSUMPTION]). Not started → «Spillet har ikke startet.» and no tables. Else per Role (Detaljist → Fabrikk) an h2 and a table in its own `ScrollRegion` (Weeks as rows: Uke, Spilt av, Inn ordre, Inn levering, Lager, Restordre, Ordre, Kost, Merknad; header row sticky, Uke column sticky; region capped in height); every number formatted by `formatNumber` only, empty for an Order not placed; marks as text. Weeks as rows keeps names and marks readable without abbreviation (Design Notes).
- **Activation:** `MatrixWall` and `MatrixTable` take `onActivate(id)`: a click on a row, Enter on a focused cell (wall) or row header (table). The list's and allocation's «Spill n» become links. Before navigating, the Oversikt URL is replaced with `?spill=<id>` (and `&visning=tabell` from the table) so browser Back and the Oversikt crumb (same params) return with focus on that game's first wall cell or table row header.
- **Live:** `gameInsightKey(id)` added to the `game` topic in `topics.ts`; the page's query refetches on it (AD-8).
- Copy in `nb.insight` (`[ASSUMPTION]` where not the epic's); no page-level horizontal scroll at 320 px; Skjelett while loading; axe at 1440 and 320 px.

**Never:** no charts, Ordrestolper or Kjedebånd (7.8; no epic-9 chart files brought over); no Spillstyring (Epic 8); no «Melding» link (7.9); no Week total or demand shown on the Oversikt; no arithmetic in the web app; no migration; no second mark mapping.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Running | Weeks 1–2 run, 3 open | 3 rows per Role; Week 3 `order` null, shown empty | — |
| Not started | allocation, no Week | `roles` with empty `weeks`, seats with names; page «Spillet har ikke startet.» | — |
| Every reason/fallback | Decision log rows per value | the mark listed above for each | — |
| Student leaves Class | name not resolvable | `name` null → «Student» | — |
| Outsider | Student, other Class, test Game, missing, bad id | 403, one body | — |
| New Week | `game:<id>` event | new row appears without reload | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/marks.py`, `schemas.py:72` `SeatMark` -- the one AD-15 mapping to extend.
- `backend/app/modules/games/views.py:295` `table_status` -- other `seat_mark` caller (Student play screen); new marks reach `TableSeat.mark` (FR-34: takeovers shown to Students); `frontend/src/modules/games/seat-status.ts:36` reads only `guard_switch`.
- `backend/app/modules/games/repo.py` `decision_log:590`, `occupancy_history:619`, `week_states:415`, `summary:911`, `get_game` -- reads for the insight.
- `backend/app/modules/games/service.py:614-686` `ClassGameHead`, `class_game_head`, `class_game_weeks` -- pattern; new `games/insight.py` exported through `service`.
- `backend/app/modules/sessions/overview.py:198` `readable_game`, `:214` `game_weeks`, `:158` `_game_out` (holder/name rule) -- add `game_insight(user, id)`; `sessions/schemas.py` add `GameInsightOut` and parts.
- `backend/app/modules/sessions/routes.py:262` `get_game_weeks`, `_not_modified` -- route pattern.
- `backend/app/platform/authz.py:80-139` -- `games.insight`.
- `backend/app/modules/sessions/service.py:2543` pin providers -- registration pattern.
- `backend/tests/sessions/test_game_weeks.py` -- test pattern; `tests/sessions/test_game_end.py` `short_game`, `play_weeks`, `klass`; `tests/games/helpers.py` `tamper`.
- `frontend/src/components/charts/matrix-wall.tsx:202` `onKeyDown`, `:407` `Row`; `matrix-table.tsx:149,234` -- activation.
- `frontend/src/modules/games/overview-wall.tsx`, `overview-page.tsx:332` `GameRow`, `:378` `Allocation` -- wiring, return focus.
- `frontend/src/modules/games/api.ts` -- `useGameInsight`; `frontend/src/lib/api/topics.ts` -- game topic.
- `frontend/src/components/scroll-region.tsx` -- take epic-9's version unchanged (`scrollClassName`), `git checkout origin/epic-9 -- <path>`.
- `frontend/src/modules/identity/homes.ts:45` -- path helpers; `page-shell.tsx`, `breadcrumb.tsx`.
- `frontend/src/copy/nb.ts:2039` `nb.overview` -- add `nb.insight`.
- `frontend/e2e/overview.spec.ts`, `e2e/support/live-game.ts` -- e2e patterns.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/schemas.py`, `marks.py` (+ `tests/games/test_marks.py`) -- new marks; unit test every reason × kind and fallback.
- `backend/app/platform/authz.py` -- `games.insight`.
- `backend/app/modules/games/insight.py` (new), `service.py` -- `game_insight(session, game_id)`, `register_insight_links`, `InsightLink`.
- `backend/app/modules/sessions/schemas.py`, `overview.py`, `routes.py` (+ `tests/sessions/test_game_insight.py`) -- endpoint; tests: values equal stored states/Decision log, holder/name per Week, demand and weeks_total, assistant reads the same, 304, refusals identical, not started, every mark via tampered Decision log rows, a registered provider fills only Student Seats.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/scroll-region.tsx` -- from `origin/epic-9`.
- `frontend/src/components/charts/matrix-wall.tsx`, `matrix-table.tsx` (+ tests) -- `onActivate`.
- `frontend/src/modules/games/api.ts`, `insight.ts` (pure helpers + `insight.test.ts`), `insight-page.tsx`, `frontend/src/app/(app)/klasseokter/[sessionId]/oversikt/spill/[gameId]/page.tsx`, `identity/homes.ts`, `lib/api/topics.ts` -- page, route, live key.
- `frontend/src/modules/games/overview-wall.tsx`, `overview-page.tsx` -- activation, links, return focus.
- `frontend/src/copy/nb.ts` -- `nb.insight`.
- `frontend/e2e/game-insight.spec.ts` (new) -- open by wall click and by Enter in the table; header, seats, tables equal the api's values; new Week appears live; Back focuses the same game; a Student's api call is refused; axe at 1440 and 320 px, no page-level horizontal scroll.

**Acceptance Criteria:**
- Given the Oversikt, when the Lecturer clicks a wall row or presses Enter on a table row, then Spillinnsikt opens for that game with «Spill n», its status and four Seats Fabrikk first, and Back returns to the Oversikt with focus on that game.
- Given a running game, then each Role's table lists every opened Week with the api's stored values, who played it and its marks in text, and only those tables scroll sideways.
- Given a Student, staff of another Class, a test Game or a missing Game, then the insight endpoint answers the same 403.
- Given the page is open and the game advances, then the new Week appears without a reload.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both handbacks dropped; the findings were read from `review-blind-7-7.md` and `review-edge-7-7.md` in the session scratchpad.
- verdicts: 26 findings — high 0, medium 1, low 23, false 2, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) The wider `seat_mark` now gives the Student Setestatus (`TableSeat.mark`) takeover/cost-limit marks that `seat-status.ts` never words — the Seat already reads «KI-spiller» there (FR-34 holds); no screen changes; the epic asks for the one mapping, not a second one for Students.
  - `[low]` `[reject]` (blind) `decided_by` is a dead parameter of `seat_mark` — it was so since Story 6.14; the epic names the four inputs of the AD-15 mapping; the docstring says which ones mark.
  - `[low]` `[reject]` (blind) Every AI kind reads «KI-spiller»; LLM and Rule-based are not told apart — the story asks for «Student or AI player» and «KI-spiller» is the spine's term; a guard or cost-limit switch to Rule-based is marked.
  - `[low]` `[patch]` (blind) A Week the Decision log says a Student played, while a later row the same Week (a Takeover after the Order) is in force, shows «Student» without a name — patched: the Student is the Student row in force that Week (`insight.py`); the api test appends such a Takeover in Week 6 and asserts the Student's name on all six Weeks. The rest of the finding is false: two identical consecutive AI occupancies cannot follow each other without a Student between.
  - `[low]` `[patch]` (blind) A link kind with no copy shows its code; `key={href}` can collide — patched: an unknown kind reads «Åpne» (`nb.insight.otherLink`, Vitest), key is kind + href. Unguarded providers and unchecked hrefs: providers are this codebase's own modules registered at start-up, not input.
  - `[low]` `[reject]` (blind) The body-hash ETag saves no work and the page never sends `If-None-Match` — the epic asks for an ETag on every staff endpoint; names are in the body, so a version-only tag would answer 304 over a renamed Student.
  - `[medium]` `[patch]` (blind) `autoFocus` stays on after the return, so switching views moves focus to the game away from the Visningsbryter — patched: `OverviewWall` drops it on the first switch of view; the e2e asserts focus stays on the radio.
  - `[low]` `[patch]` (blind) Ctrl/Cmd-click on a list link rewrites the Oversikt's address; `?spill=` stays and refocuses on reload — patched: a modified or non-primary click leaves the address alone, and the Oversikt drops the params once read (e2e asserts the bare `/oversikt` after Back). The `useSearchParams`-without-Suspense part is false: `next build` passes and the route is dynamic.
  - `[low]` `[patch]` (blind) The Oversikt crumb returns to the wall even when the game was opened from the table — patched: opening from the table adds `?visning=tabell` to the insight address and the crumb carries it; the e2e clicks the crumb and finds the table with the row header focused.
  - `[low]` `[reject]` (blind) Rows give no hint that Enter or a click opens the game; each table is named three times — the list's «Spill n» links are the announced way in; the wall's keyboard reading is unchanged; axe passes at 1440 and 320 px.
  - `[low]` `[reject]` (blind) Scrolling inside scrolling and no side-by-side Roles; the open Week's values are unexplained — the story asks for per-Role tables each in its own region; the Rolle × Uke view is Story 7.8's.
  - `[low]` `[reject]` (blind) Marks joined by «. » without a final stop; draft copy has no tracked review point — cosmetic; every draft string is marked `[ASSUMPTION]` in `nb.ts` and listed under the decisions below.
  - `[low]` `[patch]` (blind) `unregister_insight_links` missing from `insight.__all__`; missing tests for a Student no longer in the Class, an unsnapshotted game, a 304 after a renaming — patched the `__all__`; the rest rejected: «Student» for a missing name is Vitest-covered (`holderText`), the others are untouched paths of code already tested.
  - `[low]` `[patch]` (edge) `?spill=` stays in the address and refocuses or resets the view on every remount or reload — patched with the address drop above.
  - `[low]` `[reject]` (edge) A list link always records the wall view; an Allocation game has no focus target on return — the list sits under the wall, whose cell is focused; before the Start date there is no wall to focus.
  - `[low]` `[patch]` (edge) Crumb returns to the wall while Back returns to the table — same patch as the crumb finding.
  - `[low]` `[patch]` (edge) Modified click rewrites the address — same patch as above.
  - `[low]` `[patch]` (edge) An upper-case id in the address refuses valid staff and misses `game:<id>` events — patched: the page lower-cases both ids before use.
  - `[low]` `[patch]` (edge) `keepPreviousData` could show another game's answer under a new game's address — patched by deleting it: a refetch of the same key keeps its data anyway.
  - `[low]` `[reject]` (edge) A failed live refetch shows no stale notice — the Tilkoblingslinje already covers a lost stream; a single failed read is rare and the next `game:<id>` event reads again; the fix adds a new state.
  - `[low]` `[patch]` (edge) `user_id` from the latest row in force, not the Week's Student — same patch as the blind finding.
  - `[false]` `[reject]` (edge) A,B,A repeats a seat mark — each return is a new switch in that Week, so the mark belongs there; the spec's «first appears» means where the occupancy began.
  - `[low]` `[reject]` (edge) Separate statements may read across a commit — one session, a fixed number of reads; a mixed answer is replaced by the next `game:<id>` refetch; snapshot isolation is new machinery for a rare race.
  - `[low]` `[patch]` (edge) Raw link kind and colliding keys — same patch as the blind finding.
  - `[low]` `[reject]` (edge) Setestatus now carries the new marks; its docstring is stale — duplicate of the first finding; the docstring («e.g. a Play guard switch») still holds.
  - `[false]` `[reject]` (edge) Enter on a non-header table cell does nothing — the table's body cells are not focusable; only the row header takes focus, and Enter there opens the game (e2e).
- Matrix audit: Running — `test_staff_read_every_week_of_every_role_as_stored` (Week 3 `order` null) and the e2e (the open Week's Order cell reads «ikke lagt inn» or the AI's Order); Not started — `test_a_game_not_started_has_its_seats_and_no_weeks` and Vitest «Spillet har ikke startet.»; Every reason/fallback — `test_every_reason_and_fallback_shows_its_mark…` and `tests/games/test_marks.py`; Student leaves Class — Vitest `holderText` («Student» for a null name); Outsider — `test_anyone_but_the_staff…` and the e2e Student call; New Week — the e2e (third row within 5 s). All ran and passed.

## Design Notes

- Weeks as rows, not columns: «Spilt av» names and mark texts are words; in Uke columns they would widen 36 columns or need abbreviations. The Rolle × Uke week-column view with Ordrestolper is Story 7.8's (epic-9's `OrderBarsTable`).
- The seat mark only where the Seat's occupancy began keeps «KI tok over (inaktiv)» from repeating on every later Week; the «Spilt av» column still says «KI-spiller» on each.
- Chain order in the api (Detaljist first) for both `seats` and `roles`; the page reverses the Seats for the upstream-left header.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_marks.py tests/sessions/test_game_insight.py tests/sessions/test_seat_status.py tests/games/test_play_guard_switch.py` -- pass
- `cd frontend && npx vitest run src/modules/games src/components` -- pass
- Before commit: full backend suite; `npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build`; Playwright `game-insight`, `overview`, `live-updates`, `homes`, play-screen specs -- pass

## Auto Run Result

Status: done

**Summary.** Spillinnsikt exists.
- `GET /api/games/{id}/insight` (new action `games.insight`, Class staff scope, body-hash ETag, 304): game head and status, `weeks_total`, the customer `demand` series, the four Seats with names and a `links` slot, and per Role every opened Week with stored incoming order and delivery, inventory, backlog, Order (Decision log), cost, who held the Seat and its marks. One answer (403) for Students, other Classes, test Games, missing Games and bad ids.
- The one AD-15 mapping (`games/marks.py` `seat_mark`, `SeatMark`) gained a mark for every other reason (cost limit, three Takeovers, reclaim, playout) and every fallback; the seat mark stands in the Week the occupancy began, the Order mark in its own Week. `register_insight_links(provider)` in `games.service`, none registered.
- Page `/klasseokter/{id}/oversikt/spill/{gameId}`: «Spill n», status, Seats Fabrikk first with names or «KI-spiller» and the link slot line; «Spillet har ikke startet.» before the start; per Role (Detaljist → Fabrikk) a table with Weeks as rows in its own scroll region (sticky header row and Uke column, height cap). Refetches on `game:<id>`.
- Opening: click on a wall or table row, Enter on a wall cell or table row header, or the «Spill n» link in the list and the allocation. Back and the Oversikt crumb return focus to that game, in the view it was opened from; the address then drops the return params.

**Files.**
- `backend/app/modules/games/insight.py` (new), `marks.py`, `schemas.py` (`SeatMark`), `service.py` (exports); `backend/app/platform/authz.py` (`games.insight`).
- `backend/app/modules/sessions/schemas.py` (`GameInsightOut` and parts), `overview.py` (`game_insight`, `insight_etag`), `routes.py` (route).
- `backend/tests/games/test_marks.py` (new), `tests/sessions/test_game_insight.py` (new), `tests/sessions/test_seat_status.py` (6.14 mapping test narrowed to the guard switch).
- `frontend/src/lib/api/openapi.json`, `schema.ts` (regenerated); `lib/api/topics.ts` (+ test).
- `frontend/src/components/scroll-region.tsx` — taken unchanged from `origin/epic-9` (`scrollClassName`); no other epic-9 file brought over.
- `frontend/src/components/charts/matrix-wall.tsx`, `matrix-table.tsx` (+ tests): `onActivate`, `autoFocus`.
- `frontend/src/modules/games/insight.ts`, `insight-page.tsx`, `insight.test.ts` (new); `api.ts` (`useGameInsight`); `overview-wall.tsx`, `overview-page.tsx` (activation, links, return focus); `identity/homes.ts` (paths); `app/(app)/klasseokter/[sessionId]/oversikt/spill/[gameId]/page.tsx` (new).
- `frontend/src/copy/nb.ts` (`nb.insight`); `frontend/e2e/game-insight.spec.ts` (new).

**Review.** 26 findings (blind 13, edge case 13; Sonnet): 0 high, 1 medium, 23 low, 2 false. Patched: the medium entry (autofocus lifetime) and 8 low entries (Student name in a Takeover Week, link label and key, modified clicks and the address drop, crumb view, `__all__`, upper-case ids, `keepPreviousData`); 4 of the 23 low rows are duplicates sharing those patches. Rejected: 2 false and 11 low, reasons in the triage log. Deferred: none. Follow-up review: not recommended (one medium patched and e2e-tested, no high).

**Verification.**
- Backend: full suite 2835 passed in 102 s after the patches (94 s before). The first full run had 1175 setup errors, all `psycopg ConnectionTimeout` while the stack was building and the other lane tested; the rerun passed. New tests over 1 s: `test_every_reason_and_fallback…` 2.4 s and `test_staff_read_every_week…` 2.1 s (each plays a short game), `test_anyone_but_the_staff…` 1.2 s.
- Frontend: typecheck, Vitest (62 files, 794 tests, none over 1 s), `lint:colours`, `check:copy`, `next build` pass.
- Playwright after the last change: `game-insight`, `overview`, `live-updates`, `homes`, `order-confirm`, `week-advance` — 50 passed (4 workers). Earlier runs: 9 failures with 12 workers, 8 of them `nextMail` 15 s timeouts under load (overview specs, live-updates «a co-owner…», week-advance «four Students…» and «two Students…»), which passed on rerun; one real failure — the list's «Spill n» link was 39 px wide at 320 px — fixed with `min-w-tap-target-min`. Axe runs at 1440 px (opened game) and 320 px (no page-level scroll, the Role table's region scrolls).

**Decisions taken instead of the founder.**
- Weeks as rows in the per-Role tables (columns Uke, Spilt av, Ordre inn, Levering inn, Lager, Restordre, Ordre, Kost, Merknad), so names and marks are words; the week-column Rolle × Uke view is left to Story 7.8.
- Insight route under the Oversikt: `/klasseokter/{id}/oversikt/spill/{gameId}`; the list's and the allocation's «Spill n» also link there.
- Mark set and copy `[ASSUMPTION]`: «KI tok over etter ventetiden», «KI satt inn av faglærer», «KI satt inn av gruppa», «Studenten tok setet tilbake», «KI spilte spillet ferdig», «Byttet til regelbasert KI (spillvakt|kostnadsgrense)», «Reserveordre: …» per fallback; the link slot line «Forklaring og Debrief-sammendrag kommer når studenten har kommet dit.»; link words «Forklaring», «Debrief-sammendrag», «Åpne»; «Uke for uke», «Detaljist uke for uke».
- The seat mark shows only in the Week the occupancy began; the fallback mark in each Week it applies.
- The new marks also reach the Student Setestatus' `mark` field (one mapping); the Student screen still words only the guard switch.
- `demand` is the stored customer demand of opened Weeks; `weeks_total` is served but not shown.
- The builder implemented in its own context, as the orchestrator instructed.

**Residual risks.**
- The insight ETag needs the whole read before it can answer 304; the page does not use it.
- Takeover marks are tested with tampered Decision log rows; Epic 8 writes the real ones.
- Verification-gap and intent-alignment reviews were skipped by instruction.
