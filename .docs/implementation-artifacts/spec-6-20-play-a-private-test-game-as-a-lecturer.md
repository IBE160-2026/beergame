---
title: "Story 6.20: Play a private test Game as a Lecturer (cut list, behind FEATURE_LECTURER_TEST_GAME)"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e7c88a4748aaf9bac02e5247c0ab93ed66c1d8f8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot see what the chosen Game settings do before the Start date (FR-87). The only Games are Class games, played by Students after the lock.

**Approach:**
- Backend: a `lecturer_test` row in `games.policy`, plus `games.commands.create` taking a Class session id and a ready snapshot. A flagged route seats the Lecturer, puts AI players in the other three Seats and starts the Game. The test Game reuses the Student play routes through `authz.own_seat`. Every Class-session query leaves it out.
- Frontend: a «Testspill» block on the Klasseøkt, and the same play route `/spill/{id}` with the label «Testspill». The end screen leads back to the Klasseøkt.

## Boundaries & Constraints

**Always:**
- **Flag (AD-17).** `FEATURE_LECTURER_TEST_GAME` is already in compose, and `Settings.feature_lecturer_test_game` already exists.
  - `ClassSessionOut` gains `lecturer_test_enabled: bool` and `test_game: TestGameRefOut | None`. `TestGameRefOut` is `{id, status}`: the viewer's latest test Game in that session, set only while the flag is on.
  - While the flag is off, `POST /api/class-sessions/{id}/test-game` answers 404 `not_found` and the block is not rendered.
- **Policy (AD-13).** `GamePolicy` gains two columns:
  - `game_number` (the Game takes a number in its Class session): True for `class`, False otherwise.
  - `played_by_staff` (a Lecturer of the session plays it in a Student Seat; the Game is reached from the Klasseøkt and leads back there): True only for `lecturer_test`.
  - Row `lecturer_test`:
    - snapshot `at_creation`
    - `class_session_game` True, `game_number` False, `student_occupants` True
    - inactivity_takeover, pause, play_deadline_playout, lecturer_overview, scripted_occupants, records_class_game_step and pre_play_gate all False
    - guided_weeks `settings`
  - `policy.purposes_with(column)` names the purposes for SQL filters, so no code compares a purpose literal.
- **Migration 0050** relaxes `ck_games_class_session` to `game_number IS NULL OR class_session_id IS NOT NULL`.
- **`commands.create(..., snapshot=None)`.**
  - With `snapshot` (only for an `at_creation` policy), the values are checked by `_checked_snapshot`, and no other snapshot argument is allowed (`settings_not_allowed`).
  - `_class_session` asks for a game number only when `policy.game_number` is set, and refuses one otherwise (`game_number_not_allowed`).
- **`sessions.service.start_test_game(user, session_id, role)`**:
  - Under `class_sessions.manage` (else None, which means 403). Flag off → `TestGameRefused("not_found", 404)`.
  - With the session row locked (`lock=True`), it refuses:
    - 409 `session_locked` when `is_locked(row)`
    - 409 `test_game_running` when the User's latest test Game here is not finished
    - 409 `llm_unavailable` when the AI mode is `llm` and the config is missing or `config.may_answer` is false
  - Then, in the same transaction: `build_snapshot(row)`, `create("lecturer_test", snapshot=…, class_session_id=…, within=s)`, and `assign_seat` with `student`+`user_id` in the chosen Role. The other Roles get `llm` when the snapshot has a model config, else `rule_based`.
  - After commit, `commands.start`. It returns the game id. The session row and its settings are never written.
- **Play access (AD-12).**
  - `games.service.own_game` keeps `authz.own_seat`. For a `played_by_staff` Game it returns a `StudentGame` with `number=None`, `test_game=True` and the Role the User holds now (`repo.last_seat_of`, held now only); None when they hold no Seat.
  - `sessions._own_locked_game` then requires `class_sessions.read` staff of the session's Class, with no lock check. The briefing rules come from the Game's own snapshot.
  - `own_game_session`, `propose_own_time` and `accept_own_time` answer None for a test Game.
  - No `if role ==`.
- **`StudentGameOut`:**
  - `number: int | None` (None on a test Game)
  - `test_game: bool`
  - `class_session_id`
