---
title: 'Story 1.9: Place Orders, write the Decision log and advance the Week'
type: 'feature'
created: '2026-11-17'
baseline_revision: '6c3a2c97a67fea03c19716fbef8349c8706d7058'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Guided Week whose Guided Order exceeds the maximum Order can never be completed, so such a Game stalls in Week 1.
    evidence: |-
      engine.guided_order returns the starting demand even above max_order (documented); validate() only warns
      (max_order_may_bind), place_order refuses the Order as order_invalid, and engine.advance would refuse it too.
      Decide in the engine/settings rules (error instead of warning, or cap the Guided Order).
    location: >-
      backend/app/engine/guided.py, backend/app/engine/settings.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A started Game (Story 1.8) has open turns but nothing can place an Order, so no Week advances, no Game finishes and no decision can be read back (FR-67, FR-26, FR-28).

**Approach:** Add `seat_weeks` (the Decision log, Alembic `0004`), the commands `games.commands.place_order` and `games.commands.finish`, the predicate `games.rules.week_complete`, a Decision log read (`games.views.decision_log`), and `python -m app.sim play` / `log`.

## Boundaries & Constraints

**Always:**
- `place_order(game_id, seat, week, order, decided_by)` (seat = Role or Seat id) is one transaction like every command: lock Game row → checks → writes → `_commit_change` (one version bump, one `game:<id>` notify) even when it advances or finishes.
- Checks, in this order, each refusing with nothing stored: `game_not_found` 404, `seat_not_found` 404, `game_not_started` 409 (lifecycle `not_started`), `game_finished` 409 (lifecycle `finished`), `decided_by_invalid` 422 (not a `DecidedBy`), `order_invalid` 422 (`type(order) is not int` or outside 0..`max_order`), `week_not_open` 409 (week ≠ newest stored opened Week), `order_exists` 409 (a `seat_weeks` row exists), `guided_order_required` 422 (Guided Week and decided_by ≠ `guided` or order ≠ `engine.guided_order(settings)`), `decided_by_invalid` 422 (`guided` outside a Guided Week). Guided Week = `week <= settings.guided_weeks`, read through `games.policy(purpose).guided_weeks == "settings"` (no purpose branch).
- The `seat_weeks` row: `id` UUIDv7, `game_id`, `seat_id`, `week`, `state_seen` = the `SeatState` exactly as `games.views.seat_state` returns it for that Seat and Week (JSON), `order`, `decided_by`, `fallback = none`, `occupant_kind` + `reason` of the occupancy row in force (`from_week <= week`, newest), `opened_at` + `rule_based_reference_order` copied from the turn, `ordered_at` = DB `now()`; the turn's `ordered_at` is set to the same `now()`. A trigger refuses UPDATE and DELETE on `seat_weeks`; unique `(game_id, week, seat_id)`.
- Advance: `games.rules.week_complete(turns)` (pure: true when every open turn has `ordered_at`) is the only test. When true, the same transaction runs `engine.advance(settings, state, orders)` with the Week's stored Orders; an opened next Week is stored via `_open_week` (reference Orders from the real earlier Orders); a finished state calls `finish`, which stores the finished state in `game_weeks` (`finished = true`) and sets `lifecycle = finished`. No turn opens after the last Week.
- Earlier Orders for every Seat view (command and `games.views`) now come from `seat_weeks`, no longer from `engine.placed_orders`.
- `game_weeks` gains `finished boolean NOT NULL DEFAULT false` in its PK `(game_id, week, finished)` and an append-only trigger; the `seat_turns` trigger also refuses changing an `ordered_at` that is already set.
- `app/engine` unchanged (golden traces, `RULES_VERSION` 1, 100 % branch coverage); ruff clean; all tests pass.

