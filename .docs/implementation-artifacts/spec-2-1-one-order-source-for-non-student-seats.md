---
title: 'Story 2.1: Give every non-student Seat its Order from one order source'
type: 'feature'
created: '2026-11-17'
baseline_revision: 'df7d7c4267a78ea083c7dabda570676b16446fd4'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Opening a Week re-reads the whole Game history several times per Seat (pending_turn and place_order each run stored_play), so a 36-Week all-AI Game takes about 6 s against local Postgres.
    evidence: |-
      Blind review finding; measured 6.5 s per Classic Game in test_sim_golden (the Epic 1 runner took about 8.7 s, so this is not a regression). It will matter for the Story 2.11 batches: read the history once per Week and pass it to the order source.
    location: >-
      backend/app/modules/games/turns.py pending_turn; backend/app/modules/games/commands.py _place
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Orders for Rule-based, scripted and Guided Seats are chosen by the simulation runner's own loop (`sim._decide`, `_play_to_end`), outside `games.commands`, so real Games and later LLM Seats would need a second copy of that logic, and a Game can be left with a complete Week that nobody advances (FR-30, NFR-4, AD-2, AD-5, AD-9).

**Approach:** Add `players.ensure_order(game, seat)` in `backend/app/modules/players/service.py`, called by `games.commands` whenever a Week opens and after a switch, placing Guided/Rule-based/scripted Orders through `games.commands.place_order` inside the running transaction. Add the commands `advance` and `switch_to_rule_based`; every command entry point calls `advance` after its commit until it does nothing. The runner loses its order loop and only creates, starts and waits.

## Boundaries & Constraints

**Always:**
- `games.service.OpenGame`: a handle on the running command's transaction (session, Game id, locked Game row, settings, params) passed to `ensure_order`. `games.service.pending_turn(game, seat_id)` reads, inside that transaction, the open Week's turn: week, `guided`, guided Order, occupant kind/policy id in force (`occupancy_in_force`), stored reference Order, whether the Seat already ordered, and the `SeatState`.
- `ensure_order(game, seat_id)`: does nothing when the Game is not `running`, the Seat already has an Order for the open Week, or the occupant is `student`. Guided Week (any non-student occupant) → `guided_order`, `decided_by guided`; `rule_based` → the turn's stored `rule_based_reference_order` (never recomputed), `decided_by rule_based`; `scripted` → `engine.scripted.REGISTRY[policy_id](seat_state)`, `decided_by scripted`; `llm` outside a Guided Week → nothing (job comes in Story 2.5).
- `place_order(..., *, within: OpenGame | None = None)`: with `within` it runs in that transaction with the same checks and Decision log row, but takes no lock of its own, does not bump `version`, emits nothing and never advances or finishes. `within` for another Game → `ValueError`.
- `games.commands._open_week` calls `ensure_order` for every Seat, in chain order, after inserting the turns (from `start`, an inline advance in `place_order`, and `advance`).
- `advance(game_id) -> bool`: one transaction (lock, and only when it acts: engine advance, open next Week or `finish`, one `version` bump, one `game` event); `False` and no bump/event when the Game is not running or `rules.week_complete` is false. After its commit it, like every other entry point (`create`, `assign_seat`, `start`, outer `place_order`, `switch_to_rule_based`), calls `_settle(game_id)`: `advance` steps until one does nothing. `start` still returns the opened Week (1); `place_order` still advances inline the Week it completes, and its `OrderPlaced` describes its own transaction.
- `switch_to_rule_based(game_id, seat, reason)`: reason any `OccupancyReason` except `initial` (else `reason_invalid` 422); refuses `game_not_found` 404, `seat_not_found` 404, `game_not_started`/`game_finished` 409. Seat without an Order for the open Week → append `rule_based` row `from_week = week`, then `ensure_order` in the same transaction; Seat with one → append with `from_week = week + 1`, place nothing. Never edits a row. Registry entries `games.advance`, `games.switch_to_rule_based` → `{"game"}`.
- `games.commands` imports `players.service` lazily inside one helper (circular import); `players` imports only `games.service`, `games.commands`, `engine`, `platform`.
- `sim.py`: `_decide` and the order loop are removed; `_play_one` = create, assign, start, wait, `verify_finished`. Wait = read the Game; if not finished call `advance` once and read again; still not finished → `error game_not_finished` exit 1. `play <id>` waits then checks; an already finished Game is no longer refused. `weeks` printed from `game_summary`.
- Golden batch results captured from the baseline code (before this story) for `batches/classic-smoke.json`, `classic-rule-based.json` (new, all `rule_based`, 2 Games) and `classic-scripted.json` (new, all scripted, 2 Games): the exported Decision log without `game_id`/`seat_id` and the summary with the Game ids masked, in `backend/tests/golden/batches/`. After the story the same runs must equal them byte for byte.
- Import check test: `players` imports no `app.modules.<other>` except `games.service`/`games.commands`; nothing under `app/modules/games` imports `app.ai`, `pydantic_ai`, `openai`, `anthropic`, `httpx` or `app.modules.players` except the lazy `players.service`.
- Tests stay fast: reuse `games_db`; tests that need a manual Seat give it a `student` occupancy row through a test helper (raw insert before `start`).

