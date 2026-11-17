---
title: 'Story 1.7: Create a simulation Game with an AI player in every Seat'
type: 'feature'
created: '2026-11-17'
status: 'done'
baseline_revision: 'c5f29ded37429386dff5dcfb3a4e2286c053b60d'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Games exist only in memory (`sim trace`). Real Games and simulation Games must share stored tables and one write path (AD-2), so the first stored Game, its Seats and their occupants are needed, with the settings frozen at creation (AD-4).

**Approach:** Add `modules/games` with three tables (`games`, `seats`, `seat_occupancy`, Alembic revision `0002`), the commands `create` and `assign_seat`, the behaviour table `games.policy(purpose)`, `platform/events` (`emit` + registry), the closed scripted-policy registry `engine.scripted.REGISTRY` with one constant-Order policy, `engine.RULES_VERSION`, and `python -m app.sim create`.

## Boundaries & Constraints

**Always:**
- Only `app/modules/games/commands.py` writes the three tables. Each command is one transaction: `SELECT … FOR UPDATE` on the Game row, `version = version + 1`, `platform.events.emit` (→ `pg_notify`) with payload `{"topic", "id", "version"}` only, then commit. A failing command stores nothing, bumps nothing and notifies nothing.
- `create` inserts the Game with `version = 0`, then runs the same lock-and-bump helper, so a created Game has `version = 1`.
- Snapshot on the `games` row: `settings` JSONB = effective `GameSettings.model_dump(mode="json")` (has `schema_version`), `demand_series` JSONB (list of ints), `demand_seed` bigint, `rules_version` int (`engine.RULES_VERSION` = 1), `session_runtime` JSONB = `SessionRuntime` (`schema_version` 1, `ai_mode` ∈ {`llm`, `rule_based`}, written `rule_based`; `rule_based_params` id and `rule_based_params_version`).
- Effective settings: `demand_pattern` arg (if given) replaces `settings.demand`; seed = `seed` arg, else `settings.demand_seed`, else `demand.new_seed(secrets.token_bytes(16))`; the seed is stored in `settings.demand_seed` and the column for every pattern kind. Rebuild through `GameSettings.model_validate`, never `model_copy`.
- `create` validates with `engine.validate` before any write; the Rule-based parameter set id (default `engine.rule_based.DEFAULT_SET_ID` = `placeholder-unverified`, also used by `sim trace`) must read and parse.
- `create` fills no Seat. `assign_seat` appends `(seat_id, from_week=1, occupant_kind, policy_id, reason='initial')`; `seat_occupancy` rows are never updated or deleted (a DB trigger raises on UPDATE/DELETE).
- `games.policy(purpose)` is the only place that knows purposes; commands ask it (`scripted_occupants`, and whether `session:<id>` would be due via `lecturer_overview`) and never compare `purpose` themselves. Its table holds only `simulation` now; other purposes raise `purpose_not_supported` until their stories add them.
- Errors are `CommandError(code, message, status, fields)` with stable snake codes (AD-19 envelope-ready).
- Ids are `uuid.uuid7()`, stored as `uuid`, returned as `str`. Timestamps `timestamptz` default `now()`.
- `app/engine` keeps 100 % branch coverage and purity; ruff clean; all existing tests pass.

**Never:**
- No `start`, `game_weeks`, `seat_turns`, `SeatState`, Order placing, `game_summaries`, Pause columns, HTTP routes or SSE listener (later stories).
- No `llm` or `student` occupants (Epics 2, 5); no new third-party dependency.
- No ORM classes: SQLAlchemy Core tables only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create | `create("simulation", GameSettings(), seed=123)` | 1 Game (`not_started`, version 1, UUIDv7), 4 Seats in Role order, 0 occupancy rows, series of 36 = `engine.demand_series`, one `game` notify with version 1 | — |
| No seed | seed arg and `settings.demand_seed` None | fresh seed drawn, stored, same in settings JSON and column | — |
| Invalid settings | e.g. `guided_weeks=5` with step at Week 5, or `weeks=0`-range errors | nothing stored, no notify | `CommandError("invalid_settings", 422)`, `fields` = {engine field: engine code}, `.errors` = engine `SettingsError`s |
| Bad parameter set | unknown id / file that fails `parse_params` | nothing stored | `unknown_parameter_set` / `invalid_parameter_set` (422) |
| Unknown purpose | `"class"` | nothing stored | `purpose_not_supported` (422) |
| Assign | free Seat, `rule_based`, no policy id | row appended, version +1, one notify | — |
| Assign scripted | `scripted`, `constant-4` | row with `policy_id='constant-4'` | — |
| Occupied | second `assign_seat` same Seat | nothing changes | `seat_occupied` (409) |
| Kind not allowed | `llm`, `student`, other text; or `scripted` where policy says no | nothing changes | `occupant_kind_not_allowed` (422) |
| Policy id | scripted without id / id not in REGISTRY / rule_based with an id | nothing changes | `policy_id_required` / `unknown_policy` / `policy_id_not_allowed` (422) |
| Role / Game | Role not in the Game / unknown Game id | nothing changes | `unknown_role` (422) / `game_not_found` (404) |
| Started | `lifecycle ≠ not_started` | nothing changes | `game_already_started` (409) |
| Race | two `assign_seat` on one Seat at once | exactly one row | other gets `seat_occupied` |

