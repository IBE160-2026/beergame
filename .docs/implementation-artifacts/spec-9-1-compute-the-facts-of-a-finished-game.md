---
title: 'Story 9.1: Compute the facts of a finished Game'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '556c20c8b02e56de5706ec428e07b684b66a9c90'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A stored facts set is read with today's FactSet model, so a later ANALYSIS_VERSION that changes the shape makes version-1 rows unreadable.
    evidence: |-
      games/facts.py `_stored` validates every payload with the current `analysis.FactSet` (extra="forbid") and nothing dispatches on `analysis_version`. Harmless while only version 1 exists; settled by the first story that bumps ANALYSIS_VERSION adding a versioned reader.
    location: >-
      backend/app/modules/games/facts.py
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** Nothing after a Game can cite a number or cause yet: there is no facts set, no Detected pattern definition and no stored, checkable record of what each Seat did. Every later Debrief, Replay and report story (9.5, 9.7, 9.8, 9.14, 10.x, 13.x) needs one.

**Approach:** A pure `analysis.facts(decision_log, seat, pattern_definitions)` builds a typed facts set (chain part + Seat part) from the Decision log only; the three Detected patterns are one immutable `content` record kind (`detected_patterns`, version 1 = placeholder thresholds) pinned at the lock; `games.facts` stores each set once in `fact_sets`; `python -m app.sim facts <game_id>` prints them.

## Boundaries & Constraints

**Always:**
- `app/analysis` stays pure (stdlib, pydantic, `app.engine` only; no clock, I/O, randomness); `tests/test_imports.py::test_analysis_is_pure` keeps passing.
- Every number comes from `seat_weeks` rows (`state_seen` = `games.schemas.SeatState`, `order`, `decided_by`, `occupant_kind`); money and ratios are `Decimal` (ratios and standard deviations quantized to 0.001, ROUND_HALF_EVEN; population standard deviation), serialised as strings.
- Payload holds ids, values and Roles only: no names, no user ids, no seat ids. Fact ids are `<pattern>:<role>:<week>`; moment ids `moment:<role>:<week>`.
- The chain part of the payload is byte-identical for the four Seats of a Game.
- The pattern record: exact definition text in Norwegian bokmål worded as a pattern (validator refuses «fordi», «på grunn av», «skyldes», «førte til»), thresholds as typed parameters, one mechanism (`delay` | `supply_line` | `demand_information_lost`), and `review` = "to be reviewed by two lecturers before pilot".
- Lock pinning uses the existing `sessions.register_pin_provider`, no lock-mechanism change.
- New migration `0101` with `down_revision = "0050"`.

**Never:** no consumer wiring (no Debrief, no API route, no frontend, no `on_game_finished` hook); no LLM; no change to `seat_weeks`, the engine or the lock mechanism; no rebuild of a stored set (a stored row is returned as is, whatever its versions).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Constant demand | addendum §B trace: demand 4, all Orders 4 | `demand_std` 0, every `amplification` null, no first Week ≥ 10, holding 6.00/Seat/Week, backorder 0 | No error |
| No chain cost | every week_cost 0 | `ai_held_share` null | No error |
| Fully Rule-based Game | 4 Rule-based Seats | `student_orders` 0, `sm_excluded` true, `moments` [] | No error |
| Few student Orders | Seat with 1–9 `decided_by=student` rows | `sm_excluded` true, `moments` [] (patterns still listed) | No error |
| ≥ 10 student Orders, < 3 patterns | student weeks without pattern hits | exactly 3 moments, filled by the gap rule, only student Weeks | No error |
| Takeover | student Seat switched to `rule_based` mid-Game | moments only from student Weeks; AI-held cost counts the Seat's Weeks after the switch | No error |
| Unknown Seat / role | `facts(log, "nope", …)` or a seat not in the Game | `ValueError` / `FactsError("seat_not_found", 404)` | refused |
| Not finished | `get_or_create` on a running Game | `FactsError("game_not_finished", 409)`, nothing stored | refused |
| Concurrent first calls | two `get_or_create` at once | one row; both return it | `ON CONFLICT DO NOTHING` then select |
| CLI on non-simulation | `sim facts <class game id>` | exit 1, `error not_simulation: …` on stderr | refused |

</intent-contract>

## Code Map