**Never:** No `llm` occupant in `assign_seat`, no jobs/procrastinate, no gateway, no migration, no change to engine arithmetic or existing golden traces, no Takeover/playout, no HTTP route.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All AI | 4 `rule_based`, Classic 36 Weeks, `start` | returns 1; Game `finished`; 36 `advance` transactions after `start`, each one `version` bump and one event (35 open a Week, 1 finishes) | — |
| Interrupted | `_settle` stopped after some advances | Game running with complete open Week; `advance` finishes it | — |
| Repeat | `ensure_order` on a Seat that ordered | nothing written | — |
| Student seat | one `student` Seat, others AI, Guided Week | AI Seats ordered at open; Week waits for the student's `place_order`, which advances inline and the next Week's AI Orders are placed | — |
| Scripted | `scripted:order-incoming` | Order = `state_seen.incoming_order` after Guided Weeks | — |
| Switch, no Order | student Seat mid-Week | row `rule_based`, `from_week = week`, reason given; reference Order placed; Week advances after commit | — |
| Switch, ordered | Seat already ordered | row `from_week = week + 1`; nothing placed | — |
| Switch refused | bad reason / unknown Seat / not started / finished | nothing stored, no event | `reason_invalid` 422 / `seat_not_found` 404 / 409s |
| advance idle | not started, incomplete Week, finished | `False`, version unchanged, no event | — |
| Batches | three golden batches | output equals golden | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `_open_week` L288 (add ensure_order calls), `start` L318, `place_order` L362 (split into in-transaction body + inline advance helper shared with `advance`), `finish` L457, `_commit_change` L130, `_snapshot` L262, `__all__`.
- `backend/app/modules/games/views.py` -- `build_seat_state`, `stored_play`, `stored_orders` (in-session reads to reuse for `pending_turn`).
- `backend/app/modules/games/repo.py` -- `turn`, `occupancy_in_force`, `has_seat_week`, `week_turns`, `seats_with_occupant`, `append_occupancy`.
- `backend/app/modules/games/service.py` -- export `OpenGame`, `pending_turn`.
- `backend/app/modules/games/rules.py` -- `guided_week`, `week_complete`.
- `backend/app/platform/events/registry.py` -- add two commands.
- `backend/app/engine/scripted.py` (`REGISTRY`), `engine.guided_order`.
- `backend/app/modules/players/` -- new `__init__.py`, `service.py`.
- `backend/app/sim.py` -- `_decide` L465, `_play_to_end` L484, `_play_game` L509, `_play_one` L713, docstring `play`/`run`.
- Tests: `tests/games/helpers.py` (`play_week`, `play_to_end`), `test_place_order.py`, `test_start.py`, `test_registry.py` (RUNNERS, public command set), `test_views.py`, `test_verify.py`, `test_summary.py`, `test_create.py`, `tests/test_sim.py`.

