---
title: 'Story 1.4: Generate the demand series from a Demand pattern and a seed'
type: 'feature'
created: '2026-11-17'
status: 'done'
baseline_revision: 'faa5610d96f247e7f0cd68e34fa83a09f24f67a6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** `GameSettings.demand` is a step only, and nothing turns a pattern and a seed into the customer demand series. FR-13 needs fixed series, step, random (discrete uniform, mean Â± spread, never below 0) and step plus noise, reproducible from a seed that a person can see, store and re-enter (AD-1: randomness only from a passed seed).

**Approach:** New pure module `app/engine/demand.py`: four pattern models (a discriminated union on `kind`), `series(pattern, weeks, seed)`, `new_seed(entropy)`. `GameSettings` gains `demand_seed` and accepts any pattern; the Week sequence reads Retailer demand from the series; `validate` checks the pattern; `python -m app.sim demand` prints a series and its seed; a golden file pins stored series.

## Boundaries & Constraints

**Always:**
- Engine stays pure: no `random`, `secrets`, clock or OS entropy in `app/engine` (test_purity already enforces). The draw is a documented SHA-256 construction (Design Notes), so it is the same on every platform and Python version.
- `series` returns exactly `weeks` whole numbers â‰¥ 0; Week w's value depends only on (pattern, seed, w), so a longer Game extends a shorter one's series.
- Existing behaviour unchanged: `GameSettings()` stays Classic (`demand_seed` None), `validate`/`warnings` on it return `()`, all four existing golden traces pass unchanged.
- Validation issues use the existing `SettingsError` (stable `code`, dotted `field`, `minimum`/`maximum`/`placeholder` when a range applies). At most one error per field.
- Golden series are computed by an independent reviewer from the Design Notes algorithm with their own code, without running the engine, and compared with the stored file (no human in the loop).

**Never:**
- No DB, migration, snapshot storage or `schema_version` bump (Story 1.7 stores the series). No Replay template/ranges (FR-49, later). No new third-party dependency.
- `series` never reads a seed from anywhere but its argument; `new_seed` never gathers entropy itself.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fixed | `{"kind":"fixed","values":[4,4,9]}`, weeks 3 | `(4, 4, 9)` | â€” |
| Step | Classic step, weeks 7 | `(4,4,4,4,8,8,8)`; seed ignored | â€” |
| Random | `mean 4, spread 2`, seed 42, weeks 36 | 36 values in 2..6, identical on every call | â€” |
| Floor | `mean 1, spread 3` | values in 0..4; a draw below 0 becomes 0 | â€” |
| Step+noise | `start 4, new_level 8, change_week 5, spread 2` | Weeks 1-4 in 2..6, Weeks 5+ in 6..10; same noise draw per Week as `random` with the same seed and spread | â€” |
| No seed | random kind, `seed=None` | â€” | `series` raises `ValueError`; `validate` reports `demand_seed_required` on `demand_seed` |
| Fixed wrong length | 3 values, weeks 36 | `validate`: `fixed_series_length` on `demand.values`, min = max = 36, placeholder False | `series` raises `ValueError` |
| Negative spread | `spread -1` | `validate`: `out_of_range` on `demand.spread`, 0..20 placeholder | `series` raises `ValueError` |
| Step outside Game | step or step+noise, `change_week 40`, weeks 36 | `validate`: `demand_change_week_outside_game` on `demand.change_week`, 1..36, placeholder False | â€” |
| Seed out of range | `demand_seed -1` or 10^9 | `validate`: `out_of_range` on `demand_seed`, 0..999999999 | â€” |
| New seed | `new_seed(b"16 bytes ...")` | int in 0..999999999, same bytes â†’ same seed | non-bytes â†’ `TypeError`; < 8 bytes â†’ `ValueError` |
| Game with noise | settings with step+noise and seed | Retailer `incoming_order` in Week w = `series(...)[w-1]` | â€” |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py` -- `DemandStep` (L34-54: `demand_for`, `first_change_week`, `peak`) moves to `demand.py` and is re-exported here; `GameSettings.demand` (L72) becomes `DemandPattern`; `validate` (L191) gets demand checks after the RANGES loop, before cross-field rules; `warnings` uses `demand.start` (L267) and `demand.peak` (L295) -- every pattern must offer `starting_level`, `peak`, `first_change_week`. RANGES docstring L128-129 says "Demand ranges come with Story 1.4": update.
- `backend/app/engine/week.py` L133 -- `settings.demand.demand_for(week)`: replace with the series lookup.
- `backend/app/engine/__init__.py` -- docstring says "(none is needed yet)": update; re-export new names.
- `backend/app/sim.py` -- argparse subcommands, `main(argv) -> int`, `parser.error` for exit 2; add `demand`. CLI may use `secrets` (shell, not engine).
- `backend/tests/engine/test_purity.py` -- forbids `random`, `secrets`, `time`, `os` in engine; `hashlib` is allowed.
- `backend/tests/engine/test_settings.py` -- dump test (add `demand_seed: None`), `test_step_demand` uses `demand_for`, invalid-demand cases L72-74.
- `backend/tests/engine/test_validation.py` -- style for validation tests; `FLAT` step helper.
- `backend/tests/test_sim.py` -- `main([...])` + capsys style.
- CI gates 100% branch coverage of `app/engine` and `tests/engine`; no hypothesis installed, so "property" tests are seed sweeps.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/demand.py` -- `DemandFixed`, `DemandStep`, `DemandRandom`, `DemandStepNoise` (frozen, extra forbid), `DemandPattern` (Annotated union, discriminator `kind`), each with `level_for(week)`, `spread` (0 for fixed/step), `starting_level`, `peak`, `first_change_week`; `SEED_MAX`; `series(pattern, weeks, seed=None) -> tuple[int, ...]` (`functools.cache`d); `new_seed(entropy: bytes) -> int` -- FR-13, AD-1.
- `backend/app/engine/settings.py` -- `demand: DemandPattern`, `demand_seed: int | None = None` (strict int); `DEMAND_RANGES`; demand checks in `validate`; warnings via the pattern properties; `demand_series(settings)` convenience.
- `backend/app/engine/week.py` -- Retailer demand from `demand_series(settings)[week - 1]`.
- `backend/app/engine/__init__.py` -- re-export pattern models, `DemandPattern`, `DEMAND_RANGES`, `demand_series`; module `app.engine.demand` holds `series` and `new_seed`.
- `backend/app/sim.py` -- `demand` subcommand (Design Notes).
- `backend/tests/engine/test_demand.py` -- every I/O row; seed sweeps (seeds 0..199): bounds, every value of the range appears, mean within tolerance, prefix property, seed sensitivity; purity of inputs (no seed read elsewhere).
- `backend/tests/engine/golden/demand-series.json` + test -- stored series for random and step+noise (seeds 0, 42, 999999999), floor case, written by the independent reviewer's own implementation; record agreement in this spec.
- `backend/tests/engine/test_validation.py`, `test_settings.py`, `test_week.py`, `backend/tests/test_sim.py` -- demand validation rows, dump/rename updates, engine game with noisy demand, CLI.

