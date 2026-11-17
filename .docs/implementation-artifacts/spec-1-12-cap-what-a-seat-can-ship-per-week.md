---
title: 'Story 1.12: Cap what a Seat can ship per Week (cut list, FEATURE_CAPACITY)'
type: 'feature'
created: '2026-11-17'
baseline_revision: 'c3602f287bfe3225914fd668b3a8b5ae9a553d29'
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

**Problem:** The engine cannot model a Seat that ships at most a fixed number of units per Week, so a capped chain cannot be simulated (FR-12, FR-26, FR-29). The feature is on the cut list and must be switchable off with `FEATURE_CAPACITY` without touching anything else.

**Approach:** Add an optional per-Role `capacity` to `GameSettings`; the Week sequence ships the smallest of on-hand, owed and capacity; the conservation check and settings validation/warnings learn about it; `games.commands.create` and `sim settings` refuse a capacity when `FEATURE_CAPACITY` is off. A new hand-worked golden trace proves the capped arithmetic.

## Boundaries & Constraints

**Always:**
- `GameSettings.capacity: dict[Role, int] | None = None` (strict ints, JSON `{"retailer": 6}`). One Seat = one key; all Seats = one key per Role. A key for a Role not in `settings.roles` is refused at construction (pydantic `ValidationError`). With `None` it is left out of `model_dump` (`exclude_if`), so the dump, the stored settings JSON and every earlier output are byte-identical to before.
- Rules v1 `_open_week`: `shipped = min(on_hand, amount, capacity)` when the Role has a capacity, else unchanged; rest stays backlog. Capacity limits shipping only (Factory production is not capped). v1 is extended in place, not copied to v2: for every settings value that existed before, every output is unchanged (decision; RULES_VERSIONS.md allows output-equal edits and gets a note).
- `engine.settings.CAPACITY_RANGE = Range(minimum=1, maximum=100, placeholder=True)`. `validate(settings, *, capacity_enabled: bool = False)`: when `capacity` is set and `capacity_enabled` is False → one `SettingsError(code="capacity_disabled", field="capacity")`, no range check; else each value outside the range → `out_of_range` on field `capacity.<role>` with the range, in chain order. Capacity errors come after the demand errors and before the cross-field rules. With `capacity` None, `validate` returns exactly what it did before for every value of `capacity_enabled`.
- `warnings(settings)`: after the existing four, one `capacity_below_peak_demand` per capped Role whose capacity < `demand.peak`, in chain order, field `capacity.<role>`, values `{"role", "capacity", "peak_demand"}`.
- `check.conservation`: the `shipment` rule expects `min(on_hand, owed, capacity)` for a capped Role; `inventory_and_backlog` is skipped for capped Roles only. Docstring updated.
- `games.commands._effective_settings` calls `validate(effective, capacity_enabled=get_settings().feature_capacity)`; refusal stays `invalid_settings` 422 with `fields {"capacity": "capacity_disabled"}`. `sim settings` passes the same flag.
- Golden trace `capped-retailer-6.json` (+ hand-worked `capped-retailer-6.md`) in `GOLDEN_TRACES[1]`: Classic settings + `{"capacity": {"retailer": 6}}`, the 10 pass-through Orders of `classic-step-pass-through.json`. Upstream rows equal that trace; the Retailer ships 6 from Week 5 and its backlog grows by 2 a Week (2, 4, …, 12 in Weeks 5–10) while inventory stays positive. Worked by hand (not from the engine) and independently checked by a review sub-agent before acceptance.
- Engine + `tests/engine` keep 100 % branch coverage; ruff clean; all tests pass; every existing golden file unchanged.