## Tasks & Acceptance

**Execution:**
- `backend/tests/golden/batches/*` -- golden captures from the baseline (done first).
- `backend/app/modules/games/{commands,service,views}.py`, `platform/events/registry.py` -- `OpenGame`, `pending_turn`, `within`, `advance`, `switch_to_rule_based`, `_settle`, ensure_order calls.
- `backend/app/modules/players/{__init__,service}.py` -- `ensure_order`.
- `backend/app/sim.py` -- remove the order loop; wait.
- `backend/batches/classic-rule-based.json`, `classic-scripted.json` -- new batches.
- `backend/tests/players/test_ensure_order.py` (new) -- matrix rows for ensure_order, advance, switch.
- `backend/tests/test_imports.py` (new) -- import check.
- `backend/tests/test_sim_golden.py` (new) -- golden batches.
- Existing tests -- adapt to auto-placed Orders (student helper for manual Seats).

**Acceptance Criteria:**
- Given the three golden batches, when run after the story, then Decision log export and masked summary equal the golden files.
- Given CI commands locally, then all tests pass, engine coverage 100 %, ruff clean, smoke batch `checks ok=3 failed=0`.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 34 findings — high 0, medium 2, low 29, false 3, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) an exception in `_settle` after the caller's commit makes a committed command look failed — `_settle` now catches and logs `settle_failed`; the result stands and the Game stays complete but open for the next command; test `test_a_failed_advance_after_the_commit_leaves_the_command_standing`.
  - `[low]` `[patch]` (blind) scripted policy id missing from `REGISTRY` raises a bare `KeyError` — `players._order` raises `CommandError("occupant_not_playable", 422)`, rolling the opening command back; test `test_a_scripted_occupant_without_a_known_policy_is_refused`.
  - `[low]` `[reject]` (blind) `llm`/policy-less scripted Seats stall silently — `assign_seat` refuses both kinds today; `llm` gets its job in Story 2.5 (spec Always); policy-less scripted now refused by the patch above.
  - `[low]` `[reject]` (blind) public `place_order` does not check the occupant or `decided_by` — pre-existing since Story 1.9; the actor check comes with Story 6.12 (`place_order` takes an `actor`).
  - `[low]` `[reject]` (blind) `switch_to_rule_based` appends a row when the Seat is already Rule-based — the AC says it appends a row with the reason and never edits; the cost-limit caller (Story 2.8) decides whether to call it twice.
  - `[low]` `[patch]` (blind) lock/bump/notify test does not cover `advance` and `switch_to_rule_based` — extended `test_each_command_locks_bumps_and_notifies_in_one_transaction` for both.
  - `[medium]` `[defer]` (blind) history re-read several times per Seat when a Week opens — not a regression (faster than the Epic 1 runner); deferred to Story 2.11 batches.
  - `[false]` `[reject]` (blind) `start` returns 1 when the Game has finished — spec: `start` still returns the opened Week (1); documented in the docstring.
  - `[low]` `[reject]` (blind) `_wait_finished` does not poll — nothing places an Order asynchronously until Story 2.5, which owns the waiting for jobs.
  - `[low]` `[reject]` (blind) tests seat Students with raw SQL — no command creates a Student occupant before Epic 5; the helper is documented.
  - `[false]` `[reject]` (blind) `_settle` after `create`/`assign_seat` is useless — the AC requires every entry point to call `advance` after its commit; the check is one read without a commit.
  - `[low]` `[patch]` (blind) import check ignores relative imports — `imports()` now asserts `level == 0`.
  - `[low]` `[reject]` (blind) golden test plays only Game 0 — founder rule: fast tests; the per-Game numbers are compared row for row, the summing code is unchanged and covered by the existing `run` tests.
  - `[low]` `[reject]` (blind) `within` failure path untested — a failure raises inside the opening command's transaction, which rolls back as a whole (covered now by the `occupant_not_playable` test).
  - `[low]` `[patch]` (verification-gap) no lock-order or concurrency test for `advance`/`switch` — lock test extended (above); new `test_two_advances_at_once_advance_each_week_once`.
  - `[false]` `[reject]` (verification-gap, other) golden CSVs not in the diff — they were left out of the review diff for size only and are committed with the story.
  - `[low]` `[patch]` (verification-gap, other) `KeyError`/stall for unplayable scripted Seat — same fix as the blind row.
  - `[low]` `[patch]` (edge) `_settle` failure after commit — same fix as the blind row.
  - `[low]` `[reject]` (edge) a scripted Order above `max_order` stalls the Game — needs demand above 999, which the demand ranges exclude; the Epic 1 runner refused the same Order.
  - `[low]` `[patch]` (edge) scripted with `policy_id` None — same fix as the `KeyError` row.
  - `[low]` `[patch]` (edge) unknown policy `KeyError` — same fix.
  - `[low]` `[reject]` (edge) repeated switch — same as the blind row.
  - `[low]` `[patch]` (edge) `within` compares Game ids as strings — now compares UUIDs (`_game_uuid`).
  - `[low]` `[patch]` (edge) relative imports bypass the check — same fix as the blind row.
  - `[low]` `[patch]` (edge) deleted `occupant_not_playable` guard — restored in `players._order`.
  - `[low]` `[reject]` (edge) golden compares Game 0 only — same as the blind row.
  - `[low]` `[reject]` (intent) Students only through raw SQL — as the blind row.
  - `[low]` `[reject]` (intent) the stop between advances is simulated by replacing `_settle` — the stored state is exactly what a dead process leaves (committed advance, complete open Week).
  - `[low]` `[reject]` (intent) golden files created in this change — Epic 1 stored no batch goldens; they were captured from the baseline code before any code change (decision recorded).
  - `[low]` `[reject]` (intent) registry runners changed — needed because a Game without Students now finishes inside `start`; every command still runs.
  - `[low]` `[reject]` (intent) `sim play` semantics changed (finished Game exits 0, `game_not_finished`) — follows from the runner only waiting (decision recorded).
  - `[low]` `[reject]` (intent) public surface `within`, `OpenGame`, `PendingTurn` — the spec defines them; `ensure_order(game, seat)` needs the transaction.
  - `[low]` `[reject]` (intent) import check is a pytest test — CI runs pytest (`.github/workflows/ci.yml`).
  - `[low]` `[reject]` (intent) `epic-2-context.md` added — a workflow artifact, not product code.