</intent-contract>

## Code Map

- `backend/app/platform/db.py` -- `get_engine`, `get_sessionmaker` (async, psycopg), `dispose`; add the shared `metadata = MetaData()`.
- `backend/migrations/env.py` -- `target_metadata = None` (L20); set to `app.platform.db.metadata` after importing `app.modules.games.models`; Windows Selector loop (L46-49) reused by the sim.
- `backend/migrations/versions/0001_baseline.py` -- revision style; new `0002_games_seats_occupancy.py`.
- `backend/tests/conftest.py` -- `test_database` fixture, `libpq_dsn`, autouse `_fresh_settings` disposes the engine per test (so the sim must dispose inside its own `asyncio.run`).
- `backend/tests/test_migrations.py` -- asserts tables == {`alembic_version`} and version `0001`; update to the new tables / `0002`. `reset_schema` drops `public`, so DB tests must upgrade per test, not once per session.
- `backend/app/engine/settings.py` -- `GameSettings`, `validate`, `demand_series`, `SettingsError`, `ROLES`.
- `backend/app/engine/demand.py` -- `new_seed(entropy)` (L176), `SEED_MAX` 999 999 999.
- `backend/app/engine/view.py` -- `SeatView` (the only input of scripted policies).
- `backend/app/engine/rule_based.py` -- `parse_params(text, set_id)`; add `DEFAULT_SET_ID`.
- `backend/app/platform/parameter_sets.py` -- `read_parameter_set`, `UnknownParameterSetError`.
- `backend/app/sim.py` -- argparse subcommands with `handler`/`command_parser`; `DEFAULT_RULE_BASED_PARAMS` (L58) to be replaced by the engine constant.
- `backend/app/platform/logging.py` -- allowlisted fields include `game_id`, `seat_id`.
- `backend/tests/engine/test_purity.py` -- scans `app/engine/*.py`.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/scripted.py` -- `ScriptedPolicy = Callable[[SeatView], int]`; `REGISTRY: Mapping[str, ScriptedPolicy]` (read-only) with `constant-4` (always 4, ignores the view) -- AD-22.
- `backend/app/engine/__init__.py`, `rule_based.py` -- `RULES_VERSION = 1`, `DEFAULT_SET_ID`; export.
- `backend/app/platform/db.py` -- shared `metadata`.
- `backend/app/platform/events/__init__.py` -- `TOPICS` (`game`, `session`, `debrief`, `user`), `CHANNEL = "events"`, `async emit(session, topic, id, version=None)`: unknown topic → `ValueError`; version only for `game` (required there); `SELECT pg_notify(:channel, :payload)` with compact JSON.
- `backend/app/platform/events/registry.py` -- `COMMAND_TOPICS = {"games.create": {"game"}, "games.assign_seat": {"game"}}` (frozen).
- `backend/app/modules/games/__init__.py`, `models.py` (Core tables + CHECKs on purpose, lifecycle, occupant_kind, reason, `from_week >= 1`; unique `(game_id, role)`, `(game_id, position)`), `schemas.py` (`Purpose`, `Lifecycle`, `OccupantKind`, `OccupancyReason`, `SessionRuntime`, `GameOverview`, `SeatOverview`), `policy.py` (`GamePolicy`: `inactivity_takeover`, `pause`, `play_deadline_playout`, `lecturer_overview` all False for simulation, `guided_weeks = "settings"`, `scripted_occupants` True; `policy(purpose)`), `repo.py` (SQL), `commands.py` (`CommandError`, `create`, `assign_seat`, `__all__`), `service.py` (`get_game(id) -> GameOverview | None` with each Seat's latest occupant; re-export `policy`).
- `backend/migrations/versions/0002_games_seats_occupancy.py` -- tables, constraints, append-only trigger; downgrade drops them.
- `backend/migrations/env.py` -- real `target_metadata`.
- `backend/app/sim.py` -- `create --settings classic --seats SPEC [--seed N] [--rule-based-params ID]`; SPEC = one occupant for all Seats or a comma list per Role (`rule_based`, `scripted:<id>`); runs `create` then `assign_seat` per Seat, reads back via `service.get_game`, prints `game <id>`, `seed <n>`, `lifecycle <x>`, one `seat <role> <kind> [policy]` line per Seat; `CommandError` → `error <code>: <message>` on stderr, exit 1; disposes the engine before returning.
- Tests: `tests/engine/test_scripted.py`; `tests/test_events.py` (emit validation, payload over a real LISTEN); `tests/games/` (`conftest` fixture: upgrade head + TRUNCATE; every matrix row; UUIDv7; snapshot round-trip; occupancy UPDATE/DELETE raise; lock: a held `FOR UPDATE` blocks `assign_seat` until released; race; registry test over `commands.__all__` and every public coroutine in `commands` with LISTEN, no `session` topic; policy table; statement capture shows `FOR UPDATE` and the version bump in one transaction); `tests/test_migrations.py` updated plus downgrade to `0001` and an `alembic check` (models = migration); `tests/test_sim.py` `create` cases.

**Acceptance Criteria:**
- Given a migrated database, when `cd backend && uv run python -m app.sim create --settings classic --seats rule_based` runs, then it prints the Game id, the seed and four `seat <role> rule_based` lines read from the database, and exits 0.
- Given the CI command run locally, when it finishes, then all tests pass, `app/engine` + `tests/engine` branch coverage is 100 %, and `ruff check` / `ruff format --check` pass.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 38 findings — high 0, medium 5, low 28, false 5, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) `sim create` leaves a half-built Game and never prints its id when an `assign_seat` fails — sim now prints `note: game <id> was stored with Seats still free` on stderr; test added.
  - `[medium]` `[patch]` (blind) `alembic check` does not compare CHECK value lists hand-copied into `0002` — added `test_the_check_constraints_list_exactly_the_enum_values` (reads `pg_get_constraintdef`, compares with the enums).
  - `[low]` `[reject]` (blind) TRUNCATE bypasses the append-only trigger — TRUNCATE is a test-only reset (Design Notes); a statement trigger would break the fixture for no product gain.
  - `[low]` `[reject]` (blind) no DB constraint for one initial occupant per Seat — the Game row lock is the AD-2 guard and the race test proves it; later reasons legitimately append rows with the same `from_week`.
  - `[low]` `[reject]` (blind) Games can never be deleted — intended by AD-5 (append-only); retention (AD-14) is a later story.
  - `[low]` `[patch]` (blind) `service.__all__` does not export the types it returns — re-exported `GameOverview`, `SeatOverview`, `SessionRuntime`, `Purpose`, `Lifecycle`, `OccupantKind`.
  - `[low]` `[reject]` (blind) `get_game` omits settings/series — no consumer yet; Story 1.8+ adds what it reads.
  - `[low]` `[patch]` (blind) `service.get_game` lets `TypeError` escape for a non-string id — both id parsers now catch `ValueError, TypeError, AttributeError`; test added.
  - `[low]` `[patch]` (blind) log lines could reach stdout; the test filter hid it — subprocess test runs `python -m app.sim create` and asserts stdout holds only report lines and logs go to stderr.
  - `[low]` `[patch]` (blind) unmigrated DB gives a traceback — sim catches `DBAPIError` as `error db_error: <type>`; test added.
  - `[low]` `[reject]` (blind) `lecturer_overview` never read by commands — no purpose with an overview exists; adding a branch now would guard a state that cannot be reached; the registry docstring names where `session` arrives.
  - `[low]` `[reject]` (blind) CLI cannot choose demand — not asked by the AC (`--settings classic --seats rule_based`); Story 1.11 brings batch files.
  - `[low]` `[patch]` (blind) seat spec does not strip spaces; `assert` vanishes under `-O` — parts are stripped; explicit `game_not_found` check replaces the assert; test added.
  - `[low]` `[reject]` (blind) fixed 0.5 s drains — a late event makes positive checks fail loudly, not pass; negative checks cover rolled-back transactions that never notify.
  - `[false]` `[reject]` (blind) spec not in the diff — withheld by design from this layer.
  - `[medium]` `[patch]` (edge) partial Game after a failed assign — same root as the first blind row; same fix.
  - `[low]` `[patch]` (edge) non-Operational `DBAPIError` uncaught — same fix as the blind row.
  - `[low]` `[patch]` (edge) `assert game is not None` under `-O` — same fix as the blind row.
  - `[low]` `[patch]` (edge) `service.get_game` `TypeError` — same fix.
  - `[low]` `[patch]` (edge) `assign_seat` with an int id raises `AttributeError` — now `game_not_found`; test added.
  - `[low]` `[reject]` (edge) `get_game` reads Game and Seats in two statements — a display read; the next read is fresh; isolation plumbing outweighs the gain.
  - `[false]` `[reject]` (edge) roles out of chain order stored at the wrong position — `GameSettings.roles` order *is* the chain (downstream first, engine `ROLES` docstring); position follows it by definition.
  - `[low]` `[reject]` (edge, claim) commands do not ask `lecturer_overview` — same as the blind row.
  - `[medium]` `[patch]` (verification-gap) CHECK lists unverified — same root as the second blind row; same test.
  - `[low]` `[patch]` (verification-gap) latest-occupant selection never exercised with two rows — added `test_the_service_reports_the_latest_occupancy_row` (raw second row).
  - `[low]` `[patch]` (verification-gap) stderr logging of `python -m app.sim` unverified — subprocess test added (same as blind row).
  - `[medium]` `[patch]` (verification-gap other) partial Game — same as the first blind row.
  - `[low]` `[patch]` (verification-gap other) `get_game` `TypeError` — same fix.
  - `[false]` `[reject]` (intent) `sim create` is surface the ACs never ask for — epics.md Story 1.7 last AC asks for `python -m app.sim create --settings classic --seats rule_based`.
  - `[low]` `[reject]` (intent) `emit(session, topic, id, version)` differs from `emit(topic, id)` — the event must ride the caller's transaction (AD-8 "inside the mutating transaction") and `game` carries the version.
  - `[false]` `[reject]` (intent) one channel instead of per-topic NOTIFY — AD-8 specifies the payload `{topic, id, version}`; the topic and id are in it.
  - `[low]` `[reject]` (intent) non-engine error codes (`invalid` on type errors, command codes) — engine codes are returned for every `validate` failure; type errors never reach the engine; the other codes cover refusals the AC requires ("stable conflict code").
  - `[low]` `[reject]` (intent) scripted refusal tested through a patched policy row — only `simulation` exists; the patched row exercises the real policy lookup.
  - `[false]` `[reject]` (intent) stored `policy_id` not consumed — the consumer is Story 1.9 (`place_order`); the AC asks only that the id is stored.
  - `[low]` `[reject]` (intent) `RULES_VERSION` only stored — Story 1.10 ties it to rules packages.
  - `[low]` `[reject]` (intent) `ai_mode` fixed to `rule_based` — only mode available before Epic 2.
  - `[low]` `[reject]` (intent) registry test drops `create`'s event for `assign_seat` — the slice is deterministic (create commits first); the transaction test separately pins one commit per command.
  - `[low]` `[reject]` (intent) revision lives in shared `migrations/versions` — Alembic has one versions directory; the docstring names the owner, as the spine expects.

## Design Notes

`version = 0` then bump keeps one lock-and-bump path for every command, so the registry/lock tests treat `create` like the rest. The trigger is the strongest form of "never updated or deleted"; TRUNCATE (tests only) is not blocked. The `constant-4` policy cannot see `max_order`; a Game with `max_order < 4` is refused at Order time (Story 1.9), not here.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-report=term-missing --cov-fail-under=100` -- expected: all pass, 100 %
- `cd backend && uv run alembic upgrade head && uv run python -m app.sim create --settings classic --seats rule_based` -- expected: id, seed, 4 Seats, exit 0

