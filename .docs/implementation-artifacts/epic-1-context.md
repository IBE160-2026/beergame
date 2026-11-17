# Epic 1 Context: Game engine proven in simulation

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Build the foundation every later epic stands on: a repo that starts locally with zero keys, a pure game engine whose arithmetic is proven against hand-checked reference traces, and the stored-Game command path (Seats, occupancy, turns, Decision log) that real Class games will use unchanged. When done, the founder can run complete all-AI Games headless with `python -m app.sim` (Rule-based and scripted occupants), read a correct Decision log, and see a finished-game check pass for every Game. There is no login and no screen; the user is the founder at a terminal. The simulation runner is production code, not a throwaway prototype.

## Stories

- Story 1.1: Scaffold the repo so it starts locally with zero keys
- Story 1.2: Run the Classic chain Week by Week and match the reference trace
- Story 1.3: Check changed Game settings against ranges and warnings
- Story 1.4: Generate the demand series from a Demand pattern and a seed
- Story 1.5: Prove the bookkeeping is correct by construction
- Story 1.6: Order with the Rule-based player
- Story 1.7: Create a simulation Game with an AI player in every Seat
- Story 1.8: Start the Game and read what each Seat sees
- Story 1.9: Place Orders, write the Decision log and advance the Week
- Story 1.10: Verify every finished Game by replaying it
- Story 1.11: Run batches of all-AI Games with scripted occupants
- Story 1.12: Cap what a Seat can ship per Week (cut list, `FEATURE_CAPACITY`)

## Requirements & Constraints

- **Classic defaults:** four Roles (Retailer, Wholesaler, Distributor, Factory); starting inventory 12 per Seat; 4 units in every supply-line slot; order, shipping and Factory production delay 2; demand 4 stepping to 8 in Week 5; holding 0.50 and backorder 1.00 per unit per Week; 36 Weeks; Guided Weeks 1 to 4; maximum Order 999 (a stated placeholder that must not bind in normal play).
- **Week sequence is normative:** open the Week by receiving the incoming delivery; amount to ship = incoming order + backlog; ship the smaller of inventory and that amount (and capacity, if set); the rest is backlog; then Orders; then costs charged on end-of-Week balances; then all slots advance. The last Week runs in full; units left in slots carry no cost.
- **Slot layout at 2/2/2:** the Retailer's incoming order is customer demand with no delay; other Seats have 2 order slots; every Seat has 2 goods slots (production for the Factory). The chain starts with 80 units (48 inventory, 24 shipping, 8 production). A Factory Order reaches Factory inventory after 4 Weeks.
- **Bookkeeping invariants:** units on hand and in transit = starting units + units entered production − units delivered to customers; Seat cost = rates × end-of-Week balances; totals are sums of Week costs; inventory and backlog never both positive on an uncapped Seat. Checks return violations and never raise.
- **Reference traces:** constant demand 4 with every Order 4 keeps every Seat at 12, no backlog, 6.00 per Week. The step-to-8 golden trace must not come from the engine under test: its first 10 Weeks are worked by hand in a committed table the founder approves.
- **Settings validation:** delays 1 to 3 Weeks; all other ranges in one table with placeholder bounds marked (confirmed later by the Class session screen). Guided Weeks must end before the first demand change and leave Weeks to play. Non-blocking warnings with stable codes and the numbers behind them (supply line ≠ starting demand, backorder ≤ holding, binding maximum Order, too few Weeks for a change to pass through the chain at the chosen delays).
- **Demand patterns:** fixed series, step, random (discrete uniform over mean ± spread, floored at 0), step plus noise. Same pattern and seed give the same series on every platform; the seed is showable, storable and re-enterable; the caller supplies entropy for a new seed.
- **Rule-based player:** anchoring-and-adjustment on the Seat's own numbers only, never neighbour numbers. Parameters are a named, versioned config set; the only set shipped is `placeholder-unverified` (primary-source values are pending); never use calculator-site values. Guided Weeks order the starting demand without consulting the rule.
- **Information boundary:** what a Seat sees holds numbers only — no names, no number of Weeks, no future demand, no other Seat's state. Only the Retailer sees customer demand, for opened Weeks only.
- **Correctness:** full branch coverage is the aim for the engine; golden traces and property-based tests (fixed seed) run in CI; every finished Game is replayed and checked.
- **Capacity (cut list):** off by default behind `FEATURE_CAPACITY`; must leave every earlier golden trace and the Seat state unchanged when off.

## Technical Decisions