**Never:** No change to `SeatState`/`SeatView`/`SeatDetail`, Decision log, migrations, existing golden files or the flag's default (`true`, Story 1.1). No capacity in Seat views or briefing (Story 6.22), no settings screen (Story 5.15), no allocation rule, no rules v2.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Off by default | `GameSettings()` | no `capacity` key in dump; all goldens unchanged | — |
| One Seat capped | capacity `{retailer: 6}`, Classic step, pass-through | golden trace matches; Retailer inventory and backlog both > 0 from Week 5 | conservation `()` |
| All Seats capped | capacity 6 for all four Roles, demand 8 | every Seat ships ≤ 6 every Week; conservation `()` | — |
| Capacity ≥ demand | capacity 50 on all Roles | states equal the uncapped run | — |
| Check catches slips | capped state with `shipped` changed; uncapped Seat with both positive | `shipment` / `inventory_and_backlog` violations; none for the capped Seat's both-positive | never raises |
| Below peak | capacity 6, step 4→8 | warning `capacity_below_peak_demand` values role, 6, 8 | non-blocking |
| Out of range | capacity 0, -1, 101 (enabled) | `out_of_range` on `capacity.<role>` with min 1, max 100, placeholder | — |
| Not whole | 6.5, `"6"`, `true`, unknown Role key | `ValidationError` at construction | `invalid_settings` 422 from `create` |
| Flag off | capacity set, `FEATURE_CAPACITY=false` | `create` refused `invalid_settings`, `fields {"capacity": "capacity_disabled"}`, nothing stored; `sim settings` prints `error capacity_disabled`, exit 1 | — |
| Flag on via create | capacity `{wholesaler: 6}`, flag on | Game stored with capacity in its settings snapshot; played to the end, `verify_finished` ok | — |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py` -- `GameSettings` (add field + model validator for Roles), `RANGES`/`Range`/`_check_range`/`_range_error` (reuse), `validate` (L197, add keyword + capacity block before cross-field rules), `warnings` (L314, append), `settings.demand.peak`.
- `backend/app/engine/rules/v1/__init__.py` -- `_open_week` (L120) `shipped = min(on_hand, amount)`; docstring names capacity.
- `backend/app/engine/check.py` -- `_opened_week` `shipment` expect; `_books` `inventory_and_backlog` block; module docstring rule list.
- `backend/app/engine/__init__.py` -- export `CAPACITY_RANGE`.
- `backend/app/engine/RULES_VERSIONS.md` -- note: capacity added to v1 as an output-equal extension (Story 1.12).
- `backend/app/modules/games/commands.py` -- `_effective_settings` (L89) calls `validate`.
- `backend/app/sim.py` -- `_settings_check` (L261) calls `validate`.
- `backend/app/platform/config.py` -- `get_settings().feature_capacity` (default True; tests clear the cache, see `tests/conftest.py` L78, `tests/test_config.py` L41).
- Tests: `tests/engine/test_golden.py` (`GOLDEN_TRACES`), `golden/classic-step-pass-through.{json,md}` (format to copy), `test_settings.py` (dump equality L9), `test_validation.py`, `test_check.py`, `test_week.py`, `tests/games/test_create.py`, `tests/test_sim.py` (`settings` subcommand tests).

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/settings.py` -- `capacity` field, `CAPACITY_RANGE`, validate keyword, warning.
- `backend/app/engine/rules/v1/__init__.py` -- capped shipment.
- `backend/app/engine/check.py` -- capped `shipment` and `inventory_and_backlog`.
- `backend/app/engine/__init__.py`, `RULES_VERSIONS.md` -- export, note.
- `backend/app/modules/games/commands.py`, `backend/app/sim.py` -- pass `feature_capacity`.
- `backend/tests/engine/golden/capped-retailer-6.{md,json}` -- hand-worked trace; register in `test_golden.py`.
- `backend/tests/engine/test_capacity.py` (new) -- matrix rows for engine, check, validation, warnings.
- `backend/tests/engine/test_settings.py` -- dump without capacity; capacity round trip.
- `backend/tests/games/test_create.py`, `backend/tests/test_sim.py` -- flag off/on rows.