## Auto Run Result

Status: done

**Summary:** `modules/games` now stores Games: Alembic revision `0002` adds `games`, `seats` and `seat_occupancy` (CHECKs on purpose, lifecycle, occupant kind and reason; a trigger refuses UPDATE/DELETE on occupancy). `games.commands.create(purpose, settings, demand_pattern, seed)` validates with the engine, freezes the snapshot (settings JSONB with `schema_version`, materialised demand series, seed, `RULES_VERSION`, `SessionRuntime` with AI mode and Rule-based parameter set id + version) and stores one free Seat per Role at `version = 1`. `assign_seat` appends the initial occupant (`rule_based`, or `scripted` with an id from `engine.scripted.REGISTRY`, which starts with `constant-4`), answering stable codes (`seat_occupied`, `unknown_policy`, ...). Every command locks the Game row, bumps `version` and emits `game:<id>` through the new `platform/events.emit` and its registry. `games.policy(purpose)` is the behaviour table (simulation only). `python -m app.sim create --settings classic --seats rule_based` creates and fills a Game and prints id, seed and Seats from the database.

**Files:** `backend/app/engine/scripted.py` (new registry); `engine/__init__.py` (`RULES_VERSION`); `engine/rule_based.py` (`DEFAULT_SET_ID`); `platform/db.py` (shared `metadata`); `platform/events/__init__.py`, `registry.py` (new); `modules/games/{__init__,models,schemas,policy,repo,commands,service}.py` (new); `migrations/versions/0002_games_seats_occupancy.py` (new); `migrations/env.py` (metadata); `app/sim.py` (`create`); tests `tests/engine/test_scripted.py`, `tests/test_events.py`, `tests/games/*`, `tests/conftest.py` (`games_db`), `tests/test_migrations.py`, `tests/test_sim.py`.

