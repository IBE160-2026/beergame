---
title: 'Story 1.5: Prove the bookkeeping is correct by construction'
type: 'feature'
created: '2026-11-17'
status: 'done'
baseline_revision: '597ad62655103dacc34e8bb9a3f13ef13bf10daf'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Nothing checks that a sequence of engine Week states keeps its books: that units are conserved across the chain, that costs follow the end-of-Week balances and that totals add up (FR-29, FR-28). Without a pure check, a bookkeeping slip in `advance` or in stored data would only show in front of a Student, and Story 1.10's finished-game check has nothing to call.

**Approach:** New pure module `backend/app/engine/check.py` with `conservation(settings, states, orders) -> tuple[Violation, ...]` (empty tuple = books correct). It first checks the shape of the input (and returns only shape violations if it is malformed), then checks every state Week by Week and Seat by Seat against named rules, recomputing the expected values from the settings, the previous state and the Orders. A seeded property test drives random valid Games through the engine and requires zero violations; a mutation test alters one number and requires a violation naming that Week and Role.

## Boundaries & Constraints

**Always:**
- Engine purity (AD-1): `check.py` imports only stdlib, pydantic and `app.engine`; `test_purity` must keep passing.
- Never raises on any input of the declared types or on malformed data within them (non-`WeekState` items, wrong Roles, wrong slot lengths, non-int numbers, non-finite or non-`Decimal` costs, bad Orders, settings whose demand series cannot be built). Bad data → violations.
- Every `Violation` names `rule` (stable code from Design Notes), `week` (int, or None for whole-list shape problems) and `role` (`Role`, or None for chain-level rules), plus `expected`, `actual` (strings, may be None) and a `message`.
- Input contract: `states[0]` is Week 1 as opened by `initial_state`; `states[i] = advance(settings, states[i-1], orders[i-1])`; so `len(orders) == len(states) - 1`. The list may stop at any opened Week (Game in progress) or end with the finished state (same Week number as the one before, `finished=True`).
- Units on hand and in transit = Σ inventory + Σ `goods_slots` over Seats. Order slots (`incoming_orders`, `production_orders`) hold Orders, not units, and are not counted.
- All existing tests and golden traces pass unchanged; CI keeps 100 % branch coverage of `app/engine` and `tests/engine`.