**Acceptance Criteria:**
- Given the golden traces, when CI runs `test_golden.py`, then the four earlier traces pass unchanged and `capped-retailer-6.json` passes.
- Given `FEATURE_CAPACITY=false`, when an existing simulation batch runs, then Seat states and the Decision log equal a run without this story (no `capacity` key anywhere).
- Given the CI commands run locally, then all tests pass, engine branch coverage is 100 %, ruff is clean.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 27 findings — high 0, medium 0, low 19, false 8, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind) `inventory_and_backlog` exempts a capped Seat even when the cap did not bind — a slip in a capped Seat's inventory or backlog is still caught by `inventory_balance`/`backlog_balance`, and a wrong `shipped` by `shipment` (which includes the cap); the rule is not the only guard.
  - `[low]` `[patch]` (blind) `test_both_positive_is_allowed_on_the_capped_seat_only` never shows the capped Seat holding both — rewritten: a capped Retailer holding both passes `conservation`, the same states read as uncapped flag `inventory_and_backlog` on the Retailer only.
  - `[low]` `[patch]` (blind) `capacity={}` dumps `"capacity": {}` and is refused as `capacity_disabled` — the validator normalises an empty map to None; test `test_an_empty_capacity_is_no_capacity`.
  - `[low]` `[patch]` (blind) a bad `roles` gives a second, misleading capacity error — validator skips the chain check when `roles` failed; test `test_a_bad_chain_is_reported_once_not_again_under_capacity`.
  - `[low]` `[patch]` (blind) `sim._invalid` prints the capacity range for shape errors (not a map, unknown Role, Role outside the chain) — range now attached only for `capacity.<role>` value errors; test `test_settings_check_capacity_shape_errors_show_no_range`.
  - `[low]` `[reject]` (blind) AC 2 (flag-off batch equals the pre-story run) has no dedicated test — the earlier golden traces, Decision-log and smoke-batch tests all pass unchanged, and the settings dump without capacity is asserted equal to the pre-story dump; a two-way batch comparison adds machinery for no new evidence.
  - `[low]` `[reject]` (blind) tests live in `test_capacity.py`, not the files the task list names — fix would edit this spec; coverage is the same.
  - `[low]` `[reject]` (blind) `sim run` does not refuse a capacity up front when the flag is off — it is refused at the first `create` with `invalid_settings`, exit 1, like every engine-rule setting in Story 1.11.
  - `[low]` `[reject]` (blind) no capacity run on a two-Role chain — `capacity_of` is keyed by Role with no chain-length branch; the Role-outside-chain refusal is tested.
  - `[low]` `[reject]` (blind) `test_golden_capped_retailer…` repeats golden numbers — two assertions, harmless; it also runs `conservation` on the trace.
  - `[low]` `[patch]` (blind) docs do not say what the flag does to stored capped Games — `RULES_VERSIONS.md` now states the flag gates new settings only and stored Games run with their snapshot.
  - `[low]` `[patch]` (blind) `RULES_VERSIONS.md` omits the shared check change — note extended (check extended in place; Rule-based and Guided Order do not read capacity).
  - `[low]` `[patch]` (edge) duplicate of the bad-`roles` finding — same fix.
  - `[low]` `[patch]` (edge) duplicate of the `{}` finding — same fix.
  - `[low]` `[reject]` (edge) capacity ≤ 0 built without `validate` ships negative units — the matrix fixes 0/-1 as `validate` `out_of_range` with the range; every stored-Game path validates at `create`, as for every other setting.
  - `[low]` `[patch]` (edge) duplicate of the `sim._invalid` finding — same fix.
  - `[low]` `[reject]` (edge) `sim settings` prints the below-peak warning next to a capacity error — existing behaviour for every field (errors and warnings both printed; exit 1 on errors).
  - `[low]` `[patch]` (edge) `test_capacity_out_of_range_is_an_engine_error` depends on the flag default — sets `FEATURE_CAPACITY=true`.
  - `[false]` `[reject]` (edge) spec says `test_settings.py` gets the dump tests — claim about the spec's task list, not the code; fix would edit this spec.
  - `[low]` `[patch]` (verification-gap, other) weak last assertion in `test_both_positive…` — same fix as the blind row.
  - `[low]` `[reject]` (verification-gap, other) serializer warning in `test_a_capacity_that_is_not_a_whole_number_is_invalid` — expected from `model_construct` with 6.5; the test asserts the refusal.
  - `[false]` `[reject]` (intent) flag gates validation, not play/replay (reading A1 vs A2) — "a Game reads only its snapshot" (AD) and "leave every earlier golden trace and the Seat state unchanged when off" select A1; no Game before this story has a capacity, so "every Game" is unchanged.
  - `[false]` `[reject]` (intent) no flag-off played-Game comparison — same evidence as the AC 2 row: earlier traces and Decision-log tests pass unchanged.
  - `[false]` `[reject]` (intent) non-whole capacity range only on the CLI surface — `create` takes a typed `GameSettings`, so a non-whole value cannot reach it except via `model_construct`; `validate` and the CLI show the range for the reachable cases.
  - `[false]` `[reject]` (intent) any subset of Seats vs one/all — descriptive; a superset, as the auditor states.
  - `[false]` `[reject]` (intent) extra capacity checks beyond the AC — descriptive; not divergences.
  - `[false]` `[reject]` (intent) golden trace does not exercise a capped Seat's effect downstream — descriptive; the Wholesaler/Factory/every-Seat tests run `conservation` on those cases.

Independent hand-check (founder stand-in, 2026-11-17): a sub-agent worked Weeks 1-10 of `capped-retailer-6` by hand from addendum §B without reading the engine — 0 mismatches in every field, the Orders and the final totals; backlog grows 2, 4, …, 12 from Week 5.

## Design Notes

