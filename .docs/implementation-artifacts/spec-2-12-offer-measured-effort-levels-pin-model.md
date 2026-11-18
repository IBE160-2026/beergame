---
title: 'Story 2.12: Offer only measured Effort levels and pin the model'
type: 'feature'
created: '2026-11-18'
baseline_revision: 'dc41e6528cb705c7527c0a20af60336aff9b6435'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      An approval trusts the batch's stored mock flag, so a batch whose calls a keyless
      --worker process answered with the mock could be approved as real.
    evidence: |-
      Story 2.11 stores `simulation_batches.mock` from the runner's environment at run start;
      the llm_call rows do not record that the mock answered (provider stays the config's).
      A `sim run --worker` with a key and a worker-ai without one would store mock=false while
      the mock answers. Settling it needs the gateway to record the answering provider per
      attempt (a gateway change, out of this story).
    location: >-
      backend/app/ai/config.py approve_effort; backend/app/sim.py _key_check
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Story 2.11 reports what a model config and Effort level cost, but nothing turns a report into an offer. Every Effort level is equally usable, no model config is the default, and a fresh local database has no config at all (FR-68, FR-78, FR-79, AD-6, AD-17).

**Approach:**
- `python -m app.sim approve <batch_id> --level <name>` computes the 2.11 report and hands its figures to `ai.config.approve_effort`. That function stores an `effort_measurements` row only when the batch was real (not mock) and passed all three pass lines.
- `ai.config.offered_effort_levels` returns only the levels with a counted measurement on a reachable endpoint.
- `python -m app.ai.cli pin <config_id>` makes a config the active default. It is refused when the config offers no level.
- In `local`/`test`/`ci` with no stored config, the api, the worker and `python -m app.sim` seed a pinned `mock` config.

## Boundaries & Constraints

**Always:**
- Migration `0014` (expand-only), owned by `app/ai` (`app/ai/models.py`):
  - `effort_measurements`:
    - Keys and flags: `id` uuid PK, `model_config_id` FK `ai_model_configs` NOT NULL, `effort_level` text NOT NULL, `batch_id` uuid NULL UNIQUE (no FK: `app/ai` knows no games table), `mock` bool NOT NULL.
    - Figures, all nullable: `games` int, `cost_per_game_usd` NUMERIC(18,8), `time_per_order_median_s`, `time_per_order_p95_s`, `retries_per_order_mean`, `fallback_share`, `switched_share` (all NUMERIC).
    - Also `pass_lines` JSONB NOT NULL and `approved_at` timestamptz default `now()`.
    - CHECK `ck_effort_measurements_source`: `mock = (batch_id IS NULL)`. CHECK `ck_effort_measurements_figures`: a non-mock row has every figure.
    - An append-only trigger refuses UPDATE and DELETE.
  - `ai_default_pins`: `id` uuid PK, `model_config_id` FK NOT NULL, `pinned_at` timestamptz default `now()`. The active default is the newest row.
- `ai.config` API (no import from `modules`; reads no games table):
  - `EffortFigures`: config id, Effort levels played, mock, games, cost per Game, time per Order (median, p95, in s), mean retries per Order, fallback share, switched share, and one `PassVerdict(name, line, measured, verdict)` per pass line.
  - `approve_effort(config_id, level, batch_id, figures) -> EffortMeasurement` inserts one row and changes no config row. It raises `ConfigNotFound` or `ConfigRefused(code)`. The refusals, checked in this order:
    1. `config_mismatch`: the figures name another config.
    2. `effort_level_unknown`: the level is not on the config.
    3. `mock_batch`: the batch ran on the mock.
    4. `effort_level_mismatch`: the batch played anything but exactly this level.
    5. `pass_line_missing`: any of the three lines is absent.
    6. `pass_line_missed`: a verdict is not `pass`, or measured > line. This includes `n/a` and cut short.
    7. `already_approved`: the batch already has a measurement.
  - `offered_effort_levels(config_id) -> list[OfferedLevel(name, default, measurement)]`, in config order:
    - The result is empty when the config's `adapters.availability` is `refused` in this environment.
    - A level is offered when it has a counted measurement, and the measurement shown is the newest counted one.
    - Non-mock measurements always count. Mock ones count only when `APP_ENV` is in `local`/`test`/`ci`.
    - `default` is the first offered level.
  - `pin(config_id) -> Pinned(config, offered, evidence)`:
    - It refuses `mock_config` (a `mock` provider outside `local`/`test`/`ci`) and `no_offered_level`.
    - Otherwise it marks the config referenced and inserts a pin row.
    - `evidence` is the counted measurements of the offered levels.
  - `active_default() -> ModelConfig | None` and `measurements(config_id)`.
- Zero-config `app/ai/seed.py` `ensure_zero_config() -> str | None`:
  - It does nothing in `production`.
  - Otherwise, under `pg_advisory_xact_lock` and only when `ai_model_configs` is empty, it stores in one transaction:
    - the `mock` spec (equal to `ai-configs/mock.json`);
    - a `mock` measurement of its one level (batch NULL, figures NULL);
    - an evaluation budget of USD 10 (mock money);
    - a pin.
  - It is called by the api lifespan, `app.worker.main` and `app.sim` `__main__` (not for `trace`/`settings`/`demand`).
  - A database error is logged (`zero_config_failed`) and the process goes on.
- `sim approve` prints the report lines, then `approved config <id> effort_level <l> batch <b> measurement <m>`. On refusal it prints `error <code>: …` and exits 1. Exit 1 also when the batch is unknown or unfinished, as `report` does, or when it names no config (`model_config_missing`).
- `ai.cli`:
  - `pin <config_id>` prints `pinned <id> name=…`, one `level <name> default=yes|no` line per offered level, and one `evidence …` line per measurement. It exits 1 on a refusal or an unknown config.
  - `config show` adds `active_default` and `offered_effort_levels` (each with `default` and its `measurement`) to the JSON.
- CI:
  - A new step `uv run python -m app.ai.cli prompts check` runs after the smoke runs (the AD-6 check against stored configs).
  - The smoke script also asserts that `sim approve` of its mock batch exits 1 with `mock_batch`.

**Never:**
- No real endpoint, no `.env`, no key.
- No change to the gateway, the jobs, the report figures, the export columns or the golden files.
- `games.commands.create` keeps accepting any level of a config, because simulation measures unapproved levels. Epic 5 enforces offered levels for Class sessions.
- No UPDATE of `ai_model_configs` content.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Approve real batch | non-mock batch, all lines pass | row stored, `approved …` line, level offered | — |
| Mock batch | report says MOCK | nothing stored | exit 1 `mock_batch` |
| Missing / missed / cut short line | no `switched_share` / cost > line / cut short | nothing stored | `pass_line_missing` / `pass_line_missed` |
| Wrong level | `--level turbo`, not on config / batch played `standard`, config has `turbo` | — | `effort_level_unknown` / `effort_level_mismatch` |
| Twice | same batch approved again | — | `already_approved` |
| Mock-only DB, local/test/ci | seeded `mock` config only | `mock` config offers `standard`, is the default | — |
| Mock-only DB, production | seeded rows / mock config present, `APP_ENV=production` | seed does nothing; mock config offers nothing; real config with only mock measurements offers nothing | `pin` → `mock_config` |
| Pin unmeasured | real config, no measurement | — | exit 1 `no_offered_level` |
| Default changes | Game made with config A, then B pinned | Game keeps A; its calls use A | — |
| Seed twice | configs exist / run again | nothing seeded | — |

</intent-contract>

## Code Map

- `backend/app/ai/config.py` -- `ModelConfig`, `get`, `mark_referenced` (:451), `ConfigNotFound`; lazy import of `adapters` (:224) is the pattern for availability. New API goes here.
- `backend/app/ai/models.py` -- add the two tables (MONEY type, CheckConstraint naming `ck_<table>_<what>`).
- `backend/app/ai/adapters.py` -- `availability(spec, app_env)` and `MOCK_ENVS`.
- `backend/app/ai/budget.py` -- `set_budget(BudgetScope.evaluation(id), limit=…)`.
- `backend/app/ai/cli.py` -- `_show` (:177), `build_parser`, the `_error`/`_report_db` style, the module docstring.
- `backend/app/sim.py` -- `_report_batch` (:1286), which gets refactored to share figure loading with `approve`. Also `build_parser`, `main`, `__main__`, and the docstring.
- `backend/app/sim_report.py` -- `BatchFigures`, `PassLine.verdict`, `Figures.fallbacks` (includes `Fallback.NONE`).
- `backend/app/main.py` lifespan; `backend/app/worker.py` `main`.
- `backend/migrations/versions/0013_simulation_batches.py` -- trigger style for append-only.
- Tests: `tests/conftest.py` `AI_TABLES` (add the new tables first); `tests/test_migrations.py` `HEAD`, `HEAD_TABLES`, downgrade tests; `tests/test_sim_measure.py` `batch_file`, `batch_id_of`; `tests/test_sim_llm.py` `setup`, `run`; `tests/ai/helpers.py` `stored_config`, `MOCK`; `tests/test_worker.py` `test_main_runs_a_worker…` (monkeypatch the seed); `tests/test_imports.py` `AI_PUBLIC` (add `app.ai.seed` if imported outside `app/ai`).
- `backend/scripts/sim-llm-smoke.sh`, `.github/workflows/ci.yml`, `README.md` (Story 2.11 section).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0014_effort_measurements_pins.py` -- tables, checks, trigger, downgrade.
- `backend/app/ai/models.py`, `backend/app/ai/config.py` -- tables and API.
- `backend/app/ai/seed.py` (new) -- `ensure_zero_config`. Wire it into `app/main.py`, `app/worker.py` and `app/sim.py`.
- `backend/app/sim.py` -- `approve` subcommand, shared figure loading, `EffortFigures` built from `BatchFigures`.
- `backend/app/ai/cli.py` -- `pin`, `config show`.
- `backend/scripts/sim-llm-smoke.sh`, `.github/workflows/ci.yml`, `README.md`.
- Tests:
  - `tests/ai/test_effort.py` (new, ai_db): `approve_effort` refusals and storage, the row unchanged, append-only, `offered_effort_levels` in local versus production, `pin`, `active_default`, the seed (local, twice, production, spec equals `mock.json`).
  - `tests/test_sim_approve.py` (new): `sim approve` on a mock batch (refused), and on a batch stored as real (`endpoint.availability` monkeypatched to `real`; the gateway still uses the mock). It then checks the offer, the default change keeping a Game's config, and `ai.cli pin`/`config show`.
  - `tests/test_migrations.py`.

**Acceptance Criteria:**
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage is 100 %, golden outputs are unchanged, and any new test over 1 s is reported.
- Given `scripts/sim-llm-smoke.sh` against a scratch database, then it passes, including the refused approve.
- Given the AC "with `APP_ENV=production` nothing is seeded, a mock measurement can never be approved and the mock config can never be pinned", then one test proves all three.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 31 findings — high 0, medium 4, low 14, false 4, maybe-false 0, descriptive divergences 9 (logged as reject)
- findings:
  - Blind hunter:
    - `[medium]` `[patch]` (blind 1) `active_default` could return a pin whose config offers nothing here, for example a seeded mock pin once `APP_ENV=production`. Fixed: it now returns the newest pin whose config offers a level here, else None. Test added for a seeded database switched to production.
    - `[low]` `[reject]` (blind 2) `ai_default_pins` has no append-only trigger. Only `pin` writes it, and no code updates it. Migration 0014 already ran on the shared test databases. A trigger would need a new revision for a table nobody edits.
    - `[low]` `[patch]` (blind 3) An older local database with configs gets no default, because the AC seeds only when no config is stored. README now says how to pin one.
    - `[low]` `[reject]` (blind 4) Two concurrent approvals of one batch: the second hits the unique constraint as a db_error with exit 1. It fails loudly. Two admins approving the same batch at once is unlikely.
    - `[false]` `[reject]` (blind 5) A NULL figure hits the CHECK. Not on the `sim` path: three passing lines mean a non-null p95, so Orders with calls exist. Retries, median, fallback share and switched share are then all non-null.
    - `[low]` `[patch]` (blind 6) The CHECK constraints were untested. Three parametrised insert tests added.
    - `[low]` `[patch]` (blind 7) The p95 and switched share were computed twice. `effort_figures` now takes them from the pass lines' measured values.
    - `[low]` `[patch]` (blind 8) `config.MOCK_ENVS` is a copy. An equality test against `adapters.MOCK_ENVS` was added.
    - `[low]` `[patch]` (blind 9) A malformed batch id gave `batch_not_found`. It now gives `batch_id_invalid`, with a test.
    - `[low]` `[patch]` (blind 10) The `prompt` docstring line lost a space. Fixed.
    - `[low]` `[reject]` (blind 11) No end-to-end test for an unfinished or cut-short batch through `approve`. Those exits are the shared `_batch_figures` path tested in 2.11. The mapping is now unit-tested (VG 1).
    - `[low]` `[patch]` (blind 12) The worker test did not prove the seed runs first. It now records the call order.
    - `[low]` `[reject]` (blind 13) Pinning the active default again adds a row. This is intended pin history, and the active default is unchanged.
  - Edge-case hunter:
    - `[medium]` `[patch]` (edge 1) The `active_default` stale pin. Same root cause as blind 1, patched.
    - `[low]` `[patch]` (edge 2) `pinned_at` was the transaction start. It is now `clock_timestamp()`.
    - `[low]` `[reject]` (edge 3) The concurrent-approval race. Same as blind 4.
    - `[medium]` `[defer]` (edge 4) A batch stored as not mock but answered by a keyless worker could be approved. This is the 2.11 mock-flag design. Fixing it needs the gateway to record the answering provider. Deferred.
    - `[false]` `[reject]` (edge 5) The seed might raise a non-DB error. `MOCK_SPEC` is a constant that a test parses. `pin` cannot refuse in the seed's environments.
    - `[false]` `[reject]` (edge 6) `fallback_share` None with passing lines. Same refutation as blind 5.
    - `[low]` `[reject]` (edge 7, claim) A real config is offered locally while the mock answers. This is a recorded decision: "endpoint supports" means not refused here. Locally only dev runs see it.
    - `[false]` `[reject]` (edge 8, claim) The test approves a mock-answered batch. The test stands in for a real endpoint on purpose (no key in tests). The production rule is `mock_batch`, tested through the CLI.
  - Verification-gap reviewer:
    - `[medium]` `[patch]` (VG 1) `effort_figures` was never checked. A unit test now asserts every field, including ms→s and median/p95 order.
    - `[medium]` `[patch]` (VG 2) The advisory lock was untested. A test now runs three seeds at once and finds one config and one pin.
  - Intent-alignment auditor (descriptive):
    - `[low]` `[reject]` (a) The default reaching a Class session at creation. Epic 5 owns Class session creation; the story names Epic 5. `active_default()` is its reader.
    - `[low]` `[reject]` (b) The scope test uses a simulation Game, the only scope that exists today. It shows the Game keeps its id and its calls after the default changes.
    - `[low]` `[reject]` (c) "The one source Epic 5 reads" is a docstring promise. There is no consumer yet.
    - `[low]` `[reject]` (d) "Endpoint supports" was read as environment availability. Recorded decision.
    - `[false]` `[reject]` (e) The success path runs on the mock. This was required: no real key is available to agents (Issues #56, #60).
    - `[low]` `[reject]` (f) The seed at start is proven by stubbed entry points plus function tests. The production no-seed is proven at function level, which is where the guard lives.
    - `[low]` `[reject]` (g) The CI prompt check runs against CI's database. That database holds the seeded config and the smoke configs, which is the CI surface the AC names.
    - `[low]` `[reject]` (h) More figures are stored than the AC lists. They are additive. The time line is p95, as in 2.11.
    - `[false]` `[reject]` (i) `pin` changes the config row (`referenced_at`). The AC's "not changed" is about the approval. Freezing on pin is AD-6's `mark_referenced` contract.

## Design Notes

Decisions taken in place of the founder:
- "The endpoint supports the level" means that the config's endpoint is reachable in this environment (`availability` ≠ `refused`) and that the level is on the config. A measurement is tied to its config, which is tied to its endpoint.
- Mock measurements come only from the zero-config seed. They count in `local`/`test`/`ci` and never in `production`. A mock-only database therefore offers nothing in production, and locally it offers only the seeded `mock` config's level.
- A refused approval stores nothing: every `effort_measurements` row is an approved measurement.
- The default level is the first offered level in the config's order (the gateway already uses the first level by default).
- Pinning marks the config referenced, so a default handed to Class sessions can never change. A pin history is kept (append-only rows).
- The seeded evaluation budget is USD 10 of mock money, with the reserve from settings.
- The approval stores the figures from the report. Retries are part of the time per Order (2.11 definition), and the mean retries per Order is stored as well. The fallback share is LLM-path Orders with any fallback over all LLM-path Orders.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/ai/test_effort.py tests/test_sim_approve.py tests/test_migrations.py tests/test_worker.py tests/ai/test_cli.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100 --durations=10` -- expected: pass, once before commit
- `bash backend/scripts/sim-llm-smoke.sh` against a scratch database -- expected: exit 0

## Auto Run Result

Status: done

**Summary:**
- `python -m app.sim approve <batch_id> --level <name>` computes the Story 2.11 report and passes its figures to `ai.config.approve_effort`. The function stores an `effort_measurements` row only for a non-mock batch of exactly that level that passed its cost, time and switched-share lines. A batch is approved only once, and the config row never changes.
- `ai.config.offered_effort_levels` returns only levels with a counted measurement, on a config whose calls are not refused here. The first offered level is the default.
- `python -m app.ai.cli pin <id>`:
  - It refuses `no_offered_level`, and `mock_config` outside local/test/ci.
  - It marks the config referenced and appends an `ai_default_pins` row.
  - It prints the evidence.
- `config show` prints `active_default` and `offered_effort_levels`. `active_default()` returns the newest pin that offers a level here.
- Zero config: in local/test/ci, when no config is stored, the api lifespan, `app.worker` and `python -m app.sim` (database commands only) seed a pinned `mock` config, using an advisory lock. The seed has a mock measurement and a USD 10 evaluation budget.

**Mock-only database:**
- In local/test/ci, the seeded `mock` config offers `standard` and is the default.
- With `APP_ENV=production`:
  - nothing is seeded;
  - mock measurements never count, so no Effort level is offered and `active_default()` is None;
  - `approve` of a mock batch is refused (`mock_batch`);
  - the mock config cannot be pinned.

**Files:**
- `backend/migrations/versions/0014_effort_measurements_pins.py` (new): two tables, checks, the append-only trigger.
- `backend/app/ai/models.py`, `backend/app/ai/config.py`: the tables and the API.
- `backend/app/ai/seed.py` (new): the zero-config seed.
- `backend/app/main.py`, `backend/app/worker.py`: seed at start.
- `backend/app/sim.py`: `approve`, `_batch_figures`, `effort_figures`, seed at start.
- `backend/app/ai/cli.py`: `pin`, `config show`.
- `backend/scripts/sim-llm-smoke.sh`: asserts the mock-batch refusal.
- `.github/workflows/ci.yml`: `prompts check` step.
- `README.md`: Story 2.12 section.
- Tests:
  - `tests/ai/test_effort.py`, `tests/test_sim_approve.py` (new).
  - `tests/test_migrations.py`, `tests/conftest.py`, `tests/test_imports.py`, `tests/test_worker.py`.

**Review:** one pass, 4 layers, 31 findings.
- Patched:
  - medium: the stale default pin, the `effort_figures` test, the concurrent-seed test;
  - low: README recovery, CHECK tests, a single source for p95 and switched share, the MOCK_ENVS test, `batch_id_invalid`, the docstring, the worker order, `clock_timestamp` pins.
- Deferred: 1 medium (the mock flag trusted on approval, see frontmatter).
- Rejected: the rest, with reasons in the triage log.

**Follow-up review recommended:** true.
- 3 medium entries were patched (medium 3, low 9; the stale-pin entry groups blind 1 and edge 1).
- Unverified risk: the new `active_default` rule (skip pins that offer nothing here) has not been seen by a reviewer.

**Verification:**
- ruff check and format: clean.
- Full suite with coverage: 1523 passed in 65 s. Engine coverage 100 %. Golden outputs unchanged.
- CI-like run on a scratch database `olspillet_sim_smoke` (created and dropped), with `APP_ENV=ci`. The sequence was: `alembic upgrade head`, `sim run classic-smoke.json` (seeded the pinned mock), `config show`, `scripts/sim-llm-smoke.sh` (exit 0, approve refused `mock_batch`), and `prompts check` (ok).
- Every matrix row is covered by a passing test in `test_effort.py` or `test_sim_approve.py`.
- New tests over 1 s (`-n0`):
  - `test_a_real_batch_that_passed_is_approved_offered_and_pinned`, about 1.3 s;
  - `test_a_mock_batch_is_never_approved`, about 1.1 s.
- Migration 0014 ran once on the shared `olspillet_test*` databases. It was not changed after it ran.

**Decisions taken in place of the founder:**
1. "Endpoint supports" means that the config's calls are not refused in this environment and the level is on the config.
2. Mock measurements come only from the seed. They count in local/test/ci and never in production.
3. A refused approval stores nothing: every row is an approval.
4. The default Effort level is the first offered level in config order.
5. A pin marks the config referenced. Pins are kept as history, and the active default is the newest pin that offers a level here.
6. The seed's evaluation budget is USD 10 of mock money. The seed runs only when no config is stored, as the AC says.
7. The stored figures are games, cost per Game, time per Order (median and p95 in s, retries included), mean retries, fallback share and switched share. The time pass line is the p95.
8. The success path is tested on the mock, with the runner's endpoint check stubbed to `real`. No real measurement was run (no key, Issues #56 and #60).
9. CI runs `prompts check` against its own database.
10. Implementation ran in this session, not in a fresh subagent (a runbook constraint). Reviews ran as four independent subagents.

**Residual risks:**
- The deferred mock-flag trust.
- No real measurement exists yet, so no real Effort level is offered anywhere until the founder runs and approves one.
- CI has not run. Nothing is pushed.
