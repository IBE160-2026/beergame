---
title: 'Story 1.10: Verify every finished Game by replaying it'
type: 'feature'
created: '2026-11-17'
baseline_revision: 'c070f1232a0b4552812a06aa40e79ef395195579'
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

**Problem:** A finished Game's stored numbers (Week states, Orders, costs) are never checked, and the engine has one hard-wired rules version, so a later rules change could silently break replay of stored Games (AD-4, AD-9, FR-29, NFR-9).

**Approach:** Make each rules version its own package `engine/rules/v<N>/` selected by `rules_version`; add a pure `engine.replay`; add `games.service.verify_finished(game_id)` that replays + runs `engine.check.conservation` + checks the Decision log, and writes one immutable `game_checks` row (Alembic `0005`); the sim runner calls it after `play` and via `sim check`.

## Boundaries & Constraints

**Always:**
- `app/engine/rules/__init__.py`: `RULES_VERSION = 1` (moved here, re-exported by `app.engine`), `versions()` (packaged versions found on disk, sorted), `package(n)` (imports `app.engine.rules.v<n>`; raises `UnknownRulesVersionError` for a non-int/bool, `< 1` or missing package; re-raises a `ModuleNotFoundError` for any other module), `has_version(n)`. `rules/v1/__init__.py` holds today's `week.py` arithmetic unchanged. `engine.week.initial_state(settings, rules_version=RULES_VERSION)` and `advance(settings, state, orders, rules_version=RULES_VERSION)` dispatch to the package. `GameFinishedError`, `InvalidOrdersError`, `UnknownRulesVersionError` live in `app/engine/errors.py` and keep their `app.engine` / `app.engine.week` import paths.
- `engine.replay.replay(settings, states, orders, rules_version) -> tuple[Violation, ...]`: pure, never raises. Rebuilds from `initial_state` with the given Orders and compares each replayed state with the stored one at the same index; rule `replay` with `week` and `role` (role None for Week-level / count mismatches) and the differing field names, expected (replayed) and actual (stored) values. An unknown version → one `rules_version` violation. An engine `ValueError` (e.g. `InvalidOrdersError`) → one `replay` violation at that Week (role when it names a Role) and the replay stops.
- `verify_finished(game_id: str) -> GameCheck` (in `modules/games/checks.py`, re-exported by `service`): one transaction; returns the stored row if `game_checks` has one for the Game (idempotent, no log). Otherwise: refuses `game_not_found` 404 (bad/unknown id), `game_not_finished` 409, `rules_version_unsupported` 409 (no package) with `ViewError`, writing nothing. Then collects, without raising: `snapshot` (settings fail to validate, or stored `demand_series` ≠ the series from the settings), `stored_state` (a `game_weeks` row fails `WeekState` validation; stops further rules), `engine.replay` at the Game's stored `rules_version`, `engine.check.conservation` over the stored states and stored Orders, and `decision_log` (each `seat_weeks.state_seen` must equal `build_seat_state` over the stored states/Orders for that Week and Role; run only when conservation has no shape-rule violation).
- `game_checks`: `id` UUIDv7 PK, `game_id` FK unique, `rules_version` int, `ok` bool, `violations` JSONB list of `Violation` JSON, `checked_at` timestamptz default `now()`; CHECK `ok = (jsonb_array_length(violations) = 0)`; append-only trigger (UPDATE/DELETE refused). Insert with `ON CONFLICT (game_id) DO NOTHING`; on conflict return the stored row.
- With violations: exactly one structlog `error` line `game_check_failed` with `game_id`, `check_id`, `violation_count` only (allowlist gains `check_id`, `violation_count`); else one `info` line `game_check_passed`. The check never writes a Games/Seats/turns/Week/Decision-log row, never bumps `version`, never emits an event.
- Commands use the Game's stored `rules_version`: `_snapshot` refuses only a version with no package; `start`/`place_order` pass it to `initial_state`/`advance`; `create` stores `RULES_VERSION`.
- `games.service.rules_versions_without_package() -> tuple[int, ...]` (distinct stored `rules_version`s with no package).
- `app/engine/RULES_VERSIONS.md` records the decision (AC wording) plus: the conservation check, demand series, Rule-based player and views are not versioned yet; a version that changes them adds its own then.
- Golden traces run per version: `tests/engine/test_golden.py` maps version → trace files; a test fails when a packaged version has no traces. `test_purity.py` scans engine files recursively. Engine + `tests/engine` 100 % branch coverage; ruff clean; all tests pass.

