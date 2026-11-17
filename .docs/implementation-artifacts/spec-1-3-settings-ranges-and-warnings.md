---
title: 'Story 1.3: Check changed Game settings against ranges and warnings'
type: 'feature'
created: '2026-11-17'
status: 'done'
baseline_revision: 'c3860df6b824ff1b5179858a82f71ef9f40e5612'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** `GameSettings` (Story 1.2) only guards types and signs. Nothing defines the allowed range of each setting, rejects Guided Weeks that collide with the demand change, or warns on risky but legal combinations, and a Seat cannot start with backlog. Simulations now, and the Class session screen in Epic 5, need one pure definition of what is allowed (FR-12).

**Approach:** Add `starting_backlog` to `GameSettings`; add `RANGES`, `validate(settings)` and `warnings(settings)` to `app/engine/settings.py` returning frozen issue models with stable codes; make `initial_state` honour the starting backlog; add two hand-worked golden traces (delays 1/1/1 and 3/3/3, both with starting backlog); add `python -m app.sim settings check <file>`.

## Boundaries & Constraints

**Always:**
- Engine stays pure (stdlib + pydantic, no I/O); `validate`/`warnings` never raise on any constructed `GameSettings`, and return tuples in a fixed order (RANGES order, then cross-field rules).
- `validate` returns at most one error per field path: a range/precision error on a field suppresses that field's cross-field rule error.
- Delays: 1 to 3 Weeks, not placeholder. Every other range is in `RANGES` with `placeholder=True` (to be confirmed with the Class session screen in Epic 5).
- Each issue carries `code` (stable snake_case string), `field` (dotted path, e.g. `order_delay`), a plain `message`, and: errors `minimum`/`maximum` (and `placeholder`) when a range applies; warnings `values: dict[str, str]` with the numbers behind them (decimal strings for money).
- `GameSettings()` stays Classic: `validate` and `warnings` both return `()`; the two Story 1.2 golden traces stay unchanged.
- New golden traces are worked by hand into `.md` tables first and the `.json` is written from the table, never from engine output; an independent reviewer re-works them (no human in the loop).