**Never:** No `players.ensure_order`, no `games.commands.advance` command, no `actor` argument, no fallback values other than `none`, no `game_checks`/replay check, no batch runner, no HTTP route (Stories 1.10, 1.11, 2.1, 6.x). No ORM classes, no new dependency.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One Order | running Classic, Week 5, retailer, 6, `rule_based` | one `seat_weeks` row, turn `ordered_at` set, version +1, one notify, no advance | — |
| Last Order of a Week | 3 of 4 placed | same transaction stores Week w+1 state + 4 turns; version +1 once | — |
| Guided Week | Week 1–4, `guided`, `guided_order` (4) | stored | other order / other `decided_by` → `guided_order_required` 422 |
| `guided` after Guided Weeks | Week 5, `guided` | nothing | `decided_by_invalid` 422 |
| Bad value | -1, 1000, 4.0, True, "4" | nothing | `order_invalid` 422 |
| Bad decided_by | `"robot"` | nothing | `decided_by_invalid` 422 |
| Wrong Week | week ≠ open Week | nothing | `week_not_open` 409 |
| Second Order | same Seat + Week | nothing | `order_exists` 409 |
| Unknown | bad Game id / Role | nothing | `game_not_found` / `seat_not_found` 404 |
| Not started | `not_started` Game | nothing | `game_not_started` 409 |
| Last Week complete | Week 36, 4th Order | finished state stored, `lifecycle finished`, no Week 37 turns | later `place_order` → `game_finished` 409 |
| Tamper | UPDATE/DELETE on `seat_weeks` or `game_weeks` | DB raises | — |
| Race | last two Orders at once | exactly one advance, version +2 total | — |
| Sim play | `sim play <id>` on a started Game | each turn: Guided Week → `guided_order`/`guided`; `rule_based` → stored reference/`rule_based`; `scripted` → `REGISTRY[policy_id](seat_state)`/`scripted`; prints `game`, `lifecycle finished`, `weeks 36`; exit 0 | refusal → `error <code>: …`, exit 1 |
| Sim log | `sim log <id>` | header + one row per Week and Seat: week, role, incoming_order, incoming_delivery, shipped, inventory, backlog, order, cost (= `state_seen.week_cost`), decided_by, reference | unknown Game → exit 1 |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `_commit_change` (L122), `_snapshot` (L254), `_open_week` (L281: pass real earlier Orders), `start` (L311); add `place_order`, `finish`, `__all__`.
- `backend/app/modules/games/repo.py` -- `lock_game`, `seats_with_occupant` (L66), `week_states` (L101: exclude/order by `finished`), `turn` (L111); add open-Week turns, occupancy in force, `insert_seat_week`, `set_ordered_at`, `seat_weeks` reads (orders per Week, Decision log rows), `insert_week(..., finished)`.
- `backend/app/modules/games/models.py` -- `game_weeks` (L76), `seat_turns`; add `seat_weeks`.
- `backend/app/modules/games/schemas.py` -- add `DecidedBy`, `Fallback` enums, `OrderPlaced` result, `DecisionLogRow`; add `guided: bool` to `TurnOverview`.
- `backend/app/modules/games/rules.py` (new) -- `week_complete`.
- `backend/app/modules/games/views.py` -- `build_seat_state` (pure, reuse in the command), `_opened`/`_week`, `seat_state`, `open_turn`; add `decision_log`; Orders from `seat_weeks`.
- `backend/app/modules/games/service.py` -- re-exports.
- `backend/app/platform/events/registry.py` -- add `games.place_order`, `games.finish` (`{"game"}`).
- `backend/migrations/versions/0003_game_weeks_seat_turns.py` -- trigger style for `0004`.
- `backend/app/engine/` -- read-only: `advance`, `guided_order`, `seat_view`, `GameFinishedError`; `REGISTRY` in `engine/scripted.py`.
- `backend/app/sim.py` -- `_start_game`/`_show_seat` patterns, `_report`, `COLUMNS`/`_format`, `build_parser`, docstring.
- Tests: `tests/conftest.py` (TRUNCATE list), `tests/test_migrations.py` (HEAD_TABLES, version `0004`, downgrade to `0003`, CHECKS), `tests/games/test_registry.py` (RUNNERS, found set), `tests/games/test_start.py` (ordered_at trigger case), `tests/games/test_views.py`, `tests/test_sim.py`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0004_seat_weeks.py` + `models.py` -- `seat_weeks` (columns above, CHECKs `week >= 1`, `"order" >= 0`, `rule_based_reference_order >= 0`, `decided_by`/`fallback`/`occupant_kind`/`reason` IN enum values, FKs, unique key), append-only trigger; `game_weeks.finished` + PK change + append-only trigger; replace `seat_turns_keep_opening` to guard a set `ordered_at`; downgrade restores 0003 exactly.
- `schemas.py`, `rules.py`, `repo.py`, `views.py`, `commands.py`, `service.py`, `registry.py` -- as in Boundaries.
- `backend/app/sim.py` -- `play <game_id>` and `log <game_id>` subcommands; docstring.
- `backend/tests/games/test_place_order.py` (new) -- every matrix row; one transaction lock→bump→notify with writes; the update-attempt test; race test; Guided Week for `rule_based` and `scripted` occupants; finish; `state_seen` equals `seat_state`; occupancy fields; Orders read from `seat_weeks`.
- Update `conftest.py`, `test_migrations.py`, `test_registry.py`, `test_start.py`, `test_sim.py` (`play`, `log`, refusals).

**Acceptance Criteria:**
- Given a finished Classic Game played by four Rule-based players via `sim play` (seed 7), when `sim log <id>` runs, then it prints 144 rows and each (Week, Role) cost equals the cost of `sim trace --orders rule_based` (Classic), and the Orders are equal too.
- Given the CI commands run locally, when they finish, then all tests pass, `app/engine` + `tests/engine` branch coverage is 100 %, ruff check/format clean.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 23 findings — high 0, medium 1, low 18, false 4, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) `decided_by` not checked against the occupant in force — deliberate (Design Notes): Guided Orders of Student Seats (6.10) and Epic 2 fallbacks legitimately differ; no caller passes a mismatch; a per-kind rule adds guards for states not shown.
  - `[low]` `[patch]` (blind) `sim play` loops forever if another writer finishes the Game — the loop now re-reads the Game after each pass and stops on its stored lifecycle.
  - `[low]` `[patch]` (blind) `sim play` reuses the Seats read at the start — same fix: occupants are re-read each pass.
  - `[low]` `[reject]` (blind) nothing limits a Game to one finished `game_weeks` row — only `finish` writes it, once, inside the locked transaction that completes the last Week; append-only trigger blocks edits; tampering-only.
  - `[low]` `[reject]` (blind) `finished` stored in the column and in the JSON — written together by `finish` from the same `WeekState`; rows are append-only.
  - `[low]` `[reject]` (blind) `finish` exported/registered though it joins its caller's transaction — the AC names `games.commands.finish`, and Story 2.1's `advance` calls it too; the registry entry states it shares the caller's one event.
  - `[low]` `[reject]` (blind) TRUNCATE bypasses the append-only triggers — only tests truncate; no code path does.
  - `[low]` `[reject]` (blind) no composite FK Seat↔Game / log row↔turn — `place_order` takes the Seat from the locked Game's own Seats; same decision as Story 1.8's triage.
  - `[low]` `[reject]` (blind) missing occupancy row reported as `week_not_open` — unreachable: `start` fills every Seat before Week 1 opens.
  - `[low]` `[reject]` (blind) each Order re-reads the whole Game (O(n²)) — 36 Weeks at most; well under a second per Order in the tests.
  - `[low]` `[reject]` (blind) downgrade restores the 0003 trigger body from a copy — the text is identical to 0003 (same template with the extra clause empty); dev-only path.
  - `[low]` `[reject]` (blind) untested paths (takeover occupancy, other policies, enum arguments, unknown UUID for `log`, `play_week` returning None) — takeovers and other policies do not exist before Epics 5/8; the rest are test-helper or trivially typed paths.
  - `[low]` `[patch]` (verification-gap) `sim play` resume branch untested — added `test_play_continues_a_partly_played_week`.
  - `[low]` `[reject]` (verification-gap) 0004 downgrade only tested on an empty schema — the code deletes finished rows after dropping the trigger and before restoring the PK; dev-only path, seeding needs a full Game.
  - `[medium]` `[defer]` (edge) a Guided Week with `guided_order > max_order` can never complete — pre-existing engine behaviour: `engine.guided_order` documents it and `warnings` only warns (`max_order_may_bind`); `sim trace` fails the same way. Deferred.
  - `[low]` `[reject]` (edge) turn ordered without a `seat_weeks` row gives a raw DB error — unreachable: both are written in the same transaction.
  - `[low]` `[reject]` (edge) decider vs occupant mismatch — same as the blind row.
  - `[low]` `[patch]` (edge) `sim play` spins if another writer finishes the Game — same fix as the blind row.
  - `[false]` `[reject]` (edge) scripted policy called with a `SeatState` instead of a `SeatView` — `SeatState` subclasses `SeatView` (Story 1.8), so it is one; the AC of Story 1.11 says so too.
  - `[low]` `[reject]` (edge) `play_week` returns None when nothing is left — test helper only, used on running Games.
  - `[false]` `[reject]` (intent) Guided Orders refused rather than substituted — the AC's outcome (fixed Order, `decided_by = guided`, every occupant kind) holds in the log, tested for `rule_based` and `scripted` occupants.
  - `[false]` `[reject]` (intent) `week_complete(turns)` instead of `week_complete(game)` — it is still the one predicate every advance asks, over the open Week's turns the Game has; Story 6.10 extends the same rows with `viewed_at`.
  - `[false]` `[reject]` (intent) "before any reader can see it" proved on raw storage, not the read surface — the views read only that storage; the one-commit test and the reader-thread test cover it.

## Design Notes

The finished state has the last Week's number, so `game_weeks` keys on `(game_id, week, finished)`: every engine state stays in one table for Story 1.10's replay and Story 1.11's summaries. `place_order` refuses (rather than rewrites) a non-guided Order in a Guided Week: Stories 2.1 and 6.10 have their callers pass the Guided Order with `decided_by = guided`, so a mismatch is a caller bug. `decided_by` is not checked against the occupant kind: Epic 2 records fallbacks where they differ. `sim play` is the single-Game driver that Story 1.11 turns into a batch runner.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-report=term-missing` -- expected: all pass, engine 100 %
- `cd backend && uv run alembic upgrade head && uv run python -m app.sim create --settings classic --seats rule_based --seed 7`, then `start <id>`, `play <id>`, `log <id>` -- expected: 144 Decision log rows, exit 0

