---
title: 'Story 1.11: Run batches of all-AI Games with scripted occupants'
type: 'feature'
created: '2026-11-17'
baseline_revision: '21feebf45dba305a1206b874043b5da4409dcbcc'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The runner plays one Game at a time by hand (`create`, `start`, `play`); there is no batch command, no summary read from the stored tables, only one scripted policy, no CSV export and no CI smoke run (FR-30, FR-67, AD-22).

**Approach:** Add `python -m app.sim run <batch.json> [--export DIR]`: for each Game of the batch it calls `create`, `assign_seat`, `start`, the existing play loop and `verify_finished`, then prints a per-Game and batch summary built from a new read `games.service.game_summary`. Add scripted policy `order-incoming`, a committed smoke batch and a CI step that runs it.

## Boundaries & Constraints

**Always:**
- Batch file: UTF-8 JSON object, unknown keys refused. `seed` (int, required), `games` (int 1..100, required), `seats` (required: one Seat spec string for every Role, or an object with exactly one spec per Role of the settings; spec = `rule_based` | `scripted:<id>` with id in `REGISTRY`), `settings` (optional object of `GameSettings` overrides, default Classic), `demand` (optional `DemandPattern`, replaces the settings' pattern), `rule_based_params` (optional set id, default `placeholder-unverified`). Game *i* (0-based) uses demand seed `seed + i`; `seed + games - 1` must be 0..`SEED_MAX`. An unreadable/invalid file → `error invalid_batch: <detail>` on stderr, exit 2, no Game stored.
- Each Game goes through `games.commands.create("simulation", …)`, `assign_seat` per Role, `start`, then `place_order` for every open turn using the existing `_decide` (Guided Order in a Guided Week, stored reference Order for `rule_based`, `REGISTRY[policy_id](SeatState)` for `scripted` with `decided_by = scripted`), then `game_service.verify_finished`. No SQL in `sim.py`; no web app.
- `engine/scripted.py`: `REGISTRY` gains `order-incoming`, which returns `view.incoming_orders[-1]` (this Week's incoming order; customer demand for the Retailer). Pure, takes only a `SeatView`.
- `games.service.game_summary(game_id) -> GameSummary` (new `modules/games/summaries.py`, re-exported): reads in one session the Game, its finished `game_weeks` row, the Decision log grouped by `decided_by`, and `game_checks`. Fields: `game_id`, `demand_seed`, `weeks` (the finished state's Week), `total_cost` (tuple of `(role, Decimal)` in chain order, each Seat's `total_cost` of the finished state), `chain_cost` (their sum), `orders` (tuple of `(decided_by, count)` in `DecidedBy` order, zero counts left out), `check` (`GameCheck | None`). Refuses `game_not_found` 404, `game_not_finished` 409 (`ViewError`).
- Summary output (stdout), one block per Game in batch order, then the batch block:
  `game <id> seed <s> weeks <n> check ok` | `check failed <count>` | `check missing`
  `cost retailer=<x> wholesaler=<x> distributor=<x> factory=<x> chain=<x>`
  `orders guided=<n> rule_based=<n> …`
  `batch games <n> weeks <sum> checks ok=<n> failed=<n>`, then `cost …` and `orders …` lines summed over the Games' summaries. Exit 0 only when every check is ok; 1 on any failed check or refused command (its `error <code>: …` on stderr; the batch stops there).
- `--export DIR`: creates DIR if missing and writes `DIR/decision-log.csv` from `game_service.decision_log`: header `game_id,week,seat_id,role,occupant_kind,decided_by,fallback,order,rule_based_reference_order,incoming_order,incoming_delivery,shipped,inventory,backlog,supply_line,position,week_cost,total_cost`, one row per Game, Week and Seat in batch, Week and chain order. Ids, Roles, fixed codes and numbers only; no timestamps or text.
- `backend/batches/classic-smoke.json`: 3 Classic Games, seed 7, Retailer `rule_based`, Wholesaler `scripted:order-incoming`, Distributor `scripted:constant-4`, Factory `rule_based`.
- `.github/workflows/ci.yml` backend job, after pytest: `uv run alembic upgrade head` then `uv run python -m app.sim run batches/classic-smoke.json`.
- `sim.py` docstring documents `run`. Engine + `tests/engine` keep 100 % branch coverage; ruff clean; all tests pass.

**Never:** No change to commands, engine arithmetic, migrations or golden files; no LLM occupant, jobs, HTTP route or parallelism; no new dependency; no numbers kept from the play loop for the summary.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Smoke batch | `run batches/classic-smoke.json` | 3 Games finished, 3 `game_checks` rows ok; summary values equal SQL over `game_weeks`/`seat_weeks`; `orders guided=16 rule_based=64 scripted=64` per Game | exit 0 |
| Twice | same file run twice | per Game index, every Week's Orders and costs equal | — |
| Scripted policies | `order-incoming` Seat | after the Guided Weeks every Order equals `state_seen.incoming_order`, `decided_by scripted` | — |
| Export | `--export DIR` | `DIR/decision-log.csv`, `1 + games*weeks*4` lines, header as stated | — |
| Bad file | missing file, not JSON, unknown key, `games 0`, wrong Role in `seats`, unknown policy, seed overflow | nothing stored | `error invalid_batch: …`, exit 2 |
| Bad settings | settings that break the engine rules | — | `error invalid_settings: …` on stderr, exit 1 |
| Failed check | `verify_finished` returns `ok false` (monkeypatched) | that Game shows `check failed N`; batch `failed=1` | exit 1 |
| Summary refusals | unknown id / running Game | — | `game_not_found` 404 / `game_not_finished` 409 |

</intent-contract>

## Code Map

- `backend/app/sim.py` -- `_seats_spec` (L327) parses Seat specs; `_create_game` (L362), `_play_game` (L461), `_decide` (L442), `_check_game` (L494), `_report` (L350), `_run` (L343), `build_parser` (L561). Refactor the create/play bodies into helpers that raise, so `create`/`play` keep their output and `run` reuses them; `db.dispose()` once per command.
- `backend/app/engine/scripted.py` -- closed `REGISTRY` (`MappingProxyType`); add `order-incoming`.
- `backend/app/engine/view.py` -- `SeatView.incoming_orders` (last = this Week).
- `backend/app/engine/demand.py` -- `SEED_MAX`.
- `backend/app/modules/games/views.py` -- `ViewError`, `_uuid`, `decision_log` (L134) pattern for the new read.
- `backend/app/modules/games/repo.py` -- `get_game`, `week_rows` (L212), `game_check` (L222); add `orders_by_decided_by` (GROUP BY).
- `backend/app/modules/games/checks.py` -- how a `game_checks` row becomes a `GameCheck` (reuse that converter).
- `backend/app/modules/games/schemas.py`, `service.py` -- add `GameSummary`, export `game_summary`.
- `.github/workflows/ci.yml` -- backend job; DATABASE_URL already points at the CI Postgres.
- Tests: `tests/test_sim.py` (`create`, `report`, `played_game`, `log_lines` helpers), `tests/engine/test_scripted.py` (asserts the registry holds only `constant-4`: update), `tests/games/helpers.py` (`query`), `tests/conftest.py` (`games_db`).

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/scripted.py` -- add `order-incoming`.
- `backend/app/modules/games/repo.py`, `schemas.py`, `summaries.py` (new), `service.py` -- `game_summary`.
- `backend/app/sim.py` -- `run` subcommand, batch model, summary, export; docstring.
- `backend/batches/classic-smoke.json` -- smoke batch.
- `.github/workflows/ci.yml` -- simulation smoke step.
- `backend/tests/engine/test_scripted.py` -- `order-incoming` cases (Retailer and upstream, first Week, after a change).
- `backend/tests/games/test_summary.py` (new) -- values against SQL, refusals, missing check.
- `backend/tests/test_sim.py` -- every matrix row.

**Acceptance Criteria:**
- Given the smoke batch, when `python -m app.sim run batches/classic-smoke.json` runs against the dev database, then it prints 3 Game blocks and a batch block with `checks ok=3 failed=0` and exits 0.
- Given the CI commands run locally, when they finish, then all tests pass, `app/engine` + `tests/engine` branch coverage is 100 %, and ruff check/format are clean.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 34 findings — high 0, medium 0, low 24, false 10, maybe-false 0
- findings:
  - `[low]` `[patch]` (verification-gap) batch `rule_based_params` never shown to reach the Games — added `test_run_uses_the_batch_rule_based_parameter_set` (stored runtime set id `stock-30`, Week 5 Wholesaler Order 13) and `test_run_refuses_an_unknown_rule_based_parameter_set` (exit 1, `unknown_parameter_set`).
  - `[low]` `[patch]` (verification-gap) help text says exit 2 for any invalid batch file, but engine-rule settings and unknown sets exit 1 — the `run` docstring now names both as exit 1 (refused by `create`) and exit 2 as unreadable / wrong shape; the spec fixes exit 1 for `invalid_settings`.
  - `[low]` `[reject]` (intent) no structural check that the runner writes no game table — `sim.py` has no SQL and imports only `games.commands`/`games.service`; an import lint is new machinery beyond the AC.
  - `[false]` `[reject]` (intent) `run` test does not check rule_based Orders against the stored reference — `_decide` is unchanged, and `test_log_of_a_rule_based_game_matches_the_engine_only_trace` asserts Order = reference for every rule_based row.
  - `[low]` `[reject]` (intent) batch per-Role costs and Order counts checked against constants, not SQL — per-Game lines are checked against SQL and the batch chain cost against a SQL sum; the constants equal 3 × the per-Game counts.
  - `[low]` `[reject]` (intent) the CI step itself is not run by any test — GitHub CI cannot run without a push (runbook); the same command ran locally against the dev database (exit 0).
  - `[low]` `[patch]` (intent + blind) batch totals are runner sums while the docstring said the runner computes nothing — docstring now states the batch totals are sums of numbers read back from the database (reading D2).
  - `[low]` `[reject]` (edge) `order-incoming` can exceed a low `max_order` and abort the batch — `max_order` is a placeholder that must not bind in normal play; a clamp needs `max_order`, which `SeatView` does not carry.
  - `[low]` `[patch]` (edge + blind) a mid-batch failure leaves stored Games with no ids printed — `_play_one` records each id as soon as `create` returns; the error path prints `note: games stored before the stop: …`; test `test_run_stopped_partway_names_the_games_already_stored`.
  - `[low]` `[patch]` (edge) orphaned `not_started` Game after an `assign_seat`/`start` refusal — same fix as above (id recorded right after `create`).
  - `[low]` `[reject]` (edge) truncated CSV left on a mid-write `OSError` — rare (disk full); temp-file + rename adds machinery; the run exits 1 with `export_failed`.
  - `[low]` `[patch]` (edge + blind) a failed export hides the summary — the summary now prints before the export is written; test asserts the batch line on `export_failed`.
  - `[low]` `[reject]` (edge) empty export dir left after a failed run — harmless; removing it adds branches.
  - `[low]` `[patch]` (edge + blind) engine-rule settings / unknown set exit 1 vs documented 2 — same root as the help-text row; docstring corrected (spec keeps exit 1).
  - `[low]` `[patch]` (edge) `settings.demand_seed` silently overridden by `seed` — `load_batch` refuses it with `invalid_batch` (`settings.demand_seed: use seed`); new parametrised case.
  - `[false]` `[reject]` (edge) non-command exceptions give a traceback — those are bugs; same handling as every other sim subcommand.
  - `[low]` `[patch]` (blind) CSV test checks format, not values — the export test now compares every CSV row with `seat_weeks` + `state_seen`.
  - `[low]` `[reject]` (blind) export silently replaces an existing file — the docstring now says it replaces; the user picks the directory.
  - `[low]` `[reject]` (blind) CSV has no seed or batch columns — `game_id` joins each row to the printed summary and the stored Game; the AC asks for the Decision log only.
  - `[low]` `[patch]` (blind) `as_game_check` used across modules but not in `checks.__all__` — added.
  - `[low]` `[reject]` (blind) UUID-parse-or-404 block repeated — pre-existing pattern in four modules; a shared helper is a refactor outside the story.
  - `[false]` `[reject]` (blind) `game_summary` reads without one snapshot — only finished Games are summarised; `game_weeks`/`seat_weeks` are append-only and the `game_checks` row is immutable and read once.
  - `[false]` `[reject]` (blind) `order-incoming` crashes on empty `incoming_orders` — `SeatView.incoming_orders` has `min_length=1`.
  - `[low]` `[reject]` (blind) `rule_based_params` untested — same as the first row (patched there).
  - `[low]` `[patch]` (blind) `seats` object with an extra Role key untested — new parametrised case.
  - `[low]` `[reject]` (blind) settings that change the Roles untested — `load_batch` and the summary key on `settings.roles`; no Role-changing setting is in scope of Epic 1.
  - `[low]` `[reject]` (blind) a comma list in a `seats` string is refused although `create --seats` accepts it — the object form is the per-Role spelling; tested (`seats: `).
  - `[low]` `[reject]` (blind) CI smoke run skips `--export`; coverage gate excludes `sim.py` — export is tested in pytest; the coverage gate's scope is a Story 1.1 decision.
  - `[false]` `[reject]` (blind) `orders ` with a trailing space for an empty batch — `games ≥ 1` and every Game has Orders, so the list is never empty.
  - `[false]` `[reject]` (intent) reading B2 (order the incoming delivery) — "order what came in" in the beer-game literature is the pass-through of the incoming order; B1 matches the Story 1.2 `pass-through` trace.
  - `[false]` `[reject]` (intent) reading C2/C3 for `seed` — descriptive; C1 keeps Game 0 equal to `sim create --seed`, recorded in Design Notes.
  - `[false]` `[reject]` (intent) reading E1 for the export — descriptive; fixed codes are not names or free text (decision recorded).
  - `[false]` `[reject]` (intent) scope reading A2 — descriptive; Story 2.x expects the runner's own loop.
  - `[false]` `[reject]` (intent) runner reads `policy_id` from `GameOverview` not the occupancy row — `GameOverview.seats` is the latest occupancy row (`repo.seats_with_occupant`), and the test joins `seat_occupancy.policy_id`.

## Design Notes

Seed `seed + i` keeps Game 0 equal to a single `sim create --seed <seed>` Game and makes a seeded Demand pattern differ across a batch while staying reproducible. The batch totals are sums of the stored per-Game summaries, so every printed number traces to `game_weeks`, `seat_weeks` or `game_checks`. Expected Orders per Game in the smoke batch: 4 Guided Weeks × 4 Seats = 16 `guided`, 32 × 2 = 64 `rule_based`, 64 `scripted`.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-report=term-missing --cov-fail-under=100` -- expected: all pass
- `cd backend && uv run alembic upgrade head && uv run python -m app.sim run batches/classic-smoke.json --export <scratch dir>` -- expected: `checks ok=3 failed=0`, exit 0, CSV with 433 lines

## Auto Run Result

Status: done

**Summary:** `python -m app.sim run <batch.json> [--export DIR]` plays a batch of simulation Games. Each Game goes through `games.commands` (`create`, `assign_seat`, `start`, `place_order`), then `verify_finished`. The runner then prints one block per Game and one for the batch: Total cost per Role and for the chain, Weeks played, Orders per `decided_by`, and the check result. Every per-Game number comes from the new `games.service.game_summary`, which reads the finished `game_weeks` row, the Decision log counts and `game_checks`; the batch block sums those. `--export` writes `DIR/decision-log.csv`. The scripted registry gains `order-incoming`. CI runs the committed smoke batch after the migrations.

**Files:**
- `backend/app/engine/scripted.py`: `order-incoming` policy.
- `backend/app/modules/games/summaries.py` (new): `game_summary`.
- `backend/app/modules/games/repo.py`: `orders_by_decided_by`, `finished_state`.
- `backend/app/modules/games/schemas.py`: `GameSummary`.
- `backend/app/modules/games/service.py`: re-exports.
- `backend/app/modules/games/checks.py`: `_check` made public as `as_game_check`.
- `backend/app/sim.py`: `run` subcommand, `load_batch`, `summary_lines`, CSV export; play loop moved into `_play_to_end`; docstring.
- `backend/batches/classic-smoke.json` (new): 3 Classic Games, seed 7, mixed occupants.
- `.github/workflows/ci.yml`: `alembic upgrade head`, then the smoke run.
- Tests: `tests/games/test_summary.py` (new), `tests/test_sim.py`, `tests/engine/test_scripted.py`.

**Review:** one pass, 34 findings (low 24, false 10). Patched (all low): batch `rule_based_params` tests, docstring on exit codes and batch sums, Game ids printed when a batch stops partway, summary printed before the export, `settings.demand_seed` refused in a batch file, CSV values compared with `seat_weeks`, extra-Role case, `as_game_check` in `__all__`. Rejected findings and reasons are in the triage log. Nothing deferred.

**Follow-up review recommended:** false. Patched counts: high 0, medium 0, low 10 entries.

**Verification:**
- `ruff check`, `ruff format --check`: clean.
- `pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-fail-under=100`: 1082 passed, 100 % (local compose Postgres).
- Dev database: `alembic upgrade head`, then `sim run batches/classic-smoke.json --export <scratch>`: 3 Games `check ok`, `batch games 3 weeks 108 checks ok=3 failed=0`, exit 0, CSV 433 lines.
- Matrix audit: every row is covered by a passing test in `test_sim.py`, `test_summary.py` or `test_scripted.py`.

**Decisions taken in place of the founder:**
1. Batch file is JSON: `seed`, `games` (1 to 100), `seats` (one spec for every Role, or an object per Role), optional `settings` overrides, `demand`, `rule_based_params`. Unknown keys and `settings.demand_seed` are refused.
2. Game i of a batch uses demand seed `seed + i`.
3. The second scripted policy is `order-incoming`: it orders this Week's incoming order (customer demand for the Retailer).
4. The summary is plain `key=value` lines; batch totals are sums of the stored per-Game numbers; a missing check counts as failed.
5. Exit codes: 0 all checks ok; 1 failed check or refused command (incl. engine-rule settings, unknown parameter set); 2 unreadable or wrongly shaped batch file. A batch stops at the first refusal and prints the ids already stored.
6. Export: one `decision-log.csv` per run (replaced if present), with fixed codes (`occupant_kind`, `decided_by`, `fallback`) besides ids, Roles and numbers; no timestamps.
7. Smoke batch: 3 Classic Games, Retailer and Factory Rule-based, Wholesaler `order-incoming`, Distributor `constant-4`.
8. The implementation ran in the orchestrating agent's own context (runbook); the review layers were independent subagents.

**Residual risks:**
- The CI smoke step was not run on GitHub (no push).
- Story 1.10's `sim check --all` acceptance criterion is still not implemented (outside this story).
