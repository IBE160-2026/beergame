---
title: "Story 6.10: Play the Guided Weeks"
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '61c3c29c0e55f257f34d4314f0439a94ee4b59c8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** In a Class game's Guided Weeks nothing places a Student-held Seat's fixed Order and nothing records that the Student has seen the Week, so the game cannot pass its Guided Weeks with Students in it, and the play screen has no order area (FR-24, FR-31, UX-DR20, UX-DR62).

**Approach:** The Week-opening transaction places the Guided Order for every Seat, Students included. A new command `games.commands.view_week` sets `viewed_at` (new column) on the Student's own turn once and advances the Week when `games.rules.week_complete` (extended) says every Student-held Seat has viewed it. The play envelope gains the own turn (`guided`, `order`, `viewed`); the play screen shows the Ordrefelt's read-only Veiledet uke state and calls the view route once per Guided Week.

## Boundaries & Constraints

**Always:**
- Only `games.commands` writes; `view_week` is one transaction with the Game row lock, the open-Week check after the lock, a version bump and events: `game:<id>`, `session:<id>` where `games.policy` lists the overview (via `_commit_change`), `user:<id>` for the viewer and, when it advances, for every Student holding a Seat. Registered in `platform/events/registry.py`.
- `view_week` repeated for the same Week writes nothing, bumps nothing, emits nothing. It refuses: `game_not_found` 404, `game_not_started`/`game_finished` 409, `week_not_open` 409, `week_not_guided` 409, `seat_not_student` 409 (occupant in force is not a Student), `seat_not_yours` 409 (another User's Seat).
- `week_complete(turns, guided=...)`: every turn has `ordered_at`; in a Guided Week also every turn whose occupant in force that Week is `student` has `viewed_at`. Its callers pass turns with that occupant (one repo read). The view that completes the Week advances exactly one Week in its transaction; `_settle` runs after commit like every command.
- Guided Orders for Student Seats go through `players.ensure_order` → `place_order(..., within=game)`, `decided_by = guided`; no model call. Simulation Games (no Students) and the golden batch results are unchanged.
- `switch_to_rule_based` in a Guided Week treats a Student Seat without `viewed_at` as not yet ordered (founder decision 2026-11-12: viewing counts as ordering for Takeover), so a switched Seat never stalls the Week.
- Envelope `turn` = `{guided, order, viewed}`: own Seat only, the open Week; `order` is the own placed Order or null. Never the number of Guided Weeks.
- UI: label «Din ordre for Uke {n}», the Order in a read-only field (`future-tint`, `ink-muted` value, `figure-order`), no confirm button, the line «Veiledet uke. Ordren er fast og legges inn automatisk.» (draft copy [ASSUMPTION] in `nb.ts`). Placed first in the right column (after the table on phone). Copy says nothing about how many Guided Weeks remain.
- The web app calls `POST /api/me/games/{id}/weeks/{week}/view` when a Guided Week with `viewed = false` is on screen, once per Week per mount; a 409 is ignored (the next `game:` event refetches).

**Never:** No editable Ordrefelt, − / + segments, help line, «Bekreft ordre» or preview (6.11–6.12); no `wait_started_at` or Setestatus (6.14); no Takeover/inactivity logic beyond the switch rule above (Epic 8); no edit of `sprint-status.yaml`; no change to `SeatState`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Week opens, 4 Students | `start` of a Classic Class game | four `seat_weeks` rows `guided`, 4 each; Week 1 stays open | — |
| Views in turn | three views | each sets `viewed_at`, no advance | — |
| Last view | fourth view | one advance in its transaction; Week 2 opens with four guided Orders | — |
| Simultaneous views | four views at once | exactly one advance per Week | row lock serialises |
| Repeat view | view again | 204, no write, no version bump, no event | — |
| Stale week | view Week 2 when Week 3 is open | — | 409 `week_not_open` |
| Non-guided week | view in Week 5 | — | 409 `week_not_guided` |
| Other game | any id not own | — | 403 `forbidden` (as the play route) |
| Play screen Uke 3 | envelope `turn.guided` | read-only 4, Veiledet uke line, POST view once | 409 ignored |
| Play screen Uke 11 | `turn.guided = false` | no order area, no POST | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `_open_week` :851 (ensure_order per Seat), `_place` :1094 (`week_complete` call :1183), `_complete_week` :1295, `_advance_once` :1310, `switch_to_rule_based` :1352, `_commit_change` :227, `start` user-event loop :976 (pattern for Student events). Add `view_week`, export in `__all__`.
- `backend/app/modules/games/rules.py:17` `week_complete` -- extend with `guided`; `guided_week` :12.
- `backend/app/modules/games/repo.py:375` `turn`, :388 `week_turns`, :396 `set_ordered_at`, :407 `occupancy_in_force` -- add `week_turns_with_occupant`, `set_viewed_at`.
- `backend/app/modules/games/models.py:157` `seat_turns` -- add `viewed_at`; trigger `seat_turns_keep_opening` (latest in `migrations/versions/0012_near_optimal_reference.py`) must also keep a set `viewed_at`. New migration `0047_seat_turns_viewed_at.py`.
- `backend/app/modules/players/service.py:46` `_order` -- guided before the Student check.
- `backend/app/modules/games/schemas.py:264` `TurnOverview` (add `viewed_at`), :282 `PendingTurn` doc; `views.py:144` builds it.
- `backend/app/platform/events/registry.py` -- `games.view_week`.
- `backend/app/platform/authz.py:105` -- add `games.play_own` (ANY_USER, scope `own_seat`).
- `backend/app/modules/sessions/service.py:1288` `student_play_of` (add `turn`), :1329 `start_own_game` pattern for `view_own_week`; `schemas.py:408` `PlayOut`; `routes.py:594` play route pattern.
- `backend/tests/games/helpers.py:38` `play_week` -- view Student Seats in Guided Weeks; tests placing a Student's guided Order by hand (`tests/games/test_place_order.py`, `test_registry.py`, `tests/players/test_ensure_order.py`, `tests/sessions/test_play.py:65`) must adapt.
- `backend/tests/games/test_play_fixture.py:67` -- fixtures `play-week-{1,3,11,14,30}.json` gain `turn`.
- `frontend/src/modules/games/play-page.tsx:113` `Running`; `api.ts` (`startGame` pattern); `src/copy/nb.ts:1478` `games.play`; `src/components/text-field.tsx:53` read-only classes; `src/lib/api/openapi.json` + `schema.ts` regenerated (`uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, `npm run api:generate`).
- `frontend/e2e/chain-band.spec.ts:23` `openPlay` stub pattern; `e2e/support/classes.ts` `expectAccessible`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0047_seat_turns_viewed_at.py` -- add nullable `viewed_at timestamptz`; trigger also refuses changing a set `viewed_at`; downgrade restores 0012's function.
- `backend/app/modules/games/models.py`, `repo.py` -- column; `week_turns_with_occupant` (turn + occupant kind and user in force that Week); `set_viewed_at`.
- `backend/app/modules/games/rules.py` -- `week_complete(turns, *, guided)`.
- `backend/app/modules/players/service.py` -- guided Order for every occupant kind.
- `backend/app/modules/games/commands.py` -- `view_week(game_id, seat, week, *, actor)`; callers of `week_complete`; switch rule.
- `backend/app/modules/games/schemas.py`, `views.py`, `registry.py`, `authz.py` -- `viewed_at` on `TurnOverview`; registry entry; permission.
- `backend/app/modules/sessions/{schemas,service,routes}.py` -- `PlayTurnOut` on `PlayOut`; `view_own_week`; `POST /api/me/games/{game_id}/weeks/{week}/view` → 204 (operation `viewMyGameWeek`).
- `backend/tests/games/test_view_week.py` -- command: idempotence, refusals, events, advance in-transaction, switch rule; `tests/games/test_registry.py` runner; `tests/sessions/test_guided_weeks.py` -- the api test of four Students through Weeks 1–5 (orders of views varied, one simultaneous round with `asyncio.gather`), one advance per Week, four guided Orders per Guided Week; adapt existing tests.
- `frontend/src/modules/games/order-field.tsx` (new) -- the Ordrefelt, only its guided read-only state; `api.ts` `viewWeek`; `play-page.tsx` renders it and calls view; `nb.ts` copy.
- `frontend/src/modules/games/fixtures/play-week-*.json`, `test_play_fixture.py` -- `turn`.
- `frontend/e2e/guided-week.spec.ts` (new) -- Uke 3 stub: label, read-only value 4, no button, Veiledet uke line, POST view once with Week 3; Uke 11: no order area, no POST; axe at 320/360/1440.

**Acceptance Criteria:**
- Given a Class game in a Guided Week, when the Student opens the play screen, then «Din ordre for Uke N» and the fixed Order show read-only with the Veiledet uke line and no confirm button, at 320/360/1440 px with no axe violation.
- Given four Students in a Classic Class game, when they view Weeks 1–4 in varied orders and simultaneously, then each Guided Week has four `guided` Orders and advances exactly once, and Week 5 opens waiting for Student Orders.
- Given a simulation batch, when it runs, then its golden results are unchanged (existing tests).

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 30 findings — high 0, medium 1, low 13, false 16, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: a failed view is never sent again (`useGuidedView` adds the Week to `sent` first and swallows every error), so a dropped request stalls the Week — a 403/409 is left to the next `game:` event; any other failure is sent again after 5 s (`VIEW_RETRY_MS`); e2e with Playwright's clock: 500 retried, 409 not.
  - `[low]` `[reject]` blind: the hook logs no failure — the web app has no client telemetry; the retry covers the harm.
  - `[false]` `[reject]` blind: "on screen" not checked against page visibility — the AC says "when the play screen loads that Week"; mount is that moment.
  - `[false]` `[reject]` blind: a Student who never opens the page stalls the class — the founder decision makes viewing the Order; inactivity and Takeover are Epic 8 by the story's own text.
  - `[low]` `[patch]` blind: every command refusal becomes 409, 404 codes included, and the route lists too few codes — not-found refusals and `seat_not_yours` now answer 403 like any other game (FR-5); the docstring names every 409 code.
  - `[low]` `[patch]` blind: a Seat moved between the ownership check and the command leaks `seat_not_yours` — same fix (403).
  - `[low]` `[reject]` blind: the occupancy-in-force rule exists twice — the subquery uses the same order (`from_week desc, id desc`); a Seat without occupancy cannot exist after `start`.
  - `[low]` `[reject]` blind: after a switch of an unviewed Student the Decision log row says `student` — the row records the occupant in force when the Order was placed (AD-15), which was the Student.
  - `[false]` `[reject]` blind: the downgrade restores a hard-coded 0012 body that later revisions might have changed — only 0003, 0004, 0009 and 0012 define the function.
  - `[low]` `[reject]` blind: no feedback after the view; «legges inn» wording — the waiting status is Story 6.14; the copy is draft (#31).
  - `[low]` `[reject]` blind: `seat_state` and `open_turn` read in separate sessions; `open_turn` gains a query — same pattern as before; an event refetches.
  - `[low]` `[reject]` blind: settings parsed again in `_week_complete` — negligible cost.
  - `[false]` `[reject]` blind: `session:` from `view_week` asserted nowhere — `test_registry` runs `view_week` on a Class game and asserts exactly `{game, session, user}`.
  - `[low]` `[reject]` blind: untested concurrent view+switch and view+order — switches mid-Week are Epic 8; views and Orders serialise on the Game row lock like every command.
  - `[low]` `[reject]` blind: e2e pins RGB values for the tokens — same pattern as the chart tests; a token change should be seen.
  - `[medium]` `[patch]` edge: failed `viewWeek` never retried — same root as the first row; patched there.
  - `[false]` `[reject]` edge: a Student occupancy with no `user_id` can never be viewed — `assign_seat`/`move_seat` always store the Student id (`user_id_required`).
  - `[low]` `[patch]` edge: a Guided Week opened before this story has no Student Order, so the view cannot complete it — `view_week` places it through `ensure_order` when `ordered_at` is unset; test with the pre-6.10 order source.
  - `[low]` `[patch]` edge: `viewed_at` recorded but Week never completes when `ordered_at` is NULL — same root and fix as the previous row.
  - `[false]` `[reject]` edge: `open_turn` may raise `week_not_open` in the envelope — `start` and every advance write the turns with the Week in one transaction; `play.week` is that Week.
  - `[low]` `[patch]` edge: 404 refusals leave the api as 409 — patched (403).
  - `[low]` `[reject]` edge: Decision log says `student` for a switched Week — as the blind row (AD-15).
  - `[low]` `[reject]` verification-gap: `complete_running_games` still lists a Guided Week waiting for views, so each rescue pass makes one no-op `advance` read — recorded in Design Notes as a candidate list; `_advance_once` re-checks `week_complete`; moving the guided/Student rule into SQL would duplicate it.
  - `[low]` `[patch]` verification-gap: the 0047 downgrade's trigger body is never checked — `test_migrations` now asserts after the downgrade to 0046 that the function has no `viewed_at` and keeps the near-optimal rule.
  - `[medium]` `[patch]` verification-gap (other): failed view not retried — same root as the first row.
  - `[false]` `[reject]` intent: browser-to-backend round trip untested — same split as Stories 6.6–6.9: e2e on engine-pinned stand-ins, the api in `test_guided_weeks.py`.
  - `[false]` `[reject]` intent: `session:` not asserted — `test_registry` asserts it.
  - `[false]` `[reject]` intent: no LLM Seat in a Guided Week tested — `tests/players/test_llm_jobs.py` and `tests/test_sim_llm.py` assert `guided` Orders with no model call and still pass.
  - `[false]` `[reject]` intent: golden results not checked — `tests/test_sim_golden.py` ran in the full suite and passed unchanged.
  - `[low]` `[reject]` intent: the `switch_to_rule_based` change lands on Epic 8's surface — the founder decision names Takeover explicitly; without it a switched Seat would stall the Week; recorded as a decision.

## Design Notes

Founder-level calls: the envelope carries the own turn (`turn`) rather than bumping `SeatState`, which is the LLM/Decision-log boundary; `view_week` only applies to Guided Weeks (refuses otherwise) and to the Student holding the Seat; the help line «Hele tall fra 0 til {maks}.» is not shown in the read-only Guided state (nothing can be typed); the Veiledet uke line is draft copy. `complete_running_games` (rescue-loop candidates) stays a candidate list: `advance` re-checks `week_complete`. Added during implementation: the week table's Din ordre cell at nå shows the placed fixed Order in a Guided Week (`WeekTable nowOrder`, as the Landing already does) instead of the empty dashed cell; tests that exercised Week-1 Orders by hand now use Games with `guided_weeks=0`, and `seat_student` gives each test Student a deterministic id (`student_of`).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_view_week.py tests/sessions/test_guided_weeks.py -q` -- pass
- `cd frontend && npx playwright test e2e/guided-week.spec.ts --workers=2` -- pass
- full: backend pytest; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** Every Seat now gets the fixed Guided Order when a Guided Week opens, Students included (`players.ensure_order`). A new command `games.commands.view_week` sets `seat_turns.viewed_at` (migration 0047; the trigger keeps it once set) on the Student's own turn once, emits `game:`, `session:` (Class games) and `user:` (the viewer; every Student when it advances), and the view that leaves no Student Seat unviewed advances exactly one Week in its own transaction (`rules.week_complete(turns, guided=)`). `switch_to_rule_based` treats an unviewed Guided Week as not yet ordered. The api adds `POST /api/me/games/{id}/weeks/{week}/view` (204; 409 codes; 403 for any other game) and `turn {guided, order, viewed}` on the play envelope. The play screen shows the Ordrefelt's read-only state («Din ordre for Uke 3», the 4 on `future-tint`, «Veiledet uke. Ordren er fast og legges inn automatisk.», no button), the fixed Order in the table's Din ordre cell at nå, and sends the view once per Week (sent again after 5 s on a passing failure).

**Files.**
- `backend/migrations/versions/0047_seat_turns_viewed_at.py` (new), `games/models.py`, `games/repo.py` -- column, trigger, `week_turns_with_occupant`, `set_viewed_at`, `seat_week_order`; unused `week_turns` removed.
- `games/rules.py`, `games/commands.py` -- `week_complete(guided=)`, `view_week`, `_week_complete`, switch rule.
- `players/service.py` -- Guided Order for every occupant.
- `games/schemas.py`, `games/views.py` -- `TurnOverview.viewed_at` and `order`.
- `platform/events/registry.py`, `platform/authz.py` -- `games.view_week`, `games.play_own`.
- `sessions/{schemas,service,routes}.py` -- `PlayTurnOut`, `view_own_week`, the route.
- `frontend/src/modules/games/order-field.tsx` (new) and its test, `play-page.tsx`, `api.ts`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}`, fixtures `play-week-*.json` (`turn`).
- Tests: `tests/games/test_view_week.py`, `tests/sessions/test_guided_weeks.py`, `e2e/guided-week.spec.ts` (new); adapted `tests/games/helpers.py` (`student_of`, `view`, `play_week`), `test_place_order.py`, `test_start.py`, `test_views.py`, `test_registry.py`, `tests/players/test_ensure_order.py`, `tests/sessions/test_play.py`, `test_play_fixture.py`, `test_migrations.py`, e2e envelope types.

**Review.** One pass, four layers, 30 findings (high 0, medium 1, low 13, false 16). Patched: view retry (medium); 403 for not-found and `seat_not_yours`; a missing Student Order placed at the view; downgrade trigger test. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. Patched entries: 1 medium, 3 low; no high.

**Founder-level decisions taken (no human in the loop).** The envelope carries the own turn instead of bumping `SeatState`. `view_week` applies only to Guided Weeks and the Seat's own Student; other games, moved Seats and not-found answer 403. The view is sent on page load (no visibility check). The help line is not shown in the read-only state. Draft copy «Veiledet uke. Ordren er fast og legges inn automatisk.» [ASSUMPTION]. The fixed Order also fills Din ordre at nå. `switch_to_rule_based` treats an unviewed Guided Week as not ordered (founder decision 2026-11-12 on Takeover). `user:` goes to the viewer and, on an advance, to every Student. A failed view (not 403/409) is sent again after 5 s. `complete_running_games` stays a candidate list. Tests that placed Week-1 Orders by hand now use `guided_weeks=0`. Implementation ran in the orchestrating agent's context (caller's runbook); reviewers were sub-agents.

**Verification.**
- Backend: 2704 passed (76 s), ruff clean; golden batch results unchanged.
- Frontend: typecheck, Vitest 547 passed, `check:copy`, `lint:colours`, build (local and compose image).
- Playwright full `--workers=2`: 364 passed (6.2 min) before the review patches; after them the play specs (55) passed.
- Slow new tests: `test_four_students_view_the_guided_weeks_in_any_order` 3.8 s alone (6.8 s under full-suite load: four Weeks of HTTP views with logins); the guided e2e at 320/360/1440 px about 1.1 s each (axe). No fixed sleeps (the retry test uses Playwright's clock).
- Migration 0047 is new; no migration that had already run was changed.

**Residual risks.** A Student who never opens a Guided Week holds the game until Epic 8's Takeover. The rescue loop makes one no-op advance read per waiting Guided Week per pass. Draft copy awaits the founder (#31).