**Never:** No change to v1 arithmetic or any golden file; no batch runner, jobs, `ops.sweep` or HTTP route (1.11, 3.x); no ORM classes; no new dependency; no update of a `game_checks` row.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean Game | Classic seed 7 played by `sim play` | `ok`, `violations ()`, `rules_version 1`, one row with `checked_at`; Game version unchanged; no event | — |
| Twice | second call | same `GameCheck` (same id), still one row; concurrent calls → one row | — |
| Tampered Week state | `game_weeks` Week 10 retailer inventory +1 (trigger bypassed in test) | `ok false`: `replay` (10, retailer) + conservation rules; one error log line, ids only; Game rows unchanged | — |
| Tampered Order | `seat_weeks` Week 7 wholesaler order changed | `replay` violations from Week 8 | — |
| Tampered cost | Week state `cost` / `state_seen.week_cost` changed | `replay` + `cost` / `decision_log` at that Week and Role | — |
| Unfinished / unknown | running Game; bad or unknown id | nothing written | `game_not_finished` 409; `game_not_found` 404 |
| No package | stored `rules_version 99` | nothing written | `rules_version_unsupported` 409 |
| Throwaway v2 | test module `app.engine.rules.v2` (one changed rule) in `sys.modules`; Game A, B finished under v1, B's `rules_version` set to 2 | A ok; B `ok false` with `replay` violations, row `rules_version 2` | — |
| Sim | `sim play <id>` | after `weeks 36` prints `check ok`; `sim check <id>` prints `check ok` / `check failed N` + one `violation <rule> week <w> role <r>` line each | failed → exit 1; refusal → `error <code>: …`, exit 1 |

</intent-contract>

## Code Map

