---
title: 'Story 2.11: Measure a model and Effort level on batches of simulated Games'
type: 'feature'
created: '2026-11-18'
baseline_revision: 'b56940e25c53d5e41c14f13828a5102d8f6a34d9'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** `python -m app.sim run` plays all-AI batches with `llm` Seats, but stores no batch. Nothing reports what a model config and Effort level cost and how they behaved. The founder has no evidence to pick a model and Effort level for teaching (FR-78, PRD §10.1, SM-3, SM-6).

**Approach:**
- Store each `run` as a `simulation_batches` row, with its batch file, its pass lines, whether it ran on the mock, and its start time.
- Link the batch's Games through `games.batch_id`, and store the Effort level on Decision log rows.
- Add `python -m app.sim report <batch_id>`. It computes every figure from the Decision log and the `llm_call` rows of the batch's Games.
- Add a CI smoke step that plays `llm` Games on the mock through a real `worker-ai` process and prints the report.
- The real OpenRouter measurement is documented as commands. It is not run here: it needs the founder's key.

## Boundaries & Constraints

**Always:**
- Migration `0013` (expand-only) does three things:
  - Table `simulation_batches`: `id` uuid PK, `batch_file` JSONB, `pass_lines` JSONB (`{}` when none), `mock` boolean, `started_at` timestamptz default `now()`. A trigger refuses UPDATE and DELETE, so pass lines can never change once a Game of the batch exists.
  - `games.batch_id`: nullable uuid, FK to `simulation_batches`, indexed.
  - `seat_weeks.effort_level`: nullable text.
  - Both tables are owned by `modules/games` (`models.py`).
- Writes and reads:
  - `games.service.create_batch(batch_file, pass_lines, mock) -> str` is the one writer of `simulation_batches`.
  - `games.service.get_batch(batch_id)` returns `SimulationBatch` (id, batch_file, pass_lines, mock, started_at, game ids in creation order). It refuses with `ViewError` `batch_not_found` 404.
  - `games.commands.create(..., batch_id=None)` sets `games.batch_id`. An unknown id is refused with `batch_not_found` 422.
- `_place` writes `seat_weeks.effort_level = SessionRuntime.effort_level` when the occupant in force is `llm`, and NULL otherwise. `DecisionLogRow.effort_level` reads it back. The `--export` CSV columns do not change (golden files).
- Batch file:
  - Optional `pass_lines` object with keys `cost_per_game_usd`, `time_per_order_p95_s`, `switched_share`. Each key is optional, a decimal ≥ 0, with shares ≤ 1. Unknown keys are refused.
  - No pass line has a default in code.