## Design Notes

`start` does not advance inline, so a Game with four AI Seats shows the "one Week per transaction" shape: `start` opens Week 1 and places its Orders, then 36 `advance` transactions follow. `place_order` keeps its Story 1.9 inline advance (AD-2: the command that makes the Week complete advances it); any Week that is already complete when it opens is advanced by `_settle` after the commit.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-report=term-missing --cov-fail-under=100` -- expected: all pass
- `cd backend && uv run python -m app.sim run batches/classic-smoke.json` -- expected: `checks ok=3 failed=0`

## Auto Run Result

Status: done

**Summary:** `players.ensure_order(game, seat)` is now the one order source. `games.commands._open_week` calls it for every Seat inside the transaction that opens the Week (from `start`, an inline advance in `place_order`, and `advance`), and `switch_to_rule_based` calls it after appending its row. It places Guided, Rule-based (the stored reference Order) and scripted Orders through `place_order(..., within=OpenGame)`, which joins the running transaction and never advances. New commands `advance` (one Week per transaction, `finish` on the last) and `switch_to_rule_based`; every command calls `_settle` (advance until nothing happens) after its commit, so `start` on four Rule-based players returns a finished Game. The simulation runner lost `_decide` and its order loop and now creates, starts and waits.

**Files:**
- `backend/app/modules/players/{__init__,service}.py` (new): `ensure_order`.
- `backend/app/modules/games/turns.py` (new): `OpenGame`, `pending_turn`.
- `backend/app/modules/games/commands.py`: `_open_week` calls the order source; `_place`/`_step` split; `place_order(within=)`, `advance`, `switch_to_rule_based`, `_settle`.
- `backend/app/modules/games/{schemas,service,repo}.py`, `platform/events/registry.py`: `PendingTurn`, exports, `repo.seat`, two registry entries.
- `backend/app/sim.py`: order loop removed; `_wait_finished`.
- `backend/batches/classic-rule-based.json`, `classic-scripted.json`, `backend/tests/golden/batches/*` (goldens captured from the baseline before any code change).
- Tests: `tests/players/test_ensure_order.py`, `tests/test_imports.py`, `tests/test_sim_golden.py` (new); existing games and sim tests adapted (Student seats through `seat_student`).

**Review:** one pass, 34 findings (medium 2, low 29, false 3). Patched: `_settle` failures logged after commit; `occupant_not_playable` for an unknown scripted policy; UUID comparison for `within`; no relative imports in the import check; lock/bump/notify test for `advance` and `switch_to_rule_based`; concurrent `advance` test. Deferred: history re-reads per Seat (performance, Story 2.11). Rejected findings and reasons are in the triage log.

**Follow-up review recommended:** false. Patched counts: high 0, medium 1, low 10 rows.

**Verification:**
- `ruff check`, `ruff format --check`: clean.
- Full `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100`: 1153 passed, 1 failed (the extended registry lock test, which counted the switch's follow-up advances); fixed and the file re-run: 4 passed; `tests/players` and `test_imports.py`: 18 passed. Engine coverage 100 %.
- `sim run batches/classic-smoke.json`: `checks ok=3 failed=0`.
- Golden batches: Decision log and per-Game summary of the first Game of each batch equal the baseline captures.
- Matrix audit: All AI, Interrupted, Repeat, Student seat, Scripted, Switch (no Order / ordered / refused), advance idle and Batches each have a passing test in `tests/players/test_ensure_order.py` or `tests/test_sim_golden.py`.
- Slow tests (over 1 s): the full-Game tests take about 6-7 s each (`test_start_plays_a_game…`, the three golden batch cases); the switch and advance tests 1-3 s. Existing Epic 1 batch tests in `test_sim.py` take 13-39 s, as before.

**Decisions taken in place of the founder:**
1. `ensure_order` takes an `OpenGame` (the running command's transaction) and a Seat id; `place_order` gained the keyword `within`.
2. `start` does not advance inline (returns Week 1 even when finished); `place_order` keeps the Story 1.9 inline advance; every command then settles.
3. `advance` loops after its own commit like every other command; it returns whether it advanced.
4. `switch_to_rule_based` accepts every reason except `initial` (`reason_invalid` 422) and appends a row even if the Seat is already Rule-based.
5. `llm` outside a Guided Week gets no Order yet (Story 2.5); in a Guided Week it gets the Guided Order.
6. Epic 1 stored no batch goldens: they were captured from the baseline code for the smoke batch plus two new batches (all Rule-based, all scripted); the test plays only the first Game of each to stay fast.
7. `sim play` on a finished Game now reports it (exit 0); a Game waiting for an Order no source places gives `game_not_finished`, exit 1; the runner may call `advance` once to repair a stopped Game.
8. `_settle` swallows and logs failures after the commit (the command's result stands).
9. The import check is a pytest test (CI runs pytest).
10. Tests seat Students by inserting occupancy rows directly, since no command creates a Student before Epic 5.
11. Implementation ran in the orchestrating agent's own context (runbook); the four review layers were independent sub-agents.

**Residual risks:**
- CI not run on GitHub (no push).
- A Game with an `llm` Seat waits outside the Guided Weeks until Story 2.5 adds the job.
- Per-Week history re-reads (deferred).

