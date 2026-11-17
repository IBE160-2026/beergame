# Epic 1 Context: Game engine proven in simulation

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Lay the foundation the whole product builds on: a scaffolded repo that starts locally with zero keys, a pure game engine whose arithmetic is proven against hand-checked reference traces, and the stored-Game command path (Seats, occupancy, turns, Decision log) that real Class games will later use. When done, the founder can run complete all-AI Games headless with `python -m app.sim` (Rule-based and scripted occupants), read a correct Decision log, and see a finished-game check pass for every Game. There is no login and no screen; the user is the founder at a terminal. This is also the prototype runner: it is production code, not throwaway.

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

- **Classic defaults:** 4 Roles (Retailer, Wholesaler, Distributor, Factory); starting inventory 12 per Seat; 4 units in every supply-line slot; order, shipping and Factory production delay 2; demand 4 stepping to 8 in Week 5; holding 0.50 and backorder 1.00 per unit per Week; 36 Weeks; Guided Weeks 1 to 4; maximum Order 999 (placeholder, must not bind in normal play).
- **Week sequence (normative):** on opening, receive incoming delivery → amount to ship = incoming order + backlog → ship min(inventory, amount to ship[, capacity]), rest is backlog → show → all Seats order → charge costs on end-of-Week balances → advance slots. The last Week runs in full; units left in slots carry no cost.
- **Slot layout at 2/2/2:** Retailer's incoming order is customer demand with no delay; other Seats have 2 order slots; every Seat has 2 goods slots (production for Factory). Start: 48 in inventory + 24 shipping + 8 production = 80 units. Order in Week t reaches upstream in t+2; shipment arrives in t+2; Factory Order reaches Factory inventory after 4 Weeks.
- **Bookkeeping invariants:** units on hand and in transit = starting units + units entered production − units delivered to customers; Seat cost = rates × end-of-Week balances; totals = sums of Week costs; inventory and backlog never both positive except on a capped Seat.
- **Reference trace:** constant demand 4 and all Orders 4 → every Seat holds 12, no backlog, cost 6.00 per Week. The step-to-8 golden trace must not be produced by the engine under test: its first 10 Weeks are hand-worked in a committed table the founder checks.
- **Settings validation:** delays 1 to 3 Weeks; other ranges in one table with placeholder bounds marked; Guided Weeks must end before the first demand change and leave Weeks to play. Non-blocking warnings with stable codes and numbers (supply line ≠ starting demand, backorder ≤ holding, binding max Order, too few Weeks for a change to pass the chain — ~Week 21 at 2/2/2, ~Week 29 at 3/3/3).
- **Demand patterns:** fixed series, step, random (discrete uniform over mean ± spread, never below 0), step plus noise. Same pattern + seed → same series on every platform; seed is showable, storable, re-enterable.
- **Rule-based player:** Sterman-style anchoring-and-adjustment using only the Seat's own numbers (never neighbour numbers). Parameters are a named, versioned config set; the only set shipped is `placeholder-unverified` (primary-source values pending, issues #8/#17); never use calculator-site values. Guided Weeks order the starting demand without consulting the rule.
- **Capacity (cut list):** off by default; behind `FEATURE_CAPACITY`; must leave every existing golden trace unchanged. Capacity 6 with demand 8 grows backlog by 2 a Week.
- **Correctness:** full branch coverage aimed for in engine; golden traces in CI; property-based tests with fixed seeds; every finished Game re-verified (NFR-9).

## Technical Decisions

