---
title: 'Story 1.8: Start the Game and read what each Seat sees'
type: 'feature'
created: '2026-11-17'
status: 'done'
baseline_revision: '51b6152ec3538234432ae7516c494b6472db1733'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A stored Game (Story 1.7) cannot start: there is no stored Week state, no open turn, no reference Order and no model of what a Seat may see. Every later player (Student screen, LLM prompt, Decision log) needs one information boundary (AD-3) and turns with one clock (AD-20).

**Approach:** Add `game_weeks` and `seat_turns` (Alembic `0003`), the command `games.commands.start`, the pure engine helper `engine.view.seat_detail` (supply line slots, cost lines, history rows, preview coefficients), the boundary model `games.schemas.SeatState` (extends `engine.SeatView`), `games.views` (`build_seat_state`, `seat_state`, `open_turn`) and `python -m app.sim start` / `show`.

## Boundaries & Constraints

**Always:**
- `start` is one transaction like every command (lock Game row, checks, writes, `_commit_change` bump + `game:<id>` notify). Order inside it: fill every free Seat with `rule_based`, `from_week=1`, `reason=initial` through the same helper `assign_seat` uses; `engine.initial_state(settings)` → one `game_weeks` row (`state` = `WeekState.model_dump(mode="json")`); one `seat_turns` row per Seat with `opened_at` (DB `now()`), `ordered_at` NULL and `rule_based_reference_order` = `rule_based.order(settings, seat_view(...), params)`; `lifecycle = running`.
- Week opening is one helper (`_open_week`) that Story 1.9 reuses; reference Orders are computed only there. A DB trigger refuses any UPDATE that changes `seat_turns.rule_based_reference_order`, `opened_at`, `game_id`, `seat_id` or `week`, and any DELETE.
- The Game reads only its snapshot: settings from `games.settings`, params from `session_runtime` (id; file version must equal the stored version), and `start` refuses if `rules_version ≠ engine.RULES_VERSION` or if `demand_series(settings)` ≠ the stored `demand_series`.
- `SeatState` = `SeatView` + `schema_version: Literal[1]` + `week`, `incoming_order`, `incoming_delivery`, `shipped`, `supply_line_slots` (each `stage` ∈ {`ordered`, `in_transit`, `in_production`}, `quantity`, `arrival_week`), `overdue` (supply line minus the slots: units the upstream Seat owes), `position` (inventory − backlog + supply line), `cost_lines` (`holding` / `backorder`: units, rate, amount), `week_cost`, `total_cost` (earlier Weeks + this Week), `history` (one row per earlier Week: week, incoming order, incoming delivery, shipped, inventory, backlog, supply line, position, cost, order), `min_order` 0, `max_order`, `preview` (`order_arrival_week`, `supply_line_base`, `position_base`: value after typing x = base + x). Numbers and Roles only. All game arithmetic lives in `app/engine`; `games.views` only assembles.
- `build_seat_state(settings, states, orders, role)` reads only that Role's Seat from `states`; Earlier Orders for the DB path come from `engine.view.placed_orders(settings, states)` (read from the opened states) until Story 1.9 stores them.
- Neighbour numbers stay empty (no Information visibility yet). `app/engine` stays pure with 100 % branch coverage; ruff clean; all tests pass.