**Never:**
- No new demand kinds or seed (1.4), no conservation check (1.5), no capacity or capacity warning (1.12), no DB, no migration, no `schema_version` bump (nothing is stored yet).
- `GameSettings` construction does not call `validate` (callers decide); do not loosen the existing pydantic type/sign constraints.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Classic | `GameSettings()` | `validate` → `()`, `warnings` → `()` | — |
| Delay out of range | `order_delay=4` | one error `out_of_range`, field `order_delay`, min 1, max 3, placeholder False | — |
| Several bad fields | `weeks=500, max_order=0` | two errors, one per field | — |
| Too precise rate | `holding_cost=Decimal("0.505")` | error `too_many_decimal_places` on `holding_cost`, with range | — |
| Guided vs change | `guided_weeks=5` (change Week 5) | error `guided_weeks_not_before_demand_change` | — |
| No Weeks to play | `weeks=4, guided_weeks=4`, demand flat (`new_level=start`) | error `guided_weeks_leave_no_weeks_to_play` | — |
| Flat demand | `new_level == start` | no demand-change rule applies, no too-few-Weeks warning | — |
| Inventory and backlog | `starting_inventory=12, starting_backlog=4` | error `starting_inventory_and_backlog` on `starting_backlog` | — |
| Warnings | `supply_line=5`; `backorder_cost=0.50`; `max_order=50`; `weeks=20` | warnings `supply_line_differs_from_demand`, `backorder_not_above_holding`, `max_order_may_bind`, `too_few_weeks_for_demand_change`, each with its numbers; `validate` → `()` | — |
| Arrival arithmetic | Classic delays 2/2/2; 3/3/3 | `demand_change_reaches_retailer(settings)` = 21; 29 | — |
| Starting backlog | 1/1/1 and 3/3/3, inventory 0, backlog 4 | slot counts follow delays; Week 1 opens with backlog carried; goldens match | — |
| CLI ok/warn | `settings check file.json` (valid, maybe warnings) | prints warnings (or `OK`), exit 0 | — |
| CLI errors | file with range errors or pydantic-invalid values | prints each error with its allowed range, exit 1 | missing file / bad JSON → argparse error, exit 2 |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py` -- `GameSettings` (frozen, `extra="forbid"`, Classic defaults, `Units`/`Delay`/`Week`/`Rate` annotated types), `DemandStep.demand_for`. Add `starting_backlog`, `RANGES`, issue models, `validate`, `warnings`, `demand_change_reaches_retailer`. Module docstring says "Ranges and warnings are Story 1.3": update.
- `backend/app/engine/week.py` -- `initial_state` builds `_Carry(backlog=0, ...)`: use `settings.starting_backlog`. `_open_week` already ships incoming order + backlog.
- `backend/app/engine/__init__.py` -- re-export the new public names.
- `backend/app/sim.py` -- argparse subcommands, `main(argv=None) -> int`, `parser.error` for exit 2; add `settings check`.
- `backend/tests/engine/test_golden.py` -- parametrized over golden file names; generic over settings overrides; add the two new files.
- `backend/tests/engine/golden/classic-step-pass-through.md` -- model for the hand table format (set-up, rules, per-Week slots, unit check, independent-check note).
- `backend/tests/engine/test_settings.py` -- `test_classic_defaults_dump_as_json_with_decimal_strings` lists the dump: add `starting_backlog: 0`.
- `backend/tests/test_sim.py` -- `main([...])` + capsys style.
- CI (`.github/workflows/ci.yml`) already gates `--cov=app/engine --cov=tests/engine --cov-fail-under=100` (branch).
- Read-only sources: epics.md Story 1.3 (line ~641); PRD FR-12 (prd.md ~238); addendum §B line 55 (Week 21 at 2/2/2, Week 29 at 3/3/3).

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/settings.py` -- add `starting_backlog: Units = 0`; `Range` (frozen: `minimum`, `maximum` as int or Decimal, `placeholder: bool`, `decimal_places: int | None`); `RANGES: Mapping[str, Range]` for every Design-Notes field; `SettingsError` and `SettingsWarning` frozen models; `validate(settings) -> tuple[SettingsError, ...]`; `warnings(settings) -> tuple[SettingsWarning, ...]`; `demand_change_reaches_retailer(settings) -> int | None`; `DemandStep.first_change_week` (None when flat) -- FR-12.
- `backend/app/engine/week.py` -- `initial_state` starts each Seat with `starting_backlog`.
- `backend/app/engine/__init__.py` -- re-export `RANGES`, `Range`, `SettingsError`, `SettingsWarning`, `validate`, `warnings`, `demand_change_reaches_retailer`.
- `backend/tests/engine/test_validation.py` -- every I/O-matrix row; every RANGES field just below min / at min / at max / just above max; placeholder flags (delays False, rest True); one-error-per-field suppression; warning thresholds on both sides; 21 and 29; never raises.
- `backend/tests/engine/test_week.py` -- starting backlog with inventory 0: Week 1 amount = demand + backlog; slot counts at 1/1/1 and 3/3/3.
- `backend/tests/engine/golden/delays-1-1-1-backlog.{md,json}`, `delays-3-3-3-backlog.{md,json}`, `test_golden.py` -- 8-Week hand traces: settings `{order_delay, shipping_delay, production_delay: 1 (resp. 3), starting_inventory: 0, starting_backlog: 4, weeks: 8}`, Classic step demand, pass-through Orders (Retailer orders demand, others their incoming order); `.md` records slots per Week and a unit check.
- `backend/tests/engine/test_settings.py` -- add `starting_backlog` to the dump test.
- `backend/app/sim.py`, `backend/tests/test_sim.py` -- `settings check <file>`: JSON object of `GameSettings` overrides (missing fields = Classic); pydantic errors are reported as `invalid` errors with the RANGES range when known; exit 1 on any error, 0 otherwise; missing file / non-JSON / non-object → exit 2.

**Acceptance Criteria:**
- Given `uv run python -m app.sim settings check f.json` with `{"order_delay": 4, "weeks": 20}`, when it runs, then it prints `error out_of_range order_delay` with `1..3` and no placeholder mark, and exits 1; with `{"weeks": 20}` it prints the `too_few_weeks_for_demand_change` warning with 21 and 20 and exits 0.
- Given the CI command, when run locally, then all tests pass, branch coverage of `app/engine` and `tests/engine` is 100%, and ruff passes.
- Given the two new hand tables, when an independent reviewer re-works them without seeing the engine, then they agree with the JSON (recorded in each `.md` and in this spec).

## Spec Change Log