- **Stack (pinned):** Python 3.14 with uv 0.13.7, FastAPI 0.162.5, Uvicorn 0.54.0, Pydantic 2.14.3 / pydantic-settings 2.16.2, SQLAlchemy 2.1.8 async on psycopg 3.3.9, Alembic 1.20.1, structlog 26.1.0, pytest 9.2.0; Node 24, Next.js 16.4.6 (App Router, standalone), React 19.3.1, TypeScript 6.0.3, Tailwind 4.3.5, shadcn CLI 4.23.0; Postgres 17; Caddy 2.11.9. Commit `uv.lock` and `package-lock.json`; `package.json` overrides openapi-typescript's TypeScript to 6.0.3.
- **Layers:** `engine/` and `analysis/` are pure (stdlib + pydantic only; no I/O, no clock, randomness only from a passed seed/entropy). `modules/<slice>/` uses `routes, service, repo, models, schemas, jobs`; other modules import only `service.py`. `platform/` holds db, config, events. `engine` imports nothing from `modules`.
- **Engine API:** `GameSettings` (one Pydantic model, `schema_version`, Decimal rates as JSON strings), `initial_state`, `advance(settings, state, orders) -> new state` (never mutates input), `settings.validate`/`warnings`/`RANGES`, `demand.series`/`new_seed(entropy)`, `check.conservation` (returns violations, never raises), `rule_based.order(settings, seat_view, params)`, `guided_order`, `scripted.REGISTRY` (closed, pure policies on `SeatView`), `SeatView` numbers-only model.
- **Rules versions:** each version is a package `engine/rules/v<N>/`; `advance` selects by `rules_version`; output-changing edits make a new version, never edit one a stored non-simulation Game references. Record in `engine/RULES_VERSIONS.md`; CI runs golden traces per version.
- **One write path:** only `games.commands` mutates Games, Seats, occupancy, turns and Week states. Each command = one transaction: `SELECT … FOR UPDATE` on the Game row, `version` increment, `platform/events.emit` → `NOTIFY` with `{topic, id, version}` only (`game:<id>`; simulation Games emit no `session:<id>`). A registry test asserts every command's topic set. `games.rules.week_complete` is the one advance predicate; exactly one Week advances per completing transaction; state stored before readable.
- **Snapshot at creation** (simulation Games): `GameSettings` JSONB, materialised demand + seed, engine `rules_version`, `SessionRuntime` (AI mode, Rule-based parameter set id; later epics add fields). A Game reads only its snapshot.
- **Occupancy** is append-only `(seat_id, from_week, occupant_kind ∈ {student, llm, rule_based, scripted}, policy_id, reason)`. `scripted` only for `purpose=simulation`. `create` fills no Seat; `start` fills free Seats with `rule_based`.
- **`games.policy(purpose)`** is the one behaviour table (`simulation`: no Takeover, Pause, playout or overview; Guided Weeks per settings). No command branches on purpose.
- **Seat state:** `games.schemas.SeatState` (versioned, extends `engine.SeatView`) is the single information boundary: numbers only, no names, no Week count, no future demand, no other Seat's state. Only the Retailer sees customer demand, for opened Weeks only.
- **Turns and Decision log:** `seat_turns` (one row per Seat per open Week, `opened_at`, reference Order computed once at Week open and never recomputed). `seat_weeks` written once by `place_order`, never updated: `state_seen`, Order, `decided_by ∈ {student, llm, rule_based, scripted, guided}`, `fallback = none`, occupancy kind/reason, `opened_at`, `ordered_at`, copied reference Order; unique `(game_id, week, seat_id)`. Errors: `422 order_invalid`, `409 week_not_open`, `409 order_exists`, stable conflict codes for double start/finished Game.
- **Finished-game check:** `games.service.verify_finished(game_id)` is idempotent, id-only; replays engine at stored `rules_version` and runs conservation; writes one immutable `game_checks` row; logs violations at error level with ids only; never changes the Game.
- **Simulation runner:** `app/sim.py` subcommands (`trace`, `settings check`, `demand`, `create`, `show`, `log`, `check --all`, `run [--export]`). Batches run only through `games.commands` with `purpose=simulation`; summaries read from the Decision log, `game_weeks` and `game_checks`, never runner memory; identical runs for same batch + seed.
- **Conventions:** UUIDv7 ids as strings; `timestamptz` UTC; Weeks integers from 1; units integers; money `NUMERIC(14,4)`/Decimal; tables plural snake_case, one owning module per table; Alembic owns every schema change (expand-then-contract), each story adds its own revision; structlog JSON with `request_id` and no names, emails or free text; errors as `{"error": {"code", "message", "fields"}}`.
- **Config:** one pydantic-settings class with `APP_ENV` and the seven `FEATURE_*` cut-list flags (default `true` locally); async engine with `max_overflow=0`; in production, missing/default `DATABASE_URL` refuses startup naming the variable (later epics extend the guard).
- **Local and CI:** `docker compose up` starts `postgres:17`, `backend`, `frontend`, `proxy` (port 8080); Caddy sends `/api/*` to api with `flush_interval -1`, 404s `/print/*`, everything else to web; `/api/health` is 200 only after reaching the DB. CI: api job (`uv sync --locked`, ruff, pytest on Postgres 17, golden traces, coverage); web job (`npm ci`, typecheck, build). Story 1.11 adds the simulation smoke step. Workers, job platform and `railway/` come in later epics.

## Cross-Story Dependencies

- 1.1 scaffold precedes all. 1.2 → 1.3 → 1.4 → 1.5 build the pure engine in order; 1.6 introduces `engine.SeatView` used by 1.7–1.11.
- 1.7 (`games`, `seats`, `seat_occupancy`, `games.policy`, `platform/events`) → 1.8 (`game_weeks`, `seat_turns`, `SeatState`, `start`) → 1.9 (`seat_weeks`, `place_order`, advance, `finish`) → 1.10 (`game_checks`, rules-version packages) → 1.11 (batch runner, second scripted policy, CI smoke).
- 1.12 extends `GameSettings`, `advance`, `check.conservation` and `warnings`; must not change prior golden traces.
- Later epics depend on this: Epic 2 adds `players.ensure_order`, `games.commands.advance`, the AI gateway, workers and `llm` occupants on top of these commands and tables; Epic 5 reuses `GameSettings`, validation and the demand series for the Class session screen (ranges confirmed there); Epic 6 renders `SeatState` and reuses `place_order`.