**Review:** one pass, 38 findings (medium 5, low 28, false 5). Patched (root causes): partial Game reported by the sim (medium), CHECK lists compared with the enums (medium), service type exports, non-string ids, DBAPIError handling, seat-spec spaces and explicit None check, latest-occupant test, subprocess stdout test (low). Deferred: none. Rejected with reasons in the triage log (TRUNCATE escape for tests, no extra unique constraint, no deletion by design, `lecturer_overview` not read until a listed purpose exists, CLI demand options, fixed drains, emit signature, single channel, etc.).

**Follow-up review recommended:** true — two medium entries were patched (partial-Game reporting in the sim error path, CHECK parity test); the reworked sim error path has been verified only by its own tests, not re-reviewed.

**Verification:** `ruff check`, `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` gives 899 passed, 100 % branch coverage (Postgres from compose); `alembic upgrade head` then `python -m app.sim create --settings classic --seats rule_based` prints the Game id, seed, `lifecycle not_started` and four `seat <role> rule_based` lines, exit 0.

**Decisions taken in place of the founder:** (1) `demand_pattern`/`seed` arguments override the ones in `settings`; with no seed anywhere a seed is drawn from OS entropy, and every Game (also step demand) stores a seed; (2) `create` inserts at version 0 and bumps to 1 through the same lock-and-bump helper as every command; (3) `games.policy` holds only `simulation` (all of Takeover, Pause, playout, overview off; Guided Weeks from settings; scripted allowed); other purposes answer `purpose_not_supported` until their stories; (4) `SessionRuntime` stores `ai_mode = rule_based` plus the parameter set id and its version; (5) `RULES_VERSION = 1` lives in `app.engine` until Story 1.10's rules packages; (6) the scripted policy id is `constant-4` (orders 4); (7) rule_based occupants take no policy id (`policy_id_not_allowed`); (8) `assign_seat` refuses a started Game (`game_already_started`) and Roles without a Seat (`unknown_role`); (9) occupancy is append-only by DB trigger; current occupant = latest row by UUIDv7; (10) events go out on one Postgres channel `events` with payload `{topic, id, version}`; `emit` takes the session; (11) `sim create --seats` takes one spec for all Seats or one per Role (`rule_based`, `scripted:<id>`), logs go to stderr; (12) `game_summaries` and Pause columns are left to the stories that use them; (13) implementation ran in the orchestrating agent's own context (runbook); review layers were independent subagents.

**Residual risks:** `constant-4` cannot see `max_order` (a Game with `max_order < 4` fails at Order time, Story 1.9); `lecturer_overview` is not yet consulted for `session` events; CI not run on GitHub (no push).