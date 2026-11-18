---
title: 'Story 2.9: Store a near-optimal reference Order for every Seat and Week'
type: 'feature'
created: '2026-11-18'
baseline_revision: '9695dc0e550a99bb68e4620d54923b62f082d76d'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Each turn stores only the Rule-based reference Order; the Play guard (2.10) and the prototype also need a near-optimal reference, computed with full knowledge of the chain, to see how close an LLM player comes to near-optimal play (FR-67, FR-79).

**Approach:** Add a pure `engine.near_optimal.order(settings, chain_state, demand_series, week, role)` (placeholder algorithm `placeholder-0`), compute it once per Seat in `_open_week`, store order + algorithm version on `seat_turns`, copy both into `seat_weeks` in `place_order`, and expose them read-only on `TurnOverview`, `DecisionLogRow` and `sim show`.

## Boundaries & Constraints

**Always:**
- `backend/app/engine/near_optimal.py`: stdlib/pydantic only, no I/O; `ALGORITHM_VERSION = "placeholder-0"`; `order(...)` dispatches through a dict `ALGORITHMS = {version: fn}` so a new algorithm is a new entry and a new `ALGORITHM_VERSION`, with no caller change. Returns a plain `int` in `0..settings.max_order`. Raises `ValueError` when `role` is not in the Game, `chain_state.finished`, `chain_state.week != week`, or `len(demand_series) < week`.
- `placeholder-0` (order-up-to with known customer demand), for the Seat at chain index `i` in Week `t`: `g` = production delay for the last Role else shipping delay; `cover` = Σ demand of Weeks `t+1 … t+order_delay+g` (Weeks past the series use its last value); `target` = `starting_inventory − starting_backlog`; `position` = `inventory − backlog + supply_line`, where `supply_line` = Σ own `goods_slots` + (last Role: Σ `production_orders[1:]`; else Σ upstream `incoming_orders[1:]` + upstream `backlog`); Order = clamp(`target + cover − position`). Document it in `backend/app/engine/near_optimal.md` as a placeholder (issue #20).
- Alembic `0012` (expand-only): `seat_turns` and `seat_weeks` get `near_optimal_reference_order INTEGER NULL` (check `>= 0`) and `near_optimal_algorithm_version TEXT NULL`, with a check that both are NULL or both set (rows from before 0012 have none). `CREATE OR REPLACE` `seat_turns_keep_opening()` so the two new turn columns cannot change once set (same rule as `ai_deadline_at`); downgrade restores 0009's function and drops the columns.
- `_open_week` passes the newest `WeekState`, the Game's stored `demand_series`, the Week and the Role; every Seat gets both values regardless of occupant. `_place` copies both from the turn, never recomputes.
- Read surfaces: `TurnOverview` and `DecisionLogRow` gain `near_optimal_reference_order: int | None` and `near_optimal_algorithm_version: str | None`; `sim show` prints `near_optimal_reference_order N placeholder-0`.

**Never:** No change to `SeatState`, `build_seat_state`, `state_seen`, the prompt, `PendingTurn`, the `ai-orders` job, rule-based outputs, the sim export/`log` columns or any golden batch file; no Play guard logic (2.10); no backfill of old rows.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Classic Week 1, constant demand 4 | `initial_state`, every Role | 4 (= Rule-based) | — |
| Classic step Week 1 | demand 4→8 in Week 5 | 8 for every Role (hand-worked: 12 + 20 − 24) | — |
| Constant demand game | Classic settings, demand 4 every Week, Rule-based players | both references equal in all 36 Weeks for all 4 Seats (engine and stored `seat_weeks`) | — |
| Supply line | any state played from a few settings (delays 1–3, backlog, capacity) | `supply_line` equals `seat_view(...).supply_line` | — |
| Huge gap | target far above position | `max_order` | — |
| Surplus | position far above target | 0 | — |
| Bad call | role not in chain / finished state / week mismatch / short series | — | `ValueError` |
| Leak | near-optimal patched to a sentinel (987, `canary-9`) in an LLM Game | sentinel absent from `state_seen`, `SeatState`, rendered prompt and stored `llm_call.request` | — |
| Immutable | started Game | `UPDATE` of either turn column refused (`keeps its opening values`) | trigger |

</intent-contract>

## Code Map

- `backend/app/engine/rule_based.py` -- pattern to mirror (pure, `lead_weeks`); `backend/app/engine/__init__.py` docstring lists engine entry points.
- `backend/app/engine/rules/v1/__init__.py` -- Week mechanics: `incoming_orders[0]` and `production_orders[0]` are already processed when the Week opens; basis for the supply-line formula.
- `backend/app/engine/view.py:60,99` -- `starting_supply_line`, `seat_view` (supply line from history) used as the oracle in tests.
- `backend/app/modules/games/commands.py:396` `_open_week` (insert_turns dict at `:442`), `:617` `_place` (`insert_seat_week` at `:673`), `_snapshot` `:344` (stored `game["demand_series"]` is checked equal to the settings').
- `backend/app/modules/games/models.py:101,127` -- `seat_turns`, `seat_weeks` tables (+ docstrings).
- `backend/migrations/versions/0009_ai_deadlines.py` -- `_keep_opening` trigger function to extend in 0012.
- `backend/app/modules/games/schemas.py:172,227` -- `TurnOverview`, `DecisionLogRow`; `views.py:116,134` builders; `backend/app/sim.py:507` `_show_seat`.
- Tests: `tests/engine/test_rule_based.py` (`play_rule_based`, golden pattern), `tests/engine/golden/rule-based-classic-step.json`, `tests/games/test_start.py:194` (trigger test, `turns`), `tests/games/test_place_order.py`, `tests/players/test_llm_jobs.py` (`llm_game`, SHORT) and `tests/players/test_llm_prompt.py` (leak tests), `tests/test_migrations.py:34` `HEAD`.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/near_optimal.py`, `near_optimal.md`, `__init__.py` docstring -- the pure function and its description.
- `backend/migrations/versions/0012_near_optimal_reference.py`, `backend/app/modules/games/models.py` -- columns, checks, trigger.
- `backend/app/modules/games/commands.py` -- compute in `_open_week`, copy in `_place`.
- `backend/app/modules/games/{schemas,views}.py`, `backend/app/sim.py` -- read surfaces.
- `backend/tests/engine/test_near_optimal.py` (new) -- matrix rows for the pure function, 100 % coverage; constant-demand coincidence; golden `tests/engine/golden/near-optimal-classic-step.json` (Classic step, Guided Weeks 1–4, then Rule-based Orders; per Week and Role both references; algorithm version and Rule-based set id), written by the engine as a regression pin.
- `backend/tests/games/test_near_optimal_reference.py` (new) -- stored turn/Decision log values for mixed occupants equal the engine's; a Classic step simulation Game's Decision log equals the golden's two series; constant demand coincides in every stored row; trigger refusal. `tests/players/test_llm_prompt.py` -- leak test row. `tests/test_migrations.py` -- `HEAD = "0012"`.

**Acceptance Criteria:**
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, existing golden outputs are unchanged, and any new test over 1 s is reported.
- Given the golden file, when an independent reviewer hand-works Weeks 1, 5 and 6 of at least two Roles from the formula, then the values match (result recorded in Auto Run Result).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 26 findings — high 0, medium 2, low 16, false 8, maybe-false 0
- findings:
  - `[medium]` `[patch]` (verification gap 1) 0012's downgrade restoring the 0009 trigger is untested — added `test_downgrade_to_0011_removes_the_near_optimal_reference` (columns, checks, trigger body, re-upgrade).
  - `[low]` `[reject]` (verification gap 2) pre-0012 NULL turns are never placed or read in a test — plain pass-through of nullable fields; no Game predates 0012 outside local dev databases.
  - `[low]` `[reject]` (intent A2) the placeholder reads the Seat, its supplier and demand, not the whole chain — AC1 says "may use"; the algorithm is open (issue #20); docs now state the limit (blind 3).
  - `[false]` `[reject]` (intent C1) the copy test would also pass if `place_order` recomputed — `_place` reads `turn[...]` (diff); the leak test's sentinel patch changes the engine, and stored rows equal the turn values.
  - `[low]` `[reject]` (intent C1b) LLM Seats are covered only under a patched sentinel — the computation in `_open_week` does not branch on the occupant.
  - `[false]` `[reject]` (intent C2/C3) two columns, checks and a trigger rewrite go beyond "a column", "expand-only" — all additive; the version must be stored with the reference (AC2).
  - `[false]` `[reject]` (intent D1) the Story 2.4 test was not extended in place — new tests in the same module extend the leak suite and cover SeatState, `state_seen` and the sent request.
  - `[false]` `[reject]` (intent E1/E2) coincidence only on the equilibrium path — the AC says "when the two references are computed" under constant demand; with other Orders demand is not the only input.
  - `[low]` `[reject]` (intent E3) the stored golden check covers 8 of 36 Weeks — the engine test covers all 36; demand is constant after Week 5 so the prefix is exact.
  - `[low]` `[reject]` (edge 1) the trigger lets NULL become a value after opening — no code path updates the columns; they are written in the turn's INSERT; changing 0012 after it ran on the shared test databases is avoided.
  - `[low]` `[reject]` (edge 2) a missed compute path would store NULL silently — the only turn insert is `_open_week`, covered by tests.
  - `[low]` `[reject]` (edge 3) `rules_version` is not passed — only rules v1 exists; a v2 with other queue semantics is a new algorithm version.
  - `[low]` `[reject]` (edge 4) `sim show` prints `None None` for pre-0012 turns — cosmetic, dev-only rows.
  - `[false]` `[reject]` (blind 1) cover runs past the Game's end — required: cutting it breaks the AC's coincidence in every Week under constant demand; documented in `near_optimal.md`.
  - `[low]` `[reject]` (blind 2) capacity ignored — placeholder (issue #20); documented.
  - `[low]` `[patch]` (blind 3) docs claimed "every Seat's state" — module docstring and `near_optimal.md` now state what `placeholder-0` reads.
  - `[low]` `[reject]` (blind 4) stored references cannot be recomputed under an older label; no check rule — not asked by the story; AC2 asks only for no caller change.
  - `[low]` `[reject]` (blind 5) see edge 1.
  - `[medium]` `[patch]` (blind 6) no 0012 downgrade test — same root cause as verification gap 1; the same new test.
  - `[false]` `[reject]` (blind 7) a failing reference blocks Week opening — `_snapshot` refuses a stored series that differs from the settings' before any Week opens, and the state/Week always match by construction.
  - `[false]` `[reject]` (blind 8) the "987" substring check is flaky — the request holds no ids (Story 2.4 test asserts it) and every input is deterministic.
  - `[false]` `[reject]` (blind 9) Guided Weeks make the reference misleading — the Play guard reads only `decided_by = llm` rows (Story 2.10 AC).
  - `[low]` `[reject]` (blind 10) the golden is only partly hand-worked — an independent hand-check of Weeks 1, 2, 5, 6 now passed (Auto Run Result).
  - `[low]` `[patch]` (blind 11a) the matrix asks for all 36 stored Weeks under constant demand, the test had 8 — test now plays 36 Weeks (3.6 s, reported).
  - `[low]` `[patch]` (blind 11b) version fields lacked docstrings — added.
  - `[low]` `[reject]` (blind 11c) `sim show` prints `None None` for pre-0012 turns — as edge 4.

## Design Notes

Why this placeholder: with full knowledge the textbook policy is order-up-to: keep inventory position at the target plus the known demand until a new Order can arrive (`order_delay + g` Weeks). Using the Game's opening effective inventory as the target makes it coincide with the Rule-based player in the Classic equilibrium (12 + 4·4 − 24 = 4), which the story requires; the real algorithm replaces it under issue #20. The supply line is read from the chain state (the upstream Seat's order queue and backlog), not from history, so the function needs one Week only.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/engine/test_near_optimal.py tests/games tests/players/test_llm_prompt.py tests/test_migrations.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:** every turn now stores a second, near-optimal reference Order and its algorithm version when its Week opens, and `place_order` copies both into the Decision log.
- `engine.near_optimal.order(settings, chain_state, demand_series, week, role)`: pure, clamped to 0..max Order. Placeholder `placeholder-0` (issue #20) = order-up-to with known customer demand: target (opening effective inventory) + demand of the next `order_delay + goods delay` Weeks − (inventory − backlog + supply line read from the chain state). New algorithms go into `ALGORITHMS` under a new `ALGORITHM_VERSION`; callers do not change.
- Migration 0012 (expand-only): `near_optimal_reference_order` and `near_optimal_algorithm_version` on `seat_turns` and `seat_weeks` (nullable for older rows, `>= 0`, both-or-neither check); the `seat_turns` trigger keeps both once set.
- Read surfaces: `TurnOverview`, `DecisionLogRow`, `sim show`. Not in `SeatState`, `state_seen`, the prompt or `PendingTurn`.

**Files:** `backend/app/engine/near_optimal.py` and `near_optimal.md` (new), `backend/app/engine/__init__.py` (docstring); `backend/migrations/versions/0012_near_optimal_reference.py` (new); `backend/app/modules/games/{models,commands,schemas,views}.py`; `backend/app/sim.py` (`show`); tests: `tests/engine/test_near_optimal.py` and golden `tests/engine/golden/near-optimal-classic-step.json` (new), `tests/games/test_near_optimal_reference.py` (new), `tests/players/test_llm_prompt.py` (leak tests), `tests/test_migrations.py` (HEAD 0012, downgrade test), `tests/test_sim.py` (`show`).

**Hand-check (in place of the founder):** an independent sub-agent rebuilt the Classic step game from the rules text with its own script (not the repo's `near_optimal`), then compared it with the golden file. Near-optimal for all four Roles in Weeks 1, 2, 5 and 6 (8, 12, 24/20/20/20, 22/20/20/20) and Rule-based for retailer and wholesaler in Weeks 5 and 6 (10/4, 12/4) matched. The whole 36-Week near-optimal series matched, the chain-state supply line equalled "ordered minus received" for every Role and Week, and both references stay 4 under constant demand. Verdict: PASS.

**Review:** one pass, 4 layers, 26 findings (medium 2, low 16, false 8). Patched: 0012 downgrade test (medium, two findings with one root cause), docs that overclaimed "whole chain", the 36-Week stored constant-demand test the matrix asks for, docstrings. Nothing deferred. Rejected with reasons in the triage log, notably: cover running past the last Week (needed for coincidence under constant demand), the trigger allowing NULL→value (no code path; avoided changing 0012 after it ran), capacity ignored (placeholder).

**Follow-up review recommended:** false. Patched entries: medium 1, low 3.

**Verification:** ruff check and format clean; full suite with coverage 1415 passed in 60 s, engine coverage 100 %, existing golden outputs unchanged (Epic 1 batch goldens, Rule-based golden). Every matrix row is covered by a passing test. New tests over 1 s: `test_the_references_coincide_in_every_stored_week_under_constant_demand` (about 3.6 s with `-n0`, a 36-Week stored Game) and `test_the_near_optimal_reference_never_reaches_state_seen_or_the_prompt` (about 1.0 s).

**Decisions taken in place of the founder:**
1. Placeholder algorithm `placeholder-0` = order-up-to on customer demand, target = opening effective inventory (`starting_inventory − starting_backlog`); demand after the last Week = last value; capacity is ignored.
2. Two columns per table (Order + version), nullable for rows before 0012, with a both-or-neither check; the trigger also protects them.
3. The value is shown in `TurnOverview`, `DecisionLogRow` and `sim show`. It is not in the sim export or `log` columns, so the Epic 1 batch goldens stay the same.
4. The golden file is written by the engine as a regression pin (Classic step, Guided Weeks 1–4, then Rule-based Orders) and was checked independently by a sub-agent (above).
5. Implementation ran in the orchestrating session, not a fresh subagent (runbook constraint); the reviews and the hand-check ran as independent subagents.

**Residual risks:** the placeholder is not a whole-chain optimiser (issue #20). Migration 0012 ran on the shared `olspillet_test*` databases and was not changed after it ran. CI has not run. Nothing is pushed.
