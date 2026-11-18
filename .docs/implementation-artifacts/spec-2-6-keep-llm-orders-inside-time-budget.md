---
title: 'Story 2.6: Keep every LLM Order inside its time budget'
type: 'feature'
created: '2026-11-18'
baseline_revision: '3fa31fe977d083d67a62d0f9133a0f2230ff2bce'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** An `llm` Seat's Order has no deadline: the job calls the gateway with `deadline=None`, nothing places the fallback when a job hangs or dies, a cancelled attempt leaves no `llm_call` row (Issue #52), and a database error while the job writes the Order leaves the Seat waiting forever (Issue #54) (FR-32, NFR-2, NFR-4, AD-5, AD-6, AD-20).

**Approach:** Store `ai_deadline_at` on each `llm` turn, computed only by a new pure `games.rules.turn_times`; the job passes it to the gateway, which keeps every attempt inside it; `worker-ai` runs a 5-second rescue loop that places the timeout fallback for overdue turns and advances complete Weeks; the gateway logs a cancelled attempt; the job retries a failed database write.

## Boundaries & Constraints

**Always:**
- Alembic `0009` (expand-only): `seat_turns.ai_deadline_at TIMESTAMPTZ NULL`, `seat_weeks.ai_deadline_at TIMESTAMPTZ NULL` (copied by `place_order`, AD-15), partial index `ix_seat_turns_ai_deadline` on `seat_turns(ai_deadline_at) WHERE ordered_at IS NULL AND ai_deadline_at IS NOT NULL`; the `seat_turns` trigger also refuses changing an `ai_deadline_at` that is set; `ck_llm_call_outcome` widened with `cancelled`. Downgrade reverses all.
- `games.rules.turn_times(game: TurnGame, seat: TurnSeat, inputs: TurnInputs) -> TurnTimes` is pure (no I/O, no clock). `TurnInputs` (frozen dataclass, extended by later stories) holds `ai_order_budget_s: float | None`. `TurnSeat` has `occupant_kind`, `opened_at`, `occupied_since: datetime | None`; `TurnGame` has `guided_week: bool`. Result `ai_deadline_at` = `max(opened_at, occupied_since) + budget` for an `llm` occupant outside a Guided Week with a budget; else None. Nothing else computes the deadline.
- `_open_week` reads the transaction's `now()` once, writes it as `opened_at` of every turn, reads the frozen Effort level's `order_time_budget_s` from `ai.config` (one read per Week, only when the runtime has a config) and writes `ai_deadline_at` from `turn_times` in the same multi-row insert.
- `PendingTurn` gains `ai_deadline_at`. The job passes it as `deadline` to `gateway.run`.
- Gateway: every attempt's timeout is `min(attempt_timeout_s, time left)`; an attempt after the first starts only when the time left is at least `attempt_timeout_s`, else `Failure("timeout", ids)`. A timed-out attempt is its own row with outcome `timeout`. A deadline already passed returns `timeout` with no attempt. `deadline=None` keeps the attempt limit and per-attempt timeout.
- Issue #52: an attempt cancelled from outside (`CancelledError`) is logged as its own row with outcome `cancelled`, its latency and any tokens, then the cancellation propagates.
- Issue #54: the job retries `place_order` on a `sqlalchemy.exc.DBAPIError` up to 3 tries in all, waiting `RETRY_DELAYS_S = (0.2, 1.0)` (module constant, patched in tests); after that it raises, and the rescue loop places the fallback at the deadline. The model is never asked again.
- `players/rescue.py`: `rescue_once(now: datetime | None = None) -> RescuePass` (counts placed, advanced, failed); `run(interval_s=RESCUE_INTERVAL_S (5.0), stop: asyncio.Event | None)`. One pass: every `games.service.overdue_llm_turns(now)` (open Week of a running Game, no Order, `ai_deadline_at <= now`, default DB `now()`) re-read via `llm_turn`; still `llm`, unordered, not Guided → `place_order(reference, rule_based, fallback=timeout, llm_call_ids=())`; `order_exists`/`week_not_open`/`game_finished` are ignored. Then `games.commands.advance` for every `games.service.complete_running_games()`. An error on one item is logged and counted; the pass goes on.
- `python -m app.worker`: with `ai-orders` among the queues it runs the rescue loop next to the worker in the same event loop and stops it when the worker stops.
- Import rules hold: `players/rescue.py` imports only `games.service`/`games.commands`, never the gateway or `players.jobs`.

