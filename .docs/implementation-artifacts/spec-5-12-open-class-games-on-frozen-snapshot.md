---
title: 'Story 5.12: Open the Class games on the frozen snapshot'
type: 'feature'
created: '2026-11-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '33cda398f3e7bec53962f7e84becbf6c686fe08c'
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Class game whose snapshot can never be set is retried each minute and nobody is told.
    evidence: |-
      due_locks returns a locked session while any Class game lacks a snapshot; open_games logs class_game_open_failed and goes on. Unreachable today, since the snapshot comes from build_snapshot; it would need set_snapshot to fail permanently (e.g. a rules_version retired after a deploy). Settle with a test that makes set_snapshot fail every time.
    location: >-
      backend/app/modules/sessions/service.py open_games, due_locks
    severity: medium (unverified)
  - summary: >-
      The AD-2 command list in ARCHITECTURE-SPINE.md does not name set_snapshot.
    evidence: |-
      ARCHITECTURE-SPINE.md:66 lists move_seat but not set_snapshot; its .memlog.md (2026-11-14) records the decision to add it. Editing a planning artifact invalidates the epic-context cache, so it is left for the planning owner.
    location: >-
      .docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md:66
    severity: low
---

<intent-contract>

## Intent

**Problem:** Story 5.11 freezes a snapshot on the Class session, but its Class games still have no settings and free Seats. `start` answers `409 game_not_ready` forever, and a session with no confirmed allocation has no games at all.

**Approach:** The lock's transaction first allocates and commits the registered Students when nothing is confirmed. After it commits, `sessions.service.open_games` hands the session's snapshot to each Class game through a new command `games.commands.set_snapshot`, one Game per transaction. That command stores the snapshot and fills every free Seat, and every Seat of a removed Student, with the AI mode's occupant through the code of `assign_seat` (now with a `replace` argument). The sweep's `sessions.lock` finder also returns locked sessions whose games still lack a snapshot. The Klasseøkt's «Fordeling» block, once the games are open, lists them from their Seats: name or «KI-spiller», and «Ikke startet».

## Boundaries & Constraints

**Always:**
- `set_snapshot(game_id, snapshot, *, keep_students)`: Game row lock, `version` +1, `game:<id>` (+ `session:<id>` by policy), `user:<id>` for every Student who held a Seat before it. Only a purpose with `snapshot == "at_lock"`. A Game that already has a snapshot is left untouched (returns False, no bump, no event). The snapshot must have exactly `SNAPSHOT_COLUMNS`, valid `GameSettings`, a matching demand series and a valid `SessionRuntime` (`invalid_snapshot` 422).
- AI kind: `llm` when the runtime has a model config, otherwise `rule_based`. Reason `initial`. A Student not in `keep_students` gets replaced; their occupancy row stays (append-only).
- `assign_seat(..., replace=False)`: `replace=True` accepts an occupied Seat while the Game is `not_started`; without it `seat_occupied` stands. Started Games still answer `game_already_started`.
- Auto-allocation runs inside the lock's transaction, under the session row lock: `allocation.allocate(registered, draw_seed())` stored as a new draft (`drawn_by` None) and committed by `_commit_allocation` (`confirmed_by` None), with the allocation notices. Only when no draft is confirmed, at least one Student is registered and the Class is writable.
- `open_games` runs after the lock commits, and also when `lock` finds the session already locked, so a half-finished open is finished by the next call or sweep. Games in game-number order.
- After the open, the «Fordeling» api answer is built from the Class games' Seats, so it matches what the Games hold.

