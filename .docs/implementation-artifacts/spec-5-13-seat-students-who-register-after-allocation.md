---
title: 'Story 5.13: Seat Students who register after the allocation'
type: 'feature'
created: '2026-11-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'd319a26eb785a4b99f8aa56e0a46813c59c85449'
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student who registers after the allocation is confirmed holds no Seat: the Klasseøkt only counts them as «ikke med», and after the lock nothing ever seats them. A Student removed from the Roster after the Class games opened keeps a Seat in a game that has not started, so the group waits for someone without access.

**Approach:** Two new `ops.sweep` due actions in `sessions`. `sessions.seat_late_registrant` finds registered Students without a Seat in a Class session with a confirmed allocation and calls `service.seat_late_registrant(class_session_id, user_id)`: before the lock a random free Seat (or a new Class game), after the lock a random AI-held Seat of an opened, not-started game, through `games.commands.assign_seat` (`replace=` after the lock). `sessions.replace_removed_student` finds Students no longer registered who hold a Seat in an opened, not-started game of a locked session and calls `service.replace_removed_student(…)`, which gives the Seat the AI mode's player. `service.students_without_seat` lists who is left; the «Fordeling» block names them and marks a removed Student's Seat.

## Boundaries & Constraints

**Always:**
- Each action: one item per transaction, ids only (`(class_session_id, user_id)`), under the Class session's row lock, idempotent (a seated Student, a registered one for the removal, an unconfirmed allocation or an archived Class: nothing, returns False). `classes` never imports `sessions`.
- Before the lock (`is_locked` false): a random Class game with a free Seat (no current occupant, `not_started`), a random free Role in it; none free → `games.commands.create` (purpose `class`, next game number, no settings) and a random Role; its other Seats get AI players at the lock (Story 5.12's open).
- After the lock: only Class games with their snapshot and `lifecycle = not_started`; a random one with an `llm`/`rule_based` Seat, a random such Role, `assign_seat(…, replace=True)` (Student row from Week 1, reason `initial`; the AI row stays). A game that started meanwhile (`game_already_started` under the Game row lock) is skipped; with none left the Student stays without a Seat.
- On seating: the draft gains the assignment (the user's earlier entries dropped), revision + 1; the Student gets `ALLOCATION_NOTICE` keyed `allocation_confirmed:{draft}:{revision}:{user}`; `user:<id>` for the Student and the other Students of that game; `session:<id>`.
- Removal: only when `locked_at` is set; AI kind from the session snapshot's runtime (`llm` with a model config, else `rule_based`), `assign_seat(…, replace=True)`, reason `initial` (cost-limit fallback as in `assign_seat`). Started games untouched. `user:<id>` for the removed Student and the game's other Students; `session:<id>`.
- Finders only return items the action can act on (no endless no-op items): late registrants of non-archived sessions with a confirmed draft that are not locked, or locked with an opened not-started game holding an AI Seat; removed Students in opened not-started games of locked, non-archived sessions.
- `students_without_seat(class_session_id)`: the registered Students holding no Seat in the session's Class games, sorted. `AllocationOut.without_seat` (`user_id`, `name`) is filled from it once the session is locked; a removed Student's Seat in a started game shows as «Ikke lenger i Klassen» (name None).

**Never:** No migration. No new cron or sweeper outside `ops.sweep`. No Seat in a started Game. No Takeover (Epic 8), no make-up (Epic 13). No sleeps; no DB-vs-host clock comparison. No change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Before lock, free Seat | confirmed, 5 Students in 2 games, 6th registers | sweep seats them in a free Seat of game 2; draft revision +1; notice; events | — |
| Before lock, all full | confirmed, 4 Students, 5th registers | new Class game 2 with the Student; no settings | — |
| After lock, AI Seat | opened, 3 Students + 1 AI, 4th registers | replaces the AI; history keeps AI row; Klasseøkt shows the name | — |
| After lock, nothing free | opened games full of Students, or all started | no Seat; finder returns nothing; `without_seat` lists them | — |
| Second sweep | already seated | finder empty; act returns False | — |
| Not confirmed | draft unconfirmed | nothing (the lock allocates) | — |
| Race | `start` vs seating on the only game | started game keeps its Seats; Student seated before start or not at all | `game_already_started` caught |
| Removed, not started | locked, opened, Student off Roster | Seat gets AI (`rule_based`/`llm`, `initial`) | — |
| Removed, started | game running | Seat untouched; block shows «Ikke lenger i Klassen» | — |

</intent-contract>

## Code Map

- `backend/app/modules/ops/sweep.py:59` `DUE_ACTIONS` -- append `sessions.seat_late_registrant` and `sessions.replace_removed_student` after `sessions.lock` (so a lock opens games first in the same sweep).
- `backend/app/modules/sessions/service.py` -- new section after `lock_refused_mail_context`: `late_registrants(now)`, `seat_late_registrant(class_session_id, user_id, *, now)`, `removed_students(now)`, `replace_removed_student(…)`, `students_without_seat`, sweep wrappers taking `(item, now)`. Reuse `repo.session_row(lock=True)`, `repo.draft_of/update_draft`, `ALLOCATION_NOTICE`, `SEAT_ORDER`, `_opened_out` (`:1368`) for `without_seat`.
- `backend/app/modules/sessions/repo.py` -- `confirmed_sessions(s)`: (id, class_id, start_at, locked_at, snapshot) of sessions whose draft is confirmed.
- `backend/app/modules/games/service.py:126` `class_games` -- already gives Seats with occupant kind and user; add `student_seated(s, class_session_id, user_id)` (wraps `repo.student_seated`) and `class_sessions_with_unstarted_games(s)`.
- `backend/app/modules/games/commands.py:458` `assign_seat` -- unchanged; `replace=True` only for `not_started` games; raises `CommandError("game_already_started")` under the row lock.
- `backend/app/modules/classes/service.py:607` `registered_students`, `:614` `student_names`, `:214` `is_writable` -- read-only reuse.
- `backend/app/platform/events/registry.py` -- `sessions.seat_late_registrant`, `sessions.replace_removed_student`: `{game, session, user}`.
- `backend/app/modules/sessions/schemas.py:352` `AllocationOut` -- `without_seat: list[AllocationStudentOut] = []`.
- `frontend/src/modules/sessions/allocation-panel.tsx`, `allocation.ts`, `frontend/src/copy/nb.ts` (`sessions.allocation`) -- «Registrert uten sete: …» line in the block and the panel; `openapi.json`/`schema.ts` regenerated.
- Tests: `backend/tests/sessions/test_late_registrants.py` (new; reuse `test_open_games.confirmed/holders/games_of`, `test_dates.student_of`, `test_lock.dated`), `frontend/e2e/class-session-lock.spec.ts` (route-faked opened answer with `without_seat` and a removed Seat), `allocation.test.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/service.py`, `repo.py` -- `student_seated`, `class_sessions_with_unstarted_games`.
- `backend/app/modules/sessions/{repo,service,schemas}.py`, `README.md` -- finders, actions, `students_without_seat`, `without_seat`.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py` -- due actions, topics.
- `backend/tests/sessions/test_late_registrants.py` -- every matrix row, events, notice, race.
- `frontend/src/modules/sessions/*`, `nb.ts`, e2e -- without-seat line, removed marker, axe at 320/360/1440.

**Acceptance Criteria:**
- Given a confirmed Class session and a Student who registers after it, when `ops.sweep` runs, then `sessions.seat_late_registrant` seats them (before the lock in a free Seat or a new Class game; after it in an AI-held Seat of a not-started game, AI row kept), and a second sweep acts on nothing.
- Given a seating, then the Student gets the allocation notice, they and the game's other Students get `user:<id>`, staff `session:<id>`, and `GET …/allocation` lists the new name where «KI-spiller» was.
- Given a locked session with no not-started game holding an AI Seat, when the sweep runs, then nothing is assigned, `students_without_seat` returns the Student, and the Klasseøkt «Fordeling» block names them as registered without a Seat.
- Given a locked session and a removed Student in an opened not-started game, when the sweep runs, then `sessions.replace_removed_student` gives the Seat the AI mode's player (reason `initial`); in a started game the Seat is unchanged and the block shows «Ikke lenger i Klassen».
- Given `start` and the seating racing on the same Game, then a started Game's Seats never change.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 34 findings — high 0, medium 0, low 20, false 11, maybe-false 3
- findings:
  - `[false]` `[reject]` blind: `repo.student_seated` not in the diff — it exists since Story 5.9 (games/repo.py:123); `openapi.json` was left out of the review diff on purpose (generated; `schema.ts` is in it).
  - `[low]` `[patch]` blind: seating ran before the removal, so a Seat freed by a removal waited a minute — the removal now runs first in `DUE_ACTIONS`; test `test_a_seat_a_removal_frees_takes_a_late_registrant_in_the_same_sweep`.
  - `[low]` `[patch]` blind: a without-Seat Student with no name read «Ikke lenger i Klassen» — the api now drops ids `student_names` no longer names (removed between the reads) and `name` is a required string; the web fallback is gone.
  - `[low]` `[reject]` blind: the sweep raises the draft revision under a Lecturer's open move — the move answers `allocation_changed`, which already says «Fordelingen er endret siden du åpnet den» and reloads the draft (Story 5.10).
  - `[low]` `[reject]` blind: the draft keeps a removed Student after the lock — after the open the block reads the Seats, not the draft, and the allocation mail checks the Roster; a re-registered Student's old entries are dropped when seated.
  - `[low]` `[reject]` blind: `missing_count` and `without_seat` are separate — the panel shows `without_seat` in place of the count once it is filled; both come from the same Seats after the open.
  - `[low]` `[patch]` blind: README claimed the finder costs nothing each minute — wording corrected; the scan itself is kept (one query skips locked sessions with no unstarted game; a confirmed session per Class is small).
  - `[false]` `[reject]` blind: more Students returned than AI Seats, failing every minute — the surplus finds no Seat once, and the next finder sees no AI Seat and returns nobody.
  - `[false]` `[reject]` blind: the two actions judge "locked" differently — both act on nothing between the Start date and the open (seating needs an opened game, the removal `locked_at`); documented in the README.
  - `[false]` `[reject]` blind: no guard on a null `snapshot` — `ck_class_sessions_lock` sets `locked_at` and `snapshot` together.
  - `[low]` `[reject]` blind: a long without-Seat line — after the lock only Students no AI Seat could take are listed; a handful at most.
  - `[low]` `[patch]` blind: no test for two late registrants in one sweep — added `test_two_late_registrants_in_one_sweep_share_the_new_class_game`; the re-registered case is covered by the draft de-duplication, not tested.
  - `[low]` `[reject]` blind: `allocation_of` reads twice — names are now filtered (patch above); a transient disagreement lasts one read.
  - `[low]` `[reject]` intent: screen criteria tested against a stubbed answer — no api route locks a session; the backend tests pin the answer's fields, as in Stories 5.11 and 5.12.
  - `[low]` `[patch]` intent: the race test does not force the refusal path — added `test_a_game_started_after_it_was_read_refuses_under_its_row_lock` (the read is made stale; `assign_seat` refuses under the Game row lock and nothing is seated).
  - `[low]` `[reject]` intent: randomness not checked — `_rng` is `SystemRandom`; only one game had free Seats by design in the tests; a statistical test would be slow.
  - `[low]` `[patch]` intent: "from Week 1" not asserted — `history()` now asserts `from_week` 1 on every row.
  - `[low]` `[reject]` intent: removal set by SQL, not the Story 4.8 route — the same pattern as Story 5.12's tests; the route sets the same `removed_at`.
  - `[false]` `[reject]` intent: the two locked predicates — as above.
  - `[false]` `[reject]` intent: AI level or config per Seat — the AI mode gives only the kind; the level and config are the Game's snapshot runtime.
  - `[false]` `[reject]` intent: `without_seat` broader than the story's case — after the lock it is exactly the registered Students the finder could not seat, which includes the story's case.
  - `[false]` `[reject]` intent: draft rewrite not in the story — needed: the allocation notice's mail reads the draft (`allocation_mail_context`).
  - `[low]` `[patch]` intent: «removed» label for a nameless without-Seat Student — same patch as the null-name row.
  - `[low]` `[patch]` edge: null name in `withoutSeatLine` — same patch.
  - `[low]` `[reject]` edge: separate transactions in `allocation_of` — as the blind row.
  - `[false]` `[reject]` edge: an older api without `without_seat` — web and api ship together behind one proxy; the field is required in the schema.
  - `[maybe-false]` `[reject]` edge: both finders scan every confirmed session twice a minute — would only be low: a session is skipped by one in-memory test once locked with no unstarted game; would settle with a load measure over a term's sessions.
  - `[maybe-false]` `[reject]` edge: a never-started opened game is re-scanned forever — would only be low: Class games start in Epics 6 and 8; the scan reads, never writes.
  - `[low]` `[reject]` edge: the Roster read outside the row lock — a Student removed in that instant is seated, and `replace_removed_student` gives the Seat to an AI player next minute; as Story 5.9's confirm.
  - `[false]` `[reject]` edge: null snapshot — the CHECK above.
  - `[false]` `[reject]` edge: other `CommandError`s fail the item each minute — before the lock only free Seats are tried under the session row lock that every seating takes; after it `replace` accepts an occupied Seat, and `student_seated` is checked under the same lock.
  - `[maybe-false]` `[reject]` edge claim: README "costs nothing" — corrected (patch above).
  - `[low]` `[patch]` verification-gap: `without_seat` stays empty before the lock is untested — asserted in `test_a_late_registrant_is_counted_missing_and_a_removed_student_loses_the_name` and before the sweep in `test_before_the_lock_a_late_registrant_takes_a_free_seat`.
  - `[low]` `[patch]` verification-gap other: the null-name fallback untested — the fallback is removed (patch above).

No independent visual reviewer was run here: the caller's orchestrator runs its own visual check after this build.

## Design Notes

Founder-level decisions taken here:
- Before the lock the late registrant is seated only once an allocation is confirmed; before that the Lecturer's preview counts them «ikke med» (Story 5.8) and the lock allocates everyone.
- Between the Start date and the opening of the games (lock not yet run, e.g. a missing provider key) nobody is seated; the next sweep after the open does it.
- Removal before the lock is left to the open (Story 5.12 `keep_students`), so the Lecturer's confirmed groups do not change shape before the Start date.
- A re-registered Student's earlier draft entries are dropped when they are seated again, so the draft never holds one Student twice.
- `without_seat` is filled only once the session is locked; before it a late registrant is seated within a minute.
- Implementation in the builder's own context (the runbook: sub-agents stop when the turn ends).
- The removal runs before the seating in `DUE_ACTIONS` (review), so a freed Seat is taken in the same minute.
- `without_seat` names only Students `student_names` still names; the line reads «N registrerte studenter har ikke sete: …» (draft copy) in the closed block and in the panel, where it replaces the «ikke med» count.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_late_registrants.py tests/sessions/test_open_games.py tests/games/test_registry.py -q` -- expected: pass, each test under 1 s
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` and Playwright -- expected: pass

## Auto Run Result

Status: done

**Summary.** Two new `ops.sweep` due actions, one Student per transaction with ids only, under the Class session's row lock. `sessions.replace_removed_student` (`removed_students` → `replace_removed_student`) gives the Seat of a Student no longer on the Roster, in an opened Class game that has not started, the AI mode's player (`llm` with a model config, else `rule_based`, reason `initial`) through `games.commands.assign_seat(replace=True)`; started games are left alone. `sessions.seat_late_registrant` (`late_registrants` → `seat_late_registrant`) seats a registered Student without a Seat in a confirmed Class session: before the lock a random free Role of a random game with a free Seat, or a new Class game (AI players at the open); after the lock a random AI-held Seat of an opened, not-started game, the AI row kept. A game that started meanwhile refuses under its row lock and is skipped. The draft gains the Seat (revision + 1), the Student gets the allocation notice, they and the game's other Students `user:<id>`, the staff `session:<id>`. `students_without_seat` lists who is left; once locked `GET …/allocation` names them in `without_seat`, and the Klasseøkt «Fordeling» block and panel say «N registrerte studenter har ikke sete: …». A removed Student's Seat in a started game keeps showing «Ikke lenger i Klassen». `classes` is unchanged.

**Files.**
- `backend/app/modules/sessions/service.py`: finders, actions, `students_without_seat`, `without_seat` in `allocation_of`.
- `backend/app/modules/sessions/{repo,schemas}.py`, `README.md`: `confirmed_sessions`, `AllocationStudentOut`, `AllocationOut.without_seat`; docs.
- `backend/app/modules/games/{repo,service}.py`: `class_sessions_with_unstarted_games`, `student_seated`.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py`: two due actions, their topics.
- `frontend/src/modules/sessions/{allocation.ts,allocation-panel.tsx}`, `frontend/src/copy/nb.ts`: the without-Seat line; `openapi.json`/`schema.ts` regenerated.
- Tests: new `backend/tests/sessions/test_late_registrants.py` (15 tests), `without_seat` in three allocation literals and one assertion in `test_allocation.py`; `allocation.test.ts`; e2e `class-session-lock.spec.ts` (without-Seat and removed-Student view, axe at 320/360/1440) and a fixture field in `class-session-allocation.spec.ts`.

**Review.** 34 findings: 9 rows patched (all low: sweep order, name filter, README wording, five test additions), 0 deferred, the rest rejected with reasons in the triage log. Follow-up review: false (no high or medium patched).

**Verification.**
- Backend: full suite 2538 passed; `ruff check` and `ruff format --check` clean. Every new test runs under 1 s (slowest 0.87 s).
- Frontend: typecheck, Vitest (433), check:copy, lint:colours and build pass.
- Playwright: full suite 263 passed (three workers, 3.6 min) on a rebuilt stack. Earlier full runs at default parallelism had load flakes in unrelated mail/registration specs (invitation, password reset, roster send, registration status), each passing alone.
- No migration was added or changed.

**Residual risks.** The finders read the Class games and Roster of every confirmed session that is not locked or still has an unstarted opened game, twice a minute; fine for a term's sessions, worth watching if old sessions pile up with never-started games. The e2e screen tests fake the locked answer (no api route locks a session); the real answer is pinned by `test_late_registrants.py`.
