---
title: 'Story 6.1: See my Class game, Role and Seats on Hjem'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'bc439a3150980d3da0f4ff24c8a9eedf91029425'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-17-let-students-choose-class-game-and-seat.md'
warnings: ['oversized']
deferred:
  - summary: >-
      At 360 px with 200 % text the shared top bar stacks the product name, the User's name and «Logg ut» on three rows before the page title.
    evidence: |-
      Visual review of Hjem (screenshot witha-360-t200). The header is Story 3.3's, unchanged by this story.
    location: >-
      frontend/src/components/app-header.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** From the Start date a Student's Hjem still shows only «Du får Rolle og spill på startdatoen.» under each Class (Story 4.5, patched by 5.17): no Class game, Role, Seats, Stegene, deadline or Lab hours, and there is no `progress` module to say which step is done.

**Approach:** Extend the Student's existing `GET /api/me/class-sessions` (the home endpoint) with the game card (`game`, read through the new `games.service.student_game` and `games.views.table_status`, only once the session is locked) and the six Stegene states computed in the api from the new `modules/progress`. Add `authz.own_seat` and a game-keyed Student read that refuses anything but the Student's own game with 403. Rebuild Hjem per Class session: game card with Setene (Fabrikk first, «KI-spiller» in text), or the Start-date line, plus Stegene, Neste frist, Labtimer and Obligatorisk.

## Boundaries & Constraints