**Never:** No start of a Class game (Epics 6 and 8). No late registrant seating (5.13). No new cron, migration or sweeper. No sleeps; no DB-vs-host clock comparison. No change to a Game that already has its snapshot.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Confirmed, 6 Students | 2 games, 2 free Seats, Rule-based | both games get the snapshot; free Seats `rule_based`/`initial`; `start` works | — |
| LLM mode | `llm` session | free Seats `llm` | — |
| Not confirmed | 5 registered, unconfirmed draft or none | lock allocates (2 games), confirms, then opens them | — |
| Nobody registered | no Students | locks, no games | — |
| Removed Student | confirmed, one Student off the Roster | that Seat gets the AI occupant; old row kept | — |
| Interrupted | `set_snapshot` fails on game 2 | game 1 opened; next sweep opens game 2 only, game 1's version unchanged | sweep logs the item |
| Race | `start` vs `set_snapshot` together | `game_not_ready`, or started with the AI mode's occupants | — |
| Second call | `set_snapshot` on an opened Game | False, nothing changes | — |
| Wrong purpose | simulation Game | — | `snapshot_not_allowed` 422 |
| Plain assign on occupied | no `replace` | — | `seat_occupied` 409 |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:457` `assign_seat` -- split the body after the row lock into `_assign(session, game, role, occupant, policy_id, student, replace)`; add `replace`. New `set_snapshot` beside it; add to `__all__`. `_commit_change` already emits `session:<id>` for Class games.
- `backend/app/modules/games/repo.py` -- `set_snapshot(session, game_id, values)` (UPDATE of the five columns); `class_sessions_awaiting_snapshot(session)` (distinct `class_session_id` of `not_started` Games with `settings IS NULL`); `class_games(session, class_session_id)` (number, id, lifecycle, `settings IS NOT NULL`).
- `backend/app/modules/games/service.py` -- expose `class_sessions_awaiting_snapshot` and `class_games` (with each Seat from `seats_with_occupant`).
- `backend/app/platform/events/registry.py` -- `games.set_snapshot: {game, session, user}`; `sessions.lock` gains `game`.
- `backend/app/modules/sessions/service.py:1790` `lock` -- auto-allocation in the transaction, `open_games` after. `:1822` `due_locks` -- add locked sessions awaiting a snapshot. `:1531` `_commit_allocation` -- `confirmed_by` optional. `:1311` `_allocation_out` -- from the games once open; `opened`, per-game `lifecycle`.
- `backend/app/modules/sessions/repo.py` -- `locked_ids(s, ids)`.
- `backend/app/modules/sessions/schemas.py:322-359` -- `AllocationGameOut.lifecycle: str | None = None`, `AllocationOut.opened: bool = False`.
- `frontend/src/modules/sessions/allocation-panel.tsx`, `allocation.ts`, `frontend/src/copy/nb.ts` -- opened state line, lead, «Ikke startet» per game; `openapi.json`/`schema.ts` regenerated.
- Tests: `backend/tests/games/test_set_snapshot.py` (new; helper `tests/games/test_class_games.py` `class_game`), `tests/games/test_registry.py` (runner), `tests/sessions/test_open_games.py` (new; reuse `tests/sessions/test_lock.py` `dated`, `test_dates.student_of`), `frontend/e2e/class-session-lock.spec.ts` (opened block, route-faked as before).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/{commands,repo,service}.py` -- `replace`, `set_snapshot`, reads.
- `backend/app/platform/events/registry.py` -- topics.
- `backend/app/modules/sessions/{service,repo,schemas}.py`, `README.md` -- auto-allocation, `open_games`, finder, opened allocation answer.
- `backend/tests/games/test_set_snapshot.py`, `test_registry.py` -- matrix rows for the command, race, replace.
- `backend/tests/sessions/test_open_games.py` -- sweep rows: confirmed, LLM, auto-allocation, removed Student, interrupted, dummy pin in every game, events, api answer.
- `frontend/src/modules/sessions/*`, `nb.ts`, e2e -- opened view with axe at 320/360/1440.

