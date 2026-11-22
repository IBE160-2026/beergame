---
title: 'Story 8.10: Start one Class game or all of them as Lecturer'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'ffc06e1357cb968c4f4b24987d4a50ad904ad7d2'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized, multiple-goals]
deferred: []
---

<intent-contract>

## Intent

**Problem:** Only a Student can start a Class game (Story 6.5); a Lecturer cannot start one game from Spillinnsikt, nor every game that has not started in one action so a whole room begins together in a Lab hour (FR-22). The Game also does not record who started it or when.

**Approach:** `games.commands.start` gains an `actor` and stores `started_by`/`started_at` (migration 0060), audits a person's start, and answers `game_already_started` with Story 8.5's `acted_by`/`acted_at`. A Lecturer-only policy `games.start` guards two routes in `sessions`: one Game (`POST /api/games/{id}/start`, Spillstyring's «Start spillet») and a batch (`GET`/`POST /api/class-sessions/{id}/start-games`) that loops one `start` per Game. The Oversikt header gets the Lenke with the real count, leading to a «Start spill» page.

## Boundaries & Constraints

**Always:**
- Migration `0060_game_started_by.py`: `games.started_by uuid NULL` (no FK, as `paused_by`) and `started_at timestamptz NULL`; CHECK `started_by IS NULL OR started_at IS NOT NULL`. No backfill (older Games read None). Model columns in `games/models.py`; `tests/test_migrations.py` HEAD → 0060.
- `games.commands.start(game_id, *, actor: UUID | str | None = None)`: under the lock, as today, plus `repo.set_started(session, id, actor)` writing `started_at = now()` and `started_by = actor`; with an actor, `audit.record(actor, "game.started", {game_id}, {started_at}, started_at)`. Refusal `game_already_started` now carries `fields` `{acted_by: {kind, user_id}, acted_at}`: kind `student` when `started_by` is a Student seated now (`seated_students`), `system` when NULL, else `staff`; `acted_at` from `started_at` (None for an older Game). Code stays `game_already_started` (the stable code since Story 6.5; the epic's `already_started` is the same race).
- The Student's `start_own_game` passes `actor=user.id`.
- Readiness = `lifecycle == not_started` and settings snapshot stored (the lock gives it), and the Class session `is_locked`. New `games.service.startable_class_games(session, class_session_id) -> list[UUID]` (one read through `repo.class_games`). `GameInsight` gains `startable`, `started_by`, `started_at`.
- `authz`: policy `games.start` = Lecturer / OWNER only (an Assistant lecturer and Students are refused, AD-12).
- `sessions/overview.py`: `start_game(user, game_id)` (as `pause_game`: `_class_for(..., "games.start")`, then `games_commands.start(actor=user.id)`; refusals raised as `StartRefused(code, status, fields)`; returns Spillinnsikt). `start_games_page(user, session_id)` → the not-started ready games (`OverviewGameOut` from the summaries, names resolved) and the Class/session crumbs; `start_games(user, session_id, game_ids)` loops the given ids that are startable games of this session, one `start` per Game in its own transaction, skips `game_already_started`, `game_not_ready` and any other `CommandError`, logs and skips any other exception, and returns `{started, skipped}` (real counts). None → 403 for anyone but a Lecturer of the Class.
- Views: `GameInsightOut.can_start` (Lecturer and startable and locked), `started_by: str | None` (name now, via `classes.actor_names`), `started_at`. `ClassOverviewOut.startable: int` (Lecturer only, else 0; 0 before the lock).
- Routes in `sessions/routes.py`: `POST /api/games/{game_id}/start` (`startGame`, → `GameInsightOut`, 409 `game_already_started` with fields, 409 `game_not_ready`); `GET /api/class-sessions/{session_id}/start-games` (`getStartGames`, → `StartGamesOut`); `POST …/start-games` (`startGames`, body `StartGamesIn {game_ids: list[UUID], 1..1000}` → `StartedGamesOut {started, skipped}`). All three use `authz.require("games.start")`; Api client regenerated with `npm run api:generate`.
- Frontend: in `spillstyring.tsx` a `StartStyring` for `can_start`: consequence «Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.» above the primary «Start spillet» (full width below 1024 px); success → «Spillet er startet.» (`role="status"`, `tabindex="-1"`, focused) replaces it and stays while the block now shows the running game; `game_already_started` → read again, then «Spillet ble startet av Sara.» (name from the view's `started_by`, else «Spillet er allerede startet.»); other refusals inline, button stays active. `Spillstyring` shows the block for a not-started game only when `can_start` or a start result is held.
- Oversikt header: Lenke «Start spill som ikke har startet (12)» when `startable > 0` → `startGamesPath(sessionId)` (`/klasseokter/{id}/oversikt/start`). New page `modules/games/start-games-page.tsx` (route `app/(app)/klasseokter/[sessionId]/oversikt/start/page.tsx`): GuardedPage lecturerHome, crumbs … / Oversikt / «Start spill»; title «Start spill»; the list of games (game name and Seats as the Oversikt words them), the line «Spillene starter for alle i dem. Reglene for ventetid gjelder fra nå.», primary «Start 12 spill»; with none «Ingen spill venter på start.» and no button; pressing posts the listed ids, then routes to the Oversikt with `?startet=<n>` where «12 spill er startet.» (`role="status"`, focused, read once, the address cleaned as `useReturnTo`). Back/crumb returns to the Oversikt. 403 → AccessDenied.
- Copy in `nb.ts` (`spillstyring.start`, `overview.start`), pure helpers in `modules/games/start-games.ts` (link text, button text, result line, `startedParam`).

**Never:** no start before the lock or of a Game without a snapshot; no change to Story 6.5's Student start gate (Starting task); no Student-visible name of a staff starter; no mail; no change to the demo Class; no DB-vs-host time comparison; no game per test in backend tests beyond the batch test's 100 copies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Lecturer starts one | ready game | running, `started_by` = Lecturer, audit `game.started`, events game/session/user | — |
| Student started first | `started_by` = Student | — | 409 `game_already_started`, `acted_by {kind: student, user_id}`, `acted_at` |
| No snapshot | not locked yet | `can_start` false, not counted | 409 `game_not_ready` on the route |
| Assistant / Student / outsider | any of the three routes | — | 403 `forbidden` |
| Batch of 100 | 100 ready games | `started: 100, skipped: 0` | — |
| Batch with one already started and one not ready | 3 ids | `started: 1, skipped: 2` | skipped, not stopped |
| Foreign id in the batch | id of another session's game | skipped, untouched | — |
| Count 0 | none ready | no Lenke; page says none | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:1001` `start` (add actor, `set_started`, audit, fields); `:2356` `_paused_by` (shape to copy); `seated_students`; `audit` already imported.
- `backend/app/modules/games/repo.py:387` `set_lifecycle` (pattern for `set_started`); `:341` `class_games` (has_snapshot, `_listed`).
- `backend/app/modules/games/models.py:113` pause columns (add `started_by`, `started_at`).
- `backend/app/modules/games/insight.py:124` `GameInsight`, `:256` constructor.
- `backend/app/modules/games/service.py:283` `class_games` (pattern for `startable_class_games`).
- `backend/app/modules/sessions/service.py:1786` `start_own_game` (pass actor); `:541` `is_locked`.
- `backend/app/modules/sessions/overview.py:72` `class_overview` (`startable`), `:379` `game_insight` (`can_start`, `started_by`), `:554-633` staff Pause pattern; `_game_out` for the page's games.
- `backend/app/modules/sessions/{schemas.py (GameInsightOut, ClassOverviewOut), routes.py:358-435 (pause routes pattern)}`.
- `backend/app/platform/authz.py:113,161` (`games.pause` → add `games.start`).
- Tests: `tests/games/test_start.py` (command), `tests/games/test_takeover.class_game` and `test_set_snapshot.{SETTINGS,snapshot}` (ready games), `tests/games/helpers.{_dump,_restore,listening,query}`; `tests/sessions/test_game_end.{klass,clock,_empty}`, `test_open_games.confirmed`, `test_lock.MINUTE`, `test_dates.START`, `test_game_insight.insight`, `test_overview.overview`, `test_staff.{ASSISTANT,put_staff,call}`.
- Frontend: `src/modules/games/{spillstyring.tsx, staff-pause.tsx (PauseResult), overview-page.tsx (OverviewHeader, useReturnTo), overview.ts (seatTexts), api.ts}`, `src/modules/messaging/message-page.tsx` (page pattern), `src/modules/identity/homes.ts`, `src/copy/nb.ts`.
- e2e: `frontend/e2e/support/live-game.ts` (`liveClassGame`: add `start: false`), `classes.ts` (`lecturerPage`, `expectAccessible`, `expectReflow`), `spillstyring.spec.ts` pattern.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0060_game_started_by.py`, `games/models.py`, `tests/test_migrations.py` -- columns.
- `games/repo.py`, `games/commands.py`, `games/service.py`, `games/insight.py` -- actor, `set_started`, audit, fields, `startable_class_games`, insight fields.
- `platform/authz.py` -- `games.start`.
- `sessions/service.py` -- Student actor.
- `sessions/overview.py`, `schemas.py`, `routes.py` -- start one, batch page/action, `can_start`, `started_by`, `startable`.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- Frontend: `games/api.ts` (`startGame`, `getStartGames`, `startGames`, keys), `games/start-games.ts` (+ Vitest), `games/start-games-page.tsx`, route page, `games/spillstyring.tsx` (`StartStyring`), `games/overview-page.tsx` (Lenke and result line), `identity/homes.ts` (`startGamesPath`), `copy/nb.ts`, fixtures with the new fields.
- Tests: `tests/games/test_start_actor.py` (actor stored, audit, fields for student/staff/system, Student path stores Student); `tests/sessions/test_lecturer_start.py` (one start through the api, 409 fields after a Student's start, `game_not_ready`, 403s, `can_start`/`startable` for Lecturer not Assistant, batch skip/foreign ids, 100 games in one action); Vitest `start-games.test.ts` and `spillstyring.test.tsx` cases; e2e `start-games.spec.ts` (one start on Spillinnsikt, the Lenke, the page, the batch, the Oversikt line, axe + reflow at 320 and 1440).

**Acceptance Criteria:**
- Given a ready Class game, when the Lecturer opens Spillinnsikt, then Spillstyring shows the consequence line above the primary «Start spillet»; before the lock, and for an Assistant lecturer, nothing is offered.
- Given the Lecturer presses «Start spillet», then the game runs for all four Seats, «Spillet er startet.» has focus, `started_by`/`started_at` are stored and an audit row `game.started` names the Lecturer.
- Given a Student started first, then the Lecturer's start answers 409 `game_already_started` with `acted_by.kind = student` and the page reads «Spillet ble startet av Sara.».
- Given two ready games, then the Oversikt header shows «Start spill som ikke har startet (2)»; the page lists both with its line and «Start 2 spill»; pressing returns to the Oversikt showing «2 spill er startet.», and the Lenke is gone.
- Given 100 ready Class games, when the batch runs, then it answers `started: 100`.
- Given 1440 and 320 px, then the block and the page have no horizontal scroll and pass axe.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter (asked to weigh concurrency), edge-case hunter, verification gap and intent alignment, all on Sonnet as the orchestrator asked. All four hand-backs dropped, so the findings were read from `review-{blind,edge,verification,intent}-8-10.md` in the session scratchpad. The diff was taken against `HEAD` (the orchestrator committed `de170e6` on `epic-8` after the baseline) and leaves out the generated api client and `.docs`.
- verdicts: 36 findings — high 0, medium 2, low 25, false 9, maybe-false 0
- findings:
  - `[false]` `[reject]` blind-1: no test races two starts. `tests/games/test_start.py:228-243` races two `start` calls on one Game under the row lock; exactly one wins. The new `fields` are read under that same lock.
  - `[low]` `[reject]` blind-2: the batch's limit of 4 is per request, so two batches and other traffic could wait on the pool (10). A start holds one connection at a time; a pool wait queues (30 s), it does not fail. Two Lecturers of one Class pressing at once is unlikely, and a global limiter adds machinery.
  - `[low]` `[reject]` blind-3 / edge-1: up to 100 starts run inside one request, with no background job. 100 games take about 8 s in the test (4 at a time); an LLM Seat's Order is queued as a job, not called inline. The AC asks for the response to give the real count, which needs the synchronous answer.
  - `[low]` `[reject]` blind-4 / edge-2 / edge-claim-2: `skipped` lumps «started meanwhile», «not ready» and «failed», and the Oversikt shows only the started count. The AC asks for «12 spill er startet.» with the real count, which it shows; a failed start is logged. A double press cannot happen (the button is unavailable while pending and after success).
  - `[low]` `[patch]` blind-5 / edge-4 / verification-other-2: `acted_by.kind` came from the Seats held now, so a Student starter whose Seat was taken over since read as `staff`. `_started_by` now reads the Game's occupancy history (any Student who held a Seat). Test added (`test_a_student_taken_over_since_is_still_named_as_a_student`).
  - `[low]` `[patch]` blind-6 / verification-other-1: the Lecturer's own test game was started without an actor, so no `started_by` and no audit row. `start_test_game` now passes the Lecturer. The pre-0060 «system» label for a Game running at deploy time is kept (no backfill; local only).
  - `[low]` `[reject]` blind-7 / edge-7: `started_at` is the transaction's `now()`, which may predate a short lock wait. Every command of `games` stamps with the transaction clock (`paused_at`, `set_pause`), so the clocks stay comparable; the wait is milliseconds.
  - `[false]` `[reject]` blind-8: the 409 hands out the starter's id. Story 8.5's `acted_by` shape is ids only by design, to a Lecturer of the Class; names are resolved from the view.
  - `[medium]` `[patch]` blind-9 / edge-3: a ready game with no Student in a Seat was counted and could be started, and its AI players would then play it out in the request, which the epic forbids before the Play deadline. `startable_class_games` and `GameInsight.startable` now require a Student in a Seat; `start_game` answers 409 `game_not_ready` for such a game. Test added (an AI-only ready game is not listed, not counted, refused and skipped by the batch). The Starting task gate stays the Student's own: the story's Lecturer starts the game for the room.
  - `[false]` `[reject]` blind-10: the re-read after a lost race has no `.catch`. `invalidateQueries` resolves when a refetch fails; it never rejects here.
  - `[low]` `[reject]` blind-11 / edge-8 / intent-3: `replaceState(null)` and a hand-typed `?startet=99`. Story 7.7's `useReturnTo` uses the same `replaceState` on this page and its e2e passes; a hand-typed count misleads only its typist.
  - `[low]` `[reject]` blind-12: `game_ids` is capped at 1000 while the page is not. A Class session of 4000 Students is beyond the product's scale.
  - `[low]` `[reject]` blind-13: a batch emits one `session:` event per game. That is each command's own event (AD-8); the Oversikt answers unchanged reads with 304. Coalescing is a platform change.
  - `[low]` `[patch]` blind-14: two weak test assertions (`!= ["not_started"] * 3`, `assert seated`). Replaced with exact ones. The rest of the item is false: no HTTP path passes a non-UUID actor, an Assistant gets 403 before any id is read, and the route maps every command status it can meet.
  - `[low]` `[reject]` edge-5: a start that commits and then reads Spillinnsikt as None (access revoked in between) answers 403. It needs the Lecturer removed from the Class within the same request.
  - `[low]` `[patch]` edge-6: after a lost race the re-read can hide «Start spillet» before the line is set, so the remounted block did not move focus. The line now takes focus whenever its result appears (`useEffect` on `result`); the e2e lost-race step asserts the focus.
  - `[low]` `[patch]` edge-claim-1: the empty page read «Ingen spill venter på å bli startet.»; the spec says «Ingen spill venter på start.». Copy aligned.
  - `[low]` `[patch]` verification-1: the batch's per-game failure isolation was untested. `test_one_failing_start_never_stops_the_others` makes one start raise `CommandError` and one `RuntimeError`; the third starts and the answer is 200 `{started: 1, skipped: 2}`.
  - `[low]` `[patch]` verification-2: a refusal on a Game started before 0060 was untested. `test_a_game_started_before_the_start_was_recorded_names_no_one` asserts `{kind: system, user_id: None}` and `acted_at: None`.
  - `[low]` `[patch]` verification-3: the lost-race UI was untested. `start-games.spec.ts` now holds a second page on the other game, lets the batch start it, presses «Start spillet» there and asserts «Spillet ble startet av {name}.» with focus.
  - `[false]` `[reject]` intent-1: `game_already_started` instead of the literal `already_started`. The AC's contract is Story 8.5's shape, which the refusal carries; the code is the stable one since Story 6.5 (Design Notes).
  - `[false]` `[reject]` intent-2: the naming line is transient. The AC places it right after the lost press («the page shows the running game with a line naming who started it»); `started_by` stays in the view.
  - `[false]` `[reject]` intent-4: 100 games are tested at the api, not through the UI. The AC asks that «a test starts 100 Class games in one action»; the action is the api call the button makes.
  - `[false]` `[reject]` intent-5: the single start lives in `sessions`. The command stays in `games`; the staff routes of Stories 8.5 and 8.7 live in `sessions` the same way.
  - `[false]` `[reject]` intent-6: `liveClassGame` now builds on `lockedClassGames`, which reads the new list. Every spec that uses it passed (163 tests).
  - `[false]` `[reject]` intent (surface summary): the Assistant's UI view is not exercised in e2e. The api answers `can_start: false`, `startable: 0` and 403 for an Assistant (backend tests), and the block renders nothing for `can_start: false` (Vitest).
- Count: 14 blind, 8 edge-case plus 2 claims, 3 verification gaps plus 2 other, 6 intent divergences plus its surface summary. Findings with the same root cause share one row, named by every member (36 findings in 26 rows).

## Design Notes

The batch takes the ids the page listed, so «Start 12 spill» never starts a 13th game that became ready meanwhile; ids of other sessions or games already started are skipped and counted, never refused, so the action is repeat-safe. The result travels to the Oversikt as `?startet=12` and is read once, as Spillinnsikt's `?spill=` return is.

The refusal code stays `game_already_started`: renaming it would break Story 6.5's Student path and its tests for no observable gain; its `fields` follow Story 8.5's shape.

The batch starts at most 4 Games at once (`BATCH_START_CONCURRENCY`, below the pool of 10), each start still its own command and transaction on its own Game row: 100 starts one after another took 14 s in the test, 4 at a time about 8 s. A game no Student holds a Seat in is never offered or started (review): its AI players would play it out at once, and AI players never play a Class game on their own before the Play deadline (Story 8.14).

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_start.py tests/games/test_start_actor.py tests/sessions/test_lecturer_start.py tests/test_migrations.py tests/test_imports.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before the commit: the full suites and the e2e specs the runbook names, plus `start-games.spec.ts`.

## Auto Run Result

Status: done

**Summary.** A Lecturer can start one Class game from Spillstyring, or every game that has not started from a «Start spill» page, and the Game records who started it and when.

- **Store.** Migration 0060 adds `games.started_at` and `started_by` (ids only, no backfill).
- **Command.** `games.commands.start(…, actor=)` stores both under the Game lock and audits a person's start (`game.started`). A start that comes second answers 409 `game_already_started` with Story 8.5's `acted_by` (`student`, `staff` or `system`) and `acted_at`. The Student's start (Story 6.5) and the Lecturer's test game now pass their actor.
- **Readiness.** A game may start when it has not started, has its snapshot (the lock) and has a Student in a Seat, in a locked Class session.
- **Api.** The policy `games.start` (Lecturers only) guards three routes in `sessions`:
  - `POST /api/games/{id}/start` answers Spillinnsikt.
  - `GET /api/class-sessions/{id}/start-games` lists the games that may start.
  - `POST …/start-games` starts the listed ones, 4 at a time, each in its own transaction. It skips the rest and answers `{started, skipped}`.
  - Spillinnsikt gains `can_start`, `started_by` (name now) and `started_at`. The Oversikt gains `startable`.
- **Screens.**
  - Spillstyring shows «Spillet starter for alle fire. …» above the primary «Start spillet». «Spillet er startet.» then takes focus. After a lost race the line reads «Spillet ble startet av Sara.».
  - The Oversikt header has «Start spill som ikke har startet (n)», which is hidden at 0.
  - The «Start spill» page lists the games with the line and «Start n spill». It returns to the Oversikt, which reads «n spill er startet.» with focus.

**Files changed**
- Backend:
  - `migrations/versions/0060_game_started_by.py` (new) and `games/models.py`: the columns.
  - `games/{commands,repo,service,insight}.py`: the actor, `set_started`, the refusal fields, `startable_class_games` and the insight fields.
  - `platform/authz.py`: `games.start`.
  - `sessions/{overview,routes,schemas,service}.py`: the routes, the batch, the view fields, and the Student's and test game's actor.
- Frontend:
  - `modules/games/{start-games.ts,start-games-page.tsx}` (new) and the route `app/(app)/klasseokter/[sessionId]/oversikt/start/page.tsx`.
  - `games/{spillstyring,overview-page,api}.tsx/ts`, `identity/homes.ts`, `lib/api/topics.ts` and `copy/nb.ts`.
  - `lib/api/{openapi.json,schema.ts}`: regenerated.
- Tests:
  - New: `tests/games/test_start_actor.py` and `tests/sessions/test_lecturer_start.py`.
  - Updated: `test_migrations.py` (HEAD 0060); `test_staff_pause_view.py` and `test_staff_takeover_view.py` (the Student's start is now audited); `test_test_game.py` (its stub takes `actor`).
  - Vitest: `start-games.test.tsx` (new), `topics.test.ts`, and fixtures in six tests.
  - e2e: `start-games.spec.ts` (new); `support/live-game.ts` now has `lockedClassGames` under `liveClassGame`.

**Review.** Four Sonnet reviewers returned 36 findings: high 0, medium 2 (one root cause), low 25, false 9.
- Patched (medium): a game with no Student is never offered or started.
- Patched (low):
  - `acted_by.kind` from the occupancy history;
  - the test game's actor;
  - focus on the lost-race line;
  - the empty-page copy;
  - exact test assertions;
  - new tests for failure isolation, a pre-0060 refusal and the lost-race UI.
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended. Patched entries: high 0, medium 1, low 8.

**Verification** (after the patches)
- **Backend.** The full suite with `--maxprocesses=8` ran 3041 tests, and 2 failed: `tests/sessions/test_staff_takeover_view.py::test_an_assistant_may_and_anyone_else_is_refused` and `tests/sessions/test_test_game.py::test_only_the_owner_starts_one_and_only_before_the_start_date`. Both were real consequences of this change (the Student's start now writes an audit row, and the stubbed `start` lacked `actor`), not flakes. The tests were fixed and both files pass. The backend code did not change after that run. ruff check and format are clean.
- **Frontend.** Typecheck, Vitest (73 files, 885 tests), `lint:colours`, `check:copy` and `next build` all pass.
- **End to end.** The stack was rebuilt after the last frontend change. Playwright with `--workers=4` ran 163 tests in 28 specs: start-games, overview, varselband, spillstyring, game-insight, live-updates, homes, student-home, game-start, the play-screen specs (guided-week, order-*, seat-status, week-*), and every spec that uses `liveClassGame`. 162 passed. `e2e/game-card.spec.ts › waiting for others only: Hjem has no primary button` failed once and passed when rerun alone. It uses mocked routes and the demo Student, with no start involved.
- **Accessibility.** axe and reflow ran on Spillstyring's start block and on the «Start spill» page, at 320 px and at 1440 px.
- **Slow tests (over 1 s).**
  - `test_lecturer_start.py::test_a_hundred_class_games_start_in_one_action` takes 7.7–9.5 s. It copies one game's rows 99 times and starts all 100 through the api, as the AC asks.
  - The other three tests in that file take 2.1 s, 2.1 s and 1.3 s. Each one allocates a Class session through the api.
  - The command tests take 0.3–0.4 s.

**Decisions taken instead of the founder.**
- The refusal keeps the existing code `game_already_started` (Story 6.5), not the epic's literal `already_started`. Its `fields` follow Story 8.5's shape.
- The Lecturer's start skips the Student's Starting task gate: the Lecturer starts the game for the room.
- A game with no Student in a Seat is not offered and is refused with `game_not_ready`: AI players never play a Class game alone before the Play deadline.
- The batch posts the ids the page listed, starts 4 at a time, and counts as skipped any id that is foreign, already started, not ready or failed.
- The result count travels to the Oversikt as `?startet=n` and is read once.
- A start with no person (simulation, pre-0060) reads as `system`.
- The Lecturer's test game start is now audited.
- Draft copy `[ASSUMPTION]`:
  - «Spillet ble startet av Sara.» and «Spillet er allerede startet.»;
  - «Spillet kan ikke startes før Startdatoen.»;
  - «Ingen spill venter på start.» and «Spill som ikke har startet»;
  - the failure lines.
- The orchestrator asked for the implementation to be done in the builder's own context, so the skill's implementation subagent was not used.

**Residual risks.**
- A batch of 100 runs about 8 s inside one request; a proxy timeout below that would show a failure although the games started.
- `skipped` does not say why, and only the started count is shown.
- The visual check is left to the separate visual agent.