**Never:**
- No `place_order`, `seat_weeks`, advance, `finish`, `players.ensure_order`, near-optimal reference, HTTP routes (Stories 1.9, 2.x, 6.x). No new dependency. No ORM classes. No change to engine outputs (golden traces unchanged, `RULES_VERSION` stays 1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start full | created Game, 4 Seats assigned | `running`, version +1, 1 `game_weeks` row (week 1 = `initial_state`), 4 `seat_turns` rows, no new occupancy, one `game` notify | — |
| Start with free Seats | 0–3 Seats assigned | free Seats get `rule_based`/`initial`/`from_week 1`; assigned ones keep theirs | — |
| Start twice | `running` Game | nothing changes, no notify | `game_already_started` (409) |
| Unknown Game | bad / unknown id | nothing | `game_not_found` (404) |
| Snapshot broken | stored series ≠ engine series, or `rules_version` unknown, or param file version ≠ stored | nothing stored | `snapshot_mismatch` (409) / `rules_version_unsupported` (409) / `parameter_set_changed` (409); unknown set → `unknown_parameter_set` (422) |
| Reference immutable | UPDATE of `rule_based_reference_order` | DB raises | — |
| Seat state | started Classic Game, `retailer`, Week 1 | Week 1, inventory 12, backlog 0, incoming order 4 (demand), supply line 12 = slots [ordered 4 → Week 4, in_transit 4 → Week 2, in_transit 4 → Week 3], overdue 0, position 24, cost lines 6.00/0.00, total 6.00, empty history, max_order 999, preview arrival Week 5 | — |
| View errors | unknown Game / Role / not started / Week not stored | — | `ViewError`: `game_not_found` / `seat_not_found` (404), `game_not_started` / `week_not_open` (409) |
| Sim show | `sim show <id> --seat retailer` | SeatState JSON, `opened_at <iso>`, `reference_order <n>`; exit 0 | `error <code>: <message>` on stderr, exit 1 |

</intent-contract>

## Code Map

- `backend/app/engine/view.py` -- `SeatView` (L31), `starting_supply_line` (L58), `seat_view` (L70): add `SupplyLineSlot`, `CostLine`, `WeekValues`, `OrderPreview`, `SeatDetail`, `seat_detail`, `placed_orders`; export in `engine/__init__.py`.
- `backend/app/engine/state.py` -- engine `SeatState`/`WeekState` (stored per Week as JSON; pipelines "arrives soonest first"; `production_orders[0]` already entered production and sits in `goods_slots[-1]`).
- `backend/app/engine/week.py` -- `initial_state`, slot layout; an Order of Week w arrives in Week w + order_delay + (shipping or production delay).
- `backend/app/engine/rule_based.py` -- `order(settings, view, params)`, `parse_params`.
- `backend/app/modules/games/commands.py` -- `_policy`, `_rule_based_params`, `_commit_change`, `assign_seat` (L197; extract its occupancy append into a shared helper), `__all__`.
- `backend/app/modules/games/repo.py` -- add `insert_week`, `insert_turns`, `set_lifecycle`, `weeks(game_id, upto)`, `open_turn(seat_id)`; reuse `seats_with_occupant` (L66).
- `backend/app/modules/games/models.py`, `schemas.py`, `service.py` -- add tables, `SeatState`, `TurnOverview`, re-exports.
- `backend/migrations/versions/0002_games_seats_occupancy.py` -- style for `0003`, trigger pattern.
- `backend/app/platform/events/registry.py` -- add `games.start`.
- `backend/app/sim.py` -- `_create_game` error-handling pattern (L335), `_run`, `build_parser`.
- `backend/tests/conftest.py` (`games_db` TRUNCATE list), `tests/test_migrations.py` (HEAD_TABLES, version), `tests/games/test_registry.py` (RUNNERS, found set), `tests/games/helpers.py`, `tests/test_sim.py`.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/view.py`, `engine/__init__.py` -- `seat_detail(settings, states, orders, role) -> SeatDetail` and `placed_orders(settings, states) -> tuple[dict[Role,int], ...]`, same input checks as `seat_view` -- the one place the boundary's numbers are computed (AD-1).
- `backend/tests/engine/test_view.py` -- slots/overdue/position/costs/history/preview on Classic Week 1 and on a step-to-8 Rule-based run; `placed_orders` reproduces the Orders given to `advance`; slots + overdue = supply line for every Role and Week; errors -- keep 100 % branch coverage.
- `backend/app/modules/games/models.py` + `migrations/versions/0003_game_weeks_seat_turns.py` -- `game_weeks(game_id FK, week ≥1, state JSONB, created_at; PK(game_id, week))`, `seat_turns(id uuid PK, game_id FK, seat_id FK, week ≥1, opened_at tz default now(), ordered_at tz NULL, rule_based_reference_order int ≥0; unique(game_id, week, seat_id))`, the trigger; downgrade drops them.
- `backend/app/modules/games/schemas.py` -- `SeatState`, `TurnOverview(week, opened_at, ordered_at, rule_based_reference_order)`.
- `backend/app/modules/games/commands.py`, `repo.py`, `platform/events/registry.py` -- `start`, `_open_week`, shared occupancy helper, `__all__`.
- `backend/app/modules/games/views.py` (new), `service.py` -- `ViewError`, `build_seat_state` (pure), `async seat_state(game_id, seat, week=None)` (seat = Role or Seat id; default = open Week), `async open_turn(game_id, seat)`; service re-exports.
- `backend/app/sim.py` -- `start <game_id>` (prints `game`, `lifecycle`, `week`, seat lines) and `show <game_id> --seat ROLE` (SeatState JSON with indent 2, then `opened_at <iso>`, `reference_order <n>`); module docstring.
- Tests: `tests/games/test_start.py` (every matrix row, one transaction with lock→bump→notify, trigger, reference = engine value, race of two `start`), `tests/games/test_views.py` (DB path + information-boundary test over every Role and Week of a Classic Game: JSON has no `weeks`/`demand`/`seed`/name keys, string values only Roles/stages/kinds/decimals, no future demand, unchanged when other Seats' states, `weeks` and the seed change; only the Retailer's incoming orders equal customer demand), registry/migration/conftest updates, `tests/test_sim.py` start/show.

**Acceptance Criteria:**
- Given a migrated database, when `uv run python -m app.sim create --settings classic --seats rule_based`, then `start <id>`, then `show <id> --seat retailer` run, then `show` prints the Retailer's SeatState JSON for Week 1 and the turn's `opened_at` and reference Order, exit 0.
- Given the CI commands run locally, when they finish, then all tests pass, `app/engine` + `tests/engine` branch coverage is 100 %, ruff check/format clean.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 34 findings — high 0, medium 1, low 24, false 9, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) `game_weeks` has no append-only trigger — only `games.commands` writes it, and Stories 1.9/1.10 decide how a finished state is stored; a trigger now would constrain that design for a tampering-only risk.
  - `[low]` `[reject]` (blind) trigger does not guard `id` or an already-set `ordered_at` — `ordered_at` gets its writer in Story 1.9, which owns that rule; no code path rewrites ids.
  - `[low]` `[reject]` (blind) no composite FK tying a turn's Seat to its Game or to `game_weeks` — `_open_week` is the only writer and takes Seat ids from the same Game; schema surface for a tampering-only risk.
  - `[false]` `[reject]` (blind) `seat_turns` lacks the Order — AD-15 puts the Order in `seat_weeks` (Story 1.9), not on the turn row.
  - `[low]` `[patch]` (blind) `seat_state` and `open_turn` pick the newest Week differently — both now use one `_opened`/`_week` helper (finished states excluded); `open_turn` takes an optional `week`.
  - `[low]` `[reject]` (blind) corrupt or gapped `game_weeks` raises instead of `ViewError` — only commands write Weeks, contiguously; a loud failure on tampered storage is correct.
  - `[low]` `[reject]` (blind) read path skips the `rules_version` check — a Game cannot reach `running` without passing it in `start`; per-version packages arrive in Story 1.10.
  - `[low]` `[patch]` (blind) `show` could print the state and turn of different Weeks — `sim show` now asks `open_turn` for `state.week`.
  - `[false]` `[reject]` (blind) a field added to `SeatDetail` but not `SeatState` is silently dropped — `SeatView`'s config is `extra="forbid"`, so validation raises; the two models share no keys.
  - `[low]` `[reject]` (blind) `SeatState` names both the engine and the boundary model — the boundary name is fixed by AD-3 and the AC; the engine type is aliased where both meet.
  - `[low]` `[patch]` (blind) future-demand check was a substring search only — added `test_a_seat_state_never_reads_demand_beyond_its_week` (Games sharing demand to Week 12 give equal states for every Role, Weeks 1–12).
  - `[low]` `[patch]` (blind) regex "no arithmetic in views" test proves little — deleted.
  - `[low]` `[reject]` (blind) `seat_detail` reads loop variables after the loop; quadratic sum — correct (non-empty guaranteed by `_checked`), 36 Weeks at most.
  - `[low]` `[patch]` (blind) CLI gaps — `--seat` metavar now `SEAT`; the rest rejected: `--week` not asked by the AC, `game_already_started` is the story's stable code, 409 for an unopened Week mirrors Story 1.9's `week_not_open`, the Guided-Week reference follows Design Notes.
  - `[low]` `[reject]` (edge) stored settings/runtime JSON failing validation raises a pydantic error — written by `create` from validated models; tampering only.
  - `[low]` `[reject]` (edge) gapped `game_weeks` rows give a traceback in `seat_state` — same as the blind corrupt-storage row.
  - `[low]` `[patch]` (edge) `open_turn` uses the row count as the newest Week — same root and fix as the blind newest-Week row.
  - `[low]` `[reject]` (edge) `open_turn` on a finished Game reports a turn as open — no finished Games exist before Story 1.9, which adds `finish`.
  - `[low]` `[reject]` (edge) `seat_state` does not check `rules_version` — same as the blind row.
  - `[low]` `[patch]` (edge) `show` race between two sessions — same fix as the blind row.
  - `[low]` `[reject]` (edge) a Role without a Seat row raises `KeyError` in `start` — `create` inserts one Seat per Role in the same transaction; unreachable without tampering.
  - `[low]` `[reject]` (edge) `week=True` or a string — internal API with type hints; callers pass `None` or an int.
  - `[low]` `[reject]` (edge, claim) engine tests do not run a step-to-8 Rule-based Game through `seat_detail` — `tests/games/test_views.py` runs a full Classic Rule-based Game through `build_seat_state` (which calls `seat_detail`) for every Role and Week; the engine suite uses distinct synthetic Orders on purpose.
  - `[medium]` `[patch]` (verification-gap) reference Orders were checked only where every Seat's Week 1 view is equal — added `test_each_turn_holds_the_reference_order_of_its_own_seat` (starting backlog 20: expected 15, 15, 15, 20).
  - `[low]` `[patch]` (verification-gap) trigger's `game_id` check untested — added the `UPDATE … SET game_id` case.
  - `[low]` `[patch]` (verification-gap other) `open_turn`/`seat_state` newest-Week disagreement — same fix as the blind row.
  - `[low]` `[patch]` (verification-gap other) regex test is not AD-1 evidence — deleted (same as the blind row).
  - `[low]` `[reject]` (intent) the every-Week proof runs on `build_seat_state`, not the DB `seat_state` — the DB function calls the same builder over stored states (tested for Weeks 1–3); Weeks past 1 cannot be stored by a command before Story 1.9.
  - `[low]` `[patch]` (intent) "searches" met by invariance, not literal search — strengthened by the demand-invariance test; the Week count cannot be searched as a value (36 is a legal Week number), so invariance under `weeks=40` is the proof.
  - `[false]` `[reject]` (intent) `overdue` exposes the upstream Seat's backlog — computed only from the Seat's own Orders and receipts (supply line minus slots), as the scramble test proves; derivable from FR-23 values.
  - `[false]` `[reject]` (intent) reference Order computed from `SeatView`, not `SeatState` — `SeatState` extends `SeatView` with the same values; `test_seat_state_is_a_seat_view_the_engine_accepts` shows equal Orders.
  - `[false]` `[reject]` (intent) CLI tested at Week 1 only — the AC asks for the started Game's open turn, which is Week 1 in this story.
  - `[false]` `[reject]` (intent) extra surface (`sim start`, snapshot refusals, exports, `ViewError`) — each is needed to reach or guard the AC paths; descriptive.
  - `[false]` `[reject]` (intent) `start(game_id)` and optional `week` differ from `start(game)` — the Game is identified by id as in Story 1.7's `assign_seat`; descriptive.

## Design Notes

Supply line slots (Week t, delays od/sd/pd, g = sd or pd for the last Role): `ordered` = own Orders of Weeks w = t−od+1 … t−1 (prefill `supply_line` for w < 1), arrival w + od + g; `in_transit` (`in_production` for the last Role) = `goods_slots[k]`, arrival t+1+k. Orders the upstream Seat already received but could not ship are in its backlog: `overdue = supply_line − Σ slots` (0 for the last Role). Arrival Weeks assume the upstream ships in full. The reference Order is the rule's answer also in Guided Weeks (Guided Orders are a separate `decided_by`, Story 1.9).

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-report=term-missing` -- expected: all pass, engine 100 %
- `cd backend && uv run alembic upgrade head && uv run python -m app.sim create --settings classic --seats rule_based` then `start <id>` and `show <id> --seat retailer` -- expected: JSON + `opened_at` + `reference_order`, exit 0

## Auto Run Result

Status: done

**Summary:** `games.commands.start` opens a stored simulation Game. In one locked, version-bumping, `game:<id>`-notifying transaction it gives every free Seat a Rule-based player (`from_week 1`, `initial`), checks the snapshot (rules version, demand series, parameter-set version), stores the engine's Week 1 state in `game_weeks`, writes one `seat_turns` row per Seat with `opened_at` and the Rule-based reference Order computed once from that Seat's own view, and sets `running`. A second `start` answers `409 game_already_started`. A DB trigger keeps a turn's opening values immutable. `games.schemas.SeatState` (extends `engine.SeatView`, `schema_version` 1) is the information boundary; its numbers come from the new pure `engine.seat_detail` (supply line slots with arrival Weeks, overdue, Posisjon, cost lines, running total, history rows, Order limits, preview coefficients). `games.views.seat_state` / `open_turn` read it from storage; `python -m app.sim start <id>` and `show <id> --seat retailer` print it.

**Files:** `backend/app/engine/view.py` (`seat_detail`, `placed_orders`, slot/cost/history/preview models), `engine/__init__.py` (exports); `modules/games/models.py` + `migrations/versions/0003_game_weeks_seat_turns.py` (tables, trigger); `schemas.py` (`SeatState`, `TurnOverview`); `commands.py` (`start`, `_open_week`, `_snapshot`, shared occupancy helper); `repo.py` (Week/turn SQL); `views.py` (new); `service.py` (re-exports); `platform/events/registry.py` (`games.start`); `app/sim.py` (`start`, `show`); tests `tests/engine/test_view.py`, `tests/games/test_start.py`, `tests/games/test_views.py` (new), `test_registry.py`, `tests/test_migrations.py`, `tests/test_sim.py`, `tests/conftest.py`.

**Review:** one pass, 34 findings (medium 1, low 24, false 9). Patched: per-Seat reference Order test (medium); one newest-Week helper for `seat_state`/`open_turn`, `open_turn(week)` and `sim show` reading one Week; demand-invariance test; trigger `game_id` test; removed the weak regex test; `--seat` metavar (low). Deferred: none. Rejected with reasons in the triage log.

**Follow-up review recommended:** false — patched counts: high 0, medium 1 (a test addition), low 8 entries.

**Verification:** `ruff check` / `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100`: 949 passed, 100 % (local compose Postgres); `alembic upgrade head`, `sim create --settings classic --seats rule_based`, `sim start <id>`, `sim show <id> --seat retailer` print the Week 1 `SeatState` JSON, `opened_at` and `reference_order 4`, exit 0. Matrix audit: every row covered by a passing test in `test_start.py`, `test_views.py` or `test_sim.py`.

**Decisions taken in place of the founder:** (1) `SeatState` fields beyond the AC list: `overdue` (units the upstream owes, derived from own numbers), `week_cost`, `min_order`; `total_cost` includes this Week's cost; history rows hold each earlier Week's values and Order; (2) supply line slots = goods in transit / in production plus own Orders not yet received upstream, arrival Weeks assume full shipment, soonest first; (3) preview coefficients = `order_arrival_week`, `supply_line_base`, `position_base` (value = base + typed Order); (4) the reference Order is the rule's answer also in Guided Weeks; (5) `start` refuses `rules_version_unsupported`, `snapshot_mismatch`, `parameter_set_changed` (409); (6) earlier Orders for the stored view are read back from the stored Week states (`engine.placed_orders`) until Story 1.9 stores them; (7) `seat_state`/`open_turn` take a Role or a Seat id, default to the newest opened Week, and refuse with `ViewError` codes `game_not_found`, `seat_not_found`, `game_not_started`, `week_not_open`; (8) added `python -m app.sim start <id>` so `show` is reachable from the CLI; (9) `game_weeks` gets no immutability trigger yet (left to Stories 1.9/1.10); (10) implementation ran in the orchestrating agent's own context (runbook); review layers were independent subagents.

**Residual risks:** `game_weeks` rows are not DB-protected against UPDATE; `open_turn`/`seat_state` on a finished Game are defined only once Story 1.9 stores finished states; CI not run on GitHub (no push).