- `backend/app/engine/week.py` -- current arithmetic (`initial_state`, `advance`, `_check_orders`, `_open_week`, `_Carry`): move to `rules/v1/__init__.py`, keep dispatchers here.
- `backend/app/engine/__init__.py` -- `RULES_VERSION` (L49) moves to `rules`; export `replay`, `UnknownRulesVersionError`, `rules`.
- `backend/app/engine/check.py` -- `Violation` (L58), `conservation` (L71); shape rule names `states_shape`, `week_sequence`, `seat_shape`, `orders_shape`, `demand_series`.
- `backend/app/modules/games/commands.py` -- `_snapshot` (L260: version test), `start` (L332 `initial_state`), `place_order` (L433 `advance`).
- `backend/app/modules/games/repo.py` -- `get_game`, `week_states` (L115, rows ordered with finished last), `decision_log` (L200); add `game_check`, `insert_game_check`, `stored_rules_versions`, `week_rows` (week + finished + state).
- `backend/app/modules/games/views.py` -- `build_seat_state` (L32), `stored_orders` (L77), `ViewError`.
- `backend/app/modules/games/models.py`, `schemas.py`, `service.py` -- add `game_checks`, `GameCheck`, re-exports.
- `backend/app/platform/logging.py` -- `ALLOWED_FIELDS`.
- `backend/migrations/versions/0004_seat_weeks.py` -- `_append_only` pattern for `0005`.
- `backend/app/sim.py` -- `_play_game` (L456), `_report`, `build_parser`, docstring.
- Tests: `tests/conftest.py` (TRUNCATE list), `tests/test_migrations.py` (HEAD_TABLES, `0005`, downgrade to `0004`), `tests/engine/test_golden.py`, `test_purity.py`, `tests/games/helpers.py` (`play_to_end`, `query`, `execute`, `listening`), `tests/games/test_start.py` (L146 version 99 case), `tests/test_sim.py` (`played_game`, `report`).

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/errors.py`, `rules/__init__.py`, `rules/v1/__init__.py`, `week.py`, `replay.py`, `__init__.py`, `RULES_VERSIONS.md` -- versioned rules + replay as in Boundaries.
- `backend/migrations/versions/0005_game_checks.py` + `models.py` -- table, CHECK, unique, trigger; downgrade drops them.
- `backend/app/modules/games/schemas.py`, `repo.py`, `checks.py` (new), `service.py`, `commands.py` -- `GameCheck`, `verify_finished`, `rules_versions_without_package`, versioned commands.
- `backend/app/platform/logging.py` -- allow `check_id`, `violation_count`.
- `backend/app/sim.py` -- `play` verifies at the end; `check <game_id>` subcommand; docstring.
- `backend/tests/engine/test_rules.py`, `test_replay.py` (new) -- dispatch, errors, every replay branch.
- `backend/tests/games/test_verify.py` (new) -- every matrix row, ids-only error log (`structlog.testing.capture_logs`), Game unchanged, `game_checks` append-only, rules versions in DB have packages.
- Update `test_golden.py`, `test_purity.py`, `conftest.py`, `test_migrations.py`, `test_sim.py`, `test_logging.py` if it pins the allowlist.

**Acceptance Criteria:**
- Given a Classic Game created with seed 7 and played by `sim play`, when `sim check <id>` runs twice, then both print `check ok`, exit 0, and `game_checks` holds one row with `ok = true`, `rules_version = 1`.
- Given the CI commands run locally, when they finish, then all tests pass, `app/engine` + `tests/engine` branch coverage is 100 %, ruff check/format clean.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 29 findings — high 0, medium 0, low 13, false 16, maybe-false 0
- findings:
  - `[low]` `[patch]` (verification-gap) no test shows `start`/`place_order` run a stored non-default `rules_version` — added `test_commands_run_the_stored_rules_version` (fake v2 doubling cost, Game stored at v2 before `start`; stored costs are doubled and the check replays clean at v2).
  - `[low]` `[patch]` (verification-gap) `sim play` exit 1 on a failed check untested — added `test_play_exits_1_when_the_finished_game_check_fails`.
  - `[low]` `[patch]` (blind) engine entry points default to the newest version silently — same root as the first row; the command-level test now pins that commands pass the stored version. The default stays for the engine-only callers (`sim trace`, golden traces).
  - `[low]` `[patch]` (blind) `replay` claims "never raises" but catches only `ValueError` — the contract is now stated in `replay.py` and RULES_VERSIONS.md: a package refuses input only with `ValueError`; anything else is a package bug that propagates.
  - `[low]` `[reject]` (blind) Decision log check ignores `rule_based_reference_order`/`decided_by` — the AC names Week state, Order and cost; recomputing reference Orders adds parameter-set handling for a field the replay does not use.
  - `[low]` `[reject]` (blind) one unreadable state row skips replay/conservation — the check is still recorded as failed with the row's Week; replaying around holes adds branches for a tamper-only state.
  - `[low]` `[reject]` (blind) nothing enforces version freezing beyond golden traces — the AC asks for golden traces per version plus the decision record; a source checksum is extra machinery.
  - `[false]` `[reject]` (blind) policy inconsistent about simulation Games — RULES_VERSIONS.md follows the AC wording (non-simulation); checking simulation Games too is stricter, not contradictory.
  - `[low]` `[reject]` (blind) `sim check` prints rule/Week/Role but not the message — the matrix fixes this line format; the details are stored in `game_checks.violations`.
  - `[false]` `[reject]` (blind) checked Games cannot be deleted; TRUNCATE bypasses trigger — Games are never deleted (seat_weeks/game_weeks are append-only since 1.9); TRUNCATE is test-only, same decision as Story 1.9.
  - `[low]` `[reject]` (blind) `_SHAPE_RULES` duplicates check.py codes — a renamed rule would only let the guarded `_decision_log` run, which catches its own errors; no named harm.
  - `[low]` `[reject]` (blind) `rules` vs `engine_rules` naming in commands — cosmetic.
  - `[low]` `[patch]` (blind) `tamper` imported across test modules — moved to `tests/games/helpers.py`.
  - `[low]` `[reject]` (blind) failure log lacks `rules_version` and rule codes — the AC says ids only; the row holds the details.
  - `[low]` `[patch]` (edge) Orders after the finish were silently ignored by `replay` though the comment said otherwise — now one `replay` violation at the last Week; test updated.
  - `[false]` `[reject]` (edge) `replay` raises on a broken package import — a broken package is a code bug; failing loudly is correct (no reachable state shown).
  - `[false]` `[reject]` (edge) `has_version` re-raises a broken package's `ModuleNotFoundError` — same as above; tested deliberately.
  - `[false]` `[reject]` (edge) a Decision log row whose role is not a Role raises — `seats.role` is written only by `create` from `settings.roles`; unreachable without tampering a table outside the AC.
  - `[false]` `[reject]` (edge) `build_seat_state` could raise TypeError/ArithmeticError on tampered values — states are validated `WeekState`s and the conservation shape rules gate the call; types are guaranteed.
  - `[false]` `[reject]` (edge) a log row for a Week beyond the stored states compares the wrong Week — such a row makes `orders_shape` fire, which skips `_decision_log`.
  - `[false]` `[reject]` (edge) `sim check` crashes on non-ViewError exceptions — those are bugs; same handling as every other sim subcommand.
  - `[false]` `[reject]` (intent) check is not triggered automatically on finish — AC-C: the sim runner calls it, a job later (Story 3.x).
  - `[false]` `[reject]` (intent) throwaway v2 is in memory, not on disk — the AC asks for a test-added throwaway; `package()` resolves it like a real one.
  - `[false]` `[reject]` (intent) stored-version guard passes by construction — the detector is tested with a planted version 99; the guard test runs on Games created in the test DB as the AC states.
  - `[false]` `[reject]` (intent) CI unchanged — CI already runs all of pytest, which now runs every version's traces.
  - `[false]` `[reject]` (intent) replay derives demand from settings — a stored series that differs is recorded as `snapshot`, so the stored series is checked.
  - `[false]` `[reject]` (intent) additions not named in the story — descriptive; each serves an AC (Decision log = altered cost, `sim check` = runner call).
  - `[false]` `[reject]` (intent) `violation_count` is not an id — a number with no personal data, inside the logging convention (ids, codes, numbers).
  - `[false]` `[reject]` (intent) tamper tests bypass triggers — descriptive; that is how an after-the-fact edit is simulated.

## Design Notes

The replay compares against the stored states rather than feeding them back in, so a tampered Week state shows at exactly its Week and Role, and a tampered Order shows from the Week it changes. The Decision log check compares typed `SeatState` models (Decimal by value), so it does not flag JSON formatting. A Game whose stored version has no package is refused rather than recorded, so a job can retry once the package exists, and the immutable row is never a false failure. The throwaway `v2` is injected into `sys.modules` in a test; `package()` resolves through `importlib`, which honours that, while `versions()` (which drives the golden traces) lists real packages only.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-report=term-missing --cov-fail-under=100` -- expected: all pass
- `cd backend && uv run alembic upgrade head && uv run python -m app.sim create --seats rule_based --seed 7`, then `start`, `play`, `check` (twice) -- expected: `check ok`, exit 0