- `backend/app/analysis/__init__.py` -- module docstring lists submodules; add `facts`.
- `backend/app/analysis/play_guard.py` + `play_guard.md` -- house style for a pure rule with its documentation file.
- `backend/app/engine/view.py:20-60` -- `SeatView.supply_line`; `CostLine(kind=holding|backorder)`.
- `backend/app/modules/games/schemas.py:190-240` -- `SeatState` (`state_seen`): `incoming_order`, `incoming_delivery`, `shipped`, `inventory`, `backlog`, `supply_line`, `cost_lines`, `week_cost`; `DecisionLogRow:411`.
- `backend/app/modules/games/views.py:235` -- `decision_log(game_id)` returns typed rows by Week and chain order: reuse.
- `backend/app/modules/games/repo.py:94,560` -- `get_game`, `decision_log`; add `fact_set`/`insert_fact_set`.
- `backend/app/modules/games/models.py` -- add `fact_sets` table (FKs to games, seats; unique `(game_id, seat_id)`).
- `backend/app/modules/games/summaries.py` -- pattern for a finished-Game read (`game_not_finished` 409).
- `backend/app/modules/content/{models,schemas,service,README}.py|md` -- `Kind`, `_SCHEMAS`, `starting_task_pin`, `pinned_version(pins)` (generalise with a `kind` arg, default Starting task).
- `backend/app/modules/sessions/service.py:2546-2561` -- `register_pin_provider`; register `detected_patterns`.
- `backend/migrations/versions/0046_content_and_starting_task.py` -- pattern for check constraint + literal seed record.
- `backend/app/sim.py:707-740,1431-1620` -- `_print_log`/`_log` and the subparser list; add `facts`.
- `backend/tests/test_imports.py:56` -- `games` may import only `players.service`, `progress.service`; add `content.service` (content imports no feature module).
- `backend/tests/content/test_content.py:65` -- asserts the exact pins dict; extend.
- `backend/tests/test_migrations.py:599` -- `ck_content_records_kind` must equal `Kind` values.
- `backend/tests/games/helpers.py` -- `played_once`, `classic_game`, `seat_student`, `student_of`, `query`; `tests/games/test_place_order_actor.py:20` -- `class_game` with a snapshot and Student Seats; `commands.switch_to_rule_based(game, role, "takeover_inactivity")` gives the Takeover.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/patterns.py` -- frozen pydantic models of the pattern set (three typed patterns, `following_weeks`) and pure `detect(...)` per pattern -- schema owned by the pure layer that interprets it.
- `backend/app/analysis/facts.py` + `facts.md` -- `LoggedOrder`, `DecisionLog`, `FactSet` (chain/seat), `facts()`, moment rule, `ANALYSIS_VERSION = 1`, `MIN_STUDENT_ORDERS = 10`, `MOMENTS = 3`; the .md documents every rule and threshold.
- `backend/app/modules/content/{models,schemas,service,README}` -- `Kind.DETECTED_PATTERNS`, schema registration, `detected_patterns(version)`, `detected_patterns_pin`, `pinned_version(pins, kind)`.
- `backend/migrations/versions/0101_fact_sets_and_detected_patterns.py` -- widen `ck_content_records_kind`, insert v1 literal, create `fact_sets` with an UPDATE-refusing trigger.
- `backend/app/modules/games/{models,repo}.py` + new `facts.py` -- table, repo reads/insert, `compute(game_id, seat)` and `get_or_create(game_id, seat)`, `FactsError`.
- `backend/app/modules/sessions/service.py` -- register the pin provider.
- `backend/app/sim.py` -- `facts` subcommand printing `{role: payload}` JSON for a finished simulation Game (computed, not stored, so new pattern versions can be reviewed).
- `backend/tests/analysis/test_facts.py`, `test_patterns.py` -- synthetic-log unit tests for every branch; `backend/tests/games/test_facts.py` -- store/idempotency/chain identity/no names/golden Games; `backend/tests/golden/facts/*.json`; updates to `test_imports.py`, `test_content.py`, `test_sim.py`.

**Acceptance Criteria:**
- Given the three golden Games (§B trace, a Takeover Game, the fully Rule-based Classic Game), when pytest runs, then each Seat's stored payload equals its golden JSON and every number equals a value recomputed in the test from raw `seat_weeks` SQL rows.
- Given a finished Game, when `get_or_create` is called twice for a Seat, then `fact_sets` holds one row and both calls return the same id and payload; the chain part is equal for all four Seats and the payload contains no UUID.
- Given a Class session locked after this story, when its snapshot is built, then `session_runtime.pins` holds `detected_patterns: {"version": N}` (latest) and `games.facts` uses that version for that Game; a Game without the pin uses the latest.
- Given a finished simulation Game, when `python -m app.sim facts <id>` runs, then stdout is JSON with one facts set per Role and exit 0.
- Given `pytest --cov=app.analysis --cov-branch` on the analysis tests, then coverage of `facts.py` and `patterns.py` is reported (aim 100 %).

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), following the orchestrator's two-reviewer rule. The verification-gap and intent-alignment layers were skipped for the same reason.
- verdicts: 22 findings — high 0, medium 3, low 11, false 5, maybe-false 3
- findings:
  - `[maybe-false]` `[defer]` (blind) Stored rows become unreadable after a FactSet shape change. This only applies once ANALYSIS_VERSION 2 exists. Deferred, with what would settle it.
  - `[medium]` `[patch]` (blind) Bad data raised a raw ValidationError or ContentNotFound. `_build` now maps both to `ViewError("facts_unavailable", 409)`, and the CLI reports it through `_report`. New test: `test_a_pinned_version_that_is_gone_or_a_broken_log_is_refused_typed`.
  - `[false]` `[reject]` (blind) Placeholder thresholds reach Class games. The story requires placeholders pinned at the lock, and each record carries `review`.
  - `[low]` `[patch]` (blind) facts.md said thresholds are "never in code". Reworded: pattern thresholds are content, and the other three numbers are code constants tied to ANALYSIS_VERSION.
  - `[medium]` `[patch]` (blind) Thresholds had no cross-field validation. Added validators (min_ratio ≥ 1, excess and shortfall ≥ 1, max_ratio ≤ 1, cover > 0) with refusal tests.
  - `[low]` `[patch]` (blind) The `_CAUSE` guard was weak. Widened it (derfor, grunnet, pga, som følge av, resultat av, skyld*, før* til, medfør*, årsak*, English words), made it tolerate any whitespace, and made it check `review` too. Tests added.
  - `[low]` `[patch]` (blind) facts.md did not say how later cost is attributed after a Takeover or cut off near the end of the Game. Now documented.
  - `[low]` `[reject]` (blind) `following_weeks` is not tied to the Game settings. It is a placeholder by design and can be reviewed as content; a fix would add parameters.
  - `[false]` `[reject]` (blind) Test coverage lacks scripted occupants and a mid-Game switch. The reference-trace golden Game uses scripted Seats, and the Takeover golden Game switches mid-Game.
  - `[low]` `[patch]` (blind) The `<= {0, 1}` assertion could pass on an empty set. It now also asserts the set is non-empty.
  - `[low]` `[reject]` (blind) `assert_recomputed` mirrors production code. The pure tests use hand-computed numbers, and the AC asks for an independent recompute of the golden Games.
  - `[low]` `[reject]` (blind) Facts are rebuilt per Seat (four reads). The cost is negligible for a founder CLI and a once-per-Seat store.
  - `[false]` `[reject]` (blind) The downgrade deletes `detected_patterns` and `fact_sets`. That is what a downgrade of 0101 must do.
  - `[low]` `[patch]` (blind) Docs lagged. The content `__main__` now lists `detected_patterns`, the `_moments` docstring matches facts.md, and the `matches` docstring explains the shared signature.
  - `[maybe-false]` `[defer]` (edge 1) Old-version rows are returned forever. Same root cause as blind 1; grouped and deferred.
  - `[medium]` `[patch]` (edge 2) An incomplete log or a missing pinned version gave a 500. Same fix as blind 2.
  - `[low]` `[patch]` (edge 3) The CLI caught neither error. Fixed by the same mapping to ViewError.
  - `[maybe-false]` `[patch]` (edge 4) Thresholds had no validators. Same fix as blind 5.
  - `[low]` `[patch]` (edge 5) `_CAUSE` missed words. Same fix as blind 6.
  - `[low]` `[patch]` (edge 6) The `_moments` docstring did not say "exactly three". Docstring aligned, and `assert MOMENTS <= MIN_STUDENT_ORDERS` added.
  - `[false]` `[reject]` (edge 7) Two first calls straddling a publish. The insert is ON CONFLICT DO NOTHING, so both calls return the one stored row.
  - `[false]` `[reject]` (edge 8) The spec names FactsError and detect(). The fix would edit this build's spec. The code uses `ViewError` and `matches()`; this is noted under Auto Run Result.

## Design Notes

Pattern rules for a Seat's row in Week t (skip `decided_by = guided`; `inc` = incoming order, `seen` = `state_seen`):
- `surge-after-shortage` (mechanism `demand_information_lost`): backlog > 0 in Week t or one of the `lookback_weeks` before, and `order ≥ min_ratio·inc` and `order − inc ≥ min_excess`.
- `large-order-full-supply-line` (`supply_line`): `order ≥ min_ratio·inc`, `order − inc ≥ min_excess`, `supply_line ≥ min_cover_weeks·max(inc,1)`.
- `low-after-overshoot` (`delay`): `order ≤ max_ratio·inc`, `inc − order ≥ min_shortfall`, `inventory ≥ min_cover_weeks·max(inc,1)`.
Later cost = the Seat's `week_cost` summed over Weeks t+1..t+`following_weeks` that exist (with `later_weeks` counted). Moments (≥ 10 student Orders only): student Weeks with a pattern, by later cost desc then Week; fill to 3 by |order − inc| desc, later cost desc, Week; output by Week.

Decisions taken for the founder: one record kind holding all three patterns (one pinned "pattern version"); `fact_sets` unique per `(game_id, seat_id)`, never rebuilt; the CLI computes without storing; `games` may import `content.service`.

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis tests/games/test_facts.py tests/content tests/test_imports.py` -- expected: pass
- `uv run pytest -n0 tests/analysis --cov=app.analysis --cov-branch --cov-report=term-missing` -- expected: facts/patterns at or near 100 %
- full `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` (if configured) -- expected: pass

## Auto Run Result

Status: done

**Summary.** A pure `analysis.facts(decision_log, seat, pattern_definitions)` builds one facts set per Seat. The chain part is identical for all Seats. The Seat part holds the Detected pattern occurrences (`<pattern>:<role>:<week>`) and the own moments. The three Detected patterns are one immutable content kind, `detected_patterns`. Version 1 holds placeholder thresholds marked "to be reviewed by two lecturers before pilot", and `sessions.lock` pins it through `register_pin_provider`. `games.facts.get_or_create` stores each set once in `fact_sets`. `python -m app.sim facts <id>` prints the sets for simulation Games.

**Files.**
- `backend/app/analysis/patterns.py`, `facts.py`, `facts.md`: the pattern schema and rules, the facts function, and the documented rules.
- `backend/app/modules/content/{models,schemas,service,__main__,README}`: the new kind, the pin provider, and `pinned_version(pins, kind)`.
- `backend/migrations/versions/0101_fact_sets_and_detected_patterns.py`: the kind check, the version-1 record, and `fact_sets` with an UPDATE trigger (down_revision 0050).
- `backend/app/modules/games/{models,repo,facts}.py`: the table, the SQL, and `compute` / `get_or_create`.
- `backend/app/modules/sessions/service.py` registers the pin. `backend/app/sim.py` adds the `facts` subcommand.
- Tests: `tests/analysis/test_facts.py`, `test_patterns.py`, `tests/games/test_facts.py` and `tests/golden/facts/*.json`. Updated: `test_imports.py`, `test_migrations.py`, `content/test_content.py`, `sessions/test_lock.py`.

**Deviations from the spec text.**
- Refusals use the existing `games.views.ViewError` instead of a new `FactsError`. Codes: `game_not_found`, `game_not_finished`, `seat_not_found`, `facts_unavailable`, `not_simulation`.
- Patterns expose `matches(...)` instead of `detect(...)`.
- The CLI tests are in `tests/games/test_facts.py`, not `test_sim.py`.
- The builder implemented the code in its own context, as the orchestrator instructed, instead of a step-03 subagent.

**Review.** 22 findings, triaged as follows:
- Patched: 12 (3 medium, 8 low, 1 maybe-false), including grouped duplicates.
- Deferred: 2, with one root cause (a versioned reader for a future ANALYSIS_VERSION).
- Rejected: 8, with reasons in the triage log.

followup_review_recommended: false. No high finding was patched, and new tests cover the medium patches.

**Verification.**
- Full backend suite: 2856 passed in 71.6 s. Ruff check and format are clean.
- Branch coverage of `facts.py` and `patterns.py` is 100 %. The migration round-trip test passes.
- Frontend typecheck, `lint:colours`, Vitest (713 tests) and `next build` pass.
- Playwright on the lane stack: `homes`, `order-confirm` (axe at 320, 360 and 1440 px), `game-end` and `week-advance`, 42 passed.
- `python -m app.sim facts` ran end to end on a simulation Game against the lane database.

Tests over 1 s:
- `test_the_fully_rule_based_golden_facts`, about 7–8 s. It plays the shared Classic Game, which is played once per run and reused by other tests.
- `test_the_takeover_golden_facts`, about 1.9 s, for the first play of a 16-Week Class game.
- `test_the_reference_trace_golden_facts`, about 1.1 s.

**Residual risks.** The placeholder thresholds and the moment rule are decisions taken on the founder's behalf and await review by lecturers. A reader for future analysis versions is deferred.