- `run` changes:
  - It takes `--config ID`, which fills `model_config` when the file names none. It refuses a file that names a different one.
  - It takes `--worker`: the runner then does not run `ai-orders` jobs itself. It waits for a separate `worker-ai`, and refuses `game_not_finished` when no Game version changes for `WORKER_STALL_S` (120 s).
  - After the key check, `run` stores the batch row: the effective batch file as JSON (the file's JSON, with `model_config` filled in), its pass lines, and `mock` (true when the batch has `llm` Seats and `endpoint.availability` answers `mock`).
  - It then prints `batch_id <id>` before the first Game, and stores every Game with `batch_id`.
- `ai.calls.game_attempts(game_ids)` returns the `llm_call` rows of purpose `player_order` whose `caller_ref.game` is one of `game_ids`. Each row carries id, game, attempt, outcome, effort_level, started_at, latency_ms, the input, output and reasoning tokens, and cost_usd. `app/ai` imports nothing from `modules`.
- The report:
  - `app/sim_report.py` is pure: no I/O. It turns per-Game inputs into figures, then into lines. The inputs per Game are the `GameSummary`, the Decision log rows, the occupancy history and the attempts. `sim report` loads the inputs and prints the lines.
  - Definitions (one AD-15 mapping):
    - **LLM-path Orders:** Decision log rows with `occupant_kind = llm` and `decided_by ≠ guided`.
    - **AI cost and tokens:** sums over the Game's attempts.
    - **Latency per attempt:** `latency_ms` of every attempt.
    - **Time per Order:** for each LLM-path Order with call ids, the span from its first attempt's `started_at` to the end (`started_at + latency_ms`) of its last attempt. Retries and back-off are included, queue wait is not.
    - **Retries per Order:** the number of call ids − 1, over LLM-path Orders with calls (mean and max).
    - **Fallback share by type:** over LLM-path Orders.
    - **llm Seats:** Seats whose first occupancy row is `llm`. **Switched:** llm Seats with a `guard_switch` row.
    - **Share of LLM Orders:** `decided_by = llm` over the rows with `occupant_kind ≠ student` and `decided_by ≠ guided`.
    - **CV of chain Total cost** across Games: sample standard deviation / mean. It is `n/a` with fewer than 2 Games or a mean of 0.
    - **Median and p95:** nearest rank. `n/a` when empty.
  - Order of lines: the first line is the mock warning or `provider real`. Then the batch head (id, started_at, config, Effort level, Games), then the per-Game blocks, then the batch block, then cut-short, then pass lines.
  - **Pass lines:** batch mean AI cost per Game ≤ `cost_per_game_usd`, batch p95 time per Order (s) ≤ `time_per_order_p95_s`, batch switched share ≤ `switched_share`. Each line reads `pass`, `miss`, `n/a` (no value measured) or `no line`.
  - **Cut short:** the first Game of the batch with a `cost_limit` occupancy row, with that row's lowest `from_week`. Otherwise `cut_short no`.
- CI step `Simulation LLM smoke run` runs `backend/scripts/sim-llm-smoke.sh` after the existing smoke run. The script:
  - runs `config add ai-configs/mock.json` and `budget set` (Story 2.2 commands);
  - starts `python -m app.worker --queues ai-orders` in the background;
  - runs `sim run batches/measure-mock-smoke.json --config <id> --worker`, then `sim report <batch_id>`;
  - stops the worker.
- Ship `batches/measure-mock-smoke.json` (2 Games of 8 Weeks, 4 `llm` Seats, pass lines) and `batches/measure-openrouter-small.json` (2 Classic Games, 4 `llm` Seats, pass lines 0.10 / 8 / 0.25). README gives the real-measurement commands and a cost estimate per batch size.

**Never:**
- No real endpoint call in tests, CI or this run. No `.env` read.
- No `effort_measurements`, `approve` or `pin` (Story 2.12).
- No change to the gateway, the jobs, the Play guard, the prompt, the export columns or the golden files.
- The runner computes no game quantity. Report numbers are stored values or statistics over them.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mock batch | 2 Games, 4 `llm` Seats, mock | `batch_id`; report first line `MOCK PROVIDER …`; figures per Game and batch; `llm_share` 1 | — |
| Rule-based batch | no `llm` Seats | report `provider none (no llm Seats)`; LLM figures `n/a`, `llm_share n/a`; pass lines `n/a` / `no line` | — |
| Pass and miss | cost line above / below the mean cost | `pass` / `miss` | — |
| No lines | batch file without `pass_lines` | every line `no line` | — |
| Bad lines | `{"cost_per_game_usd": -1}`, unknown key, share 2 | — | exit 2 `invalid_batch` |
| Cut short | budget limit 0 | Games finish on Rule-based; `cut_short game <first id> week <w>` | — |
| Cut short later | pure figures: Game 2 has the first `cost_limit` row | names Game 2 | — |
| One Game | 1 Game | `cv n/a` | — |
| Change lines | UPDATE `simulation_batches` | — | refused by trigger |
| Unknown batch | `report <random uuid>` / `report x` | — | exit 1 `batch_not_found` |
| Config clash | file names config A, `--config B` | — | exit 2 `invalid_batch` |
| Worker stall | `--worker`, no worker running, stall 0.2 s | — | exit 1 `game_not_finished` |

</intent-contract>

## Code Map

- `backend/app/sim.py` -- `BatchFile`/`Batch`/`load_batch` (:924-1016), `_play_one` (:1019), `_wait_finished` (:542, jobs worked off in-process by `_work_off_llm_orders`), `_key_check` (:1138), `_run_batch` (:1163), `_run_command`, `build_parser` (:1212). The module docstring lists the subcommands.
- `backend/app/modules/games/models.py` -- `games`, `seat_weeks` tables; `commands.py` `create` (:193), `_place` `insert_seat_week` (:720); `repo.py` `insert_game`, `decision_log` (:225), `occupancy_history` (:254); `views.py` `decision_log` (:149); `schemas.py` `DecisionLogRow` (:238); `service.py` `__all__`; `summaries.py` `game_summary`.
- `backend/app/ai/calls.py` -- `get`, `costs` (pattern for reading `llm_call`); `app/ai/models.py` `llm_calls` columns; `app/ai/endpoint.py` `availability`.
- `backend/migrations/versions/0012_near_optimal_reference.py` -- revision style; `tests/test_migrations.py` `HEAD`, `HEAD_TABLES`, downgrade tests.
- `backend/tests/conftest.py` -- `GAMES_TABLES` truncate list (add `simulation_batches`).
- Tests: `tests/test_sim_llm.py` (`setup`, `batch`, `stored_config`), `tests/test_sim.py` `run_batch` (keeps lines whose first word is in `{game, cost, orders, batch}`, so the new line is `batch_id`), `tests/players/test_cost_limit.py` (limit `"0"` pattern), `tests/test_sim_golden.py` (must stay unchanged).
- `.github/workflows/ci.yml` -- backend job, `Simulation smoke run` step.
- `README.md` -- real endpoint section (:24-32).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0013_simulation_batches.py` -- table, trigger, two columns, downgrade.
- `backend/app/modules/games/models.py`, `schemas.py` (`SimulationBatch`, `DecisionLogRow.effort_level`), `repo.py`, `views.py`, `commands.py` (`batch_id`, `effort_level`), `service.py` (`create_batch`, `get_batch`) -- storage.
- `backend/app/ai/calls.py` -- `game_attempts`.
- `backend/app/sim_report.py` (new) -- pure figures and lines.
- `backend/app/sim.py` -- `pass_lines`, `--config`, `--worker`, batch row, `report` subcommand, docstring.
- `backend/batches/measure-mock-smoke.json`, `measure-openrouter-small.json`; `backend/scripts/sim-llm-smoke.sh`; `.github/workflows/ci.yml`; `README.md`.
- Tests:
  - `tests/test_sim_report.py` (new): pure figures for every matrix row that needs no database (pass/miss/no line/n/a, CV, quantiles, cut short later, mapping).
  - `tests/test_sim_measure.py` (new): mock batch end to end (`run` then `report`), with the Effort level on `llm_call` and `seat_weeks`, budget = evaluation, the stored batch row and `batch_id`, a limit-0 cut-short batch, a changed-line refusal, an unknown batch, a config clash, and the worker path (a concurrent `run_until_idle` standing in for `worker-ai`) plus the stall.
  - `tests/test_migrations.py`: HEAD 0013, tables, downgrade to 0012.

**Acceptance Criteria:**
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, golden outputs are unchanged, and any new test over 1 s is reported.
- Given `scripts/sim-llm-smoke.sh` run locally against a scratch database with a real `worker-ai` process, then it prints a `batch_id` and a report whose first line is the mock warning.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 31 findings — high 0, medium 2, low 25, false 4, maybe-false 0
- findings:
  - Blind hunter:
    - `[medium]` `[patch]` (blind 1) A cut-short batch could pass the cost line, because its Rule-based Games cost USD 0 and lower the mean. Fixed: when the batch is cut short, every pass line it carries reads `miss (cut short)`. Tests cover it in pure code and end to end.
    - `[low]` `[reject]` (blind 2) A batch with an unfinished Game cannot be reported (exit 1). The AC reports only "a batch [that] has finished". The money spent stays visible through `ai.cli cost`.
    - `[false]` `[reject]` (blind 3) The fixed `WORKER_STALL_S` of 120 s is not shorter than a real slow Order. The Effort level's per-Order time budget (8 s) plus the `worker-ai` rescue loop (5 s) places a timeout fallback, so the Game version moves well within 120 s.
    - `[low]` `[reject]` (blind 4) The `--export` CSV has no `effort_level` or `batch_id`. Left out on purpose: the golden export files must stay unchanged. Both values are in the database.
    - `[low]` `[patch]` (blind 5) `sim_report` imported `games.schemas` directly. It now imports through `games.service`.
    - `[low]` `[patch]` (blind 6) The `int | bool` return of `_key_check` was fragile. It now returns `(exit code | None, mock)`.
    - `[low]` `[reject]` (blind 7) There is no index on `caller_ref->>'game'`, and two columns are fetched but not read. The report is an offline command over a small table. An index can come with Epic 15's cost views.
    - `[low]` `[patch]` (blind 8) The smoke script checked only the banner. It now also checks `llm_share orders=32/32` and `cut_short no`. The worker stopped cleanly in local runs.
    - `[low]` `[patch]` (blind 9) Untested behaviours: a NULL Effort level on non-LLM rows, `--config` naming the same config, and a value exactly on its line. Tests added for all three. The unfinished-batch exit was rejected, see blind 2.
    - `[low]` `[patch]` (blind 10) README gaps. It now says the OpenRouter batch uses the Classic defaults, when the limit must be raised, and that a cut-short batch misses its lines. The issue capitalisation is fixed.
    - `[low]` `[reject]` (blind 11) `batch_not_found` is 422 in `create` and 404 in the read, and there is no way to clean up a batch. This follows the existing convention (`config_not_found` is 422 in commands). The batch is append-only by design.
    - `[low]` `[reject]` (blind 12) One mock flag per batch can be wrong. The call rows do not record whether the mock answered (`provider` stays the config's provider), so the flag set at run start is the only signal. This is recorded in Design Notes and the residual risks.
  - Edge-case hunter:
    - `[low]` `[patch]` (edge 1) An unknown config left an empty batch row behind. `_key_check` now exits 1 with `config_not_found` before the batch is stored. Test added.
    - `[low]` `[reject]` (edge 2) The mock flag with `--worker`. Same claim as blind 12.
    - `[low]` `[reject]` (edge 3) A pass line of `1e400` becomes infinity in the stored copy, and the insert fails. That is unlikely, and it fails loudly as `db_error` with exit 1.
    - `[low]` `[reject]` (edge 4) A partial batch. Same claim as blind 2.
    - `[false]` `[reject]` (edge 5) The stall time. Same refutation as blind 3.
    - `[low]` `[patch]` (edge 6) The smoke script lost the run's output when it failed. It now echoes the output before exiting.
    - `[low]` `[reject]` (edge 7) A worker that dies at startup means a 120 s wait before the run fails. This is rare, and the run still fails with a clear code.
    - `[low]` `[reject]` (edge 8) TRUNCATE bypasses the row trigger. The spec covers UPDATE and DELETE, and the test cleanup relies on TRUNCATE.
    - `[low]` `[patch]` (edge 9) The docstring claim of "every figure from Decision log and llm_call" was too narrow. The `sim_report` docstring now names each source: occupancy history, finished Week state.
  - Verification-gap reviewer:
    - `[medium]` `[patch]` (VG 1) The NULL branch of `seat_weeks.effort_level` was never observed, nor was the view read-back. The cut-short test now asserts `("rule_based", None)`, and the mock test reads `decision_log(...).effort_level`.
    - `[low]` `[patch]` (VG 2) The `player_order` purpose filter was untested. The mock test now inserts a `recognition_probe` row on a batch Game and asserts that the report leaves it out.
    - `[low]` `[reject]` (VG other) TRUNCATE. Same claim as edge 8.
  - Intent-alignment auditor (descriptive; each divergence logged):
    - `[false]` `[reject]` (a) The Effort level is only on LLM-player rows, not every row. In AD-22 and FR-78 the measured level belongs to `llm` occupants. A Rule-based row carrying it would credit Rule-based Orders to the level. This is now tested.
    - `[low]` `[reject]` (b) The batch row is locked from insert, which is stricter than the AC. No command edits pass lines, and the batch row is stored before the first Game.
    - `[low]` `[reject]` (c) Time per Order is the attempt span. This is a recorded decision: queue wait in the sequential runner would add other Seats' calls.
    - `[false]` `[reject]` (d) A new CI step instead of extending the 1.11 step. The 1.11 step is kept unchanged (golden outputs), and the new step runs right after it in the same job, which matches the AC's behaviour.
    - `[low]` `[reject]` (e) The mock flag. Same claim as blind 12.
    - `[low]` `[reject]` (f) The shipped measure files take the config from `--config`. The stored batch file always names it, and a config id exists only after `config add`.
    - `[low]` `[patch]` (g) Report sources wider than two tables. Covered by the docstring patch of edge 9: the figures come from stored games and AI rows, never computed a second way.

## Design Notes

These are decisions taken in place of the founder:
- Time per Order is the span of the Order's attempts (retries and back-off included). It is not `ordered_at − opened_at`, because the runner works off jobs one by one, so the turn wait would count other Seats' calls.
- Mock detection is stored on the batch row when the run starts. With `--worker`, the worker's environment must match: CI and local both use the mock without a key.
- The batch row cannot be changed after insert. That is stricter than "after its first Game starts", and no command edits pass lines.
- The switched-share line in the shipped OpenRouter batch is 0.25, a placeholder (issue #20). The time line is 8 s (NFR-2 placeholder), the cost line USD 0.10 (C-3).

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/test_sim_report.py tests/test_sim_measure.py tests/test_sim_llm.py tests/test_sim_golden.py tests/test_migrations.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100 --durations=10` -- expected: pass, once before commit
- `bash backend/scripts/sim-llm-smoke.sh` against a scratch database -- expected: report with mock warning

## Auto Run Result

Status: done

**Summary:** `python -m app.sim run` now stores each batch and links its Games. `python -m app.sim report <batch_id>` prints what a model config and Effort level cost and how its LLM players behaved, from the stored rows alone.
- Migration `0013`:
  - `simulation_batches` holds the batch file as played, the pass lines, a `mock` flag and `started_at`. The row is append-only (trigger).
  - `games.batch_id` (FK, indexed).
  - `seat_weeks.effort_level`: set on rows an `llm` occupant ordered, NULL otherwise.
  - Both tables are owned by `modules/games`. The writer is `games.service.create_batch`, the reader `get_batch`, and `commands.create(batch_id=...)` links a Game.
- `run` changes:
  - It reads optional `pass_lines` (`cost_per_game_usd`, `time_per_order_p95_s`, `switched_share`). None has a default in code.
  - `--config ID` fills `model_config`.
  - `--worker` waits for a separate `worker-ai` process (stall 120 s).
  - It prints `batch_id <id>` before the first Game. An unknown config stops it before anything is stored.
- `report`:
  - The first line is the mock warning, `provider real`, or `provider none`.
  - Per Game and for the batch: AI cost, tokens, latency per attempt and time per Order (nearest-rank median and p95), retries per Order, fallback share by type, guard-switched share of `llm` Seats, the Share of LLM Orders (AD-15), and chain cost.
  - For the batch only: cost per Game, the CV of chain Total cost, and cut short (first Game and Week with a `cost_limit` row).
  - Pass, miss, `n/a` or `no line` against each pass line. A cut-short batch misses every line it carries.
  - The figures logic is pure (`app/sim_report.py`). `ai.calls.game_attempts` reads the `player_order` call rows.
- CI: new step `Simulation LLM smoke run` (`backend/scripts/sim-llm-smoke.sh`). It registers the mock config and budget, runs a real `worker-ai`, plays a 2-Game, 8-Week, all-`llm` batch with `--worker`, prints the report, and checks the mock banner, `llm_share 32/32` and `cut_short no`.
- **Real measurement: not run, it needs the founder's key.** The commands are in `README.md`, under "Measuring a model and Effort level (Story 2.11)". They use the batch `batches/measure-openrouter-small.json`: 2 Classic Games, 4 LLM Seats, 256 Orders, budget cap USD 1. Expected cost is about USD 0.06–0.12, with a reserved worst case of USD 0.63. The README has a cost table for 1, 2, 5, 10 and 20 Games. This is the only open item, so the story counts as `done`.

**Files:**
- `backend/migrations/versions/0013_simulation_batches.py` (new): table, trigger, two columns.
- `backend/app/modules/games/models.py`, `schemas.py` (`SimulationBatch`, `DecisionLogRow.effort_level`), `repo.py`, `views.py`, `commands.py` (`batch_id`, `effort_level` on `_place`), `service.py`, `batches.py` (new).
- `backend/app/ai/calls.py`: `game_attempts` and `PLAYER_PURPOSE`.
- `backend/app/sim_report.py` (new): pure figures and lines.
- `backend/app/sim.py`: pass lines, `--config`, `--worker`, the batch row, the `report` subcommand, docstring.
- `backend/batches/measure-mock-smoke.json`, `measure-openrouter-small.json` (new). `backend/scripts/sim-llm-smoke.sh` (new). `.github/workflows/ci.yml`. `README.md`.
- Tests:
  - `tests/test_sim_report.py` (new, pure).
  - `tests/test_sim_measure.py` (new, database).
  - `tests/test_migrations.py`: head 0013, downgrade test.
  - `tests/conftest.py`: truncate `simulation_batches`.
  - `tests/test_imports.py`: `app.ai.calls` added to the public `app/ai` surface for report reads.

**Review:** one pass, 4 layers, 31 findings (medium 2, low 25, false 4).
- Patched:
  - medium: the cut-short batch now misses its lines; tests for the NULL Effort level and its read-back.
  - low: the facade import, the `_key_check` return, the smoke script's checks and its output on failure, tests for the purpose filter, the same config and a value on its line, an unknown config storing no batch, the README, the docstring of figure sources.
- Nothing deferred. Rejected findings and their reasons are in the triage log.

**Follow-up review recommended:** true. Two medium entries were patched (cut-short verdict, Effort-level NULL test). The unverified risk is that the cut-short verdict rule (`miss (cut short)`) is new behaviour no reviewer has seen. Patched counts: medium 2, low 9.

**Verification:**
- ruff check and format: clean.
- Full suite with coverage: 1484 passed in 61 s. Engine coverage 100 %. Golden outputs unchanged.
- `bash scripts/sim-llm-smoke.sh` ran twice against a scratch database (`olspillet_sim_smoke`, created and dropped by this run) with a real `python -m app.worker --queues ai-orders`. Exit 0, mock banner first, 32/32 LLM Orders, all three lines `pass`. The worker process ended with the script.
- Every matrix row is covered by a passing test in `test_sim_report.py` or `test_sim_measure.py`.
- New tests over 1 s:
  - `test_a_mock_batch_is_stored_measured_and_reported`: about 2.5 s with `-n0`, 5.2 s under xdist. Two 3-Week Games with 4 LLM Seats.
  - `test_at_the_cost_limit_..._cut_short`: about 1.4 s / 3.5 s.
  - `test_with_worker_the_runner_waits_for_a_worker_to_play_the_game`: about 0.8 s / 1.3 s.
  - `test_the_pass_lines_never_change_once_stored`: about 0.75 s / 1.2 s.
- Migration 0013 ran once on the shared `olspillet_test*` databases and the migrations database. It was not changed after it ran.

**Decisions taken in place of the founder:**
1. Time per Order = the span from the first attempt's start to the last attempt's end (retries and back-off in, queue wait out). Latency per attempt = `latency_ms`. Median and p95 are nearest-rank.
2. Retries per Order = call ids − 1 (mean, max). Fallback share is taken over LLM-path Orders (`occupant_kind = llm`, not guided). "llm Seats" = Seats whose first occupancy row is `llm`. CV = sample standard deviation / mean (`n/a` below 2 Games).
3. The Effort level is stored only on Decision log rows an `llm` occupant ordered.
4. Pass lines are optional per key and must be ≥ 0, shares ≤ 1. They are compared as measured ≤ line, on the batch mean cost per Game, the p95 time per Order and the switched share. A cut-short batch misses every line it carries.
5. The batch row is append-only from insert, stricter than "after the first Game starts".
6. Mock detection is a flag stored when the run starts, from `endpoint.availability`, because the call rows cannot tell a mock answer apart.
7. Pass lines in `measure-openrouter-small.json`: USD 0.10 (C-3), 8 s (NFR-2 placeholder), switched share 0.25 (placeholder, issue #20). Default batch: 2 Classic Games, 4 LLM Seats, Effort level `standard`, budget cap USD 1.
8. `--config` fills the file's config. A real `worker-ai` is driven with `--worker`, stall time 120 s. The CI smoke is a new step after the unchanged 1.11 step.
9. `app.ai.calls` is part of the public `app/ai` read surface.
10. Implementation ran in the orchestrating session, not a fresh subagent (runbook constraint). Reviews ran as four independent subagents.

**Residual risks:**
- The cost estimate uses the config's placeholder prices and assumed token counts (input from measured request size, about 2.5–3.8 kB; output 150–800 tokens).
- The mock flag reflects the runner's environment. A `--worker` process with a different environment could disagree.
- CI has not run. Nothing is pushed.
