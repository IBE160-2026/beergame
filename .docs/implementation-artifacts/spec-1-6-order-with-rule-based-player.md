---
title: 'Story 1.6: Order with the Rule-based player'
type: 'feature'
created: '2026-11-17'
status: 'done'
baseline_revision: 'b471564c3066389ff8c5cfb571ceb582a9b4eda1'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** No AI player can order yet. Every empty Seat (Story 1.8 `start`) and every Seat's Rule-based reference Order (AD-20) need a documented, deterministic anchoring-and-adjustment rule (FR-33), fed by a numbers-only view of one Seat, and Guided Weeks need the fixed starting-demand Order (FR-11).

**Approach:** Add to the pure engine `SeatView` (numbers-only view of one Seat, with a builder from the Week states and the Seat's own Orders), `rule_based.order(settings, seat_view, params)` with a versioned `RuleBasedParams` model, and `guided_order(settings)`. Ship one parameter set, `placeholder-unverified`, as a JSON config file read by a small platform helper; document the rule in a Markdown file next to it; add `--orders rule_based` to `python -m app.sim trace`; pin the Classic step Orders in a golden trace.

## Boundaries & Constraints

**Always:**
- AD-1 purity: new engine files import only stdlib, pydantic and `app.engine`; no file reads in `app/engine` (the config file is read in the shell); `test_purity` passes.
- The rule reads only `seat_view.role`, `inventory`, `backlog`, `incoming_orders`, `supply_line` (and may read `order_history`), plus the Game settings passed in (delays, `max_order`, Role order). It never reads `neighbour_numbers`.
- Arithmetic in `Decimal`; result is an `int` from 0 to `settings.max_order` (round half up, then clamp). Same inputs give the same Order on every platform.
- `SeatView` holds numbers only: no names, no number of Weeks, no future demand, no other Seat's state beyond `neighbour_numbers`.
- Parameter sets are JSON files `backend/app/parameter_sets/rule_based/<id>.json` with `id`, `version`, `verified`, `source` and the parameters; a new set is a new file, selected by id, with no code change. The only shipped set is `placeholder-unverified` (`verified: false`, `source` says the values are placeholders pending the primary source, issues #8 and #17, and come from no calculator site).
- All existing tests and golden traces pass unchanged; CI keeps 100 % branch coverage of `app/engine` and `tests/engine`; ruff clean.

**Never:**
- No Sterman (1989) or calculator-site parameter values; placeholder values are round numbers chosen only so the Classic chain stays in balance.
- No DB, migration, occupancy or `seat_turns` (Stories 1.7/1.8); no `SeatState` in `games` (1.8); no Information visibility setting in `GameSettings` (later epic) — the builder leaves `neighbour_numbers` empty.
- No new third-party dependency. No change to `advance`, `initial_state`, `check`, `GameSettings`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Balance | Classic, Week 1 view of any Seat (inv 12, backlog 0, incoming 4, supply line 12), placeholder set | 4 | — |
| Constant demand | Classic with demand 4 throughout, all four Seats ordering by the rule for 36 Weeks | every Order 4 | — |
| Neighbour change | same view with different `neighbour_numbers` | same Order | — |
| Big shortfall | backlog 500, supply line 0 | clamped to `max_order` | — |
| Big surplus | inventory 500 | 0 | — |
| Half | indicated value x.5 | rounds up | — |
| Role not in settings | `view.role` not in `settings.roles` | — | `ValueError` |
| Guided Week | any settings | `guided_order` = `settings.demand.starting_level`; rule not called | — |
| Bad view | `incoming_orders` empty, `order_history` length ≠ len(incoming_orders) − 1, negative number | — | pydantic `ValidationError` |
| Bad params | missing field, theta/alpha/beta outside 0..1, id ≠ requested id | — | `ValueError`/`ValidationError`; sim exits 2 |
| Unknown set id / unsafe id (`../x`) | sim `--rule-based-params nope` | — | `UnknownParameterSetError`; sim exits 2 |

</intent-contract>

## Code Map

- `backend/app/engine/state.py` -- `SeatState`/`WeekState`: per-Week `inventory`, `backlog`, `incoming_order`, `incoming_delivery`, `goods_slots`; `WeekState.seat(role)`.
- `backend/app/engine/week.py` -- `initial_state` fills order slots (`order_delay`) and goods slots (`shipping_delay`, last Role `production_delay`) with `supply_line`; last Role's `production_orders[0]` is already in `goods_slots` when the Week opens (L131-L160).
- `backend/app/engine/settings.py` -- `GameSettings`, `Role`, `FROZEN`; `settings.demand.starting_level` exists on every pattern (`demand.py` L45, L74, L121).
- `backend/app/engine/__init__.py` -- re-exports and `__all__`; add new public names.
- `backend/app/sim.py` -- `OrderPolicy`, `orders_spec`, `_trace` loop (one state at a time); `build_parser` trace options; `parser.error` for bad input (exit 2).
- `backend/tests/engine/test_golden.py`, `golden/*.json` -- golden file style (`description`, `settings`, `orders`).
- `backend/tests/engine/test_purity.py` -- scans `app/engine/*.py` only (not subdirectories); forbids `pathlib`, `os`, `io`.
- `backend/tests/test_sim.py` -- `run(capsys, *argv)` helper and trace assertions.
- `backend/Dockerfile` -- `COPY app ./app`, so JSON under `backend/app/` ships in the image.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/view.py` -- `NeighbourNumber(role, week, quantity: Literal["inventory","backlog"], value)` and `SeatView(role, inventory, backlog, incoming_orders, supply_line, order_history, neighbour_numbers=())`, frozen, non-negative ints, `incoming_orders` non-empty (oldest first, last = this Week's incoming order), `order_history` = own Orders of earlier Weeks (length len(incoming_orders) − 1). `seat_view(settings, states, orders, role) -> SeatView` builds it from opened Week states 1..t and the Order maps of Weeks 1..t−1 -- FR-23, FR-33, AD-1.
- `backend/app/engine/rule_based.py` -- `RuleBasedParams` (frozen: `id`, `version` ≥ 1, `verified`, `source`, `theta`, `alpha_s`, `beta` Decimals in 0..1, `desired_inventory` int ≥ 0), `parse_params(text, set_id)`, `order(settings, seat_view, params) -> int` per Design Notes -- FR-33.
- `backend/app/engine/guided.py` -- `guided_order(settings) -> int` = `settings.demand.starting_level`, no cap (the I/O matrix says so; `max_order_may_bind` warns when it could bind) -- FR-11.
- `backend/app/engine/rule_based.md` -- the rule as a formula, each parameter named, the primary source (Sterman 1989, Management Science 35(3)) the final values must come from, issues #8/#17, that costs are not inputs of the rule, and how the fields map to the paper's notation (β = α_SL/α_S; `desired_inventory` + β·SL* plays the role of the paper's S′).
- `backend/app/engine/__init__.py` -- export `SeatView`, `NeighbourNumber`, `seat_view`, `RuleBasedParams`, `guided_order`; docstring names `app.engine.rule_based.order`.
- `backend/app/parameter_sets/rule_based/placeholder-unverified.json` -- the placeholder set (theta 0.50, alpha_s 0.50, beta 0.50, desired_inventory 12, version 1, verified false).
- `backend/app/platform/parameter_sets.py` -- `read_parameter_set(kind, set_id, root=...) -> str` and `UnknownParameterSetError(LookupError)`; `kind` matches `[a-z0-9][a-z0-9_-]*`, `set_id` matches `[a-z0-9][a-z0-9-]*` (the same pattern as `RuleBasedParams.id`), file must exist.
- `backend/app/sim.py` -- policies take `(settings, states, orders)`; `--orders rule_based` plays Guided Weeks with `guided_order`, later Weeks with `rule_based.order` on `seat_view(...)`; `--rule-based-params ID` (default `placeholder-unverified`); when the set is not verified, print after the table `warning: Rule-based parameter set <id> v<version> is a placeholder (unverified): <source>`.
- `backend/tests/engine/test_view.py`, `test_rule_based.py`, `test_guided.py` -- every matrix row; supply line = ordered minus received over a stepped Game (e.g. pass-through chain), checked against an independent count from the states (upstream order slots after this Week's, upstream backlog, own goods slots), for several delay mixes **and with `starting_backlog` > 0 (starting inventory 0)**; Week 1 balance for every Classic Role; rounding; clamps; each parameter moves the Order in the documented direction; role not in settings. No mock test around `guided_order` (it cannot fail); the "rule not consulted" property is tested at the policy (sim) level.
- `backend/tests/engine/golden/rule-based-classic-step.json` + test in `test_rule_based.py` -- Classic step, rule-based chain (Guided Weeks then rule): the full effective settings (`model_dump(mode="json")`, so a default change does not pass as a rule change), the 36 Order maps, final total costs and the parameter snapshot; the test checks the shipped config equals the snapshot and that replaying gives the same Orders.
- `backend/tests/test_parameter_sets.py` -- reads the shipped set; unknown and unsafe ids raise.
- `backend/tests/test_sim.py` -- `--orders rule_based` table (1 header + 144 rows + warning line), Orders equal the golden; unknown set and invalid set exit 2; constant/pass-through traces unchanged with no warning line; with a temporary set whose `desired_inventory` is 30, Weeks 1-4 order 4 (starting demand) for every Role and Week 5 orders the rule's value (≠ 4), and `rule_based_policy` called directly with a mocked rule shows the rule is not called in Guided Weeks and is called from the first Week after them. Redirect the set directory only by patching `app.sim.read_parameter_set` (one patch, no dead patches).

**Acceptance Criteria:**
- Given the CI command run locally, when it finishes, then all tests pass, branch coverage of `app/engine` and `tests/engine` is 100 %, `ruff check` and `ruff format --check` pass.
- Given `cd backend && uv run python -m app.sim trace --settings classic --orders rule_based`, when it finishes, then it prints the header, 144 Week rows and the placeholder warning line, and exits 0.
- Given the shipped parameter file is replaced by another set with a new id, when the sim runs with `--rule-based-params <new id>`, then it uses the new values with no code change (test with a temporary set via a patched directory).

## Spec Change Log

- 2026-11-17 Review loop 1 (bad_spec). Trigger: edge-case reviewer showed the Design Notes supply-line formula leaves out the upstream Seat's `starting_backlog`; probe with `starting_inventory=0, starting_backlog=20` gave the Wholesaler supply line 12 where ordered minus received is 32 (and a negative supply line, so a `ValidationError`, in other Weeks). Amended: Design Notes supply-line `start` adds `starting_backlog` for every Role but the last; Tasks require the independent-count test with starting backlog. Folded in with the re-derivation: `guided_order` uncapped (matches the I/O matrix), policy-level Guided Week tests replacing a mock test that could not fail, golden file with full settings, set-id pattern shared by reader and model, Week 1 balance for every Role, notation mapping in `rule_based.md`. Known-bad state avoided: a Seat in a Game that starts with backlog sees a supply line short by the backlog, so the rule over-orders or the view fails validation. KEEP: everything else from the first implementation (saved as patch `keep-1-6-loop0.patch` in the session scratchpad): `view.py` model and builder, `rule_based.py` formula, `RuleBasedParams`/`parse_params`, the placeholder JSON values, `platform/parameter_sets.py`, the sim `OrderPolicy` signature `(settings, states, orders)`, `rule_based_policy`, `--rule-based-params`, the warning line after the table, and every existing test — it passed 809 tests at 100 % branch coverage.

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 36 findings — high 0, medium 3, low 26, false 7, maybe-false 0
- findings:
  - `[low]` `[bad_spec]` (blind) `test_guided_order_does_not_consult_the_rule` cannot fail; the Guided Week branch of the policy is untested — same root as the verification-gap row; amendment requires policy-level Guided Week tests and drops the mock test.
  - `[low]` `[reject]` (blind) golden test replays with a test-local copy of the policy — the engine golden test must stay inside `app.engine` (coverage scope); the sim test checks the real policy's Orders against the same golden.
  - `[low]` `[bad_spec]` (blind) `PARAMETER_SETS` monkeypatch is dead (default bound at definition) — amendment: one patch on `app.sim.read_parameter_set`, no dead patches.
  - `[low]` `[reject]` (blind) `--rule-based-params` silently ignored without `--orders rule_based` — harmless; a guard adds a branch for an unlikely mistake.
  - `[low]` `[reject]` (blind) `orders_spec` returns a string marker — typed as a union and resolved in one place; restructuring adds plumbing for no visible gain.
  - `[low]` `[reject]` (blind) warning on stdout after the table — the AC asks the trace to print the table and a warning line; a failing run exits 2 before any rule output matters.
  - `[low]` `[reject]` (blind) production-vs-shipping choice written twice (`lead_weeks`, `starting_supply_line`) — two one-line expressions; a shared helper adds public surface.
  - `[low]` `[bad_spec]` (blind) reader accepts `_` in set ids, the model does not — amendment: reader uses the model's id pattern for `set_id`.
  - `[low]` `[reject]` (blind) mismatched `orders`/`states` gives an opaque negative-supply-line `ValidationError` — outside the documented input contract; pydantic's `ValidationError` is a `ValueError`.
  - `[low]` `[reject]` (blind) `OSError` from `read_text` not caught by the sim — needs a file that exists but cannot be read; unlikely, and adds a branch.
  - `[low]` `[bad_spec]` (blind) Week 1 balance test skips the Distributor — amendment: every Classic Role.
  - `[low]` `[bad_spec]` (blind) golden stores `"settings": {}`, so a default change looks like a rule change — amendment: store the full effective settings.
  - `[low]` `[reject]` (blind) `order`/`parse_params` not re-exported; sim imports the submodule — the AC names `engine.rule_based.order`, as Story 1.5 kept `engine.check.conservation`; importing a submodule by name is standard Python.
  - `[low]` `[reject]` (blind) `seat_view` recomputes sums per call (quadratic over a Game) — at most 100 Weeks x 4 Roles; Story 1.8 computes the reference once per turn.
  - `[low]` `[bad_spec]` (blind) `rule_based.md` lacks the mapping to Sterman's notation — amendment: state β = α_SL/α_S and the S′ correspondence.
  - `[medium]` `[bad_spec]` (edge) supply line leaves out the upstream `starting_backlog` — confirmed by probe (Wholesaler 12 vs ordered-minus-received 32 with backlog 20); triggered loop 1: Design Notes `start` adds `starting_backlog` for every Role but the last, plus a test.
  - `[low]` `[bad_spec]` (edge) sim does not catch `seat_view` errors — only reachable through the supply-line defect above (same root cause); fixed with it.
  - `[low]` `[reject]` (edge) Order map without the Role raises `KeyError` — Order maps come from `advance`-validated history; outside the input contract.
  - `[low]` `[reject]` (edge) `expected_incoming_order(())` raises `IndexError` — `SeatView` guarantees at least one incoming order; the helper is not called otherwise.
  - `[low]` `[reject]` (edge) `--rule-based-params` ignored with other `--orders` — same as the blind row.
  - `[low]` `[reject]` (edge) `OSError` from `read_text` — same as the blind row.
  - `[low]` `[bad_spec]` (edge) reader and model disagree on `_` in ids — same as the blind row; amended.
  - `[low]` `[bad_spec]` (edge, claim) `guided_order` caps at `max_order`, the matrix says starting level — amendment: no cap; the `max_order_may_bind` warning covers the case.
  - `[medium]` `[bad_spec]` (edge, claim) supply line is not ordered-minus-received with starting backlog — same root cause as the edge `[medium]` row.
  - `[medium]` `[bad_spec]` (verification-gap) Guided Week branch of `rule_based_policy` can be removed or shifted with no test failing — reviewer reproduced it with `guided_weeks=0`; amendment requires a set with `desired_inventory` 30 and a mocked-rule policy test at the boundary.
  - `[low]` `[bad_spec]` (verification-gap other) mock test around `guided_order` passes by construction — same as the first blind row.
  - `[low]` `[reject]` (intent) costs are not inputs of the rule although the AC lists "delays, costs, maximum Order" — FR-33 says the rule uses "only the Game settings in force", a limit not a demand that every setting moves the Order; Sterman's anchoring-and-adjustment rule has no cost term and the only source named is that paper; documented in `rule_based.md` (decision taken in place of the founder).
  - `[false]` `[reject]` (intent) the rule does not read `order_history` — the AC says "only" these inputs, a whitelist; Order history enters through the supply line.
  - `[false]` `[reject]` (intent) neighbour-number proof only at the function — the AC asks for "a test that changes the neighbour numbers and gets the same Order", which exists at `order()`; the builder has no visibility setting to fill them from yet.
  - `[low]` `[bad_spec]` (intent) "rule not consulted" not tested where it can happen — same as the verification-gap row.
  - `[false]` `[reject]` (intent) `guided_order` returns one number, not a per-Seat map — the AC signature takes only settings and the value is the same for every Seat.
  - `[low]` `[reject]` (intent) changing the default set needs a code edit — the AC asks that replacing the set needs no code change; a new set is a new file chosen by id, and Story 1.7 snapshots the id per Game.
  - `[false]` `[reject]` (intent) the placeholder set swings hard on the Classic step — the AC only asks the trace be stored as a visible pin; the values are placeholders by design.
  - `[false]` `[reject]` (intent) warning placement unspecified — any placement satisfies "prints ... a warning line".
  - `[false]` `[reject]` (intent) no import-boundary test — `tests/engine/test_purity.py` forbids `app.modules`/`app.platform` in `app/engine`.
  - `[false]` `[reject]` (intent) `OrderPolicy` change and platform reader are outside scope — both are needed for the AC's CLI and config requirements.

### 2026-11-17 — Review pass
- verdicts: 28 findings — high 0, medium 0, low 23, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) `rule_based.md` says θ, α_S, β "map one to one" though `SL*` is not the paper's constant `S′` — reworded: names line up, behaviour need not; whoever fits must check against the paper.
  - `[low]` `[patch]` (blind) expectation includes this Week's incoming order, possibly unlike the paper's timing — documented as the second point to check against the paper (issues #8/#17).
  - `[low]` `[reject]` (blind) "stays in balance" shown only at steady demand; no hand-worked post-step Weeks — the claim is the starting balance the AC asks for; the AC asks for an engine-written pin of the step, not a hand-worked trace.
  - `[low]` `[reject]` (blind) Guided Order above `max_order` gives a misleading `--orders` error — unreachable: `trace` offers only `--settings classic`; later callers validate settings and `warnings` flags it.
  - `[low]` `[reject]` (blind) `--rule-based-params` ignored without `--orders rule_based` — carried: harmless; a guard adds a branch.
  - `[low]` `[reject]` (blind) warning on stdout after the table — carried: the AC asks for a warning line in the trace output.
  - `[low]` `[reject]` (blind) `sim.py` imports the submodule from `app.engine` — carried; `from package import submodule` imports the submodule when needed, so no side effect is relied on.
  - `[low]` `[patch]` (blind) set-id pattern kept in two places with nothing tying them — added `test_set_ids_follow_the_same_pattern_as_the_parameter_model`.
  - `[low]` `[patch]` (blind) `test_view_takes_string_roles_and_role_keys` never shows Role-keyed and str-keyed Order maps agree — now builds both, compares, and checks `order_history`.
  - `[low]` `[reject]` (blind) `OSError` reading a set, and an out-of-range set through the CLI — carried (`OSError`); invalid sets through the CLI are covered by the `mismatch` and `broken` cases (same `ValueError` path).
  - `[low]` `[reject]` (blind) CLI golden test checks only the Order column — cost columns are engine fields pinned by the engine golden (total costs) and other trace tests.
  - `[low]` `[patch]` (blind) `rule_based.md` silent on Order history and θ = 0 — added both; the starting-backlog point is not a defect (the rule rightly orders less while owed units are on their way).
  - `[low]` `[reject]` (edge) Guided Order above `max_order` in the sim — same as the blind row: unreachable.
  - `[low]` `[reject]` (edge) `OSError` from `read_text` — carried.
  - `[low]` `[reject]` (edge) `--rule-based-params` ignored — carried.
  - `[low]` `[reject]` (edge) Order map without the Role raises `KeyError` — carried.
  - `[low]` `[reject]` (edge) `orders` not matching `states` — carried (outside the input contract).
  - `[low]` `[reject]` (edge) `Decimal` overflow with counts near 1e28 — no Game reaches such counts (Orders at most 9999, at most 100 Weeks).
  - `[low]` `[reject]` (edge) `expected_incoming_order(())` — carried.
  - `[low]` `[reject]` (intent) costs not used — carried (decision recorded in Auto Run Result).
  - `[false]` `[reject]` (intent) "rule not consulted" lives in the sim policy, not the engine — `guided_order` consults no rule, as the AC states; the caller-side branch is tested at the policy and CLI.
  - `[false]` `[reject]` (intent) neighbour independence only on hand-built views — carried.
  - `[low]` `[reject]` (intent) `settings` passed to the rule carries the demand pattern — the AC's own signature passes `settings`; the rule reads only delays, Role order and `max_order`.
  - `[false]` `[reject]` (intent) `seat_view` builder does not take a `SeatView` — it produces one.
  - `[low]` `[reject]` (intent) swapping the default set needs a code edit — carried.
  - `[false]` `[reject]` (intent) balance test turns Guided Weeks off — it runs the rule every Week, stricter than the AC; the golden covers Guided Weeks.
  - `[low]` `[reject]` (intent) "starting demand" for random demand is the mean, not the Week-1 draw — consistent with `warnings`, which uses the same starting level.
  - `[false]` `[reject]` (intent) the rule ignores Order history — carried.

## Design Notes

**Rule (Sterman-style anchoring and adjustment).** Let `L` = `incoming_orders`, `S = inventory − backlog`, `SL = supply_line`, `lead = order_delay + (production_delay if last Role else shipping_delay) − 1`.
- Expected incoming order: `E = L[0]`; for each later `x` in `L`: `E = theta·x + (1 − theta)·E`.
- Desired supply line `SL* = E·lead` (the supply line a Seat holds just before ordering when every Order equals demand).
- Indicated `= E + alpha_s·((desired_inventory − S) + beta·(SL* − SL))`; Order = clamp(round_half_up(indicated), 0, `max_order`).
- Classic check: E 4, S 12, SL 12, lead 3 → SL* 12 → Order 4. Costs are not inputs (Sterman's rule has none); "settings in force" means the Game's own delays and `max_order`.

**Supply line** (PRD glossary: ordered minus received): `supply_line_t = start + Σ own Orders of Weeks 1..t−1 − Σ own incoming_delivery of Weeks 1..t`, where `start = supply_line_setting·(order_delay + goods slots of the Role) + starting_backlog` for every Role but the last (the upstream Seat's opening backlog is owed to this Seat, so it was ordered and not received), and without the backlog term for the last Role (its upstream is production). Classic Week 1: 4·4 + 0 − 4 = 12. Uses only the Seat's own numbers and the settings.

**Why parameters live outside the engine:** the engine may not read files; the shell reads the JSON text and `parse_params` validates it, checking `id` equals the requested id.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-report=term-missing --cov-fail-under=100` -- expected: all pass, 100 % (Postgres from compose for non-engine tests)
- `cd backend && uv run python -m app.sim trace --orders rule_based` -- expected: header, 144 Week rows and the warning line (146 lines)

## Auto Run Result

Status: done

**Summary:** The pure engine gains `SeatView` (numbers only: Role, inventory, backlog, incoming orders, supply line, Order history, labelled `NeighbourNumber`s) with a builder `seat_view(settings, states, orders, role)` whose supply line is ordered minus received (starting pipeline plus the upstream starting backlog, plus own Orders, minus own deliveries); `rule_based.order(settings, seat_view, params)` (anchoring and adjustment: smoothed expected order, stock gap, supply-line gap against `E·lead`, round half up, clamp 0..`max_order`; never reads neighbour numbers); `RuleBasedParams` + `parse_params`; `guided_order(settings)` = starting demand. The only parameter set, `placeholder-unverified` (verified false, its source says why), is a JSON file read by `app/platform/parameter_sets.py`. `python -m app.sim trace --orders rule_based [--rule-based-params ID]` plays four Rule-based Seats (Guided Weeks order the starting demand) and prints a placeholder warning line. A golden file pins the Classic step Orders, the full settings and the parameter snapshot.

**Files:** `backend/app/engine/view.py` (new: `SeatView`, `NeighbourNumber`, `seat_view`, `starting_supply_line`); `backend/app/engine/rule_based.py` (new: params, `parse_params`, `order`); `backend/app/engine/guided.py` (new); `backend/app/engine/rule_based.md` (new: formula, parameters, source); `backend/app/engine/__init__.py` (exports); `backend/app/parameter_sets/rule_based/placeholder-unverified.json` (new); `backend/app/platform/parameter_sets.py` (new reader); `backend/app/sim.py` (policy signature, `rule_based` policy, option, warning); tests `backend/tests/engine/test_view.py`, `test_rule_based.py`, `test_guided.py`, `golden/rule-based-classic-step.json`, `backend/tests/test_parameter_sets.py`, `backend/tests/test_sim.py`.

**Review:** pass 1, 36 findings (medium 3, low 26, false 7): one bad_spec root cause (the supply line left out the upstream starting backlog; probe gave 12 instead of 32) led to loop 1, which also folded in policy-level Guided Week tests (the mock test around `guided_order` could not fail), an uncapped `guided_order` matching the matrix, full settings in the golden, one set-id pattern, every Role in the balance test, and the Sterman notation mapping; the rest rejected with reasons. Pass 2, 28 findings (low 23, false 5): 5 low patches (doc wording on how the paper's values map and what to check, Order history and θ = 0 in the doc, a test tying the set-id patterns, a Role-keyed Order map check); the rest rejected or carried. Deferred none.

**Follow-up review recommended:** false — pass 2 patched high 0, medium 0, low 5.

**Verification:** `ruff check`, `ruff format --check` clean; `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` gives 817 passed, 100 % branch coverage (Postgres from compose for the non-engine tests); `python -m app.sim trace --orders rule_based` prints 146 lines (header, 144 rows, warning) and exits 0.

**Decisions taken in place of the founder:** (1) the rule is Sterman-style anchoring and adjustment with a desired supply line `E·lead` (lead = order delay + shipping/production delay − 1) and an absolute `desired_inventory`; (2) holding and backorder costs are not inputs of the rule ("settings in force" read as a limit, not a demand that costs move the Order); (3) placeholder values θ = α_S = β = 0.50 and `desired_inventory` 12, round numbers chosen only for Classic balance, not from the paper or any calculator site; (4) the supply line is ordered minus received and counts the upstream starting backlog as owed; (5) `guided_order` returns the pattern's starting level (the mean for random demand), uncapped; (6) parameter sets are JSON files under `backend/app/parameter_sets/rule_based/`, read by a platform helper and selected by id (`--rule-based-params`, default `placeholder-unverified`); (7) the placeholder warning is the last stdout line of the trace; (8) the golden Classic-step trace is engine-written (a regression pin), not hand-worked; (9) `NeighbourNumber.quantity` is limited to inventory and backlog until Information visibility arrives; (10) implementation ran in the orchestrating agent's own context (runbook constraint); review layers were independent subagents.

**Residual risks:** the placeholder set swings hard on the Classic step (Factory Orders up to 89), expected until the paper's values arrive; the paper's fitted values may not carry over one to one (constant `S′`, timing of the expectation) and must be checked when issues #8/#17 are settled; CI not run on GitHub (no push).