**Acceptance Criteria:**
- Given a due session with a confirmed allocation and a dummy pin provider, when the sweep runs, then every Class game's `session_runtime.pins` holds the dummy value, every Seat is held, and `games.commands.start` succeeds on one of them.
- Given the opened Class games, when the Lecturer reads `GET /api/class-sessions/{id}/allocation`, then `opened` is true and each game lists four Seats with a Student's name or none (KI-spiller) and `lifecycle` `not_started`; the Klasseøkt shows them in the «Fordeling» block with «Ikke startet».
- Given the open, then `session:<id>` and `user:<id>` for each seated Student are emitted.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 46 findings — high 0, medium 5, low 19, false 12, maybe-false 10
- findings:
  - `[maybe-false]` `[defer]` blind: a Game that can never open is retried each minute with no alert — unreachable today (the snapshot is built by the same code that validates it); would need a permanently failing `set_snapshot`. Deferred, medium (unverified).
  - `[medium]` `[patch]` blind: a failed open makes a committed lock raise — `open_games` now catches and logs each Game's failure (`class_game_open_failed`) and goes on; the next sweep retries it. Cut-short test updated (first sweep counts 1).
  - `[false]` `[reject]` blind: `registered_students` read outside the lock's transaction — `classes.registered_students` takes no session (classes/service.py:607); `confirm_allocation` reads it the same way; the session row lock serialises the allocation itself.
  - `[low]` `[reject]` blind: a Student removed while the Games open one by one keeps the Seat — a window of milliseconds; Story 5.13's `replace_removed_student` handles removals after the open.
  - `[maybe-false]` `[reject]` blind: provider key not re-checked on a retried open — the lock checked it and froze the config; AD-17 governs the lock; an open retry follows within a minute. Would only be low.
  - `[low]` `[patch]` blind: the cost-limit fallback inside `set_snapshot` is undocumented — docstring now names FR-69's exception; behaviour kept (same code as `assign_seat`, as the AC asks).
  - `[low]` `[reject]` blind: `due_locks` scans every waiting Class game each minute — a small indexed-by-pk table per term; no measurable cost.
  - `[medium]` `[patch]` blind: `allocation_of` reads the Games before the access check, one query per Game — access check first; Seats now come in one query (`repo.class_session_seats`).
  - `[medium]` `[patch]` blind: `lifecycle` was a hand-written Literal — `Lifecycle` has `playing_out`, which would 500; now typed `Lifecycle`, copy for `playing_out` added.
  - `[false]` `[reject]` blind: revision reset to 1 at the lock's draw — the draft gets a new id; every check compares id and revision.
  - `[low]` `[patch]` blind: «Tomme seter har KI-spiller.» after the open — now «Tomme seter er fylt med KI-spillere.» (the lead counts Seats held, not registered Students, so that half is false).
  - `[low]` `[patch]` blind/edge: a locked session with no Students shows a stale preview as «Ikke bekreftet.» — the lock now deletes an unconfirmed draft when nobody is registered; test added. A locked-not-opened copy for archived Classes: rejected, archived Classes are read-only anyway.
  - `[low]` `[patch]` blind: no test of `sessions.lock`'s new `game` topic — the auto-allocation test asserts the emitted topics equal `COMMAND_TOPICS["sessions.lock"]`.
  - `[low]` `[reject]` blind: no test for cost limit at open, Assistant read, retried open without key — the cost-limit path is `assign_seat`'s, tested in tests/players/test_cost_limit.py; Assistant read path is unchanged `_class_for`.
  - `[low]` `[reject]` blind: `received[4:]` in test_registry — the existing pattern of `move_seat`'s runner.
  - `[low]` `[reject]` blind: test_registry imports `snapshot` from a test module — the suite imports helpers across test modules throughout.
  - `[low]` `[patch]` blind: `assert` as control flow — replaced by an explicit raise.
  - `[false]` `[reject]` blind: `__all__` order — not alphabetical before either (`OverdueTurn`, `scope_of`).
  - `[false]` `[reject]` blind: `[ASSUMPTION]` marker in nb.ts — the project's convention for draft copy.
  - `[false]` `[reject]` edge: TypeError on a malformed snapshot — the snapshot comes only from `build_snapshot`; `CommandError` is not owed to arbitrary internal input.
  - `[low]` `[reject]` edge: an invalid snapshot for an already opened Game raises — the session's snapshot never changes after the lock.
  - `[false]` `[reject]` edge: a Game whose Students were all removed is AI-only — that is the AC (every removed Student's Seat gets an AI player).
  - `[false]` `[reject]` edge: a Rule-based Seat kept in LLM mode — sessions only seat Students before the lock; no product path puts an AI in a Class game earlier.
  - `[low]` `[reject]` edge: removal between the read and the commit — as the blind row above (Story 5.13).
  - `[maybe-false]` `[defer]` edge: permanent `set_snapshot` failure retried forever — same deferred item as the first row.
  - `[medium]` `[patch]` edge: open failure raises from `lock` — same patch as above.
  - `[low]` `[patch]` edge: unconfirmed draft with nobody registered survives the lock — same patch as above.
  - `[false]` `[reject]` edge: Roster read outside the lock transaction — as above.
  - `[maybe-false]` `[reject]` edge claim: AI reason always `initial` — true except the cost-limit exception, now documented.
  - `[false]` `[reject]` edge claim: auto-allocation "inside the lock's transaction" — the draft, Games, Seats and notices are; only the Roster read is not, as in Story 5.9.
  - `[medium]` `[patch]` verification-gap: opened `missing_count` only tested at 0 — test registers a Student after the open and asserts `missing_count == 1`.
  - `[false]` `[reject]` verification-gap other: lock topic untested — now asserted anyway (patch above).
  - `[false]` `[reject]` verification-gap other: Roster read outside the transaction — as above.
  - `[low]` `[defer]` intent: `ARCHITECTURE-SPINE.md` AD-2 list lacks `set_snapshot` — its memlog records the decision; editing a planning artifact invalidates the epic-context cache; left for the planning owner.
  - `[maybe-false]` `[reject]` intent: the race test does not prove both orders happened — it asserts the invariant for whichever order the row lock gives, three times; forcing an order would need sleeps.
  - `[maybe-false]` `[reject]` intent: `start` tried on game 1 only — every Game's snapshot is asserted, and `start` refuses only on a missing snapshot.
  - `[maybe-false]` `[reject]` intent: e2e stubs the opened answer — no api route locks; the backend test pins the answer's fields, as in Story 5.11.
  - `[maybe-false]` `[reject]` intent: events checked at emission, not delivery — delivery is `platform/events`' own, tested in Epic 3.
  - `[maybe-false]` `[reject]` intent: archived-Class exception — an archived Class cannot be played or changed; recorded as a decision.
  - `[maybe-false]` `[reject]` intent: cost-limit path in `set_snapshot` untested — `_assign` is the code `assign_seat`'s cost-limit tests cover.
  - `[low]` `[reject]` visual 2: tick «2» missing under three columns — Story 5.8's tick rule, unchanged here.
  - `[low]` `[reject]` visual 3: chart spells out one game — UX-DR50: «Vis som liste» is the text view; the selected line now carries the state.
  - `[low]` `[patch]` visual 4: «Ikke startet.» reads as the last Student's — the state is now its own span in `ink-secondary`, apart from the Seats.
  - `[low]` `[reject]` visual 5: list and chart orders differ — Story 5.8's design (reading order vs chain).
  - `[low]` `[patch]` visual 6/7: closed and open blocks say different things; wording — the open panel now leads with the opened line (confirmation date secondary); «Ingen av spillene har startet ennå.», «Tomme seter er fylt med KI-spillere.».
  - `[false]` `[reject]` visual 9: US date format — the headless browser's locale, outside this story.

An independent visual reviewer checked six screenshots (closed, chart, list at 1440 and 390 px) in place of the founder: the AC holds in the list view, no layout defect at 390 px; its two material remarks were triaged above.

## Design Notes

Founder-level decisions taken here:
- Auto-allocation draws a fresh seed and ignores an unconfirmed draft the Lecturer previewed: the AC says "allocated at random with the same allocate function". It replaces that draft, so the block shows what was committed.
- No auto-allocation for an archived Class (nobody plays); its existing games are still opened. With nobody registered, an unconfirmed preview is deleted at the lock.
- A removed Student also gets `user:<id>` when their Seat goes to an AI player, so their pages reload.
- The cost-limit fallback of `assign_seat` (Rule-based, reason `cost_limit`) applies at the open too: the AC asks for "the same code".
- A Game whose open fails is logged and retried by the next sweep; the committed lock is not reported as failed.
- Implementation was done in the builder's own context, not by a step-03 sub-agent: the caller's runbook says sub-agents stop when the turn ends.
- Removed Students are judged against `registered_students` read just before the games are opened.
- The opened block keeps the chart and list views, reads «N studenter i M Klassespill.» instead of «fordeles tilfeldig», leads with «Klassespillene er klare. Ingen av spillene har startet ennå.», and shows each game's state («Ikke startet.») apart from its Seats in `ink-secondary` (draft copy).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_set_snapshot.py tests/sessions/test_open_games.py tests/sessions/test_lock.py tests/games/test_registry.py -q` -- expected: pass, each test under 1 s
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` and Playwright -- expected: pass

## Auto Run Result

Status: done

**Summary.** After the Start-date lock, every Class game opens on the Class session's frozen snapshot. The new command `games.commands.set_snapshot` stores the snapshot under the Game row lock, one Game per transaction, with one version step, `game:<id>` (+ `session:<id>`) and `user:<id>` for each Student who held a Seat. In the same transaction every free Seat, and every Seat of a Student no longer in the Roster, gets the AI mode's player (`llm` or `rule_based`, reason `initial`) through `assign_seat`'s own code, which gained a `replace` argument (accepted only before the start). When nothing was confirmed, the lock's transaction first allocates the registered Students at random and commits that as Story 5.9 does. `sessions.service.open_games` runs after the lock commits, and the sweep's `sessions.lock` finder also returns locked sessions with a Game still waiting, so an open cut short is finished next minute without touching opened Games. Once open, `GET …/allocation` answers `opened: true` and lists the Class games as their Seats hold them with each game's `lifecycle`. The Klasseøkt's «Fordeling» block says «Klassespillene er klare. Ingen av spillene har startet ennå.» and shows «Ikke startet.» beside each game.

**Files.**
- `backend/app/modules/games/commands.py`: `set_snapshot`, `_assign` (shared with `assign_seat`), `replace`, `_checked_snapshot`.
- `backend/app/modules/games/{repo,service}.py`: snapshot write, waiting sessions, Class games with Seats in one read.
- `backend/app/modules/sessions/{service,repo,schemas}.py`, `README.md`: auto-allocation, `open_games`, finder, opened allocation answer.
- `backend/app/platform/events/registry.py`: `games.set_snapshot`; `sessions.lock` gains `game`.
- `frontend/src/modules/sessions/{allocation-panel.tsx,allocation.ts}`, `frontend/src/copy/nb.ts`: the opened view; `openapi.json` and `schema.ts` regenerated.
- Tests: new `backend/tests/games/test_set_snapshot.py`, `backend/tests/sessions/test_open_games.py`; `test_registry.py` runner; `opened` in three allocation literals; `allocation.test.ts`; e2e `class-session-lock.spec.ts` (opened block, axe at 320/360/1440) and a fixture field in `class-session-allocation.spec.ts`.

**Review.** 46 findings: 13 rows patched (5 medium, 8 low), 2 deferred (frontmatter), the rest rejected with reasons in the triage log. An independent visual reviewer checked the screens in place of the founder.

**Follow-up review: true.** More than one medium was patched. The unverified risk is the patched `open_games` failure handling: a Game that fails every time is now only logged and retried each minute (deferred item 1), and no product path triggers it yet.

**Verification.**
- Backend: full suite 2518 passed after the patches; `ruff check` and `ruff format --check` clean. New tests each run under 1 s. One run hit `tests/test_sim_llm.py` once under load (passes alone and in the next full run).
- Frontend: typecheck, Vitest, check:copy, lint:colours and build pass.
- Playwright: full suite 262 passed (three workers, 4.2 min) after the review patches, on a rebuilt stack. Earlier runs at full parallelism flaked under load (homes, allocation), each passing alone.
- No migration was added or changed.

**Residual risks.** The e2e tests fake the opened answer, since no api route locks a session; the real answer is pinned by `test_open_games.py`. The race test cannot force either ordering; it asserts the invariant for whichever order the row lock gives.