**Never:** No real endpoint or rate limiter (2.7), no reservation (2.8), no playout queue or sweeper (Epic 8), no command that makes a Seat `llm` mid-Week, no change to golden sim output, no multi-second real sleep in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Deadline written | `llm` Seat, non-Guided Week, budget 8 s | `ai_deadline_at = opened_at + 8 s`; Rule-based/Guided turns NULL | — |
| Later occupant | `turn_times` with `occupied_since` > `opened_at` | deadline from `occupied_since` | — |
| Attempt timeout, no room | timeout 0.05, budget 0.08, `script(TIMEOUT)` | 1 row `timeout`, `Failure("timeout")` | — |
| Attempt timeout, room | timeout 0.05, deadline 1 s ahead, `script(TIMEOUT)` | rows `timeout`, `ok`; `Result` | — |
| Deadline passed | deadline in the past | `Failure("timeout", ())`, no row | — |
| No deadline | `deadline=None`, `script(TIMEOUT, TIMEOUT)` | 3 rows, attempt limit applies | — |
| Cancelled | task cancelled mid-attempt | 1 row `cancelled`; `CancelledError` raised | — |
| Job killed | job cancelled mid-call; loop interval 0.05, budget 0.3 | fallback `timeout` placed, `ordered_at − opened_at ≤ budget + interval` (+ slack) | — |
| Late answer | rescue placed fallback, then job finishes | job gets `order_exists`, fallback stands, its rows stay with caller ref | — |
| Overdue, not llm | turn past deadline, Seat switched to rule_based | rescue places nothing | — |
| Complete open Week | running Game, all ordered, not advanced | rescue calls `advance`, next Week opens | — |
| DB error once | `place_order` raises `OperationalError` once | Order placed on 2nd try, one gateway run | — |
| DB error always | 3 failures | job raises; rescue places fallback after deadline | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py` -- add `TurnGame`, `TurnSeat`, `TurnInputs`, `TurnTimes`, `turn_times`.
- `backend/app/modules/games/commands.py:354` `_open_week` (turn insert), `:540` `_place` (copy `ai_deadline_at` into `seat_week`), `:395` `_settle`, `:715` `advance`; `start`/`_step` call `_open_week` with `seat_ids` from `repo.seats_with_occupant` (has `occupant_kind`; latest row is the one in force when a Week opens).
- `backend/app/modules/games/repo.py` -- add `now`, `overdue_llm_turns`, `complete_running_games`; `insert_turns` unchanged.
- `backend/app/modules/games/models.py:100,118` -- `seat_turns`, `seat_weeks` columns + index.
- `backend/app/modules/games/schemas.py:185` `PendingTurn`; `DecisionLogRow`; `turns.py:54` `pending_turn` (fill `ai_deadline_at`); `views.py:134` `decision_log`; `service.py` exports.
- `backend/app/ai/config.py:60` `EffortLevel.order_time_budget_s`, `:322` `get`, `ModelConfig.effort_level`.
- `backend/app/ai/gateway.py:335` `_attempt`, `:425` `run` loop; `app/ai/models.py:83` `OUTCOMES`; `app/ai/mock.py` `TIMEOUT` step hangs until cancelled.
- `backend/app/modules/players/jobs.py:52` `deadline=None` -> turn deadline; `place_order` call sites.
- `backend/app/worker.py`, `app/platform/jobs/__init__.py:run_worker` -- add the loop beside the worker.
- `backend/migrations/versions/0003_game_weeks_seat_turns.py:49` -- trigger to replace in 0009; `0008_jobs_llm_orders.py` style.
- Tests: `tests/players/test_llm_jobs.py` (`llm_game`, `rows`, `SHORT`), `tests/ai/helpers.py` (`stored_config(**changes)` takes `effort_levels`), `tests/ai/test_gateway.py`, `tests/test_worker.py`, `tests/test_migrations.py` (head revision), `tests/test_imports.py`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0009_ai_deadlines.py` (new) -- schema above.
- `backend/app/modules/games/{rules,models,repo,schemas,turns,views,service,commands}.py` -- `turn_times`, columns, deadline write and copy, `PendingTurn.ai_deadline_at`, `overdue_llm_turns`, `complete_running_games`.
- `backend/app/ai/{gateway,models}.py` -- next-attempt rule, `cancelled` outcome and row.
- `backend/app/modules/players/jobs.py` -- deadline, DB-error retries.
- `backend/app/modules/players/rescue.py` (new) -- the loop.
- `backend/app/worker.py` -- run the loop with `ai-orders`.
- Tests: new `tests/games/test_turn_times.py` (table-driven), `tests/players/test_rescue.py` (deadline written, killed job, late answer, not-llm skip, advance, DB-error retries), gateway rows in `tests/ai/test_gateway.py`, worker loop wiring in `tests/test_worker.py`; update `test_migrations.py`.