## Auto Run Result

Status: done

**Summary:** `games.commands.place_order(game_id, seat, week, order, decided_by)` places one Order in one locked, version-bumping, `game:<id>`-notifying transaction. It writes one append-only `seat_weeks` Decision log row with `state_seen` (the Seat's `SeatState`), the Order, `decided_by`, `fallback = none`, the occupancy in force, `opened_at`, `ordered_at` and the turn's reference Order, and sets the turn's `ordered_at`. Stable refusals: `order_invalid` 422, `week_not_open` / `order_exists` / `game_not_started` / `game_finished` 409, `decided_by_invalid` / `guided_order_required` 422, `game_not_found` / `seat_not_found` 404, with the unique key `(game_id, week, seat_id)` as a backstop. When `games.rules.week_complete` holds, the same transaction runs `engine.advance` and opens the next Week (state plus turns with reference Orders), or calls `games.commands.finish`, which stores the finished state and sets `lifecycle = finished`. Seat views now read earlier Orders from the Decision log. `python -m app.sim play <id>` plays a Game to its end, and `log <id>` prints the Decision log.

**Files:** `migrations/versions/0004_seat_weeks.py` (new: `seat_weeks`, `game_weeks.finished` in the PK, append-only triggers, set `ordered_at` immutable); `modules/games/models.py`, `schemas.py` (`DecidedBy`, `Fallback`, `OrderPlaced`, `DecisionLogRow`, `TurnOverview.guided`, `GameOverview.settings`), `rules.py` (new: `week_complete`, `guided_week`), `repo.py`, `views.py` (`stored_orders`, `stored_play`, `decision_log`), `commands.py` (`place_order`, `finish`), `service.py`; `platform/events/registry.py`; `app/sim.py` (`play`, `log`); tests `tests/games/test_place_order.py` (new), `helpers.py`, `test_registry.py`, `test_start.py`, `test_views.py`, `tests/test_migrations.py`, `tests/test_sim.py`, `tests/conftest.py`.

**Review:** one pass, 23 findings (medium 1, low 18, false 4). Patched (low): `sim play` re-reads the Game each pass (no endless loop, current occupants), plus a resume test. Deferred (medium, pre-existing engine rule): a Guided Order above `max_order` stalls a Game. Everything else was rejected; the reasons are in the triage log.

**Follow-up review recommended:** false. Patched counts: high 0, medium 0, low 3 entries (one root cause plus one test).

**Verification:** `ruff check` and `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-branch`: 989 passed, 100 % (local compose Postgres). Ran `alembic upgrade head`, then `sim create --seats rule_based --seed 7`, `start`, `play` (`lifecycle finished`, `weeks 36`) and `log` (144 rows). Per (Week, Role), the cost column equals `sim trace --orders rule_based`. Matrix audit: every row is covered by a passing test in `test_place_order.py` or `test_sim.py`.

**Decisions taken in place of the founder:**
1. A Guided Week refuses anything but (`guided_order`, `guided`) with `422 guided_order_required`, and `guided` outside Guided Weeks gets `422 decided_by_invalid`. The command does not substitute the Order.
2. `decided_by` is not checked against the occupant kind.
3. Extra codes: `game_not_started`, `game_finished` (409), `decided_by_invalid`, `guided_order_required` (422), `game_not_found` / `seat_not_found` (404).
4. The finished state is stored in `game_weeks` with `finished = true` (PK `(game_id, week, finished)`). `game_weeks` and `seat_weeks` are DB append-only, and a set `ordered_at` cannot change.
5. `week_complete` takes the open Week's turns (true when all have `ordered_at`).
6. `finish(session, game_id, state)` joins its caller's transaction and is registered as `games.finish: {game}`.
7. Added `sim play` (Guided Order, stored reference Order for `rule_based`, policy for `scripted`).
8. Views read earlier Orders from `seat_weeks`.
9. `OrderPlaced`, `TurnOverview.guided` and `GameOverview.settings` were added for callers.
10. Implementation ran in the orchestrating agent's own context (runbook). The review layers were independent subagents.

**Residual risks:** the deferred Guided Order / `max_order` stall. TRUNCATE bypasses the append-only triggers. CI not run on GitHub (no push).
