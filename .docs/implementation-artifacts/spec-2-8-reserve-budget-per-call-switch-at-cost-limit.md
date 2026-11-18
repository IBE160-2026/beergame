---
title: 'Story 2.8: Reserve budget per call and switch to Rule-based players at the cost limit'
type: 'feature'
created: '2026-11-18'
baseline_revision: '02ed04f2165e00bd3324f8b35f07519681834934'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The worst-case reservation may not cover a real provider's bill if it ignores max_tokens for reasoning or adds input around the request.
    evidence: |-
      maybe-false (blind 4): mock usage stays far below the bound; settle records the true cost and logs
      ai_cost_above_reservation (tested). Settle with a real OpenRouter run comparing usage to the reservation.
    location: >-
      backend/app/ai/gateway.py worst_case
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** The gateway only adds each attempt's cost to `spent` after the attempt, so parallel calls can overspend a scope; nothing keeps the reserve for non-player purposes, nothing switches LLM Seats to Rule-based players at the limit, and there is no cost report (FR-69, AD-5, AD-6, C-3).

**Approach:** Reserve each attempt's worst-case cost with one conditional `UPDATE` on the budget row (player purposes up to `limit − reserve`), settle to the actual cost with the attempt's `llm_call` row; a failed player reservation sets `players_exhausted_at`; the `ai-orders` job then places the fallback Order and `players` switches every `llm` Seat of every unfinished Game charged to the scope; add `ai.budget.state` and `python -m app.ai.cli cost --scope`.

## Boundaries & Constraints