**Acceptance Criteria:**
- Given a finished simulated Game with `llm` Seats, when its `llm_call` and `seat_weeks` rows are read with SQL alone, then latency per attempt and `ordered_at − opened_at` per Order are available per Effort level (test).
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, golden outputs are unchanged, and any new test over 1 s is reported.
- Given `docker compose up -d worker-ai`, then the worker starts with the rescue loop and no key (checked once by a review agent or the builder, recorded).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 36 findings — high 2, medium 5, low 18, false 9, maybe-false 2
- findings:
  - `[low]` `[reject]` (intent 1) only task cancellation is tested, not a process kill — compose restarts `worker-ai`; the hand check below stopped the worker past the deadlines and the loop placed the fallbacks on restart.
  - `[low]` `[reject]` (intent 2) a mid-Week `llm` occupant is covered only by `turn_times` — no command makes a Seat `llm` mid-Week before Epic 8; the trigger lets a NULL deadline be set later.
  - `[false]` `[reject]` (intent 3) Issue #52 should reuse `timeout` — the story's `timeout` row is the per-attempt timeout, which is kept; an outside cancel is not a timeout, and no caller ever sees `cancelled`.
  - `[false]` `[reject]` (intent 4) Issue #54 belonged to the rescue loop alone — the loop is the backstop; the retry keeps the model's answer after a blip.
  - `[low]` `[reject]` (intent 5) the late-answer test does not assert the `order_exists` path — the fallback row standing with an ok `llm_call` row proves the job ended without placing.
  - `[low]` `[reject]` (intent 6) the real period is the pass time plus 5 s — negligible.
  - `[low]` `[reject]` (intent 7) no test of an `llm` turn with a NULL deadline — the SQL filter is `ai_deadline_at IS NOT NULL`; such turns first appear in Epic 8.
  - `[false]` `[reject]` (intent 8) scope additions (copy to `seat_weeks`, index, trigger) — AD-15/AD-20 copy the turn's times; the index serves the loop.
  - `[low]` `[reject]` (intent 9) one Effort level in the timing test — the GROUP BY is the per-level read; the mock config has one level.
  - `[medium]` `[patch]` (gap 1) the job's deadline was not checked end to end — new `test_the_job_keeps_a_hanging_model_inside_the_turns_deadline`; it exposed blind 7.
  - `[medium]` `[patch]` (gap 2) the loop surviving a failed pass was untested — new `test_the_loop_survives_a_failed_pass`.
  - `[low]` `[patch]` (gap 3) the fallback path's retry was untested — new test: an outage plus one `OperationalError` stores `provider_error`.
  - `[low]` `[reject]` (gap other) `serve` does not watch the loop task — `run` catches every pass error, and its wait cannot raise.
  - `[false]` `[reject]` (blind 1) the rescue fallback drops the failed attempt ids — the story says the rescue row cannot list them; `players` may not read `llm_call`; the caller ref ties them to the turn.
  - `[false]` `[reject]` (blind 2) a missing Effort level leaves no deadline — unreachable: `create` validates the level, and a referenced config is immutable.
  - `[low]` `[patch]` (blind 3) a non-`llm` Order copies the turn's deadline — `place_order` now copies `ai_deadline_at` for an `llm` occupant only (the repeated overdue pick needs Epic 8's Takeover and is not patched).
  - `[low]` `[reject]` (blind 4) the retry gate reports `timeout` after an invalid answer — the Order failed for lack of time, as the AC states.
  - `[low]` `[patch]` (blind 5) the cancel path loses the original `CancelledError`, and a log error can replace it — the original is re-raised in `finally`.
  - `[medium]` `[patch]` (blind 6) every `DBAPIError` was retried — now only `OperationalError`/`InterfaceError`; new test: an `IntegrityError` is tried once.
  - `[high]` `[patch]` (blind 7) the deadline is on the DB clock but compared with the worker's clock — real: the local Postgres container runs 96 s ahead of the host, so jobs were not bounded. `llm_turn` now returns the DB clock at the read (`read_at`), and the job gives the gateway its own now plus the time left.
  - `[low]` `[reject]` (blind 8) a downgrade with `cancelled` rows fails unclearly — documented in the revision; dev-only, as in 0008.
  - `[low]` `[reject]` (blind 9) several replicas run the loop — `order_exists` and the Game lock make passes idempotent.
  - `[low]` `[patch]` (blind 10) the worker test accepted two orderings — one ordering is asserted; the other weak assertions are rejected (the SQL read is the AC).
  - `[low]` `[reject]` (blind 11) "5 seconds" written in prose — matches AD-5's text.
  - `[low]` `[reject]` (blind 12) the config is read every Week — one indexed read per Week, for `llm` Games only.
  - `[low]` `[reject]` (blind 13) `serve` misses a dead loop task — as gap other.
  - `[low]` `[patch]` (edge 1) a cancel during a finished attempt's `_log` loses the row — `_log` is shielded.
  - `[low]` `[patch]` (edge 2) a second cancel during the write of the cancelled row — shielded.
  - `[high]` `[patch]` (edge 3) DB clock vs app clock — same root cause as blind 7.
  - `[low]` `[reject]` (edge 4) `now()` is the transaction start — AD-20 counts from `opened_at`; the opening transaction is short.
  - `[medium]` `[patch]` (edge 5) non-transient errors were retried — same root cause as blind 6.
  - `[low]` `[reject]` (edge 6) a lasting non-ENDED refusal repeats in rescue — pre-existing: every command refuses such a Game.
  - `[low]` `[reject]` (edge 7) a naive `now` — only tests pass `now`.
  - `[low]` `[reject]` (edge 8) shutdown waits on a hanging pass — rare; the DB calls end with the pool.
  - `[maybe-false]` `[reject]` (edge 9) a NULL deadline after a lasting write error — not reachable (see blind 2); low if true.
  - `[maybe-false]` `[reject]` (edge 10) SIGKILL leaves no row — no code can log it; the loop still places the Order; low.