## Auto Run Result

Status: done

**Summary:** Each rules version is now its own package, `engine/rules/v<N>/`; v1 holds the old `week.py` arithmetic unchanged. `engine.initial_state` and `engine.advance` take a `rules_version`, and `start`/`place_order` pass the Game's stored version. The new pure function `engine.replay.replay` rebuilds a Game from its Orders and reports every difference by Week and Role.

`games.service.verify_finished(game_id)` checks a finished Game in four ways:
- It replays the Game at its stored version.
- It runs `engine.check.conservation`.
- It compares each Decision log `state_seen` with the rebuilt `SeatState`.
- It compares the stored settings and demand series with each other.

It writes one append-only `game_checks` row (Alembic `0005`, unique per Game, `ok` CHECK-bound to the violations). A failed check logs one error line, `game_check_failed`, carrying `game_id`, `check_id` and `violation_count`. A second call returns the stored row. The check never changes the Game. It refuses with `game_not_found` (404), `game_not_finished` (409) or `rules_version_unsupported` (409).

`sim play` runs the check after the last Week, and `sim check <id>` runs it or reads it back. The decision is recorded in `backend/app/engine/RULES_VERSIONS.md`.

**Files:**

Engine:
- `app/engine/rules/__init__.py` (new): `RULES_VERSION`, `versions`, `package`, `has_version`.
- `rules/v1/__init__.py`: moved from `week.py`.
- `week.py`: now dispatchers.
- `errors.py` (new).
- `replay.py` (new).
- `RULES_VERSIONS.md` (new).
- `__init__.py`.