**Always:**
- Alembic `0011` (expand-only): `ai_budgets.reserved_usd NUMERIC(18,8) NOT NULL DEFAULT 0`, check `reserved_usd >= 0`. Downgrade drops it.
- Effort level gets `max_output_tokens: int` (1..1 000 000, default 4096, placeholder issue #8), sent on every request as model setting `max_tokens`; `max_tokens` and `max_completion_tokens` join `RESERVED_PARAMS`.
- Worst case of one attempt = `cost(spec, input_bound, level.max_output_tokens)` with `input_bound` = UTF-8 bytes of `json.dumps(call.request)` + `INPUT_OVERHEAD_TOKENS` (256): a byte-level tokenizer never makes more tokens than bytes.
- `budget.reserve(scope, amount, *, player) -> Reservation | None`: one `UPDATE ai_budgets SET reserved_usd = reserved_usd + :a WHERE scope AND spent_usd + reserved_usd + :a <= (limit_usd − reserve_usd if player else limit_usd) [AND players_exhausted_at IS NULL if player] RETURNING`. Never a sum over `llm_call`. On failure for a player purpose, a second `UPDATE … SET players_exhausted_at = now() WHERE … AND players_exhausted_at IS NULL RETURNING` in the same transaction; when that row returns, after commit log `ai_cost_limit_reached` with `scope_kind`, `scope_id` only.
- `budget.settle(scope, reserved, actual, *, session)`: `reserved_usd -= reserved`, `spent_usd += actual`, in the transaction that writes the attempt's `llm_call` row (replaces `charge`). `budget.release(scope, reserved)` for an attempt with no row (429, or cancelled before the attempt started).
- Gateway per attempt: deadline checks → limiter slot → reserve → attempt → log row + settle. Reservation refused → `Failure("budget_exhausted", ids so far)`. Every reservation is settled or released, also on cancellation (shielded). `_prepare` still refuses at once (no row) when the row is missing (`GatewayError`) or, for a player purpose, `players_exhausted_at` is set.
- `budget.state(scope) -> Budget | None` reports `limit`, `reserve`, `spent`, `reserved`, `players_exhausted_at`.
- Job (`players.jobs`): on fallback `budget_exhausted` it places the reference Order (`fallback = budget_exhausted`) first, then calls `players.service.apply_cost_limit(game_id)` whatever the placing returned; errors there are logged, never raised.
- `players.service.apply_cost_limit(game_id)`: scope from `games.service.budget_scope`; for each running Game from `games.service.games_charged_to(scope)`, `games.commands.switch_to_rule_based(game, seat, "cost_limit")` for every Seat whose latest occupant is `llm`; a Game that finished meanwhile is skipped. Idempotent.
- `games.commands`: while the Game's scope has `players_exhausted_at` set, `assign_seat(..., "llm")` stores `rule_based` with reason `cost_limit`, and `start` appends a `rule_based`/`cost_limit` row (from Week 1) for each `llm` Seat before the first Week opens. `games.service.scope_of(purpose, runtime)` is the one scope rule (used by `budget_scope`).
- `python -m app.ai.cli cost --scope ID [--kind evaluation|class_session]`: prints `budget <kind> <id> limit=… reserve=… spent=… reserved=… players_exhausted_at=…`, `total usd=… calls=N`, one `game <id|-> usd=… calls=N` line per Game in `caller_ref.game` (most expensive first), one `day YYYY-MM-DD usd=… calls=N` per UTC day of `started_at`; sums settled `llm_call.cost_usd` of every outcome. Unknown scope → `error budget_not_found`, exit 1; both kinds exist without `--kind` → `error scope_ambiguous`, exit 1.

**Never:** No Lecturer notice or Admin alert and no `AI_DAILY_ALERT_USD` setting (Epics 3, 15); no reservation rows or tables; no clearing of `players_exhausted_at` (raising the limit keeps it); no change to Rule-based/golden outputs; `players` and `games` import nothing new from `app.ai` beyond today's allowed modules (import test).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Reserve and settle | limit 1, mock answer | one row; `spent` = row cost; `reserved` back to 0 | — |
| Parallel reservations | limit 1, reserve 0, 20 concurrent `reserve(0.1)` | exactly 10 succeed; `spent + reserved` = 1 | — |
| Parallel calls | 8 concurrent `run` (mock, held until all have reserved) on a limit fitting 3 worst cases | exactly 3 reserve; final `spent ≤ limit`, `reserved` 0 | the other 5 `budget_exhausted` |
| Player vs reserve | limit 1, reserve 1 | player: `budget_exhausted`, `players_exhausted_at` set, log line; `recognition_probe`: `Result` | — |
| Spent mid-call | limit fits one worst case; first answer invalid | `Failure("budget_exhausted", (id1,))` | — |
| 429 then ok | `RATE_LIMITED` then ok | `reserved` 0 after; one row | — |
| Cancelled call | cancel during attempt | row `cancelled`; `reserved` 0 | — |
| Job at the limit | 2 running Games on one scope, LLM Seats, limit 0 | week Order `rule_based`/`budget_exhausted`; every `llm` Seat of both Games gets a `cost_limit` occupancy; later Weeks `rule_based`, `fallback none`, no new call | finished Game skipped |
| New occupancy | state set, `assign_seat(llm)` / `start` with an `llm` Seat | occupancy `rule_based`, reason `cost_limit` | — |
| Cost report | rows of 2 Games + a probe row, 2 days | totals per Game (`-` for the probe) and per day; budget line | unknown id → exit 1 |

</intent-contract>

## Code Map

- `backend/app/ai/budget.py` -- `Budget` (+`reserved`), `_row`, `charge` (→ `settle`), new `reserve`, `release`, `state`; log after commit.
- `backend/app/ai/gateway.py:179` `_exhausted` (player state only), `:263` `_prepare`, `:427` `_log` (settle with the reservation), `:472` `run` loop (`:519` mid-call check → per-attempt reservation; 429 branch `:539` releases; cancel path `:533`).
- `backend/app/ai/config.py:60` `EffortLevel` (+`max_output_tokens`), `:71` `RESERVED_PARAMS`.
- `backend/app/ai/adapters.py:79` `model_settings` (+`max_tokens`).
- `backend/app/ai/models.py:59` `budgets` (+`reserved_usd`); `backend/app/ai/calls.py` (+`costs(scope)` aggregate); `backend/app/ai/cli.py` (+`cost`).
- `backend/migrations/versions/0011_ai_reservations.py` (new, `0010` style).
- `backend/app/modules/games/service.py:108` `budget_scope` (→ `scope_of`), new `games_charged_to(scope)`; `repo.py` query on `games.session_runtime->>'model_config_id'`, lifecycle `running`, purpose `simulation`.
- `backend/app/modules/games/commands.py:258` `assign_seat`, `:454` `start` (`cost_limit` occupancy), `:785` `switch_to_rule_based` (used as is).
- `backend/app/modules/players/jobs.py:95` `place_llm_order`; `service.py` new `apply_cost_limit`.
- Tests: `tests/ai/test_budget.py`, `tests/ai/test_gateway.py` (`:292` mid-call test changes meaning; `scope_for`), `tests/ai/test_cli.py`, `tests/ai/test_config.py`, `tests/players/test_llm_jobs.py` (`llm_game`, `rows`, `stored_config`), `tests/test_migrations.py` (`HEAD`), `tests/test_imports.py`; any test asserting `model_settings` / `mock.last_model_settings` gains `max_tokens`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0011_ai_reservations.py`, `backend/app/ai/models.py` -- column and check.
- `backend/app/ai/{config,adapters}.py` -- `max_output_tokens`, `max_tokens` setting, reserved params.
- `backend/app/ai/budget.py` -- reserve/settle/release/state.
- `backend/app/ai/gateway.py` -- per-attempt reservation as above.
- `backend/app/ai/{calls,cli}.py` -- cost aggregate and `cost` command; module docstring.
- `backend/app/modules/games/{service,repo,commands}.py` -- `scope_of`, `games_charged_to`, `cost_limit` occupancy at assign/start.
- `backend/app/modules/players/{service,jobs}.py` -- `apply_cost_limit`, call it after a `budget_exhausted` fallback.
- Tests for every matrix row (new `tests/players/test_cost_limit.py` for the job/switch rows; budget/gateway/cli rows in their files); update migration HEAD and settings asserts. `README.md` -- the `cost` command.

**Acceptance Criteria:**
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, golden outputs are unchanged, and any new test over 1 s is reported.
- Given the import tests, then `app/ai` imports nothing from `app.modules`, and `players`/`games` keep their allowed imports.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 34 findings — high 0, medium 9, low 22, false 2, maybe-false 1
- findings:
  - `[medium]` `[patch]` (blind 1) a failed `llm_call` write rolls back the settle and leaves the reservation held — `_log` now releases it when `_write` raises; test `test_an_unexpected_error_gives_the_reservation_back[_write]`.
  - `[medium]` `[reject]` (blind 2) contention alone can set `players_exhausted_at` — AC 3 prescribes it (a failed player reservation sets the state); recorded as a residual risk.
  - `[low]` `[reject]` (blind 3) stored configs with `max_tokens` in provider params — none exists outside local dev databases; stored rows are read without `_rules` and `model_settings` filters reserved params.
  - `[maybe-false]` `[defer]` (blind 4) worst case may miss provider-side input or reasoning beyond `max_tokens` — settle with a real run; settle above the reservation now has a test.
  - `[medium]` `[patch]` (blind 5) cancel/exception release paths untested; timing-based rescue test — new gateway tests: cancel (twice) during reserve, `_attempt` raising, `_write` failing.
  - `[low]` `[reject]` (blind 6) `cost` selects are not one snapshot — a report; drift only while calls run.
  - `[low]` `[reject]` (blind 7) `budget set` and `cost` print different budget lines — `budget set` keeps Story 2.2's tested format.
  - `[low]` `[reject]` (blind 8) `start`/`assign_seat` race with the limit — self-heals: the next job gets `budget_exhausted` and switches.
  - `[low]` `[patch]` (blind 9) failed-switch test does not assert the log — `capture_logs` check added; the `fallback` NameError part is false (`_decide` assigns it before the `try`).
  - `[low]` `[patch]` (blind 10) `BudgetScope` re-export in `games.service` — removed; `state` is the name AC 5 uses; `rounding` style and the JSON index rejected (small tables).
  - `[medium]` `[patch]` (edge 1) `_log` failure leaks the reservation — as blind 1.
  - `[low]` `[patch]` (edge 2) a second cancel inside `_reserve`'s handler leaks — the handler loops until the reservation task is done; tested.
  - `[low]` `[patch]` (edge 3) a reserve error under cancel replaces the CancelledError — the same loop reads `task.exception()` and re-raises the cancel.
  - `[medium]` `[reject]` (edge 4) transient contention switches Seats — as blind 2 (AC 3).
  - `[false]` `[reject]` (edge 5) budget row missing during a player reservation — `_prepare` raises `budget_not_found` first and nothing deletes budget rows.
  - `[low]` `[reject]` (edge 6) `release` raising masks the original error — needs two DB failures in a row; rare.
  - `[low]` `[reject]` (edge 7) concurrent jobs append duplicate `cost_limit` rows — the occupant is still `rule_based`; a guard needs a new command parameter.
  - `[low]` `[reject]` (edge 8) Seat taken over between read and switch — no takeover exists before Epic 5.
  - `[low]` `[reject]` (edge 9) a non-ended CommandError stops the loop — logged by the job; the next `budget_exhausted` retries.
  - `[low]` `[reject]` (edge 10) stored `max_tokens` provider param — as blind 3.
  - `[medium]` `[reject]` (edge 11) one worst case above `limit − reserve` exhausts a fresh scope — AC 3; the bound is config data (issue #8).
  - `[medium]` `[patch]` (edge 12) claim "every reservation is settled or released" — true after the blind 1 patch.
  - `[low]` `[reject]` (edge 13) idempotence only sequential — as edge 7.
  - `[low]` `[reject]` (edge 14) settle/release signatures differ from the spec text — internal; both take the `Reservation`.
  - `[medium]` `[patch]` (verification gap 1) release on cancel-in-reserve and attempt error untested — as blind 5.
  - `[medium]` `[patch]` (verification gap 2) a non-default `max_output_tokens` is not checked — `test_the_effort_levels_output_bound_is_sent_and_reserved`.
  - `[low]` `[patch]` (verification gap other 1) second cancel in `_reserve` — as edge 2.
  - `[low]` `[reject]` (verification gap other 2) `SWITCH_ENDED` break path untested — race-only.
  - `[low]` `[reject]` (intent a) the switch starts from the job, not the state change — a flag set by the probe CLI reaches Games at their next LLM job.
  - `[low]` `[reject]` (intent b) not-started Games get a `cost_limit` row at `start` — `switch_to_rule_based` refuses them; Design Notes.
  - `[low]` `[reject]` (intent c) `max_output_tokens` is new config data — nothing bounded output before.
  - `[low]` `[reject]` (intent d) no mixed reserve/settle order in the concurrency tests — the conditional UPDATE does not depend on order.
  - `[low]` `[reject]` (intent e) Class session scopes untested — no Class session Games before Epic 5.
  - `[false]` `[reject]` (intent f) the job's "occupancy stays llm" contract changes — designed: AC 4 switches the Seats.

## Design Notes

Worst case is computed from the request actually sent (prompt + schema + settings), so it is an upper bound without a tokenizer; `max_tokens` makes the provider enforce the output bound. If a provider still bills more than reserved, `settle` records the true cost (honest `spent`) and logs `ai_cost_above_reservation`; the next reservation then sees it. A process killed between reserve and settle leaves its amount in `reserved_usd` (fails safe: less spendable, never overspend).

Not-started Games cannot be switched (`switch_to_rule_based` refuses them), so the limit reaches them at `start`; running Games are switched by the job that hit the limit.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/ai tests/players tests/test_migrations.py tests/test_imports.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:** every LLM attempt now reserves its worst-case cost on the scope's budget row and settles to its actual cost; at the players' cost limit every LLM Seat of the scope becomes a Rule-based player.
- `ai_budgets.reserved_usd` (migration 0011). `budget.reserve` is one conditional `UPDATE` (players up to `limit − reserve`, others up to `limit`); a failed player reservation sets `players_exhausted_at` once and logs `ai_cost_limit_reached` (ids only) after commit. `settle` runs in the `llm_call` row's transaction; `release` for 429s, cancels and failed writes. `budget.state(scope)`.
- Worst case = request bytes + 256 tokens at the input price, plus the Effort level's new `max_output_tokens` (default 4096, placeholder) at the output price, rounded up; `max_tokens` is sent on every request.
- The `ai-orders` job places the fallback (`budget_exhausted`), then `players.service.apply_cost_limit` switches every `llm` Seat of every running Game on the scope (`switch_to_rule_based`, `cost_limit`). `assign_seat` and `start` turn `llm` occupants into `rule_based`/`cost_limit` while the state is set.
- `python -m app.ai.cli cost --scope ID [--kind]`: budget row, total, per Game, per UTC day.

**Files:** `backend/app/ai/{budget,gateway,config,adapters,models,calls,cli}.py`; `backend/migrations/versions/0011_ai_reservations.py` (new); `backend/app/modules/games/{service,repo,commands}.py`; `backend/app/modules/players/{service,jobs}.py`; `README.md`; tests: `tests/players/test_cost_limit.py` (new), `tests/ai/{test_budget,test_gateway,test_cli,test_config,test_adapters}.py`, `tests/players/test_rescue.py` (cancel after 0.1 s), `tests/test_sim_prompt.py`, `tests/test_migrations.py`.

**Review:** one pass, 4 layers, 34 findings (high 0, medium 9, low 22, false 2, maybe-false 1). Patched: 3 medium entries (failed write leaks a reservation; untested release paths; untested non-default output bound) and 4 low (double cancel in `_reserve`, error under cancel, failed-switch log assert, `BudgetScope` re-export). Deferred: worst case vs a real bill (medium, unverified). Rejected with reasons in the triage log, notably contention setting the limit (prescribed by AC 3).

**Follow-up review recommended:** true — three medium entries were patched after the reviewers read the code (release on a failed `_write`, the `_reserve` cancel loop); patched counts: medium 3, low 4.

**Verification:** ruff check and format clean; full suite with coverage: 1387 passed in 57 s, engine coverage 100 %, golden outputs unchanged; every matrix row covered by a passing test (`test_budget.py`, `test_gateway.py`, `test_cost_limit.py`, `test_cli.py`). New test over 1 s: `test_the_job_at_the_limit_switches_every_llm_seat_of_the_scope` (about 2.7 s, five Games). Two timing tests failed once in an early targeted run right after migration 0011 ran (`test_rescue.py::test_the_job_keeps_a_hanging_model_inside_the_turns_deadline`, `test_sim_llm.py::test_a_whole_game_with_the_provider_down_finishes_on_fallback_orders`), then passed in five further runs.

**Decisions taken in place of the founder:**
1. "max tokens" = new Effort-level field `max_output_tokens`, default 4096 (placeholder, issue #8), sent as `max_tokens`; Effort levels may no longer set `max_tokens`/`max_completion_tokens`.
2. Input bound = UTF-8 bytes of the request + 256 tokens; reservations round up to 1e-8 USD.
3. A cost above its reservation is recorded as it is and logged (`ai_cost_above_reservation`).
4. A player reservation refused because other attempts hold the room also sets the cost limit (AC 3 read literally).
5. Not-started Games get `rule_based`/`cost_limit` rows at `start`; running Games are switched by the job that hit the limit.
6. No `AI_DAILY_ALERT_USD` setting yet (Epics 3 and 15 own it).
7. `cost` takes `--kind` for an id with budgets of both kinds; `game <id|->` lines dearest first, `day` lines in UTC.
8. Implementation ran in the orchestrating session, not a fresh subagent (runbook constraint); reviews ran as four independent subagents.

**Residual risks:** a process killed between reserve and settle leaves its amount in `reserved_usd` (no sweeper; fails safe); contention near the limit switches players early; migration 0011 ran on the shared `olspillet_test*` databases (not changed after it ran); CI has not run; nothing pushed.