## Design Notes

"The next attempt starts only if it can finish inside the deadline" is read literally: a retry needs its full per-attempt timeout before the deadline. The first attempt gets whatever time is left, so a job that starts late still has one chance. The rescue loop uses the database clock by default (the same clock as `opened_at`) and takes `now` for tests. The rescue fallback carries no call ids: the in-flight attempts are tied to the turn by their caller reference (Story 2.3). A mid-Week `llm` occupant (Epic 8 Takeover) passes its occupancy time as `occupied_since`; no command creates one yet, so that case is covered by the pure-function table.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest tests/games/test_turn_times.py tests/players tests/ai/test_gateway.py tests/test_worker.py tests/test_migrations.py tests/test_imports.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:** Every LLM Order now has a deadline.
- Alembic 0009 adds `ai_deadline_at` to `seat_turns` and `seat_weeks`, a partial index for the loop, a trigger rule that keeps a deadline once it is set, and the `cancelled` attempt outcome.
- The pure `games.rules.turn_times(game, seat, inputs)` is the only place the deadline is computed. It applies to an `llm` occupant outside Guided Weeks: `opened_at`, or a later occupancy start, plus the per-Order budget of the frozen Effort level.
- The job passes the deadline to `gateway.run`. Each attempt is cut to the time left, and a retry starts only when its whole timeout fits.
- `worker-ai` runs `players.rescue` every 5 s. It places the `timeout` fallback for overdue turns and advances complete Weeks left open.
- Issue #52: a cancelled attempt is logged with outcome `cancelled`, and the same cancellation then goes on.
- Issue #54: after a transient DB error the job writes the Order up to twice more (after 0.2 s and 1 s), then leaves the turn to the loop.

**Files:**
- `backend/migrations/versions/0009_ai_deadlines.py` (new): the schema.
- `backend/app/modules/games/{rules,commands,repo,models,schemas,turns,views,service}.py`:
  - `turn_times`;
  - the deadline written when a Week opens and copied for `llm` Orders;
  - `overdue_llm_turns` and `complete_running_games`;
  - `PendingTurn.ai_deadline_at` and `read_at`.