**Always:**
- `progress` (new): table `progress_steps` (migration 0045: `id` uuid pk, `user_id` FK users CASCADE, `class_session_id` FK class_sessions CASCADE, `step` text CHECK the closed enum `starting_task, class_game, explanation, debrief, quiz_passed, replay, test_submitted, assessment_ready`, `at` timestamptz, UNIQUE `(user_id, class_session_id, step)`). `service.record_step(user_id, class_session_id, step, at, *, within=None) -> bool` is idempotent (`ON CONFLICT DO NOTHING`; True only when it inserted) and, only when it inserted, emits `user:<id>` and `session:<id>` (registry `progress.record_step`). `has_step(...)`, `steps_of(session, user_id, class_session_ids)`. `progress` imports no `app.modules` code (test).
- `authz.own_seat(user, game=None) -> Select`: ids of Games where the User has any `seat_occupancy` row (holds or has held a Seat), by table name only. Policy `games.read_own` (any User; the scope decides).
- `games.service.student_game(session, user_id, class_session_id) -> StudentGame | None` (`game_id`, `number`, `role`): the Class game of the session joined through `own_seat`; the Seat the Student holds now, else the one they held last. The only way any module finds a Student's game.
- `games.views.table_status(session, game_id, viewer_id, names) -> TableStatus`: each Seat Fabrikk first `{role, holder: student|ai|free, name, mine}`; `names` is an async resolver the caller passes (`classes.service.student_names` bound to the Class); a Student no longer in the Class has `name=None`. Never stored, never in `SeatState`, never sent to an LLM.
- `EnrolledSessionOut` adds `game: StudentGameOut | None` (`id, number, role, seats[]`), set only when `is_locked` and `student_game` finds a Seat; and `steps: list[StepOut]` (`step` ∈ `class_game, debrief, quiz, replay, test, report`; `state` ∈ `done, current, locked`), always six, in that order, mapped from `class_game, debrief, quiz_passed, replay, test_submitted, assessment_ready`. With no game: every step not done is `locked`. With a game: done steps `done`, the first not done `current`, later ones `locked`.
- `GET /api/me/games/{game_id}` (sessions router, `games.read_own`): `StudentGameOut` for the Student's own game in a locked session; malformed, unknown, another's game, or a session not yet locked → 403 `forbidden` identical in every case.
- Hjem (Student): per Class heading, per Class session of it (labelled «Klasseøkt N» only when the Class has more than one): with `game`, heading «Spill 17 · Du er Grossist» and «Setene» list (Role, then name, «KI-spiller», «ledig» or «Ikke lenger i Klassen»; own row adds «(deg)»); without, «Du får Rolle og spill på startdatoen.» (or 5.17's «Velg spill og sete» Lenke while `seat_choice_open`, or its drawn line). Then Stegene, then «Neste frist» («Spillfrist ti. 8. des.»), «Labtime» rows («to. 26. nov. 14:15, Datalab A2») and «Obligatorisk» when set. A Class with no session shows the Start-date line only. Skjelett while loading, page error + «Prøv igjen» on failure. Copy in `nb.ts`; new strings `[ASSUMPTION]`.
- Stegene component in `frontend/src/components/stegene.tsx`: an ordered list; current step bold with «pågår» in text, done with «ferdig», locked rows `ink-secondary` with the lock line (e.g. «Replay, åpnes når du har bestått Debrief-quizen.»). Markers are `aria-hidden`; state never by colour alone. Takes items already in words; holds no rule.

**Never:** No game card before the lock, even after a confirmed allocation. No reading of Class games outside `student_game`/`table_status`. No web-side rule for which step is open. No change to the demo Class or to Epic 5 behaviour. No Spillkort, Setestatus order status or «Les reglene» (6.2, 6.14, 6.17). No SSE (6.4). No edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Before start | confirmed allocation, not locked | `game: null`, six steps `locked` | — |
| Locked, seated | locked, games opened | `game` number/role, four seats Fabrikk first, AI «ai» with no name, own `mine` | — |
| Locked, no Seat | registered after lock, not yet seated | `game: null`, steps locked | — |
| Steps | `class_game` recorded | class_game `done`, debrief `current`, rest `locked` | — |
| Idempotent | `record_step` twice | one row; second returns False and emits nothing | — |
| Own game | GET `/api/me/games/{own}` locked | 200 `StudentGameOut` | — |
| Other's game | another Class game / unknown uuid / malformed / own but not locked | — | 403 `forbidden` |
| Removed classmate | Student removed after lock | seat `student`, `name: null` | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- add `own_seat` next to `classes_enrolled_by` (table refs by name); `POLICIES["games.read_own"]`.
- `backend/app/platform/events/registry.py` -- `progress.record_step: {session, user}`.
- `backend/app/modules/progress/{__init__,models,service}.py` (new) -- table + service above; `backend/migrations/env.py` imports `app.modules.progress.models`; `backend/migrations/versions/0045_progress_steps.py` (new).
- `backend/app/modules/games/repo.py` -- `student_seats(session, class_session_id, user_id)` (rows joined through `authz.own_seat`: game id, number, role, holds-now, last row id); reuse `_latest_occupancy`, `seats_with_occupant`.
- `backend/app/modules/games/schemas.py` -- `TableSeat`, `TableStatus`; `service.py` -- `StudentGame`, `student_game`, `own_game(session, user_id, game_id)` (the game row if in `own_seat`), export `table_status`; `views.py` -- `table_status`.
- `backend/app/modules/sessions/schemas.py:351` `EnrolledSessionOut` -- `game`, `steps`; new `StudentGameOut`, `TableSeatOut`, `StepOut`.
- `backend/app/modules/sessions/service.py:1083` `enrolled_sessions` -- per row: `student_game` when `is_locked`, `table_status` with `classes.student_names`, `progress.steps_of`, `_stegene`; new `student_game_of(user, game_id)` for the route. `SEAT_ORDER:1462` is Fabrikk first.
- `backend/app/modules/sessions/routes.py:557` -- new `GET /me/games/{game_id}`.
- Tests: `backend/tests/sessions/test_student_home.py` (new; helpers `confirmed` from `test_open_games.py`, `sweep.run(START + MINUTE)`, `call` from `tests.classes.test_staff`, `email` from `test_student_choice.py`), `backend/tests/progress/test_progress.py` (new; `listening` from `tests/games/helpers.py`), `tests/test_migrations.py` (fold 0045 into the walk test, HEAD, HEAD_TABLES, CHECK enum test), `tests/test_imports.py` (progress imports no module).
- Frontend: `frontend/src/lib/api/{openapi.json,schema.ts}` regenerate; `frontend/src/copy/nb.ts` (`homes.student` block); `frontend/src/components/stegene.tsx` (new) + test in `components.test.tsx`; `frontend/src/modules/games/home.ts` (new, pure: seat rows, step items, deadline/lab lines) + `home.test.ts`; `frontend/src/modules/games/student-session.tsx` (new, a Class session's block); `frontend/src/modules/classes/student-home.tsx` (`status` slot reused); `frontend/src/app/(app)/hjem/page.tsx`; delete `frontend/src/modules/sessions/seat-choice-home.tsx` (its lines move into the new block; `homeLine` stays in `seat-choice.ts`).
- E2E: `frontend/e2e/student-home.spec.ts` (new) -- demo `student@` with `/api/me/class-sessions` answers laid over the real one (as `student-choice.spec.ts:177`), axe at 320/360/1440 and 360 with 200 % text via `VIEWPORTS`/`expectAccessible` (`frontend/e2e/support/classes.ts`); `student-choice.spec.ts` drawn-line test still passes.

## Tasks & Acceptance

**Execution:**
- Migration 0045, `progress` module, env import, registry -- the step table.
- `authz.own_seat`, policy; `games` repo/schemas/views/service -- `student_game`, `own_game`, `table_status`.
- `sessions` schemas/service/routes -- home fields and the game route.
- Backend tests -- every matrix row; migration walk and CHECK test; import test.
- Frontend -- regenerate api; copy; Stegene; Hjem block; unit tests of pure helpers; e2e before-start and seated states with axe at 320/360/1440 and 200 % text, tap targets ≥ 44 px, text ≥ 13 px, no horizontal scroll.

**Acceptance Criteria:**
- Given a seated Student in a locked session, when Hjem opens, then it reads «Spill 17 · Du er Grossist», lists four Seats Fabrikk first with names or «KI-spiller» in text, and Stegene shows Klassespill «pågår» and the five later steps with their lock lines.
- Given a Student before the Start date, when Hjem opens, then there is no game card, the line «Du får Rolle og spill på startdatoen.» shows and all six steps are greyed with their lock lines.
- Given a session with a next deadline, Lab hours and Obligatorisk, when Hjem renders, then «Neste frist», «Labtime» and «Obligatorisk» show, read from `/api/me/class-sessions` only.
- Given Playwright with axe at 320, 360 and 1440 px and 360 px at 200 % text, when Hjem renders both states, then no axe violation, no page-level horizontal scroll, targets ≥ 44 px, text ≥ 13 px.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 47 findings — high 0, medium 4, low 35, false 8, maybe-false 0
- findings:
  - `[low]` `[patch]` blind: `own_game` refuses a game the Student held before a move while docs say "holds or has held". Intended (only the Student's game); `games.service.own_game` docstring and the sessions README now say so.
  - `[false]` `[reject]` blind: `student_game_of` and `enrolled_sessions` read different clocks. Both use `auth.utcnow()` (`is_locked` defaults to it); there is one clock.
  - `[low]` `[reject]` blind: `last_seat_of`'s held-now query has no order. Only matters if one Student holds two Seats of one game, which allocation, moves and Student choice never produce.
  - `[low]` `[patch]` blind: `mine` and `role` come from different rules. Grouped with the first edge row: `mine` now also requires the viewer to be the current Student holder.
  - `[false]` `[reject]` blind: Fabrikk-first depends on repo order. `seats_with_occupant` orders by `position` (0 serves the customer) by contract, and `test_from_the_start_date_…` asserts the order.
  - `[low]` `[reject]` blind: several queries per locked session. A Student has one or two Class sessions; not worth batching.
  - `[low]` `[reject]` blind: names read outside the caller's transaction. Names at read time is the AD-3 rule; a name changing mid-request is harmless.
  - `[low]` `[reject]` blind: a late registrant after the start sees the Start-date line. The AC prescribes that line for "no Seat yet"; recorded design decision.
  - `[low]` `[patch]` blind: «Setene» is an `h3` beside the game title. Now `h4` under it.
  - `[low]` `[reject]` blind: the Seat shape is declared in `games` and `sessions`. Schema per module is the codebase's pattern; response validation catches drift.
  - `[low]` `[patch]` blind: missing tests (move, other Student's own Seat, no AI kind, removed Student). Added `test_a_student_moved_before_the_start_sees_only_the_new_game`; the seated test checks the other Student's own Seat and that no `rule_based`/`llm`/user id is in the answer; the removed test checks the removed Student's 403.
  - `[low]` `[reject]` blind: `/api/me/games/{id}` has no frontend consumer and documents a 422. It is the AC's game-keyed, own-seat-scoped read; FastAPI documents 422 for every route.
  - `[low]` `[reject]` blind: nothing records a step yet. The story creates `progress`; Stories 6.3 and 6.18 record `starting_task` and `class_game`.
  - `[low]` `[patch]` blind: the e2e retry test asserted only some `h2`. Now the Class heading and no alert in `main`; the extra request in `withSession` is kept (one local call).
  - `[low]` `[reject]` blind: the `class_session_id` index is unused and `at` unchecked. The FK index serves Epic 7's overview and CASCADE deletes; `at` is the recording module's.
  - `[low]` `[patch]` edge: a Seat the viewer once held, now held by another Student, could be marked `mine`. `table_status` marks `mine` only when the holder is not another Student.
  - `[low]` `[reject]` edge: held-now query unordered. Same as the blind row; unreachable.
  - `[low]` `[patch]` edge: an earlier-held game answers 403. Same entry as the first blind row (docs).
  - `[low]` `[patch]` edge: the game route served a card for an archived Class that Hjem hides. `student_game_of` now requires the Class among `classes.enrolled_classes`; the removed test archives the Class and expects 403.
  - `[false]` `[reject]` edge: an early lock shows the game before the Start date. Story 5.11's early lock is the Lecturer starting the session early; `is_locked` is the one Start-date predicate.
  - `[low]` `[reject]` edge: a names connection per locked session. As above; one or two sessions.
  - `[low]` `[reject]` edge: out-of-order done steps. Each later step's gate needs the earlier one (Epics 9–13); no reachable state.
  - `[low]` `[reject]` edge: the e2e destructures an empty Class list. The demo Student always has the demo Class (seed).
  - `[false]` `[reject]` edge: own Seat with no name reads «Ikke lenger i Klassen (deg)». A viewer not in the Class gets no session and the route refuses them, so the own Seat always has a name.
  - `[low]` `[patch]` edge (claim): "holds or has held" vs 403. Same entry as the first blind row.
  - `[false]` `[reject]` edge (claim): early lock. As above.
  - `[low]` `[patch]` verification-gap: no test of a Student moved before the lock. Added (Hjem shows the new game, the old one answers 403).
  - `[low]` `[patch]` verification-gap: no test of a removed Student on the game route. Added to `test_a_classmate_removed_after_the_start_has_no_name`.
  - `[medium]` `[patch]` verification-gap: the drawn line «Du fikk et sete ved trekning» became unreachable once the game card shows, and its e2e used an impossible answer. The game card now shows the drawn line under the title; `student-choice.spec.ts` mocks `game` too and asserts both.
  - `[low]` `[patch]` verification-gap: Stegene's mapping tested for `class_game` only. `test_a_done_step_moves_the_current_step_on` now records every step and checks each state.
  - `[medium]` `[patch]` verification-gap (other): Epic 5 drawn line vs "no change to Epic 5". Same entry as the drawn-line row.
  - `[low]` `[reject]` verification-gap (other): the Code Map names `student-session.tsx`, the diff `student-hjem.tsx`. The fix would edit this spec; noted here.
  - `[low]` `[reject]` intent: Permission denied is tested at the api only. No Student game page exists until 6.2/6.6; the web app maps 403 to the Epic 3 state on any page.
  - `[low]` `[reject]` intent: Hjem's e2e uses rewritten answers. The repo's pattern (5.17); the api states are tested against real data.
  - `[false]` `[reject]` intent: hub/Back not addressed. Already true: no navigation bar (`AppHeader`, UX-DR77) and «Til Hjem» on every Student page.
  - `[false]` `[reject]` intent: the student-choice Lenke is not exercised. `student-choice.spec.ts` opens «Velg spill og sete» from the rebuilt Hjem and passes.
  - `[low]` `[patch]` intent: the "has held" branch is unexercised. Covered by the new move test.
  - `[low]` `[patch]` intent: AD-3 not asserted. The seated test checks that no AI kind or user id is in the answer.
  - `[false]` `[reject]` intent: the game card is not the Spillkort. Spillkort is Story 6.17's.
  - `[medium]` `[patch]` visual: Setene names broke mid-word at 200 % text. Rows are now `flex-wrap` with `break-words`; the name drops under the Role.
  - `[low]` `[reject]` visual: locked Stegene rows are full sentences. The AC prescribes those lines («Replay, åpnes når …»).
  - `[medium]` `[patch]` visual: «Obligatorisk» stood alone like an empty heading. Now a label line above the game («Klasseøkt 2 · Obligatorisk» when labelled).
  - `[low]` `[patch]` visual: Role names looked like section labels. Role names regular weight; «Setene» `h4`.
  - `[low]` `[reject]` visual: class and game headings near the same size. The AC's single line «Spill 17 · Du er Grossist» is kept.
  - `[low]` `[patch]` visual: large gaps at 1440 px. The list is capped at `max-w-md`.
  - `[low]` `[reject]` visual: the before state says «startdatoen» twice. Both lines follow the AC.
  - `[low]` `[defer]` visual: the top bar stacks at 200 % text. Pre-existing (Story 3.3); deferred.

The five reviewers finished, but their completion notices did not reach this builder; their reports were read from their transcripts. The visual reviewer stood in for the founder's eye check; the builder re-captured Hjem at 320/360/1440 px and 360 px with 200 % text after the patches.

## Design Notes

Founder-level decisions taken here:
- The home endpoint is Epic 5's `GET /api/me/class-sessions`, extended: one source for card, steps, deadlines and Lab hours, so they can never disagree.
- `own_seat` counts a Seat held at any time ("holds or has held"), as `student_game` does; the game route additionally requires the session to be locked, so it never reveals a Role before the Start date.
- `table_status` takes a name resolver from the caller because `games` imports no feature module.
- A Student with no Seat after the Start date sees the same Start-date line (the AC's reading); EXPERIENCE.md's open question for a line of its own stays open.
- Draft copy: lock lines «Klassespill, åpnes på startdatoen.», «Debrief, åpnes når Klassespillet er ferdig.», «Quiz, åpnes når du har fullført Debriefen.», «Rapport, åpnes når den individuelle testen er vurdert.»; done mark «ferdig».

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_student_home.py tests/progress -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run build && npx playwright test --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** The Student's Hjem shows, per Class and Class session, the Class game from the Start date: «Spill 17 · Du er Grossist» and «Setene» Fabrikk first, each AI player as «KI-spiller» in text, the own Seat «(deg)»; before it (also after a confirmed allocation, or with no Seat) «Du får Rolle og spill på startdatoen.» or Story 5.17's Lenke. A drawn Student also reads the drawn line under the game. Then Stegene (six steps, current «pågår», later steps with their lock lines), «Neste frist», «Labtime» rows and the Obligatorisk mark.
- **api:** `GET /api/me/class-sessions` (the home endpoint) adds `game` (only when `is_locked`, through the new `games.service.student_game` and `games.views.table_status`, names via `classes.student_names` at read time) and `steps` (computed by `sessions.service.stegene` from `progress`). New `GET /api/me/games/{game_id}` (`games.read_own`, `authz.own_seat`) answers the Student's own game in a locked, non-archived session; every other id the same 403 `forbidden`.
- **progress:** new module, `progress_steps` (migration 0045), idempotent `record_step` emitting `user`/`session` only on insert (registry `progress.record_step`), `has_step`, `steps_of`; imports no feature module (test).

**Files.**
- `backend/app/platform/authz.py` (`own_seat`, `games.read_own`), `platform/events/registry.py`; `backend/app/modules/progress/{__init__,models,service}.py`, `README.md` (new); `backend/migrations/versions/0045_progress_steps.py` (new), `migrations/env.py`.
- `backend/app/modules/games/{repo,schemas,service,views}.py` (`student_seats`, `own_game`, `last_seat_of`, `TableSeat`/`TableStatus`, `StudentGame`, `student_game`, `own_game`, `table_status`).
- `backend/app/modules/sessions/{schemas,service,routes}.py`, `README.md` (home fields, `stegene`, `student_game_of`, route).
- Tests: `backend/tests/sessions/test_student_home.py`, `backend/tests/progress/test_progress.py` (new); `tests/test_migrations.py` (0045 folded into the walk test, CHECK enum test), `tests/test_imports.py`, `tests/sessions/test_dates.py` (field set).
- Frontend: `frontend/src/components/stegene.tsx` (new, reusable), `frontend/src/modules/games/{home.ts,home.test.ts,student-hjem.tsx}` (new), `frontend/src/app/(app)/hjem/page.tsx`, `frontend/src/copy/nb.ts` (`homes.student`, draft lines `[ASSUMPTION]`), `components.test.tsx`, `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated; deleted `modules/classes/student-home.tsx` and `modules/sessions/seat-choice-home.tsx`; e2e `frontend/e2e/student-home.spec.ts` (new), `student-choice.spec.ts` (drawn test now carries the game).

**Review.** 47 findings: medium 4, low 35, false 8. Patched entries: medium 3 (drawn line kept under the game card; Setene rows at 200 % text; Obligatorisk placement), low 11 (mine guard, archived-Class refusal, docs on own game, `h4`, role weight, width cap, retry assertion, five test additions). Deferred: 1 low (top bar at 200 % text, pre-existing). Rejected with reasons in the triage log.

**Follow-up review:** true. Three medium entries were patched; the specific unverified risk is the patched Hjem layout (Setene rows, Obligatorisk line, drawn line under the game), seen only in the builder's own screenshots after the patches, not by an independent visual reviewer.

**Verification.**
- Backend: 2610 passed (64 s); ruff check and format clean. New tests all under 1 s (slowest 0.92 s).
- Frontend: typecheck, Vitest 467 passed, `check:copy`, colour lint, build (in the compose image). Playwright full run with `--workers=2` before the patches: 289 passed; after the patches: 288 passed, 1 failure (`roster-entries.spec.ts` 1440 px, `net::ERR_NO_BUFFER_SPACE` on navigation) passed on `--last-failed`.
- Migration 0045 is new; it ran on the shared test databases and was not changed after.

**Residual risks.** Nothing records a step yet (Stories 6.3/6.18 will). The game route has no web consumer until 6.2/6.6. A Student with no Seat after the start sees the Start-date line (AC reading; EXPERIENCE.md's open question stays open). The e2e lays answers over the demo Student's real ones; the demo Class was not changed.