- 2026-11-17 Independent hand check of the new golden traces: a separate reviewer re-worked `delays-1-1-1-backlog` and `delays-3-3-3-backlog` (Weeks 1-8) by hand without seeing the engine or the tables, then compared with the JSON: 0 mismatches in each (rows, Orders, totals 72/56/44/36 and 72/36/32/32).

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 26 findings — high 0, medium 1, low 23, false 2, maybe-false 0
- findings:
  - `[low]` `[patch]` (verification-gap) CLI range suffix never asserted for a min-0 field — `test_settings_check_reads_rates_as_decimals` now asserts `[allowed 0.00..100.00 (placeholder)]`; new `test_settings_check_shows_a_range_whose_minimum_is_zero`.
  - `[low]` `[patch]` (verification-gap) no-Weeks-to-play rule tested only with flat demand — step-demand case `GameSettings(weeks=4, guided_weeks=4)` added.
  - `[low]` `[reject]` (intent) below-minimum values are rejected by the model, not `validate` — the spec keeps the Story 1.2 type/sign guards (a delay of 0 would break `initial_state`); the CLI reports those with their range; `test_only_max_order_has_a_below_minimum_value_the_type_allows` documents the split.
  - `[low]` `[reject]` (intent) backlog-means-no-inventory enforced in `validate`, not `initial_state` — `validate` is the gate; the engine trusts validated settings, as triaged in Story 1.2; both goldens start backlogged Seats with no inventory.
  - `[low]` `[reject]` (intent) per-Seat vs uniform starting values — "12 per Seat" in the Classic defaults is one value for every Seat; per-Role values can be added by Epic 5 without breaking this model.
  - `[low]` `[patch]` (intent) max-Order factor 10 is an unmarked placeholder — now `MAX_ORDER_PEAK_FACTOR`, documented as a placeholder next to `RANGES` (grouped with blind finding on unnamed thresholds).
  - `[low]` `[reject]` (intent) 3/3/3 trace never carries the step past the Wholesaler — the AC asks for slot counts and starting backlog at these delays; the arrival test now runs the step through the whole chain at 3/3/3.
  - `[false]` `[reject]` (intent) exit 2 for a bad file is a third outcome — a bad file is an error, and the AC only requires zero exit when there are no errors.
  - `[low]` `[patch]` (edge) UTF-8 BOM file rejected with exit 2 — reading with `utf-8-sig`; test added.
  - `[low]` `[reject]` (edge) deeply nested JSON raises RecursionError — not a realistic settings file; a guard adds code.
  - `[low]` `[reject]` (edge) a pydantic error hides range errors in other fields — range checks need a constructed model; the user sees the type error first and reruns; unlikely in practice.
  - `[low]` `[reject]` (edge) out-of-range inventory plus backlog gives two errors — they are two fields, each with a real problem; "one error per field" holds.
  - `[false]` `[reject]` (edge) reader believes below-minimum is tested for every field — `test_only_max_order_has_a_below_minimum_value_the_type_allows` states exactly which ones are.
  - `[low]` `[reject]` (blind) function `warnings` shadows the stdlib module — the name is given by the story AC (`engine.settings.warnings`).
  - `[low]` `[reject]` (blind) `SettingsWarning.values` dict is mutable — in-memory result objects; nobody mutates them; a read-only mapping complicates pydantic dumps.
  - `[medium]` `[patch]` (blind) arrival formula tested only against itself — `test_arrival_week_matches_the_engine` runs the engine (no starting inventory, pass-through) at 1/1/1, 2/2/2, 3/3/3, 1/2/3, 3/1/2 and checks the first Week the Retailer gets Factory-made extra units equals `demand_change_reaches_retailer`.
  - `[low]` `[patch]` (blind) arrival warning message overstates — message now says "if every Seat passes the demand change on at once, the first units the Factory makes for it reach the Retailer in Week N".
  - `[low]` `[reject]` (blind) no golden with mixed delays — Story 1.2's `test_mixed_delays_size_each_pipeline_and_time_the_factory` and the new arrival test (1/2/3, 3/1/2) separate the three delays.
  - `[low]` `[reject]` (blind) goldens never pay backlog down — `test_starting_backlog_ships_in_full_when_stock_allows` and the Classic step golden cover shipping out of stock; the AC asks only for the starting-backlog traces.
  - `[low]` `[reject]` (blind) a type error hides range errors in `settings check` — same as the edge row.
  - `[low]` `[reject]` (blind) demand change after the last Week gives a misleading warning — the warning stays true (the change never reaches the Retailer); demand ranges come with Story 1.4.
  - `[low]` `[reject]` (blind) mixed message styles — screens will build text from `code`, `field` and `values`; messages are for the CLI.
  - `[low]` `[reject]` (blind) no warning for starting backlog — the story lists exactly four warnings; adding more is outside it.
  - `[low]` `[patch]` (blind) unnamed threshold, `_units` used for Guided Weeks — grouped with the intent row: factor named; helper name is cosmetic.
  - `[low]` `[reject]` (blind) duplicate keys and NaN accepted — NaN is rejected by the model ("Input should be a finite number", checked); duplicate keys are an unlikely hand-edit slip.
  - `[low]` `[patch]` (blind) exit codes not documented; spec missing from the diff — exit codes 0/1/2 now in the `app/sim.py` docstring; the spec is left out of the diff on purpose (claims file for the edge layer).