- **Left out of Class-session reads.** Every Class-session query in `games/repo.py` filters on `purpose IN purposes_with("lecturer_overview")`:
  - `student_seats`, `student_seat_count`
  - `class_game_ids`, `class_games`, `class_session_seats`
  - `class_sessions_awaiting_snapshot`, `class_sessions_with_unstarted_games`

  `running_games_of_session` keeps test Games, since they are charged to the session budget through `scope_of` (issues #8, #9).
- **UI** (`modules/sessions/test-game-panel.tsx`; copy in `nb.sessions.testGame`, drafts marked [ASSUMPTION]):
  - Shown when `lecturer_test_enabled && can_manage`, as the section «Testspill» after the Klasseøkt's save row.
  - With an unfinished `test_game`: «Du har et testspill i gang.» and the Lenke «Fortsett testspillet».
  - Else, when not locked:
    - the lead «Spill mot tre KI-spillere med innstillingene slik de er lagret nå. Testspillet teller ikke i noen oversikt.»
    - Valgknapper «Din rolle» (Roles from `game_settings.roles`, default the first)
    - the secondary button «Start testspill», which navigates to `/spill/{id}`
    - errors in `ActionError`
  - When locked with no running test: «Testspill kan bare startes før Startdato.» A finished one adds the Lenke «Se forrige testspill».
- **Play screen** (the same `PlayPage`):
  - The guard lets any logged-in User through, and the api decides (403 shows AccessDenied).
  - `number === null` reads «Testspill» wherever «Spill N» reads: Topplinje, end heading, Alle rader subtitle and the not-running title.
  - For a test Game, the rules Lenke and «Til Hjem» become the Lenke «Tilbake til Klasseøkta».
  - The end screen drops the Debrief line, and its primary button reads «Tilbake til Klasseøkta».
  - The Lecturer's own Seat with no name reads «Deg».

**Never:**
- a second play screen
- a branch on the purpose literal outside `games.policy`
- `progress.record_step` for a test Game
- a test Game in the allocation, Hjem, the Lecturer overview or the sweeps' finders
- writing the Class session row
- changes to «class-of-1994»
- fixed sleeps

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start | owner, before Start date, role `wholesaler` | 201 `{id}`; Game `lecturer_test`, running, Lecturer in wholesaler (`student`), 3 AI of the AI mode; session unlocked, `game_settings` unchanged | — |
| Flag off | `feature_lecturer_test_game=False` | `lecturer_test_enabled` false, `test_game` null | POST 404 `not_found` |
| Not owner | Assistant / outsider / Student | — | 403 `forbidden` |
| Locked | Start date passed | — | 409 `session_locked` |
| Running | an unfinished test Game exists | — | 409 `test_game_running` |
| Play | Lecturer GET/order on `/api/me/games/{id}` | same answers as a Student; `number` null, `test_game` true | another Lecturer: 403 |
| Lists | test Game running, then finished | allocation, `/me/class-sessions`, lecturer overview, `progress_steps` unchanged | — |
| End | test Game finished | `/result` answers; no `class_game` step | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/policy.py`: the table, plus `purposes_with`.
- `backend/app/modules/games/commands.py`:
  - `:260` `_class_session`, `:285` `create`, `:630` `_checked_snapshot`, `:471` `assign_seat`, `:945` `start`
  - `:235` `_commit_change` (uses `lecturer_overview` for the session event)
- `backend/app/modules/games/repo.py`: `:136` `student_seats`, `:208` `student_seat_count`, `:235` `class_game_ids`, `:250`/`:265` finders, `:280` `class_games`, `:300` `class_session_seats`, `:184` `last_seat_of`, `:173` `own_game`.
- `backend/app/modules/games/service.py`: `:214` `StudentGame`, `:347` `own_game`, `:405` `scope_of` (already the Class session budget).
- `backend/app/modules/games/models.py:99` is the `ck_games_class_session`. Migrations are under `backend/migrations/versions/0049_*`, and `tests/test_migrations.py` holds HEAD.
- `backend/app/modules/sessions/service.py`:
  - `:739` `get_session`, `:1225` `_game_out`, `:1309` `_own_locked_game`, `:1618` `own_game_session`, `:1528`/`:1549` propose/accept
  - `:2505` `build_snapshot`, `:2548` `lock` (the llm config check), `:536` `is_locked`, `:642` `_class_for`
- `backend/app/modules/sessions/schemas.py` (`StudentGameOut` `:434`, `ClassSessionOut`) and `routes.py` (`start_my_game` `:697` is the pattern for refusals).
- `backend/app/platform/config.py:64` holds the flag; the tests override it with `monkeypatch.setattr(get_settings(), ...)` as the Epic 5 flag tests do.
- Tests:
  - `tests/games/test_policy.py`, `test_create.py:230` (`lecturer_test` is now supported) and `test_assign_seat.py:156`
  - `tests/sessions/test_game_end.py` (`short_game`, `klass`, `call`, `home`) and `test_lock.dated`
- Frontend:
  - `modules/sessions/class-session-page.tsx:414` (after `saveRow`), `api.ts`
  - `components/segmented-choice.tsx`, `components/action-error.tsx`, `lib/api/mutation.ts` `useAction`
  - `modules/games/play-page.tsx` (`PlayPage` guard `:74`, Topplinje `:225`, `Running` links `:383`, `NotRunning`), `game-end.tsx`, `home.ts` (`gameTitle`, `holderText`), `briefing-page.tsx:73`, `student-hjem.tsx:279`
  - `modules/identity/home-page.tsx` `GuardedPage`/`canView`, `homes.ts` `classSessionPath`/`gamePath`
  - `copy/nb.ts` (`games.play.roleGame` `:1558`, `homes.student.game`)
- E2e:
  - `support/classes.ts` (`freshClass`, `lecturerPage`, `expectAccessible`, `VIEWPORTS`)
  - `support/live-game.ts` (session creation and the save body)

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/policy.py`, `migrations/versions/0050_test_games.py`, `games/models.py` -- the columns, the row, `purposes_with` and the relaxed check.
- `backend/app/modules/games/commands.py`, `repo.py`, `service.py` -- `create(snapshot=)`, the filters, the `own_game` test path, `test_games_of(user, session)`.
- `backend/app/modules/sessions/service.py`, `schemas.py`, `routes.py` -- `start_test_game`, `POST /api/class-sessions/{id}/test-game` (`startTestGame`, body `{role}`), the `ClassSessionOut` fields, the `StudentGameOut` fields, and the `_own_locked_game` staff path.
- `backend/tests/sessions/test_test_game.py` (new) -- the matrix rows, the exclusion test that names the `reports.scope` rule, and a policy test.
- Tests -- update `tests/games/test_policy.py`, `test_create.py` and `test_migrations.py`.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/modules/sessions/test-game-panel.tsx`, `api.ts`, `class-session-page.tsx` -- the block.
- `frontend/src/modules/games/play-page.tsx`, `game-end.tsx`, `home.ts` (+ test), `briefing-page.tsx`, `student-hjem.tsx`, `identity/home-page.tsx`, `copy/nb.ts` -- the label, the back links and the guard.
- `frontend/e2e/test-game.spec.ts` (new):
  - The Lecturer starts a test Game from a fresh Klasseøkt (short: 3 Weeks, 0 Guided, `rule_based`) and lands on `/spill/{id}` with «Testspill».
  - The other Seats read «KI-spiller».
  - The Lecturer plays to the end. «Spillet er ferdig» shows «Testspill», and «Tilbake til Klasseøkta» leads back, where «Se forrige testspill» shows.
  - One axe check each on the block and the play screen at 360 and 1440 px.

**Acceptance Criteria:**
- Given the flag is off, when a Lecturer opens the Klasseøkt, then no «Testspill» block shows, and the POST answers 404.
- Given the flag is on and the session is before its Start date, when the owner picks a Role and presses «Start testspill», then the play screen of a running test Game opens with «Testspill» in the Topplinje and «KI-spiller» on the other Seats, and the Klasseøkt still saves settings.
- Given a test Game, running or finished, then allocation, Hjem, the Lecturer overview and the progress steps are as without it.
- Given the test Game ends, then «Spillet er ferdig» shows the chain total with «Testspill», and its button leads to the Klasseøkt.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: blind hunter and edge-case hunter only (the runbook caps reviewers at two); verification-gap and intent-alignment were skipped.
- verdicts: 28 findings — high 0, medium 3, low 17, false 8, maybe-false 0
- findings (blind):
  - `[medium]` `[patch]` A test Game whose `start` fails after the commit stays `not_started` and blocks every later press with `test_game_running`. Fixed: the next press starts that Game, and never makes a second one. A race on `game_already_started` counts as done. There is a new test with a failing start.
  - `[low]` `[reject]` An abandoned test Game blocks a new one. It is not stuck: «Fortsett testspillet» resumes it, and it can be played to the end. One unfinished test Game per Lecturer is a Design Notes decision. An «Avslutt» action would be new surface.
  - `[low]` `[reject]` Other staff of the Class get the `game:<id>` events of a test Game (`authz.class_games_staffed_by`). The events carry only topic, id and version, and the game itself answers them 403. Filtering would make `platform/authz` name a purpose, which it may not do.
  - `[low]` `[reject]` Nothing caps how many test Games are charged to the session budget. The intent leaves budget charging open (issues #8, #9).
  - `[low]` `[patch]` A stale Role is sent after the settings change, and `unknown_role` had no copy. Fixed: the Role falls back to the first one, and the copy line was added.
  - `[low]` `[reject]` Unsaved edits are ignored. The lead line says the game uses «innstillingene slik de er lagret nå», and a disabled state would add branches.
  - `[low]` `[patch]` In `nb.ts`, the comment of `lock` sat above `testGame`. Moved.
  - `[false]` `[reject]` `holderText` «Deg» for a removed Student: a Student no longer in the Class cannot open the game (`_own_locked_game` requires enrolment).
  - `[false]` `[reject]` `page="any"` drops AccessDenied. The api answers 403 for anyone else, and `PlayView` then renders `AccessDenied`.
  - `[low]` `[patch]` The e2e test did not assert «Deg». An assertion was added.
  - `[low]` `[reject]` Missing tests (`llm_unavailable`, `unknown_role`, the lock with a test Game, the 404s of propose/accept/Starting task). Each costs about 2.5 s of setup (founder rule: fast suite). The lock finders use the same repo filter that the lists test exercises.
  - `[false]` `[reject]` `reports.scope` has no home. The AC asks the test to name the rule for later epics, and it does.
  - `[low]` `[reject]` Every Klasseøkt read pays for the test-Game lookup. It is one small query.
  - `[low]` `[reject]` `_own_test_game` reads the Game in a second session. The snapshot never changes after creation.
  - `[false]` `[reject]` "Newest first" depends on UUIDv7. Every Game id is `uuid.uuid7()`.
  - `[false]` `[reject]` The frontend `games` module imports `sessions`. `game-action.tsx` already does.
  - `[low]` `[reject]` `__all__` order, and the undocumented 403 for an unknown session: cosmetic. The 403 is the uniform FR-5 answer.
- findings (edge case):
  - `[medium]` `[patch]` The start fails after the commit. Same root cause and fix as the first blind row.
  - `[medium]` `[patch]` A stuck `not_started` Game blocks a new one. Same root cause and fix.
  - `[low]` `[reject]` With the flag off, a User with no Lecturer role gets 403, not 404. The route policy runs first, by design (FR-5). Every Lecturer gets 404.
  - `[low]` `[patch]` Stale Role and missing `unknown_role` copy (two findings). Same fix as the blind row.
  - `[false]` `[reject]` Empty `roles`: `GameSettings` always has Roles.
  - `[low]` `[patch]` After the play screen's back link, the Klasseøkt showed a stale status. Fixed: the link invalidates the Klasseøkt query, as the end screen's button does.
  - `[false]` `[reject]` `build_snapshot` raising gives a 500. The stored settings are validated on save, and the LLM config case is refused before it.
  - `[false]` `[reject]` The Game disappears between two reads. Games are never deleted.
  - `[low]` `[reject]` (claim) Other staff get the events. Same as the blind row.
  - `[low]` `[patch]` (claim) The docstring said the start is atomic. It now describes the two steps and the retry.

## Design Notes

Founder-level calls, taken here with no human in the loop:
- All copy is draft [ASSUMPTION]: «Testspill», «Start testspill», «Din rolle», «Fortsett testspillet», «Se forrige testspill», «Tilbake til Klasseøkta», «Deg» and the lead lines.
- Only the session's owners (`class_sessions.manage`) start a test Game. An Assistant lecturer sees nothing.
- A Lecturer has at most one unfinished test Game per session. A new one may start once it has finished, but only before the Start date. A running one can be continued after the lock.
- The test Game uses the settings as stored, not unsaved edits on screen.
- The route refuses with 404 (not 422 `feature_disabled`) while the flag is off, as the AC says ("answers as not found").
- `lecturer_overview` stands for "listed in the Class session's lists". No separate column is added.
- Budget charging stays at the Class session (issues #8, #9 stay open).
- «Testspill» stands wherever «Spill N» stands, through `number: null` in the shared copy helpers, so the briefing and Hjem needed no change. The Lecturer's own Seat reads «Deg», because the Lecturer has no Student name.
- A test Game whose start failed is started by the next press.
- Built in the orchestrator's own context: the runbook says sub-agents stop at hand-back, so step 3's implementation sub-agent was not used.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/sessions/test_test_game.py tests/games/test_policy.py tests/games/test_create.py tests/test_migrations.py -q` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run src/modules/games src/modules/sessions` -- pass
- `cd frontend && npx playwright test e2e/test-game.spec.ts e2e/game-end.spec.ts e2e/homes.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can play a private test Game behind `FEATURE_LECTURER_TEST_GAME` (FR-87).
- **Backend.**
  - The `lecturer_test` policy row has two new columns, `game_number` and `played_by_staff`, plus `purposes_with`.
  - Migration 0050 relaxes `ck_games_class_session`, so a test Game holds its session without a number.
  - `commands.create(snapshot=)` takes a ready snapshot.
  - `POST /api/class-sessions/{id}/test-game` (`startTestGame`) builds the session's snapshot, seats the Lecturer as a `student` and AI players of the session's AI mode in the other Seats, and starts the Game. The session row is never written.
  - The Lecturer plays through the Student routes (`authz.own_seat` plus staff of the Class).
  - Every Class-session list query filters on `purposes_with("lecturer_overview")`.
  - `ClassSessionOut` gains `lecturer_test_enabled` and `test_game`. `StudentGameOut` gains `test_game`, `class_session_id` and `number: int | None`.
- **Frontend.**
  - The Klasseøkt has a «Testspill» block: Valgknapper «Din rolle» and the secondary button «Start testspill», or «Fortsett testspillet» / «Se forrige testspill».
  - The play route opens to any logged-in User (the api decides).
  - «Testspill» replaces «Spill N» on the game's screens, and the own Seat reads «Deg».
  - «Tilbake til Klasseøkta» replaces the rules and Hjem links, and «Gå til Debrief».

**Files.**
- `backend/app/modules/games/policy.py`, `models.py`, `migrations/versions/0050_test_games.py`: the row, the columns and the check.
- `games/commands.py`, `repo.py`, `service.py`: `create(snapshot=)`, the list filters, `staff_test_games`, `held_role` and the `own_game` test path.
- `sessions/service.py`, `schemas.py`, `routes.py`: `start_test_game`, the route, the fields and `_own_test_game`.
- `backend/tests/sessions/test_test_game.py` (new); `tests/games/test_policy.py`, `test_create.py`, `tests/test_migrations.py`.
- `frontend/src/lib/api/openapi.json`, `schema.ts`: regenerated.
- `modules/sessions/test-game-panel.tsx` (new), `api.ts`, `class-session-page.tsx`.
- `modules/games/play-page.tsx`, `game-end.tsx`, `home.ts` (+ test), `identity/home-page.tsx`, `copy/nb.ts` (drafts marked [ASSUMPTION]).
- `frontend/e2e/test-game.spec.ts` (new).

**Review.** Two layers reported 28 findings: medium 3 (one root cause), low 17, false 8.
- Patched: the stuck start, the stale Role and the `unknown_role` copy, the copy comment, the e2e «Deg» assertion, the back link's stale status, and the docstring.
- Deferred: none.
- Rejected, each with its reason in the triage log.

**Follow-up review:** false. One medium root cause was patched and covered by a new test; nothing was high.

**Verification.**
- Backend: the full suite passed (2754 passed, 70.8 s alone; 86 s while the compose build ran beside it). `ruff` is clean.
- Migration 0050 is new; no earlier migration was changed.
- Frontend: `tsc`, Vitest (692), `check:copy` and the Next build (compose image, rebuilt after the patches) passed.
- Playwright after the patches: `test-game`, `game-end`, `homes`, `seat-status`, `order-confirm`, `student-home` and `class-session` passed (66). Before the patches, `chain-band`, `order-field`, `week-table`, `graph-over-table`, `game-start`, `guided-week`, `time-proposal`, `class-session-lock` and `class-session-settings` also passed.
- `order-confirm` «a typed value comes back after a reload» failed once and passed on rerun (flaky, unrelated).
- New tests over 1 s:
  - backend: setup about 4 s per test (the `klass` fixture); the main call 1.7 s and the flag-off call 1.1 s
  - e2e: about 3 s each (live)
  - no fixed sleeps

**Residual risks.**
- Co-staff of the Class get `game:<id>` event pings for a test Game. The game itself answers them 403.
- Test Games are charged to the session's AI budget, with no cap (issues #8, #9).

Visible screens changed: the Klasseøkt (the new «Testspill» block, flag on) and the play route and end screen of a test Game. Class games are unchanged.