Migration: `migrations/versions/0005_game_checks.py`.

Games module:
- `checks.py` (new): `verify_finished`, `rules_versions_without_package`.
- `models.py`, `schemas.py` (`GameCheck`), `repo.py`, `service.py`.
- `commands.py`: uses the stored version.

Other code:
- `platform/logging.py`: allowlist gains `check_id` and `violation_count`.
- `app/sim.py`: `play` runs the check; new `check` subcommand.

Tests:
- New: `tests/engine/test_rules.py`, `test_replay.py`, `tests/games/test_verify.py`.
- Updated: `test_golden.py` (traces per version), `test_purity.py` (recursive), `conftest.py`, `helpers.py` (`tamper`), `test_migrations.py`, `test_sim.py`.

**Review:** one pass, 29 findings (low 13, false 16). Patched (low):
- a command-level test that a stored v2 Game is started and advanced by v2;
- a test that `sim play` exits 1 on a failed check;
- the stated rules-package error contract behind "never raises";
- Orders after the finish are now reported by `replay`;
- `tamper` moved to the shared helpers.

All other findings were rejected; the reasons are in the triage log. Nothing deferred.

**Follow-up review recommended:** false. Patched counts: high 0, medium 0, low 5 entries.

**Verification:**
- `ruff check` and `ruff format --check`: clean.
- `pytest --cov=app/engine --cov=tests/engine --cov-branch --cov-fail-under=100`: 1041 passed, 100 % (local compose Postgres).
- On the dev database: `alembic upgrade head`, then `sim create --seats rule_based --seed 7`, `start`, `play` (`weeks 36`, `check ok`), and `check` twice (`check ok`, exit 0). `game_checks` holds one row: `ok = true`, `rules_version = 1`.
- Matrix audit: every row is covered by a passing test in `test_verify.py`, `test_replay.py` or `test_sim.py`.

**Decisions taken in place of the founder:**
1. The rules-version layout: `engine/rules/v<N>/` packages resolved through `importlib`. `RULES_VERSION` lives in `engine/rules` and is still re-exported. The error types moved to `engine/errors.py`, keeping their old import paths.
2. Commands now accept any packaged `rules_version` (before, only the newest) and run it.
3. A Game whose stored version has no package is refused (`409 rules_version_unsupported`) and nothing is stored, so a later job can retry once the package exists.
4. Extra check rules beyond replay and conservation:
   - `snapshot`: the stored settings or demand series do not match;
   - `stored_state`: an unreadable Week state row;
   - `decision_log`: `state_seen` differs from what the Seat saw.
5. One `game_checks` row per Game (unique `game_id`, `ON CONFLICT DO NOTHING`), immutable through a trigger.
6. The error log carries `game_id`, `check_id` and `violation_count`; the last two were added to the logging allowlist.
7. `sim play` runs the check and exits 1 when it fails; added `sim check`.
8. Golden traces are mapped per version in `test_golden.py`. The stored-version guard is `games.service.rules_versions_without_package`.
9. The throwaway v2 in tests is a module put in `sys.modules`; its one changed rule doubles the cost.
10. The implementation ran in the orchestrating agent's own context (runbook). Review layers were independent subagents.

**Residual risks:**
- TRUNCATE bypasses the append-only triggers (tests only).
- One unreadable Week state row hides the other rules of that Game in its single stored check.
- CI was not run on GitHub (no push).
