---
title: 'Story 2.10: Switch a drifting LLM Seat to a Rule-based player with the Play guard'
type: 'feature'
created: '2026-11-18'
baseline_revision: 'ee894ce4ab57f776461920a61c9a764ac44192ca'
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

**Problem:** An LLM player that orders erratically, or suspiciously near-optimally, keeps its Seat for the whole Game. Nothing compares its Orders with the two references stored on every turn (Rule-based, near-optimal from Story 2.9) (FR-79).

**Approach:** Add a pure Play guard `analysis.play_guard` (`evaluate`, `is_calibrated`) whose band parameters are one versioned placeholder parameter set (issue #20). Freeze the set's id and version in the Game snapshot. Run the guard in `place_order` for every `decided_by = llm` Order. On `switch`, append a `rule_based` / `guard_switch` occupancy row from the next Week.

## Boundaries & Constraints

**Always:**
- `backend/app/analysis/play_guard.py` imports only the stdlib, pydantic and `app.engine`. It does no I/O and reads no clock. It defines:
  - `PlayGuardParams` (frozen). Fields: `id`, `version`, `verified`, `source`, `distance` (`Literal["absolute_units"]`: |Order − reference| in units), `window_weeks` ≥1, `minimum_weeks` ≥1, `lower_distance` ≥0, `lower_share` (0..1), `upper_margin` (0..1), `large_distance` ≥0, and `calibrated_profiles: dict[name, GameSettings]` (at least one entry).
  - `parse_params(text, set_id)`, the same rules as `rule_based.parse_params`.
  - `GuardRow` with fields `week`, `order`, `decided_by: str`, `rule_based_reference_order`, `near_optimal_reference_order: int | None`.
  - `GuardResult` with fields `decision` (`within_band` | `switch`), `statistic` (`lower_share` | `upper_closeness` | `large_deviation` | None, the cause of a switch), `value` (the cause's value), `llm_weeks`, `lower_share`, `upper_closeness` (each Decimal | None).
- `evaluate(seat_weeks, params, *, calibrated=True)` works as follows:
  - It keeps only rows with `decided_by == "llm"`, sorted by Week.
  - With fewer rows than `minimum_weeks` it returns `within_band` with no statistics.
  - The window is the last `window_weeks` of those rows.
  - **Lower limit:** `lower_share` is the share of window rows with distance to the Rule-based reference ≤ `lower_distance`. When `calibrated` is false, `large_distance` is used instead and the cause is `large_deviation`. If the share is below `params.lower_share`, the result is `switch`.
  - **Upper limit** (only when `calibrated`): over window rows where the near-optimal reference is set and differs from the Rule-based one, `upper_closeness` is the mean of |Order − NO| / |RB − NO|. If it is below `upper_margin`, the result is `switch`. With no such rows the limit is not applied.
  - The lower limit is checked first.
- `is_calibrated(settings, params)` is true iff `settings` minus `demand_seed` equals some profile minus `demand_seed` (python-mode dump).
- The set file is `backend/app/parameter_sets/play_guard/placeholder-0.json`, version 1, `verified: false`, with a source text that names issue #20. It holds the placeholders `absolute_units`, window 8, minimum 8, lower distance 4, lower share 0.95, upper margin 0.05, large distance 16, and one profile, `classic` (`GameSettings()` without seed). Document it in `backend/app/analysis/play_guard.md`.
- `SessionRuntime` gets `play_guard_params: str | None` and `play_guard_params_version: int | None`. Both are set together. They are None only on Games created before this story, and the guard does not run for those Games.
- `commands.create` takes `play_guard_params: str = DEFAULT_PLAY_GUARD_SET` and refuses an unknown or invalid set with `unknown_parameter_set` / `invalid_parameter_set` (422). The default constant lives in `games.commands`, not in `analysis`, so a new set or profile needs no change in `analysis`.
- `_snapshot` refuses a Game whose frozen guard set version differs from the file with `parameter_set_changed` (409). This matches the Rule-based precedent.
- In `_place`, after `insert_seat_week` and before any advance, when `decider is LLM` and the Game has a guard set:
  - Read the Seat's `seat_weeks` rows through the new `repo.seat_guard_rows`, which includes the new row.
  - Evaluate with `calibrated = is_calibrated(settings, params)`.
  - On `switch`, append an occupancy row (`rule_based`, `policy_id` None, reason `guard_switch`, `from_week = week + 1`) and log `play_guard_switched` with the statistic and value.
- A read surface `views.occupancy_history(game_id)`, exported in `games.service`, returns `OccupancyRow`s (`role`, `seat_id`, `from_week`, `occupant_kind`, `policy_id`, `reason`), by Seat position and then row id.

**Never:**
- No guard call in `players.jobs`, `players.service` or the rescue loop.
- No migration: JSONB runtime and the `guard_switch` reason already exist.
- No change to `SeatState`, `PendingTurn`, the prompt, rule-based outputs or golden files.
- No sim export columns (Story 2.11).
- No `replay_default` profile (Story 10.1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Too few | 7 `llm` rows far off, minimum 8 | `within_band`, statistic None | — |
| Non-llm rows | 20 guided/rule_based/scripted rows far off + 7 `llm` within | `within_band` (only 7 counted) | — |
| Far above | 8 `llm` rows at RB+20 | `switch`, `lower_share`, value 0 | — |
| One outlier | 7 within + 1 off in the window of 8 | `switch` (0.875 < 0.95) | — |
| Window rolls | old outliers outside the last 8 | `within_band` | — |
| Near-optimal hugger | Order = NO, refs differ but within 4 | `switch`, `upper_closeness` 0 | — |
| Coinciding weeks | Order = RB = NO every Week | `within_band`, `upper_closeness` None | — |
| At RB | Order = RB, refs differ | `within_band`, `upper_closeness` 1 | — |
| Uncalibrated | Order = NO (within 4 of RB), `calibrated=False` | `within_band` (no upper limit) | — |
| Uncalibrated, large | Orders RB+20, `calibrated=False` | `switch`, `large_deviation` | — |
| Uncalibrated, moderate | Orders RB+10, `calibrated=False` | `within_band` | — |
| Profiles | Classic (any seed) / Classic with another delay / a set that adds a `replay_default`-like profile | True / False / True for that profile | — |
| Bad set | wrong id, no profiles, share > 1 | — | `ValueError` / `ValidationError` |

</intent-contract>

## Code Map

- `backend/app/analysis/__init__.py` -- empty package (spine: Play guard statistics live here, pure).
- `backend/app/engine/rule_based.py` -- pattern for `Params` + `parse_params`; `backend/app/platform/parameter_sets.py` `read_parameter_set(kind, id)`; `app/parameter_sets/rule_based/placeholder-unverified.json`.
- `backend/app/modules/games/commands.py` -- `_rule_based_params` (:138) pattern for loading a set with CommandErrors; `create` (:159) builds `SessionRuntime`; `_snapshot` (:345); `_place` (:624): `insert_seat_week` (:680), then advance (:705); `switch_to_rule_based` (:827) shows the occupancy row shape.
- `backend/app/modules/games/schemas.py` -- `SessionRuntime` (:83, extra forbid, validator pattern), `OccupancyReason.GUARD_SWITCH` exists.
- `backend/app/modules/games/repo.py` -- `append_occupancy` (:72), `occupancy_in_force` (:182), `decision_log` (:225) query pattern; `models.seat_occupancy`.
- `backend/app/modules/games/views.py` `decision_log` (:136) pattern; `service.py` `__all__`.
- `backend/app/modules/players/llm.py:200` `request_inputs` -- mock answer = Rule-based reference; tests patch it to script the mock player.
- Tests: `tests/players/test_llm_jobs.py` (`llm_game`, `rows`, `jobs.run_until_idle`), `tests/games/helpers.py` (`query`, `execute`), `tests/games/test_create.py:56` runtime dict, `tests/games/test_start.py:166` changed-set refusal, `tests/engine/test_purity.py` (import scan pattern), `tests/test_parameter_sets.py`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/play_guard.py`, `play_guard.md`, `analysis/__init__.py` docstring -- the pure guard and its description.
- `backend/app/parameter_sets/play_guard/placeholder-0.json` -- placeholder set.
- `backend/app/modules/games/schemas.py` -- runtime fields + validator; `OccupancyRow`.
- `backend/app/modules/games/commands.py` -- load/freeze in `create`, check in `_snapshot`, run in `_place`.
- `backend/app/modules/games/repo.py`, `views.py`, `service.py` -- `seat_guard_rows`, `occupancy_history`.
- `backend/tests/analysis/__init__.py`, `test_play_guard.py` (new) -- every matrix row, the shipped set parses, the Classic profile equals `GameSettings()`, and the purity import scan of `app/analysis`.
- `backend/tests/games/test_play_guard_switch.py` (new) -- integration through the real job + mock gateway path, with `llm.request_inputs` patched to script the answer:
  - Three Classic simulation Games, retailer `llm`, scripted far above / at the near-optimal reference / at the Rule-based reference. The first two switch at the minimum Weeks: occupancy `guard_switch` with `from_week` = guided + 8 + 1, and later rows are `rule_based`, `reason = guard_switch`, with no further LLM calls. The third has no switch.
  - A refused changed set version.
  - The runtime has the set id and version.
  - The job module has no guard import.
- `backend/tests/games/test_create.py`, `test_start.py` -- runtime dict; unknown guard set refused.

**Acceptance Criteria:**
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, and any new test over 1 s is reported.
- Given a guard-switched Seat, when `occupancy_history` is read, then its `guard_switch` row's `from_week` is the Week after the switch-causing Order, and every Decision log row from then on has `occupant_kind = rule_based` and `reason = guard_switch`.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 26 findings: high 0, medium 1, low 14, false 11, maybe-false 0
- findings:
  - `[low]` `[reject]` (intent A2) `evaluate` takes a `calibrated` keyword and the caller combines it with `is_calibrated`. That keeps the AC's call `evaluate(seat_weeks, params)` valid. `place_order` always passes the flag, and a test checks it is `True` on calibrated settings.
  - `[false]` `[reject]` (intent D) the guard runs inside the job's `place_order` call. The AC places the guard in `place_order`, and the spine (AD-5) says the job "never runs the Play guard" meaning its own code. Both hold.
  - `[medium]` `[patch]` (intent E2, verification gap 1, blind 4) the upper limit is never reached through `place_order`: the integration near-optimal player switches on `lower_share`, and a dropped near-optimal column would pass every test. Added `test_place_order_feeds_the_guard_the_stored_references`. It spies `evaluate` in a real Game and asserts it gets every LLM row with both stored references (some differing, none None) and `calibrated=True`. The upper limit itself is unit-tested.
    - A scripted "clamped near-optimal" player was tried first. It stayed in the band under the placeholders, so it could not show an upper switch.
  - `[low]` `[reject]` (intent E1, edge 3) the three Games run on Classic cut to 10 Weeks, made calibrated by a test profile, not on a 36-Week Classic Game. Founder rule that tests must be fast: about 2 s per Game here, against about 7 s each on Classic. The shipped `classic` profile is pinned by unit tests: it equals `GameSettings()`, and `is_calibrated(GameSettings())` is true.
  - `[low]` `[reject]` (intent E3) the tests drive Games through `commands` and `jobs.run_until_idle`, not the `sim` CLI. Both are the same job and gateway path. `sim` reporting of switches is Story 2.11.
  - `[low]` `[reject]` (intent G, blind 13) the switch has no HTTP or export surface and its statistic is not stored on the row. Epic 2 has no API screens. The service read gives the Week, and the log line gives the statistic.
  - `[false]` `[reject]` (blind 1) a Seat can be switched twice. After a switch from `week+1`, `_check_llm` refuses any later `llm` Order, because the occupancy in force is `rule_based`. A second Order for the same Week gets `order_exists`.
  - `[low]` `[patch]` (blind 2, verification other 1, edge 1) the `placed_directly` break condition was dead or wrong. It now stops when the turn is already ordered.
  - `[low]` `[patch]` (blind 3, verification other 2) a switch on the last Week writes `from_week = weeks + 1`. This is deliberate and mirrors `switch_to_rule_based`. It is now documented in `play_guard.md`.
  - `[low]` `[reject]` (blind 5) `calibrated` defaults to True. See intent A2.
  - `[low]` `[reject]` (blind 6) no cross-field checks such as `large_distance >= lower_distance`. These are placeholders (issue #20), and the guard is still well-defined without them.
  - `[low]` `[reject]` (blind 7) the set file is read twice on an LLM Order. That is one small file, matching the Rule-based set, which is also read per command.
  - `[low]` `[reject]` (blind 8) a version bump refuses Games without LLM Seats. This is deliberate under AD-4, as for the Rule-based set. `play_guard.md` says a changed version is refused.
  - `[low]` `[patch]` (blind 9) Weeks with no near-optimal reference were undocumented. Documented in `play_guard.md`.
  - `[false]` `[reject]` (blind 10) ordering by occupancy id is wrong. Ids are UUIDv7, and `models.seat_occupancy` defines "latest by id" as the current occupant.
  - `[low]` `[reject]` (blind 11) `GuardRow.decided_by` is a plain `str`. `commands` passes the stored value, which a DB check constrains to `DecidedBy`.
  - `[false]` `[reject]` (blind 12) the profile can go stale silently. `test_the_shipped_set_is_a_marked_placeholder` asserts `classic == GameSettings()`, so it fails on any default change.
  - `[low]` `[reject]` (blind 14) the invalid-set test is async and does not test an id mismatch. The id mismatch is covered by `test_a_set_must_hold_the_id_asked_for`. Being async is harmless.
  - `[false]` `[reject]` (blind 15) the spec is missing from the diff. That is deliberate: the spec goes to the edge-case layer as the claims file.
  - `[low]` `[patch]` (edge 2) the job scan used a non-recursive glob. Now `rglob`.
  - `[false]` `[reject]` (edge 4) `test_start.py` has no guard refusal. The refusals are in `test_play_guard_switch.py`. The spec task named the file loosely, and coverage exists.
  - `[false]` `[reject]` (intent B) the reading of the upper limit is B1. This is recorded in Design Notes as a decision taken in place of the founder.
  - `[false]` `[reject]` (intent C) the reading of uncalibrated settings is C1. Recorded in Design Notes.
  - `[false]` `[reject]` (intent F) the snapshot is `SessionRuntime`, which matches both readings.
  - `[false]` `[reject]` (intent "stays Rule-based") this holds through append-only occupancy, and the later Weeks are checked in tests.
  - `[false]` `[reject]` (intent additions) Games from before 2.10 are not guarded, and there is a `create` parameter and refusals. These are the spec's own rules, tested.

## Design Notes

These are readings of FR-79 under issue #20, taken in place of the founder.
- **Upper limit.** "On average no closer to the near-optimal reference than a margin of 5%" is read as a normalised closeness: per Week where the references differ, the LLM Order's distance to near-optimal divided by the gap between the references (0 = at near-optimal, 1 = at Rule-based). The mean must stay ≥ 0.05.
- **Uncalibrated settings.** The lower limit is kept, with the larger `large_distance`.
- **Minimum Weeks** counts all `llm` Orders of the Seat. The window is the newest `window_weeks` of them.
- **A switch in the last Week** still appends its row (`from_week = weeks + 1`), so the switch is recorded.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/analysis tests/games/test_play_guard_switch.py tests/games/test_create.py tests/games/test_start.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100 --durations=10` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:** `place_order` now runs the Play guard on every `decided_by = llm` Order, in the same transaction. A Seat whose LLM player leaves the band gets one appended occupancy row (`rule_based`, reason `guard_switch`, `from_week = week + 1`) and stays Rule-based for the rest of the Game.
- `analysis.play_guard.evaluate(seat_weeks, params, *, calibrated)`: pure. It reads only `llm` rows and never switches below the minimum Weeks. Over a rolling window it checks:
  - the lower limit: share of Orders within a distance of the Rule-based reference;
  - the upper limit: mean normalised closeness to the near-optimal reference over Weeks where the references differ.
  - On uncalibrated settings only a large deviation switches.
- `is_calibrated(settings, params)` matches the set's named settings profiles (`classic` only), ignoring the seed.
- Parameters are the versioned placeholder set `app/parameter_sets/play_guard/placeholder-0.json` (issue #20). A Game freezes its id and version in `SessionRuntime`, and a changed version is refused (`parameter_set_changed`).
- New read: `games.service.occupancy_history(game_id)` gives the switch Week.
- No migration.

**Files:**
- `backend/app/analysis/play_guard.py` and `play_guard.md` (new): the pure guard and its placeholder description.
- `backend/app/analysis/__init__.py`: docstring.
- `backend/app/parameter_sets/play_guard/placeholder-0.json` (new): the set.
- `backend/app/modules/games/commands.py`: freeze in `create`, check in `_snapshot`, `_run_play_guard` in `_place`.
- `schemas.py`: `SessionRuntime` fields and `OccupancyRow`.
- `repo.py`, `views.py`, `service.py`: `seat_guard_rows` and `occupancy_history`.
- Tests:
  - `tests/analysis/test_play_guard.py` (new): matrix, set, profiles, purity.
  - `tests/games/test_play_guard_switch.py` (new): three scripted mock LLM players through the real job and gateway path, uncalibrated settings, Games from before 2.10, refusals, guard input wiring, no guard in the job.
  - `tests/games/test_create.py`: runtime dict.
  - `tests/test_sim.py`: a monkeypatch now redirects only the Rule-based set.

**Review:** one pass, 4 layers, 26 findings (medium 1, low 14, false 11).
- Patched:
  - A test that `place_order` feeds the guard both stored references and the calibration flag (medium).
  - The test driver's break condition.
  - The recursive scan of `players`.
  - Docs for the last-Week switch and for missing near-optimal references.
- Nothing deferred.
- Rejected with reasons in the triage log. Notably, the three-Game test runs on 10-Week Classic made calibrated by a test profile, not on 36-Week Classic: about 2 s against about 7 s per Game, under the founder's fast-test rule.

**Follow-up review recommended:** false. Patched entries: medium 1, low 4.

**Verification:**
- ruff check and format: clean.
- Full suite with coverage: 1449 passed in 60 s. Engine and analysis coverage 100 %. Golden outputs unchanged.
- Every matrix row is covered by a passing unit test.
- New tests over 1 s (with `-n0`):
  - `test_three_scripted_llm_players` [far-above / near-optimal / within-band]: about 2.2 to 2.4 s each.
  - `test_uncalibrated_settings_apply_only_the_large_deviation`: about 2.7 s, two Games.
  - `test_a_game_from_before_the_guard_is_not_guarded` and `test_place_order_feeds_the_guard_the_stored_references`: about 1.3 s each.
  - Each plays a 10-Week Game. The `ai-orders` job path costs about 0.2 s per LLM Order.

**Decisions taken in place of the founder (issue #20 placeholders):**
1. Parameter set `placeholder-0` v1, `verified: false`: distance `absolute_units`, window 8, minimum 8, lower distance 4 units, lower share 0.95, upper margin 0.05, large distance 16 units, one profile `classic` (= `GameSettings()` without seed).
2. Upper limit = mean of |Order − NO| / |RB − NO| over window Weeks where NO ≠ RB, which must be ≥ 0.05. Weeks with no stored NO do not count.
3. Uncalibrated settings: no upper limit, and the lower limit uses the large distance (statistic `large_deviation`). "Calibrated" means exact equality with a profile, the seed aside, so a Classic Game with any changed setting (Weeks, Guided Weeks, capacity) is uncalibrated.
4. The minimum counts all `llm` Orders of the Seat. The lower limit is checked before the upper one.
5. The set id and version are frozen in `SessionRuntime`. A changed version refuses every command of that Game, as for the Rule-based set. Games created before 2.10 have no set and are not guarded. The default set id lives in `games.commands`, so a new set or profile needs no change in `analysis`.
6. A switch caused by the last Week's Order is still recorded (`from_week` = Weeks + 1).
7. With these placeholders a player ordering exactly the near-optimal reference is usually caught first by the lower limit, because NO and RB differ by more than 4 units. The upper limit then catches only a player that is close to NO where the references are close.
8. The implementation ran in the orchestrating session, not a fresh subagent (runbook constraint). The reviews ran as independent subagents.

**Residual risks:**
- All band values are uncalibrated placeholders (issue #20). Real LLM players may be switched often with a window of 8 and 95 %, since one Order off by more than 4 switches the Seat.
- No migration, so the shared test databases were not changed.
- CI has not run. Nothing is pushed.