## Design Notes

RANGES (placeholder unless noted): `starting_inventory` 0–100, `starting_backlog` 0–100, `supply_line` 0–100, `order_delay`/`shipping_delay`/`production_delay` 1–3 (**confirmed**, FR-12), `holding_cost` 0.00–100.00 and `backorder_cost` 0.00–100.00 (2 decimal places), `weeks` 1–100, `guided_weeks` 0–20, `max_order` 1–9999. Demand fields get their ranges with the pattern kinds in Story 1.4.

Cross-field errors (field in brackets): `starting_inventory_and_backlog` [starting_backlog] both > 0; `guided_weeks_not_before_demand_change` [guided_weeks] change Week exists and `guided_weeks >= change_week`; `guided_weeks_leave_no_weeks_to_play` [guided_weeks] `guided_weeks >= weeks`. When both guided rules fail, report the first.

Warnings: `supply_line_differs_from_demand` `supply_line != demand.start`; `backorder_not_above_holding` `backorder_cost <= holding_cost`; `max_order_may_bind` `max_order < 10 × peak demand` (PRD: single Orders reached ~10× average), values include the threshold; `too_few_weeks_for_demand_change` arrival > `weeks`.

Arrival (each Seat reacts at once, n Roles): `change_week + n·order_delay + production_delay + (n−1)·shipping_delay`. 4 Roles, change 5: 2/2/2 → 5+8+2+6 = 21; 3/3/3 → 5+12+3+9 = 29 (addendum §B). Matches engine timing: Order in t received t+o; Factory Order enters production t+o, reaches inventory t+o+p; shipment arrives t+s.

## Verification

**Commands:**
- `cd backend && uv sync --locked && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-report=term-missing --cov-fail-under=100` -- expected: all pass, 100% (Postgres from compose running for the non-engine tests)
- `cd backend && uv run python -m app.sim settings check <tmp>.json` -- expected: as in the AC

## Auto Run Result

Status: done

**Summary:** `GameSettings` gains `starting_backlog`; `app/engine/settings.py` adds `RANGES` (delays 1-3 confirmed, all other bounds placeholders), `validate` (stable codes, one error per field, range then cross-field rules), `warnings` (four non-blocking warnings with their numbers), `demand_change_reaches_retailer` (21 at 2/2/2, 29 at 3/3/3, as addendum §B) and `MAX_ORDER_PEAK_FACTOR`; `initial_state` starts Seats with the starting backlog; `python -m app.sim settings check <file>` prints errors with ranges and warnings (exit 0 / 1 errors / 2 bad file).

**Files:** `backend/app/engine/{settings,week,__init__}.py` (ranges, validation, warnings, starting backlog); `backend/app/sim.py` (`settings check`); `backend/tests/engine/test_validation.py` (new); `backend/tests/engine/{test_settings,test_week,test_golden}.py`; `backend/tests/engine/golden/delays-{1-1-1,3-3-3}-backlog.{json,md}` (hand-worked 8-Week traces); `backend/tests/test_sim.py`.

**Independent golden check (no human in the loop):** a separate reviewer re-worked both new traces by hand without seeing the engine or the tables: 0 mismatches; totals R/W/D/F 72/56/44/36 (1/1/1) and 72/36/32/32 (3/3/3).

**Review:** 26 findings. Patched 8 rows (1 medium: arrival formula now checked against the engine at five delay sets; 7 low: CLI range suffix for min-0 fields, step-demand no-Weeks test, named placeholder factor, BOM files, clearer arrival message, exit codes documented). Deferred none. Rejected 16 low and 2 false, reasons in the triage log.

**Follow-up review recommended:** false — patched high 0, medium 1, low 7.

**Verification:** `ruff check`, `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` → 185 passed, 100% branch coverage (Postgres from compose); `settings check` with `{"order_delay": 4, "weeks": 20}` → error `out_of_range order_delay [allowed 1..3]` plus a warning, exit 1; with `{"weeks": 20}` → warning with `arrival_week=21, weeks=20`, exit 0.

**Residual risks:** all bounds except delays and the factor 10 are placeholders until Epic 5; per-Role starting values (Epic 5 wording) would need a model extension; CI change not run on GitHub (no push).
