---
title: 'Story 8.12: Fill every waited-for Seat in one action'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '07447ff8d890567fb1cf7b22f78cd52b18068f01'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** At the start of a Lab hour a Lecturer must put AI players in stuck Seats one by one (Story 8.5); FR-37 asks to fill every waited-for Seat of one Class game, or of all of them, in one action. "Waited for" is also defined twice today (inline in `rules.game_status` and in `games.overview.recompute`).

**Approach:** One pure predicate `games.rules.waited_for(turn, *, guided)` used by `game_status` and the summary. The `takeover` command gains `only_waited_for`, which re-checks under the Game lock and skips a Seat that ordered since or now has Tilrettelegging. A Lecturer-only batch (`GET`/`POST /api/class-sessions/{id}/waited-for-seats`) lists the waited-for Seats from `game_summaries` (the rows that give «Venter») and loops one `takeover` per Seat. Spillstyring gets the per-game secondary button, and the Oversikt header gets a Lenke to a «Sett inn KI-spillere» page.

## Boundaries & Constraints

**Always:**
- `rules.waited_for(turn, *, guided) -> bool`: `occupant_kind == student` and `wait_started_at` set and not `has_ordered(turn, guided=guided)`. `game_status` is `waiting` when any open-Week turn is `waited_for` (else `running`); `games.overview.recompute` builds `waiting_for` with it. No migration.
- `commands.takeover(..., only_waited_for: bool = False)`: when true, after `can_take_over` passes, under the same lock it refuses with 409: `game_paused` (a paused game), `order_exists` (the Seat has ordered: `has_ordered`), `not_waited_for` (no wait started), and `tilrettelegging` (the Student's time factor is above 1, read through `_time_factors`). Everything else is Story 8.5's staff Takeover: reason `takeover_staff`, `actor_user_id` = the Lecturer, `ensure_order`, audit `seat.taken_over`, the notices and events, and in a Guided Week the Seat is taken from this Week and `_settle` advances.
- `games.service.waited_for_seats(session, class_session_id, game_id=None) -> list[WaitedSeat(game_id, game_number, seat_id, role, user_id, since)]`: read from the `waiting` summaries' `waiting_for`, with the Seat ids from one `seats` read. The order is game number, then chain order. A paused game has no waited-for Seats (its status is `paused`). `games.service.class_seat_games(session, class_session_id, seat_ids) -> dict[seat_id, game_id]` maps the posted ids to games of this Class session.
- Tilrettelegging here means a time factor above 1 (`sessions.service.time_factors`). Such Seats are left out of the count and the press, and are listed as «Ikke med (tilrettelegging): …».
- `authz` policy `games.fill_seats` = Lecturer / OWNER only.
- `sessions/overview.py`:
  - `waited_for_page(user, session_id)` → `WaitedForSeatsOut {class_session_id, class_id, class_name, session_number, server_now, games: [{game_id, game_number, seats: [{seat_id, role, name, since}]}], left_out: [{seat_id, role, name}]}`.
  - `fill_waited_for(user, session_id, seat_ids)`: ids not of this session are skipped `not_listed`. Seats are grouped by Game, at most 4 Games at a time, seats of one Game in turn, each `takeover(only_waited_for=True)` in its own transaction. A `CommandError` is skipped with its code; any other exception is logged and skipped `failed`; neither stops the others. Answers `FilledSeatsOut {inserted, skipped: [{seat_id, reason}]}`.
  - `class_overview` gains `fillable: int` (Lecturer only, else 0).
  - `game_insight` gains `waited_for: [InsightWaitedOut {seat_id, role, name}]` and `left_out` (same shape), filled only for a Lecturer.
- Routes: `GET /api/class-sessions/{id}/waited-for-seats` (`getWaitedForSeats`) and `POST` (`fillWaitedForSeats`, body `FillSeatsIn {seat_ids: list[UUID], 1..4000}`), both `authz.require("games.fill_seats")`, 403 `forbidden` for anyone but a Lecturer of the Class. Regenerate the api client with `npm run api:generate`.
- Frontend:
  - `FillStyring` in Spillstyring after «I rommet» when `waited_for` is non-empty (or a result is held). It shows the draft consequence line above the secondary «Sett inn KI-spiller i alle seter som blir ventet på (2)», then «Ikke med (tilrettelegging): Jonas» when `left_out` is non-empty. A press posts that game's listed seat ids. «2 KI-spillere satt inn.» (`role="status"`, `tabindex="-1"`, focused) replaces it. A refusal or failure shows inline and the button stays active.
  - Oversikt header: the Lenke «Sett inn KI-spiller i alle seter som blir ventet på (9)» when `fillable > 0`, linking to `/klasseokter/{id}/oversikt/sett-inn`.
  - Page `fill-seats-page.tsx`: GuardedPage lecturerHome, crumbs ending in «Sett inn KI-spillere», title «Sett inn KI-spillere». It lists per game «Spill 2» with seats «Noah, 23 t» (`waitDuration` from `server_now`), then «Ikke med (tilrettelegging): …», the line «Studentene kan ta setene tilbake fra neste Uke.» and the primary «Sett inn 9 KI-spillere». A press posts the listed ids, then `router.replace` to the Oversikt with `?satt-inn=<n>`, where «9 KI-spillere er satt inn.» takes focus and the address is cleaned. When there are none it shows «Ingen seter blir ventet på nå.» and no button. 403 shows AccessDenied.
  - The page's key is read again on `session:` events (`topics.ts`).
  - Copy in `nb.ts` (`spillstyring.fill`, `overview.fill`); pure helpers in `modules/games/fill-seats.ts`. A count of 1 reads «1 KI-spiller satt inn.» / «1 KI-spiller er satt inn.» / «Sett inn 1 KI-spiller».
- Spine Deferred item: add «Decided in Story 8.12» for the batch Takeover.

**Never:** no Assistant lecturer or Student access to the batch; no Takeover of a Seat with Tilrettelegging or one that ordered since through the batch; no second occupancy row on a repeat; no change to the per-Seat action of Story 8.5; no game per test; no DB-vs-host time comparison; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Error |
|---|---|---|---|
| Two waiting games, 3 waited-for Seats, one with factor 2 | GET | 2 listed in two games, `left_out` 1; Oversikt `fillable` 2 | — |
| Press | the 2 ids | `inserted 2, skipped []`; occupancy `takeover_staff` + Lecturer; audit | — |
| Ordered since | 1 id, its Student ordered | `skipped [{id, order_exists}]` | not stopped |
| Repeat | same ids again | `inserted 0`, skipped `takeover_exists` | — |
| Foreign / unknown id | id of another session | skipped `not_listed` | — |
| One Game fails | takeover raises in game A | game B still filled | logged |
| Guided Week, unviewed | waited-for by `viewed_at` | taken; Week advances when complete | — |
| Assistant / Student / outsider | GET or POST | — | 403 |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py:18` `has_ordered`, `:51` `can_take_over`, `:110` `game_status` (use `waited_for`).
- `backend/app/modules/games/overview.py:42-70` inline waited-for predicate (replace).
- `backend/app/modules/games/commands.py:1811` `takeover` (add `only_waited_for` after `can_take_over`); `:1631` `_time_factors`; `rules.is_paused`.
- `backend/app/modules/games/service.py:715-760` `SummarySeat/SummaryWait/ClassGameSummary`, `class_overview` (summaries), `startable_class_games` (pattern); `repo.py` for a seats-by-game read.
- `backend/app/modules/sessions/overview.py:90` `class_overview` (`startable` pattern), `:405` `game_insight`, `:727-806` `_lecturer_session`/`start_games_page`/`start_games` (batch pattern with semaphore), `:54` `time_factors` import.
- `backend/app/modules/sessions/{schemas.py (StartGamesOut, StartedGamesOut, StartGamesIn, GameInsightOut, ClassOverviewOut), routes.py:522-559}`; `backend/app/platform/authz.py:116,168`.
- Tests: `tests/sessions/test_lecturer_start.py` (api pattern), `tests/games/test_takeover.py` (`class_game`), `tests/games/helpers.py`, `tests/sessions/test_game_insight.py` (the Assistant-vs-Lecturer equality test).
- Frontend: `src/modules/games/{spillstyring.tsx, start-games-page.tsx, start-games.ts, overview-page.tsx (OverviewHeader, useStartedCount, StartedLine), overview.ts (waitDuration), api.ts}`, `src/lib/api/topics.ts:50`, `src/modules/identity/homes.ts:53`, `src/app/(app)/klasseokter/[sessionId]/oversikt/start/page.tsx`, `src/copy/nb.ts:2145,2526`; e2e `start-games.spec.ts`, `support/{live-game,classes,auth}.ts`.

## Tasks & Acceptance

**Execution:**
- `games/rules.py`, `games/overview.py` -- `waited_for`, used by both.
- `games/commands.py` -- `only_waited_for` refusals.
- `games/service.py`, `games/repo.py` -- `waited_for_seats`, `class_seat_games`.
- `platform/authz.py` -- `games.fill_seats`.
- `sessions/{overview,schemas,routes}.py` -- page, batch, `fillable`, insight fields.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- Frontend: `games/{api.ts, fill-seats.ts (+ Vitest), fill-seats-page.tsx, spillstyring.tsx, overview-page.tsx}`, route page `oversikt/sett-inn/page.tsx`, `identity/homes.ts`, `lib/api/topics.ts`, `copy/nb.ts`, fixtures with new fields.
- Tests: `tests/games/test_waited_for.py` (pure predicate and status; the command's refusals on one module game); `tests/sessions/test_fill_seats_view.py` (the I/O matrix through the api on one module-scoped session); e2e `fill-seats.spec.ts` (per-game press and result, Oversikt Lenke → page → press → result line, axe and reflow at 320 and 1440).
- `ARCHITECTURE-SPINE.md` -- decision record.

**Acceptance Criteria:**
- Given a waiting Class game with 2 waited-for Seats, when the Lecturer opens Spillinnsikt, then the consequence line and «Sett inn KI-spiller i alle seter som blir ventet på (2)» show, with «Ikke med (tilrettelegging): Jonas» for a Seat with Tilrettelegging. An Assistant lecturer sees none of it.
- Given the press, then «2 KI-spillere satt inn.» has focus and both Seats are AI-held with the `takeover_staff` mark.
- Given waited-for Seats in the Class session, then the Oversikt header has the Lenke with the real count, matching the waiting games' `waiting_for` less the left-out Seats. The page lists them, and pressing returns to the Oversikt with «N KI-spillere er satt inn.» focused and the Lenke gone.
- Given 1440 and 320 px, then the block and the page have no horizontal scroll and pass axe.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter (asked to weigh concurrency), edge-case hunter, verification gap and intent alignment, all on Sonnet as the orchestrator asked. All four hand-backs dropped, so the findings were read from `review-{blind,edge,verification,intent}-8-12.md` in the session scratchpad. The diff was taken against `HEAD`, because the orchestrator committed sprint and log files on `epic-8` after the baseline. It leaves out the generated api client and `.docs`.
- verdicts: 33 findings — high 0, medium 6, low 18, false 9, maybe-false 0
- findings:
  - `[false]` `[reject]` blind-1 / edge-6: `playing_out` games and policies without inactivity Takeover are listed but always skipped. No path reaches `playing_out` before Story 8.14, which plays games out and clears their waits. The summaries list only Class games, whose policy has inactivity Takeover.
  - `[low]` `[reject]` blind-2: Tilrettelegging is read through two paths. `_time_factors` is empty only for a Game with no Class session or no frozen Inactivity limit, and a listed Class game has both. Both paths read `sessions.service.time_factors`.
  - `[medium]` `[patch]` blind-3 / edge-1 / edge-4 / edge-9: a fill where every Seat failed answered 200 with `inserted: 0`. The UI then said «Setene blir ikke ventet på lenger.» or «0 KI-spillere er satt inn.» and dropped the button. Fixed: `fillFailed` (no Seat put in and a Seat `failed`) now makes both presses a failure, said inline («KI-spillerne ble ikke satt inn. Prøv igjen.») with the button kept. Vitest covers it.
  - `[medium]` `[patch]` blind-4 / edge-2: the per-game result line never cleared, so new waited-for Seats in a later Uke got no button until a reload. Fixed: `Spillstyring` clears the result when the listed Seats change to a non-empty set.
  - `[false]` `[reject]` blind-5: each Takeover tells every Student of the game. The AC asks for «the rows, warning and notices of Story 8.2» per filled Seat, and the dedupe key is per occupancy row by design.
  - `[low]` `[reject]` blind-6: the gate of four Games is per request. This is the same trade-off as Story 8.10's batch: a pool wait queues rather than fails, and a shared limiter adds machinery.
  - `[low]` `[reject]` blind-7: up to 4000 ids, no deadline, no cancellation safety. A Class session's Seats are bounded by its games, and the 100-game fill takes about 10 s in the test. A partial fill leaves each Seat's own transaction committed, and a repeat is safe.
  - `[low]` `[patch]` blind-8 / intent-3: no real concurrency or failing-Game test. `test_a_hundred_class_games_fill_in_one_action` runs the real `takeover` over 100 Games four at a time. Ten Seats order between the listing and the press, and one Game fails for real. The counts must match the occupancy rows. The main test also pins the gate: at most four Games at once and one Seat per Game at a time.
  - `[low]` `[reject]` blind-9: Spillinnsikt reads the whole Class session's summaries for one game. That is two small reads on a table of at most a few hundred rows; a per-game filter adds parameters to two functions.
  - `[low]` `[reject]` blind-10: the page's list can change under the Lecturer's click. Lists read again on events (AD-8), and the api re-checks every Seat under its lock, so a changed Seat is skipped.
  - `[low]` `[patch]` blind-11: the batch log named only `inserted`. `lecturer_filled_seats` now logs `requested`, `inserted`, `skipped` and `failed`. Each Takeover is audited, as the AC asks.
  - `[false]` `[reject]` blind-12 / verification-other-1: `policy.py` at the root is not this story's. An earlier agent left it untracked on purpose, and it is never staged.
  - `[low]` `[reject]` edge-3: a partial fill does not list the skipped Seats. The AC asks for the result line with the real count, which the line shows.
  - `[low]` `[patch]` edge-5: the page counted waits from its mount time, so after a refetch every wait was overstated. It now counts from the answer's arrival (`dataUpdatedAt`).
  - `[low]` `[reject]` edge-7: `_fillable` reads Tilrettelegging even when no game waits. This is on purpose: the Oversikt reads a fixed number of queries whatever its games (NFR-3), which the query-count test pins.
  - `[false]` `[reject]` edge-8: a summary role with no Seat is dropped silently. Every summary row is written from the Game's own Seats in the same transaction, and Seats are never deleted.
  - `[low]` `[patch]` verification-1: `waitedForSeatsKey` was not pinned in `topics.test.ts`. It is now in `ALL` and in the `session:` expectation.
  - `[low]` `[patch]` verification-2: the bound of four concurrent Games was unobserved. The main test now fills twelve Seats of six Games through a counting stub and asserts a peak of four Games and one Seat per Game. The layer filed it as defer, but the fix is a direct test addition.
  - `[low]` `[reject]` verification-other-2: the order within a game is not pinned. Display only, and it follows the summary's chain order.
  - `[low]` `[patch]` intent-1: the AC's api test with 100 Class games was missing. It has been added (see blind-8), at about 10 s, one waited-for Seat per game.
  - `[low]` `[patch]` intent-2: the effects of a filled Seat were only partly asserted. The main test now asserts that the AI player's Order stands this Week (`ensure_order`) and that every Student of the game gets a `takeover_notice`. The Guided Week advance is asserted through the Uke 2 that follows.
  - `[low]` `[reject]` intent-4: the UI interactions are covered by the e2e spec, not by component tests. `fill-seats.spec.ts` presses on both surfaces and asserts the result lines, their focus, the Lenke and its removal.
  - `[low]` `[patch]` intent-5: the Assistant's per-Seat action on a Seat with Tilrettelegging was not asserted. The main test now has the Assistant lecturer take that Seat through Story 8.5's route.
  - `[false]` `[reject]` intent-6: the decision record is in `.docs`, outside the diff. The spine's Deferred item has «Decided in Story 8.12», and so do the Design Notes.
  - `[false]` `[reject]` intent-7: `game_status` changed meaning. The AC asks for exactly this predicate. A wait starts when the first Student orders, so the status is the same for every turn the commands write. Only test fixtures without a wait start changed.
  - `[false]` `[reject]` intent-8: the shown counts come from summaries while the press decides. This is the AC's design: one list read from the rows that give «Venter», re-checked under the lock.
- Count: 12 blind, 9 edge-case (two of them claims), 2 verification gaps plus 2 other, and 8 intent divergences. The intent layer is descriptive, so each divergence is one row. Findings with the same root cause share one row and name every member: 33 findings in 26 rows.

## Design Notes

Recorded decision (spine Deferred item «batch Takeover»): the batch posts the listed Seat ids. `sessions` loops one `games.commands.takeover(actor="staff", only_waited_for=True)` per Seat, each in its own transaction under the Game row lock, Games four at a time and Seats of one Game in turn. Skips carry the command's stable code, `not_listed` or `failed`. The answer gives the real counts, so a repeat inserts nothing (the second Takeover is `takeover_exists`).

Decisions taken here:
- A paused game is not "waited for": its status is `paused`, and the «Venter» count leaves it out. Its Seats stay reachable one by one.
- "Tilrettelegging" for this purpose is a time factor above 1. A share-of-Weeks adjustment does not change waiting.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_waited_for.py tests/games/test_game_summaries.py tests/sessions/test_fill_seats_view.py tests/sessions/test_overview.py` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run src/modules/games/fill-seats.test.tsx` -- pass
- `cd frontend && npx playwright test e2e/fill-seats.spec.ts` (stack up) -- pass
- `cd frontend && npx vitest run src/lib/api/topics.test.ts` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can put AI players in every Seat the Class games wait for, in one game from Spillstyring or in all games from a page reached from the Oversikt header. Seats whose Student has Tilrettelegging are left out and named. Each Seat gets one staff Takeover in its own transaction, so a Seat that ordered meanwhile is skipped, a repeat inserts nothing, and a failing Game stops no other.

- **One predicate.** `games.rules.waited_for(turn, *, guided)` is true for a Student-held Seat whose wait has started and which has not ordered; in a Guided Week, viewing counts as ordering. `game_status` gives `waiting` from it, and the summary's `waiting_for` lists by it. The fill's list and count read those same rows, so they always agree with «Venter».
- **Command.** `takeover(..., only_waited_for=True)` re-checks under the Game lock. It refuses `game_paused`, `order_exists`, `not_waited_for` and `tilrettelegging` (a time factor above 1). Everything else is Story 8.5's staff Takeover: `takeover_staff` with the Lecturer, `ensure_order`, the audit row, Story 8.2's notices, and the Guided Week advance.
- **Api.** `GET`/`POST /api/class-sessions/{id}/waited-for-seats` sit under the Lecturer-only policy `games.fill_seats`. The answer is `{inserted, skipped: [{seat_id, reason}]}`; a posted id of no game of the Class session is skipped `not_listed`, and a failure is skipped `failed`. Games run four at a time, and the Seats of one Game run in turn. The Oversikt gains `fillable`; Spillinnsikt gains `waited_for` and `left_out`, both for a Lecturer only.
- **Screens.**
  - Spillstyring shows the draft consequence line above the secondary «Sett inn KI-spiller i alle seter som blir ventet på (2)», then «Ikke med (tilrettelegging): Jonas». After the press, «2 KI-spillere satt inn.» takes focus.
  - The Oversikt header has the Lenke «… (9)», hidden at 0. It opens the page «Sett inn KI-spillere»: per game «Spill 2» with «Noah, 23 t», the left-out line, «Studentene kan ta setene tilbake fra neste Uke.» and «Sett inn 9 KI-spillere». The press returns to the Oversikt, where «9 KI-spillere er satt inn.» takes focus.
- **Docs.** The spine's Deferred item records «Decided in Story 8.12».

**Files changed**
- Backend:
  - `games/{rules,overview,commands,service,repo}.py`: the predicate, the re-check, `waited_for_seats`, `class_seat_games`, and the Seat-id read.
  - `sessions/{overview,schemas,routes}.py`: the page, the batch, `fillable`, and the insight fields.
  - `platform/authz.py`: `games.fill_seats`.
- Frontend:
  - New: `games/fill-seats.ts`, `games/fill-seats-page.tsx` and route `oversikt/sett-inn/page.tsx`.
  - `games/{spillstyring.tsx (FillStyring), overview-page.tsx (Lenke, result line), api.ts}`, `identity/homes.ts`, `lib/api/topics.ts` and `copy/nb.ts`.
  - `lib/api/{openapi.json,schema.ts}`: regenerated.
- Tests:
  - New: `tests/games/test_waited_for.py`, `tests/sessions/test_fill_seats_view.py` (the whole flow and 100 games), `src/modules/games/fill-seats.test.tsx` and `e2e/fill-seats.spec.ts`.
  - Updated: `test_game_summaries.py` (fixtures carry `wait_started_at`), `test_overview.py` (a waiting game from the start, so the query count stays fixed), `topics.test.ts`, and the new fields in seven Vitest fixtures.
- Planning: `ARCHITECTURE-SPINE.md` (the decision) and `epic-8-context.md` (recompiled: the spine was newer).

**Review.** Four Sonnet reviewers reported 33 findings: high 0, medium 6, low 18, false 9.
- Patched:
  - Medium: a fill where every Seat failed now fails inline; the per-game result clears when new Seats are waited for.
  - Low: the batch log carries `requested`, `skipped` and `failed`; the page counts waits from the answer's arrival; the topics test pins the page's key; a 100-game test; the concurrency gate pinned; Story 8.2's effects asserted; an Assistant lecturer's per-Seat action on a Seat with Tilrettelegging asserted.
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended. Patched entries: high 0, medium 2, low 8.

**Verification**
- Backend: the full suite with `--maxprocesses=8` passed, 3065 tests. It ran again in full after the last test patch: 3065 passed. ruff check and ruff format are clean on the touched files.
- Frontend: typecheck, Vitest (75 files, 902 tests), `lint:colours`, `check:copy` and `next build` all pass.
- End to end: after the last frontend change the stack was rebuilt. Playwright with `--workers=4` ran 138 tests in 25 specs: fill-seats, game-insight, guided-week, homes, in-room, live-updates, order-confirm, order-failures, order-field, overview, pause, peer-insert, reclaim, seat-status, spillstyring, staff-pause, start-games, student-home, takeover, takeover-overview, tilrettelegging, varselband, week-advance, week-table and week-transition. All passed.
- No test failed once and then passed on rerun.
- Accessibility: axe and reflow ran on the Spillstyring block and on the page, each at 320 px and at 1440 px.
- Matrix audit: every I/O row is covered by `test_fill_seats_view.py`. The Guided Week row is Seat a2 in Uke 1.
- Slow tests (over 1 s):
  - `test_a_hundred_class_games_fill_in_one_action`: 10 to 13 s. These are the AC's 100 Class games, with one waited-for Seat per game to keep it short.
  - `test_a_lecturer_fills_the_waited_for_seats_of_one_game_and_of_all`: 3 to 4 s, with 2.5 s of setup. It is one session for the whole flow.

**Decisions taken instead of the founder.**
- A paused game is not waited for. «Venter» leaves it out, and so do the count and the press (`game_paused`); its Seats stay reachable one by one.
- Tilrettelegging here means a time factor above 1; a share of Weeks does not change waiting.
- The fill is for Lecturers only (`games.fill_seats`). Assistant lecturers keep only the per-Seat action, as EXPERIENCE.md's Who says.
- The per-game button posts its Seat ids to the same batch endpoint as the page.
- A Seat that ordered and completed its game's Week is skipped `not_waited_for`, since the game had moved on. One that ordered while the Week stayed open is skipped `order_exists`.
- A press that put no one in because a Seat failed is shown as a failure, with the button kept. When none was put in because every Seat had ordered, the line «Ingen KI-spillere satt inn. Setene blir ikke ventet på lenger.» is shown instead.
- Draft copy `[ASSUMPTION]`:
  - the consequence line «KI-spillere bestiller for Noah og Emma fra denne Uka. Studentene kan ta setene tilbake fra neste Uke.»;
  - the list label «Seter som blir ventet på» and the empty line «Ingen seter blir ventet på nå.»;
  - the line for none put in, and the failure line «KI-spillerne ble ikke satt inn. Prøv igjen.»;
  - the singular forms («1 KI-spiller satt inn.»).
- The orchestrator asked for the implementation in the builder's own context, so the skill's implementation subagent was not used.

**Residual risks.**
- Up to 100 games' Takeovers run inside one request, about 10 s in the test. A disconnect mid-fill leaves the Seats done so far filled, and a repeat is safe.
- The visual check is left to the separate visual agent.