Retailer trace, Weeks 5–10 (delivery from the existing pass-through trace: 4,4,4,4,8,8): on hand 16,14,12,10,12,14 → ship 6 → inventory 10,8,6,4,6,8; owed 8,10,12,14,16,18 → backlog 2,4,6,8,10,12; cost 0.5·inv + bl = 7.00,8.00,9.00,10.00,13.00,16.00. Upstream Seats are unaffected because the Retailer's Orders and every shipment upstream of it are the same as in the uncapped trace.

Flag default `true` (Story 1.1, SETUP-GUIDE) is kept; "off by default" in the AC is the setting (`capacity = None`). `validate` defaults `capacity_enabled=False` so a caller that forgets the flag fails closed.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-report=term-missing --cov-fail-under=100` -- expected: all pass
- `cd backend && uv run python -m app.sim run batches/classic-smoke.json` -- expected: `checks ok=3 failed=0`

## Auto Run Result

Status: done

**Summary:** `GameSettings` gains an optional per-Role `capacity` (one Seat or every Seat), left out of the dump when unset so settings without it serialise exactly as before. Rules v1 ships the smallest of on hand, owed and capacity; units it cannot ship stay as backlog. The conservation check includes the cap in `shipment` and exempts capped Seats only from `inventory_and_backlog`. `validate` refuses a capacity with `capacity_disabled` unless the caller passes `capacity_enabled` (from `FEATURE_CAPACITY`), and range-checks it 1..100 (placeholder maximum); `warnings` adds `capacity_below_peak_demand`. `games.commands.create` and `sim settings check` pass the flag. A new hand-worked v1 golden trace caps the Retailer at 6.

**Files:**
- `backend/app/engine/settings.py`: `capacity` field, `capacity_of`, `CAPACITY_RANGE`, `validate(…, capacity_enabled)`, capacity warning.
- `backend/app/engine/rules/v1/__init__.py`: capped shipment.
- `backend/app/engine/check.py`: capped `shipment`, `inventory_and_backlog` for uncapped Seats only.
- `backend/app/engine/__init__.py`, `RULES_VERSIONS.md`: export; note on extending v1 and the check in place, and on stored Games.
- `backend/app/modules/games/commands.py`, `backend/app/sim.py`: pass `FEATURE_CAPACITY`; CLI shows the capacity range.
- `backend/tests/engine/golden/capped-retailer-6.{json,md}`, `test_golden.py`: new trace.
- `backend/tests/engine/test_capacity.py` (new), `tests/games/test_create.py`, `tests/test_sim.py`: tests.

**Review:** one pass, 27 findings (low 19, false 8). Patched (low): empty `{}` normalised to None, no duplicate capacity error on a bad chain, CLI range only for capacity value errors, flag set explicitly in a create test, stronger both-positive test, `RULES_VERSIONS.md` note. Rejected findings and reasons are in the triage log. Nothing deferred.

**Follow-up review recommended:** false. Patched counts: high 0, medium 0, low 6 entries.

**Verification:**
- `ruff check`, `ruff format --check`: clean.
- `pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-fail-under=100`: 1132 passed, 100 % (local compose Postgres).
- `sim run batches/classic-smoke.json`: `checks ok=3 failed=0`.
- Matrix audit: every row covered by a passing test (`test_capacity.py`, `test_golden.py`, `test_create.py`, `test_sim.py`).
- Founder check by an independent sub-agent: hand-worked capped trace, 0 mismatches.

**Decisions taken in place of the founder:**
1. Capacity is a per-Role map (`{"retailer": 6}`); "all Seats" = one key per Role; `{}` = no capacity.
2. `FEATURE_CAPACITY` gates only settings validation (`create`, `sim settings`); its default stays `true` (Story 1.1). "Off by default" is read as `capacity` unset by default. `validate` fails closed (`capacity_enabled=False`) when a caller omits the flag. Stored Games always play with their snapshot.
3. Capacity was added to rules v1, not a new v2, because every output for settings without capacity is unchanged.
4. Capacity range 1..100, maximum a placeholder like the other ranges.
5. Capacity limits shipping only; Factory production is not capped.
6. Golden trace: Retailer capped at 6 with the Classic pass-through Orders of Story 1.2's trace, Weeks 1-10.
7. Implementation ran in the orchestrating agent's own context (runbook); review layers and the hand-check were independent sub-agents.

**Residual risks:**
- CI not run on GitHub (no push).
- Capacity is not yet shown to Seats (Story 6.22) or settable on a screen (Story 5.15).