- **Layers:** `backend/app/engine/` is pure (stdlib and pydantic only; no I/O, no clock, randomness only from a passed seed) and imports nothing from `modules`. It owns all game arithmetic: `GameSettings`, `initial_state`, `advance(settings, state, orders)` (returns a new state, never mutates input), settings validation and warnings, demand series, conservation check, Rule-based player, Guided Order, the closed `scripted` policy registry, and `SeatView`. `modules/<slice>/` follows `routes, service, repo, models, schemas, jobs`; other modules import only `service.py`.
- **Numbers:** units are integers; cost rates and money are `Decimal` / `NUMERIC(14,4)`, travelling in JSON as decimal strings (`"0.50"`). `GameSettings` is one Pydantic model with `schema_version`, stored as JSONB, and is also the future schema for Class session settings and the Replay scenario.
- **One write path:** only `games.commands` mutates Games, Seats, occupancy, turns and Week states. Each command is one transaction: `SELECT … FOR UPDATE` on the Game row, `version` increment, and `platform/events.emit` → `NOTIFY` with `{topic, id, version}` only. Every command's topics are declared in `platform/events/registry.py` and asserted by a test; simulation Games emit only `game:<id>`. New commands are added to this list, never beside it.
- **Advance:** `games.rules.week_complete(game)` is the one predicate; the transaction that makes it true advances exactly one Week, storing the state before any reader can see it.
- **Snapshot at creation:** simulation Games freeze `GameSettings`, the materialised demand series with its seed, the engine `rules_version` and a `SessionRuntime` (AI mode, Rule-based parameter set id; later epics add fields). A Game reads only its snapshot.
- **Purpose:** every Game has a `purpose`; `games.policy(purpose)` is the one behaviour table and no command branches on purpose. `scripted` occupants exist only for `purpose = simulation`.
- **Occupancy** is an append-only history `(seat_id, from_week, occupant_kind, policy_id, reason)`; rows are never updated or deleted. `create` fills no Seat; `start` gives every free Seat a Rule-based player.
- **Seat state:** `games.schemas.SeatState` (versioned, extends `engine.SeatView`) is the single information boundary for the play screen, the LLM prompt and the Decision log; fields are added to it, never beside it. People-side data (names, waiting) is a separate view, never stored or sent to an LLM.
- **Turns and Decision log:** `seat_turns` holds one row per Seat per open Week with `opened_at` and the Rule-based reference Order computed once at Week open, never recomputed. `seat_weeks` rows are written once by `place_order` and never updated; `decided_by` and `fallback` are separate fields; unique key `(game_id, week, seat_id)`. Errors use stable codes in the envelope `{"error": {"code", "message", "fields"}}`.
- **Rules versions:** each engine version is a package `engine/rules/v<N>/` selected by the stored `rules_version`; an output-changing edit is a new version, never an edit to one a stored non-simulation Game references. Golden traces run per version.
- **Jobs-ready checks:** the finished-game check is idempotent, takes only a Game id, writes one immutable `game_checks` row, logs violations with ids only, and never changes the Game.
- **Simulation runner:** `app/sim.py` drives everything only through `games.commands` with `purpose = simulation`; summaries read from stored tables, never runner memory; identical batch and seed give identical runs.
- **Conventions:** UUIDv7 ids as strings; `timestamptz` in UTC; Weeks are integers from 1; tables plural `snake_case` with one owning module; Alembic owns every schema change (expand-then-contract), each story adds its own revision; structlog JSON with no names, emails or free text. Folders are `backend/` and `frontend/`; compose services carry the same names; URL paths stay `/api/*`.

## Cross-Story Dependencies

- 1.1 (done) precedes all. 1.2 → 1.3 → 1.4 → 1.5 build the pure engine; 1.6 adds `engine.SeatView`, which 1.7–1.11 use.
- 1.7 (`games`, `seats`, `seat_occupancy`, `games.policy`, `platform/events`) → 1.8 (`game_weeks`, `seat_turns`, `SeatState`, `start`) → 1.9 (`seat_weeks`, `place_order`, advance, `finish`) → 1.10 (`game_checks`, rules-version packages) → 1.11 (batch runner, second scripted policy, CI simulation smoke step).
- 1.12 extends `GameSettings`, `advance`, the conservation check and warnings without changing earlier golden traces.
- Later epics build on these: Epic 2 adds `players.ensure_order`, a separate `games.commands.advance` called after each command's commit, the AI gateway, workers and `llm` occupants; Epic 5 reuses `GameSettings`, validation, `RANGES` and the demand series for the Class session screen; Epic 6 renders `SeatState` and reuses `place_order`.