**Acceptance Criteria:**
- Given `uv run python -m app.sim demand --pattern step+noise --seed 42`, when it runs twice, then both print `seed 42` and the same 36-value series, exit 0; without `--seed` it prints a newly drawn seed that, passed back with `--seed`, reproduces the series.
- Given the CI command, when run locally, then all tests pass, branch coverage of `app/engine` and `tests/engine` is 100%, ruff passes.
- Given `demand-series.json`, when the independent reviewer recomputes it from the Design Notes alone, then all values agree.

## Spec Change Log

- 2026-11-17 Independent golden series (no human in the loop): a separate reviewer wrote its own code from the Design Notes rule alone, without seeing `backend/`, and produced `backend/tests/engine/golden/demand-series.json` (random mean 4 spread 2 at seeds 0, 42, 999999999; step+noise 4â†’8 Week 5 spread 2 at seed 42; random mean 1 spread 3 at seed 7, which hits the floor; `new_seed(b"0123456789abcdef") = 636950687`). The engine reproduces every value: 0 mismatches.

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 30 findings — high 0, medium 2, low 25, false 3, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) `demand --weeks 0` or negative crashes with a traceback — `_demand` now rejects `--weeks` outside `RANGES["weeks"]` (1..100) with exit 2; test `test_demand_weeks_outside_the_game_range_exit_2` (0, -1, 101).
  - `[low]` `[patch]` (blind) `_open_week` rebuilds the series every Week for fixed/step — `series` now goes through one bounded cache for every kind (`_materialise`, `lru_cache(256)`).
  - `[low]` `[patch]` (blind) unbounded `@cache` grows with every seed — replaced by `lru_cache(maxsize=256)` (same edit).
  - `[low]` `[reject]` (blind) `initial_state`/`advance` raise a plain `ValueError` on unvalidated settings — the engine trusts validated settings, as triaged in Stories 1.2/1.3; failing loudly is the intended behaviour and `series` documents it.
  - `[low]` `[reject]` (blind) guided-weeks error still reported next to `demand_change_week_outside_game` — two fields, each with a real problem; same rule as the Story 1.3 row on inventory plus backlog.
  - `[low]` `[patch]` (blind) fixed-series item errors in `settings check` lose their range — the item index is dropped so the field is `demand.values` with `[allowed 0..100 (placeholder)]`; test added.
  - `[low]` `[reject]` (blind) `demand` prints a seed for step/fixed — the AC asks it to print the series and its seed; the seed is harmless and keeps output uniform.
  - `[low]` `[reject]` (blind) golden lacks a step+noise floor case and a spread-0 case — the floor is pinned by the mean 1 / spread 3 case; step+noise shares the noise draw (tested Week by Week); spread 0 is tested in `test_spread_zero_is_the_level`.
  - `[low]` `[reject]` (blind) `level_for` gives odd answers for Weeks outside 1..len — only `series` calls it, with Weeks 1..weeks; a guard adds branches for an unreachable case.
  - `[low]` `[reject]` (blind) `peak` with negative spread is below the level — a negative spread is a `validate` error; warnings on invalid settings are secondary.
  - `[low]` `[reject]` (blind) `series`/`new_seed` not re-exported from `app.engine` — the AC names `engine.demand.series` and `engine.demand.new_seed`; the package docstring points there.
  - `[low]` `[patch]` (verification-gap other) fixed item errors show no range — same as the blind row; patched.
  - `[medium]` `[patch]` (verification-gap other) CLI crash on `--weeks` below 1 — same as the blind row; patched.
  - `[low]` `[patch]` (edge) CLI `--weeks 0`/negative uncaught — same root cause as the blind row; patched.
  - `[low]` `[patch]` (edge) `--weeks` above the RANGES maximum accepted — same check now bounds it (101 → exit 2).
  - `[low]` `[reject]` (edge) `--values`/`--mean` silently ignored for another pattern — defaults are documented in `--help`; guards add branches for a slip a user sees in the output.
  - `[low]` `[patch]` (edge) extra top-level key named like a demand field gets a demand range — demand ranges now apply only to fields under `demand`/`demand_seed`; test asserts no range on `start`.
  - `[low]` `[patch]` (edge) fixed item loc `demand.values.i` — patched with the blind row.
  - `[low]` `[reject]` (edge) bare `ValueError` from engine on unvalidated settings — same as the blind row.
  - `[low]` `[patch]` (edge) O(weeks²) per Game for unseeded kinds — patched with the cache row.
  - `[low]` `[patch]` (edge) unbounded cache — patched.
  - `[low]` `[reject]` (edge) `validate_demand` runs with an out-of-range `weeks` — the range error on `weeks` is reported first; the extra rows stay true for the given `weeks`; unlikely in practice.
  - `[low]` `[patch]` (edge) documented error order says DEMAND_RANGES order but `change_week` follows `spread` — docstring now states the actual order.
  - `[low]` `[patch]` (edge) only `_noisy` was cached — patched with the cache row.
  - `[false]` `[reject]` (edge) "no seed read elsewhere" untested — `test_purity` fails if the engine imports `random`, `secrets`, `os`, `time` or `datetime`, so the engine has no other seed source.
  - `[low]` `[reject]` (edge) task list names `test_week.py`, test lives in `test_demand.py` — the fix edits this spec.
  - `[false]` `[reject]` (intent) wide reading (series wired into `GameSettings` and the Week sequence) — the `validate` AC checks the pattern against the number of Weeks, so the pattern must live in the settings, and a settings pattern the engine cannot play would be incoherent.
  - `[low]` `[reject]` (intent) floor reading makes the distribution non-uniform at 0 — the epic context says "floored at 0"; recorded as a decision in Design Notes.
  - `[low]` `[reject]` (intent) "every platform" argued from the algorithm, not shown — SHA-256 and integer arithmetic only; an independent implementation reproduced every stored value; CI on Linux runs the same golden.
  - `[false]` `[reject]` (intent) Story 1.3 tests edited — the new rule "step Week outside the Game" (this story's AC) changes those outcomes; the edits add the new error, nothing else.

## Design Notes

**Draw (rules of the series, normative):** for Week w (1-based) with level L = `level_for(w)` and spread s > 0: `d = SHA-256(f"{seed}:{w}".encode("ascii"))`, `r = int.from_bytes(d, "big") % (2*s + 1)`, value = `max(0, L - s + r)`. With s = 0, value = L (no seed needed for fixed and step). Bias of `% n` on a 256-bit integer is below 2^-240: no rejection loop.

**Floor:** "never below 0" is read as a floor on the drawn value (epic context: "floored at 0"), so mass below 0 lands on 0. Truncating the range instead was rejected: the epic context says floored.

**Seed:** a whole number 0..999 999 999 (`SEED_MAX`), short enough to read aloud and type; `new_seed(entropy)` = `int.from_bytes(SHA-256(entropy), "big") % (SEED_MAX + 1)`, needs â‰¥ 8 bytes. `demand_seed` lives in `GameSettings` because the settings define the whole arithmetic; it is required for the kinds `random` and `step+noise` (by kind, whatever the spread) and ignored for `fixed` and `step`.

**Pattern fields and ranges** (`DEMAND_RANGES`, placeholder unless noted): `start`, `new_level`, `mean`, each item of `values` 0â€“100; `spread` 0â€“20 (`int`, strict, negatives accepted by the model so `validate` can report them); `change_week` 1..weeks (not placeholder); fixed length = weeks (not placeholder); `demand_seed` 0..999 999 999 (not placeholder). Fixed `values`: at least 1 item. An item out of range gives one `out_of_range` error on `demand.values` naming the first bad Week. Error order: RANGES fields, then `demand.*` (pattern field order), then `demand_seed`, then cross-field rules.

**Properties:** `starting_level` = `values[0]` / `start` / `mean`; `peak` = max of levels + spread; `first_change_week` = first Week whose level differs from Week 1 (fixed), step rule (step, step+noise), None (random).

**CLI:** `demand --pattern {fixed,step,random,step+noise}` (default `step`), `--weeks` (36), `--start 4 --new-level 8 --change-week 5 --mean 4 --spread 2`, `--values 4,4,8` (required for fixed), `--seed N` (else drawn with `new_seed(secrets.token_bytes(16))`). Prints `seed N` then `series v1 v2 ...`; demand errors from `validate` print like `settings check` and exit 1; bad pattern input exit 2.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-report=term-missing --cov-fail-under=100` -- expected: all pass, 100% (Postgres from compose running for the non-engine tests)
- `cd backend && uv run python -m app.sim demand --pattern step+noise --seed 42` (twice) -- expected: identical output

## Auto Run Result

Status: done

**Summary:** New pure module `app/engine/demand.py`: four Demand patterns (`fixed`, `step`, `random`, `step+noise`, a discriminated union on `kind`), `series(pattern, weeks, seed)` (discrete uniform noise from SHA-256 of `"{seed}:{week}"`, floored at 0, bounded cache) and `new_seed(entropy)` (caller-supplied bytes, seed 0..999 999 999). `GameSettings.demand` accepts any pattern and gains `demand_seed`; the Week sequence reads Retailer demand from the series; `validate` reports `fixed_series_length`, `out_of_range` (levels, spread, fixed items, seed), `demand_change_week_outside_game` and `demand_seed_required` with ranges; `python -m app.sim demand` prints `seed N` and the series.

**Files:** `backend/app/engine/demand.py` (new: patterns, series, new_seed); `backend/app/engine/settings.py` (pattern union, `demand_seed`, `DEMAND_RANGES`, `validate_demand`, `demand_series`, warnings via pattern properties); `backend/app/engine/week.py` (Retailer demand from the series); `backend/app/engine/__init__.py` (exports); `backend/app/sim.py` (`demand` subcommand; demand field paths and ranges in `settings check`); `backend/tests/engine/test_demand.py` (new); `backend/tests/engine/golden/demand-series.json` (new, independent); `backend/tests/engine/{test_validation,test_settings}.py`; `backend/tests/test_sim.py`.

**Independent golden check (no human in the loop):** a separate agent computed `demand-series.json` from the Design Notes rule with its own code, without seeing `backend/`; the engine matches every value.

**Review:** 30 findings (blind 11, verification-gap 0 gaps + 2 other, edge 13, intent 4). Patched: 1 medium entry (CLI `--weeks` outside 1..100 crashed; now exit 2) and low entries (bounded cache for every kind, fixed-item and extra-key ranges in `settings check`, error-order docstring). Deferred none. Rejected 13 low and 3 false, reasons in the triage log.

**Follow-up review recommended:** false — patched high 0, medium 1 (one entry), low 4 entries.

**Verification:** `ruff check`, `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` → 662 passed, 100% branch coverage (Postgres from compose); `python -m app.sim demand --pattern step+noise --seed 42` twice → identical `seed 42` / 36-value series; without `--seed` a fresh seed is printed and reproduces its series.

**Decisions taken in place of the founder:** (1) the seed lives in `GameSettings.demand_seed`, required for `random`/`step+noise`; (2) "never below 0" = floor the drawn value (mass at 0), per the epic context "floored at 0"; (3) the draw is SHA-256-based, not Python `random`, for cross-version stability; (4) seeds are whole numbers 0..999 999 999 and `new_seed` needs ≥ 8 bytes of entropy; (5) placeholder ranges: levels and fixed items 0–100, spread 0–20; (6) a step Week after the last Week is now an error, so two Story 1.3 tests gained that error; (7) CLI defaults: Classic step 4→8 at Week 5, mean 4, spread 2, 36 Weeks; (8) implementation ran in the orchestrating agent's own context (runbook constraint), not a separate implementation subagent.

**Residual risks:** spread and level bounds are placeholders until Epic 5; changing the draw rule later needs a new rules version (Story 1.10); CI not run on GitHub (no push).
