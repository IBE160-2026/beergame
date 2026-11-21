---
title: 'Story 6.6: See my Seat''s Week in the week table'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '6c438d26d9f1507eb05cd4bc227d58409d357de0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The play route `/spill/{id}` shows only «Uke n», Role, game and the Seats. A Student cannot see their Seat's numbers: there is no play endpoint returning `seat_state`, no week table, no Totalkostnad, and the number formatter lacks kroner and a narrow-cell option.

**Approach:** Add one play endpoint `GET /api/me/games/{id}/play` returning `{seat_state, table_status, server_now, next_change_at}` for the Student's own running game, with `net_inventory` added to the engine's per-Week values and to `SeatState` (schema_version 2, version-1 rows upgraded on read). The play screen gets the Topplinje with Totalkostnad, an HTML week table in one labelled scroll region (phone: nå − 7 … nå + 4; ≥ 1024 px: Uke 1 … nå + 4 with Sendt and På vei, two-column layout), and a Lenke to «Regler før første ordre».

## Boundaries & Constraints

**Always:**
- `SeatState` stays the only number source. New field `net_inventory: int` (Lager − Restordre, computed in `engine.view`) on `WeekValues` (history) and `SeatDetail`/`SeatState` (nå). `SeatState.schema_version` becomes `Literal[2] = 2`; a `mode="before"` validator upgrades a version-1 dict (stored `state_seen`) by filling `net_inventory = inventory − backlog` on it and each history item, so `checks._decision_log` still matches. Engine coverage stays 100 %.
- Envelope `PlayOut` (sessions schemas): `seat_state: SeatState` (games model as is), `table_status: TableStatusOut {seats: list[TableSeatOut]}`, `server_now` (database clock, `repo.clock_now`), `next_change_at: datetime | None` (None until a due time exists: Story 6.14). Route under policy `games.read_own`, operation `getMyGamePlay`; same `_own_locked_game` check (403 `forbidden`, identical body, for any other id); 409 `game_not_running` when `play_status` is not `running`. Seat = the Student's own `StudentGame.role`.
- Web computes no game quantity: every cell shows a `seat_state` field as returned (history `WeekValues`, then nå's `incoming_order`, `incoming_delivery`, `shipped`, `net_inventory`, `supply_line`, `position`, `week_cost`; Levering right of nå = `supply_line_slots` by `arrival_week`). Only display logic: column window, matrix-step bin, formatting.
- Table: `<table>` in rem/em, `<th scope="col">` per Uke (sr-only «Uke » prefix), `<th scope="row">` per row incl. «Uke», cells not focusable, weight 400, only the nå Uke number bold (`table-now`). Rows phone: Uke, Ordre inn, Levering, Netto lager, Posisjon, Din ordre, «Kost, kr»; ≥ 1024 px adds Sendt (after Levering) and På vei (after Netto lager). Columns: phone nå − 7 … nå + 4 (from Uke 1 when nå < 8); ≥ 1024 px Uke 1 … nå + 4, via CSS (`hidden lg:table-cell`). Future columns `future-tint`. Netto lager cells: matrix steps (|v| 1–9/10–19/20–34/35+, `net-pos-*`/`net-neg-*`, 0 = `net-zero`), `ink` text on steps 1–2, `paper` on 3–4, signed with true minus. Posisjon plain `ink`, no fill. Levering arrivals right of nå: outlined box plus sr-only «, bestilt, ikke garantert»; a visible key line under the table «Tall i ramme: bestilt, ikke garantert.» [ASSUMPTION draft]. Din ordre at nå: empty dashed cell. «Kost, kr» narrow format.
- Region: `role="region"`, name «Graf og tabell», `tabIndex=0`, `overflow-x: auto` with a visible thin scrollbar; sticky row-label column on `paper` (`row-label-phone`/`row-label-laptop` minimum, wraps); week columns `w-[1.6em] min-w-[1.6em]`, no horizontal padding; on phone the region sits at the 16 px chart gutter. On load (and when `seat_state.week` changes) `scrollLeft = clamp(nåColumn.offsetLeft − labelWidth, 0, max)`. Caption «Sveip for tidligere uker» shows while `scrollLeft > 0`.
- Topplinje: h1 «Uke 11», «Grossist, Spill 17» (`ink-secondary`) under it, at right «Totalkostnad» (`caption`) over «68,00 kr» (`figure-total`), plain text in this story. Never the number of Weeks.
- Formatter `frontend/src/lib/number-format.ts` extended in place: `kroner: true` → two decimals + no-break space + «kr»; `narrow: true` → trailing fraction zeros dropped («6.0000» → «6», «6.5000» → «6,5»). Vitest covers both.
- While the game or the envelope loads, the page shows the Skjelett with the table's rows and 12 columns (`PageShell` `skeleton` prop). Live: `topics.ts` maps `game:<id>` to the envelope key (`["games","mine",id,"play"]` sits under `["games","mine",id]`; verify prefix invalidation, else add it).
- Copy in `nb.games.play`, drafts marked [ASSUMPTION]; table terms from `nb.terms`.

**Never:** No graph, now-line, Kjedebånd, Ordrefelt, typed preview, Setestatus line, «Alle rader og kostnad» or «Kostnad så langt» (6.7+); no Totalkostnad button; no reference Order, number of Weeks, future demand or other Seat's numbers in the envelope; no second number formatter; no change to `sprint-status.yaml` or «class-of-1994».

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Own running game | Student, Week 3 | 200 envelope; `seat_state.week == 3`, own Role, history of 2 | — |
| Hidden information | each of 4 Roles | no `weeks`, reference-order or demand-series key anywhere; `incoming_orders` length = week; no other Role's numbers | — |
| Not running | `ready` / `finished` game | 409 `game_not_running` | play page shows 6.5's not-running view |
| Not own | other's / unknown / not-uuid / outsider | 403 `forbidden`, same body | access denied page |
| Stored v1 `state_seen` | Decision log row without `net_inventory` | reads as v2 with it filled; finished-game check ok | — |

</intent-contract>

## Code Map

- `backend/app/engine/view.py:152` `WeekValues`, `:181` `SeatDetail`, `:211` `seat_detail` -- add `net_inventory`; engine tests in `backend/tests/engine/` (find the `seat_detail` test) keep 100 %.
- `backend/app/modules/games/schemas.py:161` `SeatState` -- version 2 + v1 upgrade validator (pattern: `engine/settings.py:107` `_upgrade_version_1`).
- `backend/app/modules/games/checks.py:156` -- compares stored vs rebuilt; must stay equal after upgrade.
- `backend/app/modules/games/repo.py:343` `clock_now`; `service.py:237` `play_status`, `:252` `own_game`; `views.py:121` `seat_state(game_id, seat)` (own session).
- `backend/app/modules/sessions/{schemas.py:383,service.py:1219-1313,routes.py:574}` -- `PlayOut`, `student_play_of`, route beside `get_my_game`.
- `backend/tests/sessions/test_start_game.py` -- helpers `confirmed`, `sweep.run(START + MINUTE)`, `task_done`, `email(i)`, `call`; `games.commands.place_order(game_id, role, week, order, "guided"|"student")`, guided Weeks need `"guided"` and the guided order.
- `frontend/src/modules/games/{play-page.tsx,api.ts}`, `identity/page-shell.tsx` (add `header`, `skeleton` props), `components/skeleton.tsx`, `identity/homes.ts` (briefing path), `lib/api/topics.ts`.
- `frontend/src/theme/theme.css` -- tokens `net-*`, `future-tint`, `table-cell`, `table-now`, `figure-total`, `row-label-*`, `gutter-phone-chart`.
- `frontend/e2e/game-start.spec.ts` -- stand-in pattern (`withGame`, `page.route`), `student-home.spec.ts` 200 % text + `textAtLeast13px`; `support/classes.ts` `expectAccessible`.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/view.py` + engine test -- `net_inventory` on `WeekValues`, `SeatDetail`.
- `backend/app/modules/games/schemas.py` -- `SeatState` v2 with v1 upgrade; test in `backend/tests/games/` for the upgrade and the finished-game check on a v1 row.
- `backend/app/modules/sessions/{schemas,service,routes}.py` -- `PlayOut`, `TableStatusOut`, `student_play_of`, `GET /api/me/games/{game_id}/play`.
- `backend/tests/sessions/test_play.py` (new) -- matrix rows over the real api (four Students, played to Week ≥ 6 so history exists).
- `backend/tests/games/test_play_fixture.py` (new) + `frontend/e2e/fixtures/play-week-11.json` -- the e2e stand-in envelope's `seat_state` is the engine's Grossist in Uke 11 of a Classic game with fixed Orders; the test rebuilds and compares it.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/lib/number-format.ts` (+ test) -- `kroner`, `narrow`.
- `frontend/src/modules/games/week-table.ts` (+ `week-table.test.ts`) -- pure: columns and rows from `seat_state` (window, cell kinds, bins, formatted text).
- `frontend/src/modules/games/week-table.tsx` -- the region and table.
- `frontend/src/modules/games/play-page.tsx`, `api.ts`, `page-shell.tsx`, `skeleton.tsx`, `topics.ts`, `copy/nb.ts` -- envelope query, Topplinje, layout, Lenke, Skjelett.
- `frontend/e2e/week-table.spec.ts` (new); `game-start.spec.ts` -- stand-in envelope route for running games.

**Acceptance Criteria:**
- Given the Uke 11 fixture at 360 px and 100 % text, when the play page renders, then the Topplinje shows «Uke 11», «Grossist, Spill 17», «Totalkostnad» over the fixture's total in «n,nn kr», 12 week columns (4 … 15) are fully visible with «11» bold, rows are as listed, Netto lager cells carry matrix fills, Levering 12–14 are outlined with the screen-reader label, Din ordre at 11 is a dashed empty cell, and the briefing Lenke is present.
- Given 320 px, then 10 columns are visible, nå + 4 is the right edge, the caption «Sveip for tidligere uker» shows; at 320 and 360 px with 200 % text the nå column is in view; at every size no text < 13 px or clipped, no page-level horizontal scroll, axe clean.
- Given 1440 px, then two columns, the table runs Uke 1 … 15 with Sendt and På vei.
- Given a throttled 4G profile, when the play page opens, then the Skjelett shows and then the table within 3 s.
- Given Vitest, then `kroner`/`narrow` formatting and the week-table model (window at nå < 8, bins, arrivals) pass.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 33 findings — high 0, medium 0, low 21, false 12, maybe-false 0 (the 4G finding, raised by blind and intent, has one shared row)
- findings:
  - `[low]` `[reject]` blind: `student_play_of` reads status, people, state and clock at slightly different moments. `seat_state` is read for the Week `play_status` named, which stays opened even if the game advances or finishes meanwhile; the next `game:` event refetches. No wrong number can show.
  - `[low]` `[patch]` blind: `server_now`/`next_change_at` accepted naive datetimes. Now `AwareDatetime`; OpenAPI regenerated.
  - `[false]` `[reject]` blind: shipped goods labelled "ordered, not guaranteed". The story and EXPERIENCE.md (stance 3) label every known arrival right of nå that way.
  - `[false]` `[reject]` blind: phone cannot reach Weeks before nå − 7. The story fixes the phone window at nå − 7 … nå + 4; «Sveip» refers to hidden columns of that window.
  - `[low]` `[patch]` blind: a `game_not_running` envelope showed a page error. The page now refetches the game, which then shows its finished/next-action view.
  - `[false]` `[reject]` blind: `history[week − 1]` by position. `engine.seat_detail` builds `history` as Weeks 1 … t − 1 in order, without gaps.
  - `[low]` `[reject]` blind: no validator that v2 `net_inventory == inventory − backlog`. Every v2 state is built by `engine.seat_detail`; a guard adds complexity for an unreachable case (`checks._decision_log` already compares against a rebuild).
  - `[false]` `[reject]` blind: v2 in the LLM prompt and Decision log untested. `players/llm.py` reads named fields; the full backend suite (LLM prompt tests, finished-game checks on v2 rows) and `prompts check` pass.
  - `[false]` `[reject]` blind: 409 docs wrong for `playing_out`. Docs say "before the start and after the end"; playing out is neither.
  - `[low]` `[reject]` blind + intent: the 4G test's stand-in envelope is fulfilled in the browser, unthrottled. True; the JS, page and session requests are throttled and the run takes ≈ 2.2 s of the 3 s. A throttled real envelope needs a really running Class game (Start date + sweep), which the e2e stand-in pattern of 6.2–6.5 avoids; the envelope is one ≈ 6 kB request.
  - `[false]` `[reject]` blind: no refresh at Week turnover. Every command emits `game:<id>` (`_commit_change`), and `topics.test.ts` now pins that `game:<id>` invalidates `playKey`.
  - `[low]` `[reject]` blind: PlayView branches without a component test. The forbidden-game path is covered by `game-start.spec.ts`; the rest is shown by the e2e flows.
  - `[false]` `[reject]` blind: tab title and Topplinje may show different Weeks. The Topplinje only renders when the envelope is shown, and the title then reads the same envelope.
  - `[low]` `[patch]` blind: the empty Din ordre cell said nothing to a screen reader. It now reads «ingen ordre ennå» [ASSUMPTION draft]; e2e asserts it.
  - `[low]` `[patch]` blind: fixture builder hard-coded four Guided Weeks. The offset now comes from `settings.guided_weeks`.
  - `[low]` `[patch]` blind: negative `netStep` edges untested. Added −19, −34, −35.
  - `[false]` `[reject]` edge: `ViewError` when a running game has no open Week. A running or playing-out Game always has an opened Week (6.5 triage).
  - `[low]` `[reject]` edge: reads from different moments. As blind 1.
  - `[low]` `[patch]` edge: `game_not_running` page error. As blind 5.
  - `[false]` `[reject]` edge: stale cached 403 envelope. A 403 envelope means the game is not the Student's; the game read answers the same.
  - `[low]` `[reject]` edge: the Skjelett draws 12 columns in Uke < 8. The Skjelett stands while the Week is still unknown; cosmetic.
  - `[low]` `[patch]` edge: text-size change without width change did not re-scroll. The observer now also watches the table and the scroll width.
  - `[false]` `[reject]` edge: history indexed by position. As blind 6.
  - `[low]` `[reject]` edge: `game-start.spec.ts` serves the Uke 1 envelope for other Weeks. Test-only; every running state there is Week 1 or 11.
  - `[low]` `[patch]` edge (claim): `test_play.py` played only to Week 3. Now Week 6, past the Guided Weeks, with Student Orders.
  - `[low]` `[reject]` edge (claim): the spec names `frontend/e2e/fixtures/`. The fix is a spec edit; the fixtures sit in `frontend/src/modules/games/fixtures/` because the Docker build typechecks Vitest files and excludes `e2e/`.
  - `[low]` `[patch]` verification-gap: re-scroll after a change of layout untested. New e2e «a changed width brings nå back into view»; the Week-change path is pinned when the Ordrefelt can advance a Week (6.11/6.12).
  - `[low]` `[patch]` intent: Week 3 only; "customer demand only for the Retailer" not asserted per Role. Week 6 now, and the test asserts the Retailer's incoming orders are the demand series and no other Role's are.
  - `[low]` `[reject]` intent: screen tested against stand-ins, not the live endpoint. The stand-ins' `seat_state` is pinned to the engine and validated as `PlayOut`; the live endpoint is pinned by `test_play.py`.
  - `[low]` `[reject]` intent: `table_status` has no screen consumer. «Setene» shows the same `table_status` through `useMyGame`; Setestatus (6.14) will read the envelope.
  - `[false]` `[reject]` intent: `next_change_at` always null. Story 6.14 adds due times; the field is in the envelope as required.
  - `[low]` `[patch]` intent: tablet layouts untested. Added 1024 × 768 (laptop layout) and 768 × 1024 (phone layout) to the viewport matrix.
  - `[false]` `[reject]` intent (R4): «68,00 kr» not shown. The fixture is the engine's real Uke 11 (82,00 kr); the format is the story's.

## Design Notes

Founder-level calls: `net_inventory` is added to the engine/`SeatState` rather than subtracted in the browser (AD-1/AD-10), with an upgrade of stored version-1 rows instead of a migration; `next_change_at` is null until a due time exists (6.14); `server_now` is the DB clock (AD-20); 409 `game_not_running` outside `running`; Totalkostnad is text until «Alle rader og kostnad» exists; the laptop layout switches at 1024 px (tablets in landscape at ≥ 1024 px get it; narrower landscape tablets keep the phone layout); the right column holds «Setene» until the Ordrefelt arrives; no now-line before the graph (6.7); the key line and screen-reader label copy are drafts.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/engine tests/games/test_play_fixture.py tests/sessions/test_play.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run build && npx playwright test --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** A Student's play route now shows their Seat's Week. New `GET /api/me/games/{id}/play` (policy `games.read_own`, operation `getMyGamePlay`) answers the own running Class game with `{seat_state, table_status, server_now, next_change_at}`: 403 `forbidden` alike for every other id, 409 `game_not_running` before the start and after the end. `engine.view` gains `net_inventory` (on `SeatDetail` and each `WeekValues` row); `SeatState` is `schema_version` 2 and reads stored version-1 `state_seen` rows as version 2 (`net_inventory` filled from their inventory and backlog), so finished-game checks still match. The play screen shows the Topplinje («Uke 11», «Grossist, Spill 17», «Totalkostnad» over «82,00 kr»), the week table in one scroll region «Graf og tabell» (phone: nå − 7 … nå + 4 with Uke, Ordre inn, Levering, Netto lager, Posisjon, Din ordre, «Kost, kr»; from 1024 px Uke 1 … nå + 4 with Sendt and På vei in a two-column layout), matrix-step Netto lager cells, outlined known arrivals labelled «bestilt, ikke garantert», an empty dashed Din ordre at nå, «Sveip for tidligere uker» while earlier Uker are scrolled away, a Lenke to «Regler før første ordre», «Til Hjem» and «Setene». The number formatter gains `kroner` and `narrow` in place. The Skjelett shows the table's rows and 12 columns.

**Files.**
- `backend/app/engine/view.py`, `backend/tests/engine/test_view.py` -- `net_inventory`.
- `backend/app/modules/games/schemas.py`, `service.py` -- `SeatState` v2 + v1 upgrade; `database_now`.
- `backend/app/modules/sessions/{schemas,service,routes}.py` -- `PlayOut`, `TableStatusOut`, `student_play_of`, `GameNotRunning`, the route.
- `backend/tests/sessions/test_play.py`, `backend/tests/games/test_seat_state_version.py`, `test_play_fixture.py` (new); `test_views.py` -- version 2.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated; `topics.ts` comment, `topics.test.ts` pins `playKey`.
- `frontend/src/lib/number-format.ts` (+ test) -- `kroner`, `narrow`.
- `frontend/src/modules/games/{week-table.ts,week-table.test.ts,week-table-view.tsx,play-page.tsx,api.ts}`, `fixtures/play-week-{1,11}.json` -- model, view, page, `usePlay`, stand-ins. (The view is `week-table-view.tsx`, not `week-table.tsx`, so it does not shadow the model; the fixtures sit under `src/` because the Docker build typechecks Vitest files and leaves out `e2e/`.)
- `frontend/src/modules/identity/page-shell.tsx` -- `header` and `skeleton` props.
- `frontend/src/copy/nb.ts` -- `games.play.table` (drafts [ASSUMPTION]: «bestilt, ikke garantert», «Tall i ramme: bestilt, ikke garantert.», «ingen ordre ennå»).
- `frontend/e2e/week-table.spec.ts` (new), `game-start.spec.ts` -- stand-in envelope.

**Review.** One pass, four layers, 33 findings (high 0, medium 0, low 21, false 12). Patched (11 rows, all low): aware datetimes; refetch of the game on `game_not_running`; screen-reader text for the empty Din ordre; guided-week offset in the fixture builder; negative `netStep` edges; re-scroll on scroll-width change; api test to Week 6 with a per-Role customer-demand assertion; resize e2e; tablet landscape/portrait viewports. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. No high or medium entry was patched.

**Founder-level decisions taken (no human in the loop).** Netto lager comes from a new engine/`SeatState` field (`net_inventory`, schema_version 2) instead of browser arithmetic, with stored version-1 rows upgraded on read rather than migrated; `server_now` is the database clock; `next_change_at` is null until Story 6.14 adds due times; 409 `game_not_running` outside running/playing-out; the play endpoint does not itself enforce the briefing gate (the page does, as in 6.5); Totalkostnad is plain text until «Alle rader og kostnad» exists (6.16); laptop layout from 1024 px (tablet landscape ≥ 1024 px gets it, portrait the phone layout); the right column holds the Lenker and «Setene» until the Ordrefelt arrives; no now-line before the graph (6.7); only the nå Uke number is bold; week columns are exactly 1.6 em with no side padding so 12 fit at 360 px; draft copy listed above; the visible key line under the table; the fixture is the engine's real Uke 11 (82,00 kr, not the mockup's 68,00 kr). The implementation ran in the orchestrating agent's own context (caller's runbook), not a separate implementation subagent.

**Verification.**
- Backend: 2674 passed (65 s), engine coverage 100 %, ruff check/format clean, `app.ai.cli prompts check` ok. Tests over 1 s: `test_the_envelope_is_the_own_seat_in_the_open_week_for_every_role` ≈ 2.5 s (four Students, five Weeks of Orders), `test_any_other_game_is_refused_alike` ≈ 1.3 s.
- Frontend: typecheck, Vitest 504 passed, `check:copy`, build; compose rebuilt; full Playwright `--workers=2`: 330 passed (5.6 min). New e2e tests 0.3–1.2 s, except the throttled-4G test ≈ 2.2 s (throttling is the point); no fixed sleeps.
- No migration.

**Residual risks.** The 4G check throttles the page and session requests but not the stand-in envelope. The re-scroll after a Week change is pinned only once the Ordrefelt can advance a Week. Draft copy awaits the founder (#31).