- `backend/app/ai/{gateway,models}.py`: the retry rule and the `cancelled` row.
- `backend/app/modules/players/jobs.py`: the deadline on the worker's clock, and retries on transient DB errors.
- `backend/app/modules/players/rescue.py` (new): the loop.
- `backend/app/worker.py`: runs the loop with `ai-orders`.
- `README.md`: the loop.
- Tests:
  - New: `tests/players/test_rescue.py`, `tests/games/test_turn_times.py`.
  - Updated: `tests/ai/test_gateway.py`, `tests/test_worker.py`, `tests/test_migrations.py`.

**Review:** one pass, 4 layers, 36 findings (high 2, medium 5, low 18, false 9, maybe-false 2).
- Patched entries by verdict:
  - High (1): the deadline read from the DB clock was compared with the worker's clock.
  - Medium (3): a test of the job's deadline, a test that the loop survives a failed pass, and retries limited to transient errors.
  - Low (5): a test of the retry on the fallback path, the deadline copied only for `llm` Orders, the original `CancelledError` re-raised with `_log` shielded, and one ordering in the worker test.
- Deferred: none.
- Rejected, with reasons in the triage log:
  - a process-kill test, and the mid-Week `llm` path (Epic 8);
  - `cancelled` instead of `timeout`;
  - call ids on the rescue fallback, and a missing Effort level;
  - the failure type the retry gate reports;
  - a downgrade with rows, and several replicas;
  - prose, and the config read every Week;
  - the transaction-start clock, a naive `now`, the shutdown wait, and the row after a SIGKILL.

**Follow-up review recommended:** true, because a high was patched. The deadline now reaches the worker's clock through the time left as read on the DB clock (`read_at`). The local Postgres container runs about 96 s ahead of the host, and the new job test passes only with this fix. No independent reader has checked the conversion yet.

**Verification:**
- `ruff check` and `ruff format --check`: clean.
- Full suite: 1335 passed in about 50 s. With coverage: engine coverage 100 %, golden outputs unchanged.
- Matrix audit: every row has a passing test in `tests/players/test_rescue.py`, `tests/games/test_turn_times.py` or `tests/ai/test_gateway.py`.
- Docker hand check, done by the builder:
  - `docker compose up -d --build backend worker-ai` started with no key.
  - With `worker-ai` stopped, a mock Game with four `llm` Seats was started and left past its 8-second deadlines.
  - On restart the loop placed 4 `timeout` fallbacks (`llm_order_rescued`), and the jobs ended at the passed deadline, with no errors.
  - `backend` and `worker-ai` were then stopped and removed.
- New tests over 1 s (each run includes the one-time pydantic-ai import of about 1 s per process):
  - `test_time_per_attempt_...`: 2.5 s.
  - `test_a_killed_job_...`: 1.5 s.
  - `test_an_llm_turn_gets_its_deadline_...`: 1.4 s.
  - `test_the_loop_survives_a_failed_pass`: 1.4 s.
  - Four more tests in `test_rescue.py`: 1.0 to 1.1 s each.

**Decisions taken in place of the founder:**
1. A retry needs its whole per-attempt timeout before the deadline. The first attempt takes whatever time is left.
2. An attempt cancelled from outside gets the new outcome `cancelled` (Issue #52). No caller ever sees it.
3. On `OperationalError` or `InterfaceError` the job makes 3 tries in all, waiting 0.2 s and then 1 s (Issue #54). It never asks the model again. After the third try the loop places the fallback.
4. The rescue fallback carries no call ids. The attempts are tied to the turn by their caller reference.
5. The deadline lives on the DB clock. The job converts it to its own clock through the time left, and the loop compares on the DB clock.
6. No deadline is set in Guided Weeks, for occupants that are not `llm`, or for a Game without a model config. `seat_weeks.ai_deadline_at` is set only for `llm` Orders.
7. `turn_times` already supports the deadline of a Seat that becomes `llm` mid-Week (`occupied_since`). Epic 8's Takeover writes it.

**Residual risks:**
- CI has not run, because nothing was pushed.
- Migration 0009 was changed after its first run. The shared test databases `olspillet_test_gw0` to `olspillet_test_gw11` were downgraded to 0008 and upgraded again; none was dropped.
- The dev database `olspillet` is at 0009 and holds one more finished mock LLM Game.
- A hard-killed worker still leaves no row for the attempt in flight.
