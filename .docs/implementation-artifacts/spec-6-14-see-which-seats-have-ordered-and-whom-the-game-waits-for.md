---
title: "Story 6.14: See which Seats have ordered and whom the game waits for"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '750bc6316461c1676fde2dd167881360d3aae75b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['multiple-goals', 'oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The play screen and Hjem list «Setene» (Role and holder) but not who has ordered this Uke, whom the game waits for or for how long, so a Student cannot tell whether it is their turn (FR-25, FR-24, FR-34, UX-DR25, UX-DR62, UX-DR69, AD-3, AD-15, AD-20).

**Approach:** Store the wait start: a migration adds `seat_turns.wait_started_at`, written only by `games.commands` (a Student's own `place_order`, and `view_week` in a Guided Week) on the open Week's turns that have not ordered, the time from `games.rules.turn_times` with a new clock-start input. `games.views.table_status` adds per Seat `ordered`, `wait_started_at` and a `mark` from one new AD-15 mapping exposed by `games` `service.py`. The web app gets a reusable Setestatus in `frontend/src/components/` (dot, Role, name or «KI-spiller», status text), on the play screen right under the Ordrefelt and on Hjem, ticking the wait from `server_now`, with a polite «Venter på: …» announcement.

## Boundaries & Constraints

**Always:**
- «Ordered» per turn = `ordered_at` set, and in a Guided Week a Student-held turn also needs `viewed_at` (one predicate `rules.has_ordered`, reused by `week_complete`).
- `wait_started_at` is set in the same transaction, only where it is NULL and the turn has not ordered, when a Student orders (`decided_by = student`) or views a Guided Week; kept once set by the `seat_turns` trigger. Never set by guided/AI Orders.
- `table_status` (running/playing-out game, open Week): `ordered`, `wait_started_at` (None once ordered), `mark` (`guard_switch` when the latest occupancy `reason` is `guard_switch`, else None); for a game not running all three are None. Students still see only «KI-spiller» for any AI.
- Play envelope `next_change_at` = earliest stored `ai_deadline_at` of an unordered open-Week turn that is after `server_now`, else null; the web app refetches the envelope then. StudentGameOut (Hjem, `/api/me/games/{id}`) gains `server_now`.
- Row status text: «har bestilt», «venter, 3 min», «venter» (no wait start, or an AI player), «venter (deg)» (own Seat). Filled dot = ordered, hollow = waiting, dot `aria-hidden`; text always states it. Guard-switched AI row: holder reads «KI-spiller (regelbasert)» [ASSUMPTION].
- Duration from `server_now` offset and the stored time: «under 1 min», «N min» (< 60), «N t» (< 48 t), «N d» [ASSUMPTION].
- «Venter på: Jonas (3 min) og deg.»: waited-for Seats in list order, Student by name (Role when no name), AI by Role, own as «deg» last, duration only for Students with a wait start. It is a polite sr-only live region, updated only when the set of waited-for Seats changes (not every minute); no visible line under the button. The Confirmed message becomes «Ordren på 24 er sendt. Venter på Jonas (3 min).» when someone else is waited for.
- Setestatus sits directly under the Ordrefelt (before the Lenker) on the play screen, on Hjem in place of «Setene», and on the not-running play screen without status. Live updates never move focus. Named empty slots: `statusLine` (above), `controls` (below), `rowDetail`/`rowAction` per row.
- `game:<id>` events also refresh Hjem's sessions (`topics.ts`).

**Never:** Pause, Takeover, Reclaim, «I rommet», `takeover_due_at` (Epic 8); Spillkort wording changes (6.17); spinner or extra AI copy; «LLM-spiller» or model names to Students; a wait computed anywhere but from the stored column; fixed sleeps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Nobody ordered | open free Week, no Student Order | all Student rows «venter», no duration; announcement «Venter på: …» names them | — |
| First Student orders | Sara orders 24 | Sara «har bestilt»; Jonas «venter, 0→3 min» from stored start; others' `wait_started_at` = Sara's transaction time | — |
| Second Student orders | Jonas orders later | Jonas's `wait_started_at` unchanged by any later write | trigger refuses a change |
| Guided Week, one absent | three viewed, Noah not | viewers «har bestilt»; Noah «venter, N min» from first view | — |
| AI not yet ordered | LLM Seat thinking | «KI-spiller» «venter», no spinner; `next_change_at` = its `ai_deadline_at` | past deadline → null |
| Guard switch | latest occupancy reason `guard_switch` | `mark: guard_switch`; row «KI-spiller (regelbasert)» | — |
| Game not running | ready / finished | `ordered`/`wait_started_at`/`mark` None; rows without dot/status | — |

</intent-contract>

## Code Map

- `backend/migrations/versions/0047_seat_turns_viewed_at.py` -- template for new `0048_seat_turns_wait_started_at.py` (add column + trigger keeps it once set; trigger body must keep the `viewed_at` rule).
- `backend/app/modules/games/models.py:157` `seat_turns` -- add `wait_started_at` column.
- `backend/app/modules/games/rules.py` -- `week_complete:17` (extract `has_ordered`), `TurnInputs:54` add `clock_start`, `TurnTimes:64` add `wait_started_at`, `turn_times:69` returns it (max with `occupied_since`), unaffected `ai_deadline_at`.
- `backend/app/modules/games/repo.py` -- `_latest_occupancy:108`/`seats_with_occupant:90` add `reason`; `week_turns_with_occupant:388` already returns all turn columns + occupant; new `set_wait_started_at(turn_id, at)` (WHERE NULL); `now:338`.
- `backend/app/modules/games/commands.py` -- `_place:1095` (after `set_ordered_at`, before `_step`, when `decider is STUDENT`) and `view_week:1339` (after `set_viewed_at`) call new `_start_waits(session, game, week)`.
- `backend/app/modules/games/schemas.py:429` `TableSeat` add `ordered`, `wait_started_at`, `mark: SeatMark | None`; `TableStatus` add `next_due_at`; new `SeatMark` StrEnum (`guard_switch`).
- `backend/app/modules/games/marks.py` (new) `seat_mark(decided_by, fallback, occupant_kind, reason)`; re-exported from `service.py` (views cannot import service: cycle).
- `backend/app/modules/games/views.py:216` `table_status` -- reads game, open Week turns, guided flag; fills new fields.
- `backend/app/modules/sessions/service.py:1222` `_game_out` / `:1289` `student_play_of` -- pass new seat fields, `server_now`, `next_change_at`; `schemas.py:430` `TableSeatOut`, `StudentGameOut`.
- `backend/tests/sessions/test_play.py:125` asserts seat keys -- update; helpers `running`, `played_to`; `tests/sessions/test_orders.py` `free_week`, `order`; `tests/sessions/test_guided_weeks.py` `view`; `tests/games/test_turn_times.py`.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate (`cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`; `cd frontend && npm run api:generate`).
- `frontend/src/modules/games/play-page.tsx:186` `Seats` -> Setestatus under `OrderField`; `:381` NotRunning; refetch at `next_change_at`; Confirmed waiting text to `OrderField`.
- `frontend/src/modules/games/order-field.tsx:94` `Confirmed` -- append waiting text.
- `frontend/src/modules/games/student-hjem.tsx:146` -- Hjem «Setene» -> Setestatus; `home.ts:20` `holderText`.
- `frontend/src/lib/api/topics.ts` `game` case -- add `enrolledSessionsKey`.
- `frontend/src/copy/nb.ts:354` `homes.student` / `games.play.order` -- new strings.
- `frontend/src/modules/games/fixtures/play-week-*.json`, `frontend/e2e/support/play.ts` -- seats gain new fields.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0048_seat_turns_wait_started_at.py`, `models.py` -- column + trigger.
- `backend/app/modules/games/{rules,repo,commands,schemas,marks,views,service}.py` -- as Code Map.
- `backend/app/modules/sessions/{schemas,service}.py` -- seat fields, `server_now`, `next_change_at`.
- `backend/tests/games/test_turn_times.py` -- clock start unit tests. `backend/tests/sessions/test_seat_status.py` (new) -- api: free Week before/after first Student Order (stored start equals that turn's `ordered_at`, unchanged by the second Order, never set on ordered turns); Guided Week absent Student; Hjem seats + `server_now`; `guard_switch` mark via `switch_to_rule_based(..., "guard_switch")`; `next_change_at` from a set `ai_deadline_at`. Update `test_play.py` keys.
- `frontend/src/components/seat-status.tsx` (+ `seat-status.test.tsx`) -- component, pure text helpers (`waitText`, `waitingLine`) unit-tested.
- `frontend/src/modules/games/{play-page,order-field,student-hjem,home}.tsx/ts`, `topics.ts`, `nb.ts`, fixtures, `e2e/support/play.ts` -- wiring.
- `frontend/e2e/seat-status.spec.ts` (new) -- stubbed play screen at 320/360/1440 with Students and AI in ordered/waiting states (one axe per width, no page horizontal scroll, text per row), duration ticking via `page.clock`, a refetched envelope updating rows without focus move and the announcement text, Confirmed with «Venter på», `next_change_at` refetch.

**Acceptance Criteria:**
- Given a running Class game, when the Setestatus renders on the play screen or Hjem, then it lists all four Seats with dot, Role, name or «KI-spiller» and «har bestilt» / «venter, 3 min» / «venter» / «venter (deg)», under the Ordrefelt before and after the own Order, with no visible «Venter på» line under the button.
- Given another Seat orders, when the `game:<id>` event arrives, then the rows update without reload or focus move and «Venter på: …» is announced politely.
- Given Playwright with axe at 320, 360 and 1440 px, then rows reflow with no page horizontal scroll and no violation.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- verdicts: 36 findings — high 0, medium 1, low 29, false 6, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: two Students ordering at once could store a wait start on a turn that just ordered — every command takes the Game row lock (`repo.lock_game`) first, so the second transaction reads the turns only after the first commits.
  - `[low]` `[reject]` blind: `occupied_since` never passed by `_start_waits` — no mid-Week change of a waited Seat exists before Epic 8 (Takeover/Reclaim); `turn_times` already takes it and Epic 8 passes it.
  - `[low]` `[reject]` blind: a Seat changing hands mid-Week keeps the old wait start — same: Epic 8's Takeover owns it.
  - `[low]` `[reject]` blind: a free Seat treated as rule-based in `_start_waits` — no effect; same fallback as `_open_week`; a running game has no free Seat.
  - `[low]` `[reject]` blind: one UPDATE per waiting turn — at most four rows per Student Order; the value goes through `turn_times` as the AC asks.
  - `[low]` `[reject]` blind: the guard-switch mark also shows on a finished game — true of the Seat after the run as well; the not-running test is about order state.
  - `[low]` `[reject]` blind: `useServerNow` takes the offset at render, not fetch — cached data older than `staleTime` (30 s) is refetched on mount; the error stays under 30 s on a minute display.
  - `[low]` `[reject]` blind: `useRefetchAt` counts from mount — same 30 s bound; the rescue loop's Order also emits `game:<id>`.
  - `[low]` `[reject]` blind: after an overdue deadline `next_change_at` is null — by design: the rescue loop's event refreshes the screen (6.4 live path).
  - `[low]` `[reject]` blind: the announcement keeps the duration of its change; a holder change on the same Role is not announced — announcing only when whom the game waits for changes is the decision; mid-Week holder changes come with Epic 8.
  - `[low]` `[reject]` blind: every `game:` event refetches Hjem — at most four players per game; Hjem must update (AC «on Hjem»).
  - `[low]` `[patch]` blind: the trigger test accepted any exception — now `pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values")`.
  - `[low]` `[reject]` blind: no unit tests for the three hooks — the e2e drives them with Playwright's clock (ticking, announcement unchanged on a tick and changed on a new waiting set, refetch at `next_change_at`).
  - `[low]` `[reject]` blind: no backend tests for an AI wait start, a takeover, `PLAYING_OUT`, a Week-completing view — AI rows show no duration; the rest is Epic 8 or unchanged paths.
  - `[false]` `[reject]` blind: `seat_mark` takes two unused inputs — the AC names exactly these four inputs for later readers.
  - `[low]` `[patch]` blind: badly reflowed `seat_turns` docstring — reflowed.
  - `[low]` `[reject]` edge: `occupied_since` not passed — as blind row 2.
  - `[low]` `[reject]` edge: the guard-switch mark shows in the Week of the switch — that Week the LLM has already ordered (the guard runs on its Order), so the row reads «har bestilt»; the label is one Week early only.
  - `[low]` `[reject]` edge: holder from the latest occupancy, order state from the one in force — the holder rule is Story 6.1's; they differ only across a switch.
  - `[false]` `[reject]` edge: a Student Seat's Order by another decider does not start the wait — in Epic 6 a Student Seat's free-Week Orders are only `student`; «when the first Student orders» is the AC.
  - `[low]` `[reject]` edge: cached envelope refetches late — as blind row 8.
  - `[low]` `[reject]` edge: `setTimeout` overflow beyond 24.8 days — AI deadlines are seconds after the Week opens.
  - `[low]` `[reject]` edge: cached `server_now` understates waits — as blind row 7.
  - `[low]` `[reject]` edge: announcement key ignores holder names — as blind row 10.
  - `[false]` `[reject]` edge: unparsable `wait_started_at` shows NaN — the api sends an `AwareDatetime`.
  - `[false]` `[reject]` edge: Confirmed shows a visible «Venter på» — the AC asks the Confirmed message to name whom the game waits for; the rule is about a separate line under the button.
  - `[false]` `[reject]` edge: no horizontal-scroll check — `expectAccessible` asserts `scrollWidth <= clientWidth`.
  - `[low]` `[reject]` intent: the 2 s live path is tested by a stubbed refetch, not an SSE event — the house pattern; SSE→invalidation is `live-updates.spec.ts` and `topics.test.ts`.
  - `[medium]` `[patch]` intent: axe at 320/360/1440 ran only with AI ordered and Students waiting — the per-width test now also shows a waiting AI player, a guard-switched one and the own Order sent (Confirmed «… Venter på Fabrikk og Jonas Berg (3 min).») before its one axe check.
  - `[low]` `[reject]` intent: Hjem has no refetch at `next_change_at` — the AC puts it in the play envelope; Hjem refreshes on `game:` events.
  - `[low]` `[reject]` intent: `seat_mark` defined in `marks.py`, re-exported from `service.py` — `views` cannot import `service` (cycle); readers outside `games` get it from `games.service`.
  - `[low]` `[reject]` intent: AI rows show no duration though a start is stored — decision R4(a): «venter» with no extra copy (UX-DR62); the stored start serves Epic 7/8 readers.
  - `[low]` `[reject]` intent: no front-end Guided Week render — rows are data-driven; the api test covers the Guided case.
  - `[low]` `[patch]` verification-gap: `next_change_at` tested with one future deadline — now two future deadlines set later-first; asserts the nearer one, then the later after the first Seat orders.
  - `[low]` `[reject]` verification-gap: `occupied_since` branch unreachable — as blind row 2.
  - `[low]` `[reject]` verification-gap: holder/mark vs order state in the switch Week — as edge row 2.

## Design Notes

Founder-level calls: AI rows show «venter» without duration (wait bounded by NFR-2); `next_change_at` = nearest future AI deadline (the only due time before Epic 8); duration units and «KI-spiller (regelbasert)» are draft copy; the mark lives in `games/marks.py`, exported through `service.py`; own Seat named «deg» last in «Venter på»; the waiting set (not the minute) drives the announcement.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_seat_status.py tests/sessions/test_play.py tests/games/test_turn_times.py -q` -- pass
- `cd frontend && npx vitest run src/components src/modules/games` -- pass
- `cd frontend && npx playwright test e2e/seat-status.spec.ts e2e/homes.spec.ts e2e/order-confirm.spec.ts --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** The play screen and Hjem show the Setestatus: every Seat with a dot (filled ordered, hollow waiting, decorative), Role, name or «KI-spiller», and «har bestilt», «venter, 3 min», «venter» or «venter (deg)». It stands right under the Ordrefelt through the whole Uke and replaces «Setene» on Hjem. Migration 0048 adds `seat_turns.wait_started_at`; a Student's own Order (`place_order`, `decided_by = student`) or Guided view (`view_week`) sets it in the same transaction on the open Week's turns that have not ordered, via `rules.turn_times` with a new `clock_start` input; the trigger keeps it once set. `rules.has_ordered` is the one per-turn predicate (also used by `week_complete`). `table_status` adds `ordered`, `wait_started_at` and `mark` (AD-15 `seat_mark`; `guard_switch` → «KI-spiller (regelbasert)»). The envelope's `next_change_at` is the nearest future AI deadline and the page reads again then; Hjem's game gains `server_now`. The wait ticks on the server's clock; «Venter på: Jonas (3 min) og deg.» is a polite sr-only announcement, changed only when whom the game waits for changes; Confirmed reads «Ordren på 24 er sendt. Venter på Jonas (3 min).». `game:` events also refresh Hjem. Epic 8 slots (`statusLine`, `controls`, row `detail`/`action`) render nothing.

**Files.**
- `backend/migrations/versions/0048_seat_turns_wait_started_at.py` (new), `backend/app/modules/games/models.py` -- column + trigger.
- `backend/app/modules/games/rules.py` -- `has_ordered`; `TurnInputs.clock_start`; `TurnTimes.wait_started_at`.
- `backend/app/modules/games/commands.py` -- `_start_waits` from `_place` (Student) and `view_week`.
- `backend/app/modules/games/repo.py` -- `reason` on the latest occupancy; `set_wait_started_at`.
- `backend/app/modules/games/{schemas,marks (new),service,views}.py` -- `SeatMark`, `seat_mark`, `TableSeat` fields, `due_times`.
- `backend/app/modules/sessions/{schemas,service}.py` -- seat fields, `server_now` on the game, `next_change_at`.
- `backend/tests/sessions/test_seat_status.py` (new); `tests/games/test_turn_times.py`, `tests/test_migrations.py`, `tests/sessions/{test_play,test_student_home,test_start_game}.py` updated.
- `frontend/src/components/seat-status.tsx` (new) -- reusable Setestatus with Epic 8 slots.
- `frontend/src/modules/games/{seat-status.ts,seat-status-view.tsx,seat-status.test.tsx}` (new) -- words, server clock, announcement.
- `frontend/src/modules/games/{play-page,order-field,student-hjem}.tsx` -- placement, refetch at `next_change_at`, Confirmed with «Venter på»; `order-field.test.tsx`, `home.test.ts`.
- `frontend/src/lib/api/{topics.ts,topics.test.ts,openapi.json,schema.ts}`, `frontend/src/copy/nb.ts`, `frontend/src/modules/games/fixtures/play-week-*.json`, `frontend/e2e/support/play.ts`, `frontend/e2e/seat-status.spec.ts` (new).

**Review.** One pass, four layers, 36 findings (high 0, medium 1, low 29, false 6). Patched: axe at three widths now covers AI players and Students in both states (medium); trigger test uses `pytest.raises`; `next_change_at` tested with two future deadlines; docstring reflow. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. Patched: 1 medium (a test), 3 low.

**Founder-level decisions taken (no human in the loop).** AI rows read «venter» without a duration (the AI wait is bounded, UX-DR62) and are named by Role in «Venter på»; the own Seat is «deg», last. Durations «under 1 min», «N min», «N t» (< 48 t), «N d» [ASSUMPTION]. Guard switch reads «KI-spiller (regelbasert)» [ASSUMPTION]. `next_change_at` = nearest future AI deadline (the only due time before Epic 8). The announcement changes only when the set of waited-for Seats changes, not every minute. `seat_mark` lives in `games/marks.py`, exported through `games.service` (import cycle). The wait start is written on every Student Order where still unset (same result as «first Student»). Hjem's «Setene» became the Setestatus with hairline rows; `game:` events refresh Hjem. A game that is not running shows the rows without dot or status. Implementation ran in the orchestrator's context per the runbook; reviewers were sub-agents.

**Verification.**
- Backend: full suite 2720 passed, 7 failed (migration HEAD and a seats-equality assertion, both caused by the change) → fixed; those files 16 passed; `test_seat_status.py` 6 passed after review patches; ruff clean.
- Frontend: typecheck; Vitest 653 passed; `check:copy`; colour lint; build (compose image).
- Playwright: `seat-status.spec.ts` 7 passed (after patches); homes, student-home, order-confirm/failures/field, guided-week, game-start, week-table, chain-band, graph-over-table, live-updates, briefing, starting-task: 138 passed.
- Slow new tests: the per-width Setestatus test about 2 s (one axe per width); `test_seat_status.py` tests 2–4 s each (Class session setup). No fixed sleeps.
- New migration 0048 (not changed after it ran).

**Residual risks.** The e2e uses stand-in envelopes; the real route is held by `test_seat_status.py`. Waits shown from cached data can be up to 30 s short until the refetch. Mid-Week Seat changes (Epic 8) must pass `occupied_since` to `turn_times`. Draft copy awaits the founder.