**Never:**
- No change to `advance`, `initial_state`, `WeekState` or `GameSettings` behaviour. No DB, migration, `game_checks` table or CLI command (Story 1.10). No capacity handling (Story 1.12 exempts capped Seats from the both-positive rule).
- No new third-party dependency (Hypothesis is not in the spine's Stack table): property tests use a seeded `random.Random` in the test code only.
- The check never calls `advance`/`initial_state` to get its expected values: expectations are recomputed from settings, previous state and Orders, so an engine bug cannot hide itself.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Classic finished | `GameSettings()`, 36 Weeks of Orders 4, 37 states | `()`; Week 1 chain units 80 before opening | — |
| In progress | first 10 states, 9 Orders | `()` | — |
| Finished, units left in slots | finished state | units in slots counted in `units_conserved`; finished `total_cost` = Σ Week costs, no cost for slots | — |
| One unit altered | Wholesaler inventory +1 in Week 7 | violations incl. `inventory_balance`, week 7, wholesaler; `units_conserved`, week 7, role None | — |
| One cost altered | Factory cost +0.50 in Week 3 | `cost`, week 3, factory | — |
| One total altered | Retailer `total_cost` in finished state | `total_cost` (retailer) and `chain_total_cost` (None), week 36 | — |
| Both positive | a Seat with inventory 2 and backlog 1 (balances otherwise consistent) | `inventory_and_backlog`, that Week and Role | — |
| Malformed | `[]`; item not a `WeekState`; wrong Role order; slot length wrong; `inventory="x"` via `model_construct`; cost `Decimal("NaN")`; Orders count wrong, missing Role, non-int, negative, above `max_order`; Week numbers out of sequence; `finished` not last | only shape violations (`states_shape`, `seat_shape`, `orders_shape`, `week_sequence`) | never raises |
| Unbuildable demand | random pattern with `demand_seed=None` | `demand_series` violation, week None | never raises |

</intent-contract>

## Code Map

- `backend/app/engine/state.py` -- `SeatState` fields and their meaning (L13-L40): `goods_slots` = units in transit to the Seat after this Week's shipment moved in (last Role: production); `incoming_orders[0]` = Order received this Week; `production_orders[0]` = Factory Order that entered production when this Week opened; `cost` = this Week's cost, `total_cost` = Σ earlier Weeks. `WeekState.seat(role)`.
- `backend/app/engine/week.py` -- reference semantics only (do not reuse in the check): `initial_state` fills every slot with `supply_line` (goods slots: `shipping_delay`, last Role `production_delay`; order slots `order_delay`); `_open_week` L131-L160; finished state L91-L104 is a copy of Week N with `total_cost` charged and order slots shifted, no new Week.
- `backend/app/engine/settings.py` -- `GameSettings` (roles may be any non-empty unique tuple; first Role faces the customer, last produces; a 1-Role chain is both), `demand_series(settings)` (raises `ValueError` on unbuildable patterns), `FROZEN` config, `Role`.
- `backend/app/engine/__init__.py` -- re-export `Violation`; module `app.engine.check` holds `conservation` (AC names `engine.check.conservation`).
- `backend/tests/engine/test_week.py` -- style (`CONSTANT`, `FOURS`, `units(state)` helper).
- `backend/tests/engine/test_purity.py` -- forbids `random` etc. in `app/engine` only; tests may use `random`.
- CI `.github/workflows/ci.yml` -- `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100`; no CI change needed.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/check.py` -- `Violation` (frozen pydantic) and `conservation(settings, states, orders)`: shape pass, then the rules in Design Notes; module docstring states the rules -- FR-29, FR-28, AD-1.
- `backend/app/engine/__init__.py` -- export `Violation`; docstring mentions `app.engine.check.conservation`.
- `backend/tests/engine/test_check.py` -- every I/O matrix row; one test per rule showing the rule fires with the right week/role; an over-shipping forgery (shipped, inventory, backlog and cost changed together so every balance holds) is caught by `shipment` alone; a finished state at the right index stamped with the wrong Week gives `week_sequence`; 1-Role chain and 1/1/1, 3/3/3 delays with starting backlog pass; every shape branch.
- `backend/tests/engine/test_check_properties.py` -- seeded property test (`random.Random(20261117)`, 300 runs): random valid settings (`validate(...) == ()`, all four demand kinds, delays 1-3, 1-4 Roles, Orders drawn from {0, `max_order`, uniform 0..`max_order`, near demand}), finished or stopped early → `conservation == ()`; mutation property: alter one int field or slot by ±1 or one cost by ±0.01 in a random state and Seat → a violation with that Week, that Role and the rule the altered field belongs to (Design Notes). Failure messages print run index and settings JSON. No separate same-process reproducibility test (it would prove nothing beyond `random.Random`).

**Acceptance Criteria:**
- Given the CI command run locally, when it finishes, then all tests pass, branch coverage of `app/engine` and `tests/engine` is 100 %, `ruff check` and `ruff format --check` pass.
- Given the Classic Game played with Orders 4 for 36 Weeks, when `conservation` runs on its 37 states, then it returns `()`, and the units sum at Week 1 before opening is 80.
- Given the property test with its fixed seed, when it runs, then every run passes the check, and a failure message names the run and its settings so it can be reproduced.

## Spec Change Log

- 2026-11-17 Review loop 1 (bad_spec). Trigger: blind, edge-case and verification-gap reviewers all showed that a Seat shipping more than it holds (with inventory, backlog and cost changed to match) passed every rule, so negative balances and an over-shipping engine slip went unseen. Amended: Design Notes add the `shipment` rule (shipped = min(on hand, owed)); Tasks add the over-shipping forgery test, the wrong-Week finished-state test, and require the mutation property to assert the rule as well as Week and Role; the same-process reproducibility test is dropped. Known-bad state avoided: a check that accepts negative inventory or over-shipping. KEEP: everything else in the first implementation (shape pass returned alone, recomputed expectations from settings/previous state/Order history, rule codes and messages, `starting_units`, finished-state handling, test files and generator) — it passed all tests and 100 % branch coverage.

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 29 findings — high 0, medium 4, low 18, false 7, maybe-false 0
- findings:
  - `[medium]` `[bad_spec]` (blind) nothing checks shipped ≤ on hand or non-negative balances; a consistent over-shipping forgery passes — confirmed by probe (Retailer shipped +20, inventory −20, backlog −20, cost recomputed → `()`); triggered the `shipment` rule amendment (loop 1).
  - `[low]` `[bad_spec]` (blind) no test alters several fields consistently — same root cause; amendment adds the over-shipping forgery test.
  - `[low]` `[reject]` (blind) never-raises only for bad states, not bad arguments/settings — `orders=None` is outside the declared types; `series` raises only `ValueError` and always returns `weeks` values; settings come from validated `GameSettings`; guards for `model_construct`-built settings are unlikely in use and add branches.
  - `[low]` `[reject]` (blind) `chain_total_cost` cannot fire alone — true, it restates the per-Seat sums, but the AC names the chain total explicitly; harmless and cheap.
  - `[low]` `[reject]` (blind) `Role.X` and `"x"` keys merged silently; normalisation rebuilt per Role — `Role` is a `StrEnum`; a mapping with both forms of one key is not produced by any caller; the guard adds a branch.
  - `[low]` `[reject]` (blind) rule codes typed as `str` — codes are pinned by tests; a `Literal` adds surface for no reachable harm.
  - `[low]` `[reject]` (blind) `conservation` not re-exported from `app.engine` — the AC names `engine.check.conservation`; same choice as Story 1.4 (`engine.demand.series`).
  - `[low]` `[patch]` (blind) mutation property checks only Week and Role, not the rule — now asserts the rule each altered field belongs to.
  - `[low]` `[patch]` (blind) same-process reproducibility test proves nothing and costs runtime — removed.
  - `[low]` `[reject]` (blind) `week_sequence` labelled with the state's own (wrong) Week — the message names the item index; changing the label adds a branch.
  - `[low]` `[reject]` (blind) magic numbers 10 and 150 in tests — deliberate pins; a change to the field lists or generator should fail loudly.
  - `[false]` `[reject]` (blind) spec missing from the reviewed diff — by design the spec goes only to the edge-case layer as claims.
  - `[medium]` `[bad_spec]` (edge) over-shipping passes every rule — same root cause as the first blind row.
  - `[low]` `[bad_spec]` (edge) negative ints accepted by the shape pass — same root cause; with `shipment` and valid starting values, every balance and slot stays ≥ 0 by induction.
  - `[low]` `[reject]` (edge) settings built with `model_copy`/`model_construct` (roles `()`, `order_delay` 0) can raise — `roles=()` returns `seat_shape` and `orders_shape` violations (probe); `order_delay` 0 needs hand-made states and unvalidated settings; Story 1.10 loads stored settings through validation.
  - `[false]` `[reject]` (edge) `orders=None` or an unsized iterable raises — outside the declared `Sequence` types; the spec promises no-raise for inputs of the declared types.
  - `[medium]` `[bad_spec]` (edge, claim) "an engine slip cannot hide itself" is false for over-shipping — same root cause as the first blind row.
  - `[low]` `[reject]` (edge, claim) never-raises claim vs unvalidated settings — same as the edge `model_copy` row.
  - `[low]` `[patch]` (verification-gap) finished state at index 36 stamped Week 35 untested — added `(36, {"week": 35})` to `test_weeks_out_of_sequence`.
  - `[medium]` `[bad_spec]` (verification-gap other) negative inventory/backlog accepted — same root cause as the first blind row.
  - `[low]` `[patch]` (verification-gap other) mutation property does not check the rule — same as the blind row; patched.
  - `[false]` `[reject]` (intent) entered production read from the Orders, not the state — deliberate (Design Notes), so a changed Factory slot cannot balance itself out.
  - `[false]` `[reject]` (intent) totals lag one Week in an open Game — that is the engine's state contract (`total_cost` = earlier Weeks; `cost` = this Week); the finished total holds the full sum and is checked.
  - `[low]` `[reject]` (intent) never-raises not shown for bad settings or non-sequences — same as the blind row.
  - `[false]` `[reject]` (intent) "slots carry no cost" only indirect — `test_units_left_in_slots_at_the_end_are_counted_and_carry_no_cost` charges slots into the total and the check flags it.
  - `[low]` `[reject]` (intent) seeded loops instead of a property library — Hypothesis is not in the Stack table; the AC asks for a fixed seed and reproducible failures, which the seeded generator gives.
  - `[false]` `[reject]` (intent) no capacity input — capacity does not exist until Story 1.12; every Seat is uncapped.
  - `[false]` `[reject]` (intent) scope beyond the named invariants — the per-Seat rules are what lets a violation name the Role, as the AC requires.
  - `[low]` `[reject]` (intent) reuse only via `app.engine.check` — same as the blind export row.

### 2026-11-17 — Review pass
- verdicts: 24 findings — high 0, medium 0, low 16, false 8, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) a failing property run cannot be replayed on its own (shared `rng`; `alter` draws differ per test) — each run now draws from `random.Random(f"{SEED}-{run}")`; failure messages print that seed and the altered field, sign and state index.
  - `[low]` `[reject]` (blind) a `Violation` cannot tell the last opened Week from the finished state — both are Week N of the Game; finished-state messages say "after the last Week"; a state index or flag adds public surface Story 1.10 does not need.
  - `[low]` `[patch]` (blind) finished-state rule mapping undocumented — module docstring now states which rule names each finished-state field.
  - `[low]` `[reject]` (blind) Order keys normalised twice, series built twice, `cast` — at most 100 Weeks x 4 Roles; restructuring the passes adds plumbing for no visible gain.
  - `[low]` `[reject]` (blind) rule codes not published as a constant; tests restate field lists — codes are pinned by tests; a public constant adds surface.
  - `[low]` `[patch]` (blind) no deterministic Week 1 baseline test — added Week 1 rows for `inventory_balance`, `backlog_balance`, `in_transit` and `shipment`.
  - `[low]` `[patch]` (blind) tests rely on violation order (`found[0]`, `found[-1]`) — both now select the violation by rule.
  - `[low]` `[reject]` (blind) shape violations carry little structured detail — the message names the item and the problem; structured fields for malformed data add branches without a consumer.
  - `[false]` `[reject]` (blind) `test_constant_demand_keeps_every_seat_at_12` tests only the engine — it asserts `conservation(...) == ()` first.
  - `[low]` `[reject]` (blind) generator fixes `guided_weeks=0`, whole cents, no multi-field forgery — Guided Weeks do not enter the arithmetic; cents are the `RANGES` precision; the over-shipping forgery has a dedicated test.
  - `[low]` `[reject]` (edge) settings built by `model_copy`/`model_construct` can raise — carried: same location and claim as the pass-1 row.
  - `[false]` `[reject]` (edge) `orders` not a sequence raises — carried: outside the declared `Sequence` type.
  - `[low]` `[reject]` (edge) finished state shares its Week with the last opened Week, so keys repeat — same as the blind row above; both states are real and each violation is true.
  - `[low]` `[reject]` (edge, claim) never-raises vs unvalidated settings — carried from pass 1.
  - `[low]` `[patch]` (verification-gap) finished-state `inventory` entry unpinned — added `(36, Role.WHOLESALER, "inventory", 1, "inventory_balance")`.
  - `[false]` `[reject]` (intent) rule vocabulary beyond the four named invariants — carried: per-Seat rules let a violation name the Role; all four named invariants are present.
  - `[false]` `[reject]` (intent) total-cost timing — carried: engine state contract; the finished total is the full sum.
  - `[false]` `[reject]` (intent) "slots carry no cost" only implied — carried: a dedicated test charges slots and is flagged.
  - `[false]` `[reject]` (intent) no capacity input — carried: capacity arrives in Story 1.12.
  - `[low]` `[reject]` (intent) never-raises not shown for top-level arguments — carried from pass 1.
  - `[false]` `[reject]` (intent) the Orders-length precondition goes beyond the AC — the AC signature takes `orders`; one Order map per advanced Week is the only alignment that matches `advance`, and the docstring states it.
  - `[low]` `[reject]` (intent) seeded generator, no property library — carried from pass 1.
  - `[false]` `[reject]` (intent) FR-29's "runs over every finished Game and logs" not wired — Story 1.10's work; the intent says build only this story.
  - `[low]` `[reject]` (intent) lists must start at Week 1 — the finished-game check replays whole Games; a mid-Game slice has no previous state to check against; documented.

## Design Notes

**Notation.** State index s (0-based) = number of Orders applied before it. Opened state s is Week t = s + 1; the finished state (if any) has index N = `settings.weeks` and Week N. `d` = `order_delay`, `fill` = `supply_line`. For a Role sequence of Orders `o_1..o_s`, the order-slot history is `H = (fill,)*d + (o_1, …)`; after s Orders the slots are `H[s : s+d]`.

**Rules (stable codes).**
- `units_conserved` (role None): Σ inventory + Σ goods_slots = `start_units` + Σ entered production − Σ Retailer `shipped`, sums over the opened Weeks up to this one (the finished state adds nothing). `start_units` = n·`starting_inventory` + `fill`·((n−1)·`shipping_delay` + `production_delay`) (80 under Classic). Entered production in Week t = `H_last[t−1]` (last Role's Order history), never read from the state.
- `in_transit`: opened Week: `incoming_delivery` = prev `goods_slots[0]` and `goods_slots` = prev `goods_slots[1:]` + (arriving,), arriving = upstream Seat's `shipped` this Week, or entered production for the last Role. Week 1 prev slots = `(fill,)*len`. Finished: both equal the Week-N values.
- `shipment`: opened Week: `shipped` = min(prev inventory + `incoming_delivery`, prev backlog + `incoming_order`) (FR-26: ship the smaller of what is on hand and what is owed). Finished: equals Week N's (reported under `inventory_balance`). With valid starting values this also keeps inventory, backlog and every slot at 0 or above, so no separate sign rule is needed.
- `inventory_balance`: inventory = prev inventory + `incoming_delivery` − `shipped`; `backlog_balance`: backlog = prev backlog + `incoming_order` − `shipped`. Week 1 prev = `starting_inventory` / `starting_backlog`. Finished: inventory, backlog, shipped equal Week N's.
- `incoming_order`: first Role = `demand_series(settings)[t−1]`; others = `incoming_orders[0]`. Finished: equals Week N's.
- `order_slots`: `incoming_orders` = downstream Role's `H[s:s+d]`; last Role's `production_orders` = own `H[s:s+d]`; others empty (shape).
- `cost`: cost = `holding_cost`·inventory + `backorder_cost`·backlog.
- `total_cost`: `total_cost` at index s = Σ stated `cost` of opened states 0..s−1 for that Seat (so the finished total = Σ Weeks 1..N; slots never cost).
- `chain_total_cost` (role None, last state only): Σ Seat `total_cost` = Σ all stated costs of earlier opened states.
- `inventory_and_backlog`: never both > 0 (every Seat is uncapped until Story 1.12).
- Shape (returned alone when any is found): `states_shape` (empty list, item not a `WeekState`), `week_sequence` (opened Week ≠ index+1, Week beyond `settings.weeks`, `finished` anywhere but last or not on Week `settings.weeks`), `seat_shape` (Roles ≠ `settings.roles` in order, field not a plain int, cost not a finite `Decimal`, slot not a tuple of ints or wrong length), `orders_shape` (count ≠ len(states)−1, not a mapping, unknown/missing Role, value not int or outside 0..`max_order`), `demand_series` (series cannot be built).

**Why recompute instead of replay:** replaying with `advance` and comparing would make the check trust the engine it is meant to prove; the rules restate FR-26/29 independently.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-report=term-missing --cov-fail-under=100` -- expected: all pass, 100 % (Postgres from compose for non-engine tests)

## Auto Run Result

Status: done

**Summary:** New pure module `backend/app/engine/check.py`: `conservation(settings, states, orders)` returns a tuple of `Violation(rule, week, role, expected, actual, message)`, empty when the books are right. A shape pass (`states_shape`, `week_sequence`, `seat_shape`, `orders_shape`, `demand_series`) reports malformed data alone and never raises; then every state is checked against rules recomputed from settings, previous state and Order history without calling the engine: `units_conserved` (80 at the start under Classic; entered production from the Orders), `in_transit`, `shipment`, `inventory_balance`, `backlog_balance`, `incoming_order`, `order_slots`, `cost`, `total_cost`, `chain_total_cost`, `inventory_and_backlog`. A finished state counts units left in slots and charges them nothing. `starting_units(settings)` is public; `Violation` is exported from `app.engine`.

**Files:** `backend/app/engine/check.py` (new: check and rules); `backend/app/engine/__init__.py` (export `Violation`, docstring); `backend/tests/engine/test_check.py` (new: matrix rows, one test per rule, over-shipping forgery, shape cases); `backend/tests/engine/test_check_properties.py` (new: 300 seeded random valid Games pass; one number altered by one is named by rule, Week and Role).

**Review:** pass 1, 29 findings (medium 4, low 18, false 7): one bad_spec root cause (over-shipping with matching balances passed every rule) led to loop 1, which added the `shipment` rule and its tests; low items folded in (rule asserted in the mutation property, wrong-Week finished state test, same-process reproducibility test dropped); the rest rejected with reasons. Pass 2, 24 findings (low 16, false 8): 5 low patches (per-run seeds for replay, finished-state rules documented, Week 1 baseline rows, finished inventory row, order-independent assertions); the rest rejected or carried. Deferred none.

**Follow-up review recommended:** false — pass 2 patched high 0, medium 0, low 5.

**Verification:** `ruff check`, `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` gives 736 passed, 100 % branch coverage (Postgres from compose for the non-engine tests).

**Decisions taken in place of the founder:** (1) property tests use a seeded `random.Random` in the tests, not Hypothesis (not in the Stack table; no new dependency); (2) "units in transit" counts goods slots only, not order slots; units entered production come from the Order history, not the state; (3) the check also verifies per-Seat flow (`shipment`, balances, slots, incoming orders) so a violation can name the Role; (4) malformed input returns shape violations only; (5) state lists start at Week 1 with one Order map per advanced Week; the finished state is the same Week with `finished=True`; (6) every Seat is treated as uncapped until Story 1.12; (7) settings are trusted as validated `GameSettings` (Story 1.10 loads validated settings); (8) implementation ran in the orchestrating agent's own context (runbook constraint), not a separate implementation subagent; review layers were independent subagents.

**Residual risks:** a mid-Game slice cannot be checked on its own; rule codes are plain strings pinned by tests; CI not run on GitHub (no push).
