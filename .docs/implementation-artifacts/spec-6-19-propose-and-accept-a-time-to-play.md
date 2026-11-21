---
title: "Story 6.19: Propose and accept a time to play"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '9e4a9a1c73badd0aafc863bd108a62ae764bdb0d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Students of a Class game have no way to agree on a time to play inside the product (FR-22). They would need a chat, which v1 does not offer.

**Approach:**
- Backend: two new `games.commands`, `propose_time` and `accept_time`. They write a proposal table and an acceptance table owned by `modules/games`. A new digest notice kind `time_proposed` tells the other Students. `StudentGameOut` gains `time_proposal`, and two Student routes call the commands.
- Frontend: one `TimeProposal` component. On Hjem it shows the proposal line, «Godta tidspunktet» and the in-place form «Foreslå tidspunkt». On the play screen it shows the line and the accept button.

## Boundaries & Constraints

**Always:**
- **Tables** (migration 0049, `games/models.py`):
  - `time_proposals`: `id`, `game_id` (FK `games`), `proposed_by` (uuid, no FK, ids only), `at` (timestamptz), `created_at`, and `UNIQUE (game_id)`.
  - `time_acceptances`: `proposal_id` (FK `time_proposals` ON DELETE CASCADE), `user_id`, `accepted_at`, with the primary key `(proposal_id, user_id)`.
  - Only `games.commands` writes them.
- **`propose_time(game_id, at, *, actor, latest)`** runs in one transaction with the Game row lock, `_commit_change` (version, `game`, and `session` where the Lecturer overview lists the Game), and the database clock (`repo.clock_now`). It refuses:
  - 404 `game_not_found`
  - 409 `game_finished`
  - 409 `seat_not_yours` (the actor does not hold a Student Seat in the Game now)
  - 422 `time_out_of_range` unless `now < at` and, when `latest` (the Play deadline the caller passes) is set, `at <= latest`. A naive `at` is also refused this way.
  On success it deletes the Game's earlier proposal (its acceptances go with it) and inserts the new one. Then, for every other Student holding a Seat, it calls `notify.enqueue(session, user, "time_proposed", f"time_proposed:{proposal_id}:{user}", ref=proposal_id)`, which emits `user:<id>`. It returns the proposal id.
- **`accept_time(game_id, proposal_id, *, actor)`** runs the same way. It refuses `game_not_found`, `game_finished` and `seat_not_yours`. It answers 409 `proposal_gone` when the Game's open proposal is not `proposal_id` or its time has passed, and 409 `own_proposal` for the proposer. An acceptance already stored changes nothing (no write, no version, no event) and returns False. Otherwise it stores the acceptance, commits the change and emits `user:<id>` for every Student holding a Seat. It returns True.
- **Registry and AD-2.**
  - `COMMAND_TOPICS`: `games.propose_time` and `games.accept_time` are `{game, session, user}`.
  - `test_registry.py` gets a runner for each. Each runs on a Class game with two Students.
  - `commands.__all__` lists both.
  - The AD-2 list in the `commands` docstring names them.
- **AD-20.** `rules.turn_times` and `seat_turns` never read the proposal. An api test shows that the `seat_turns` rows of a running game are byte-for-byte the same before and after `propose_time` and `accept_time`.
- **Read.**
  - `games.service.open_time_proposal(session, game_id)` returns `(id, at, proposed_by, accepted user ids in acceptance order)`, or None when there is no proposal, the Game is finished, or `at <= ` the database clock.
  - `sessions._game_out` adds `time_proposal: TimeProposalOut | None` to `StudentGameOut`:
    - `id`
    - `at`
    - `proposed_by` and `accepted_by[]`, each `{name, mine}`, with names through `_names_in`
    - `can_accept`: the viewer holds a Seat, is not the proposer and has not accepted
  - Hjem (`/me/class-sessions`) and the play route (`/me/games/{id}`) both read it there.
- **Routes** (`games.play_own`, through `_own_locked_game`; any other game is 403 `forbidden`):
  - `POST /api/me/games/{id}/time-proposal` takes `{at}` (`proposeMyGameTime`).
  - `POST /api/me/games/{id}/time-proposal/{proposal_id}/accept` (`acceptMyGameTime`).
  - Both answer 200 with the `StudentGameOut` as it now stands. `propose` passes the session row's `play_deadline` as `latest`. Refusals keep the command's status and code. `seat_not_yours` and 404 are the uniform 403.
- **Mail.**
  - `messaging.delivery.KINDS` gets `time_proposed` as `DIGEST`. Its context is `sessions.service.time_proposal_mail_context`, which reads at send time.
  - It answers None (no mail) when:
    - the proposal is gone or replaced
    - its time has passed
    - the Game is finished
    - the Class is archived
    - the User is no longer a registered Student
  - Otherwise it gives `class_name`, `game_number`, `proposer` (the name) and `at` in Europe/Oslo.
  - Templates `kinds/time_proposed.{txt,html}.j2` hold draft copy.
- **UI** (`modules/games/time-proposal.tsx`, copy in `nb.games.timeProposal`, drafts marked [ASSUMPTION]):
  - The line «Kari Nordmann foreslår å spille to. 26. nov. kl. 14:15.» (own: «Du foreslår …»), or «En Student foreslår …» when the name is unknown.
  - Under it «Godtatt av Per Hansen og deg.» or «Ingen har godtatt ennå.»
  - When `can_accept`, the secondary button «Godta tidspunktet», one press.
  - A proposal whose `at` has passed by the server clock (`useServerNow`) is hidden at once.
  - Hjem only, while the game is not finished, the viewer holds a Seat and the session has a `play_deadline`: the Lenke-button «Foreslå tidspunkt» opens a form in place. The form has:
    - the title «Foreslå tidspunkt»
    - `TextField type="date"` «Dato» and `type="time"` «Klokkeslett», and no text field
    - a consequence line, «De andre i spillet får beskjed og kan godta tidspunktet.», plus «Forslaget erstatter det som står nå.» when one is open
    - the primary «Send forslaget til gruppen»
    - «Avbryt»
  - Focus moves to «Dato» on open. «Avbryt» returns focus to «Foreslå tidspunkt». A sent proposal closes the form and moves focus to a `role="status"` line, «Forslaget er sendt.».
  - **Validation.** An empty field gives «Velg en dato.» or «Velg et klokkeslett.». A time not after server-now, or after the Play deadline, gives «Velg et tidspunkt mellom nå og Spillfristen, {osloDateText(play_deadline)}.» under the time field, in the Tekstfelt/Ordrefelt error pattern. The api's 422 `time_out_of_range` gives the same text.
  - While the form is open on Hjem, the session's primary game action steps back to a Lenke/secondary, so Hjem keeps one primary.
- On the play screen (running, and not started), the component sits under the Setestatus without the propose form.

**Never:**
- free text in the form, the table, the notice or the mail
- the proposal among the `turn_times`/Inactivity/Takeover inputs
- host-clock comparisons in the api: the database clock only (Issue #63); tests set the Play deadline relative to `now()` in SQL
- a confirmation dialog
- changes to «class-of-1994»
- fixed sleeps

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Propose | Student A, `at` within now..Play deadline | proposal stored; `game`, `session`, `user:` B (notice `time_proposed:{pid}:{B}`); A's response has `time_proposal.proposed_by.mine` | — |
| Out of range | `at` ≤ now or > Play deadline | nothing stored | 422 `time_out_of_range` |
| Replace | B proposes while A's (accepted by C) is open | A's row and acceptances gone; one open proposal (B's) with no acceptances; new dedupe keys | — |
| Accept | B on A's proposal | B in `accepted_by`; events `game`, `session`, `user` | — |
| Accept twice | B again | 200, no event, no version bump | — |
| Accept own / stale | A on own; B on a replaced or passed id | — | 409 `own_proposal` / `proposal_gone` |
| Finished / passed | game finished, or `at` passed | `time_proposal` null on Hjem and play | propose/accept 409 `game_finished` |
| Other game | another Student's game | — | 403 `forbidden` |
| AD-20 | propose + accept on a running game | `seat_turns` unchanged | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py`:
  - `:229` `_commit_change`, `:1342` `view_week` (the pattern: lock, checks, `_commit_change`, `user` events), `:1335` `_actor`, `:793` `_game_uuid`
  - `__all__` `:70`
  - `repo.seats_with_occupant` gives the current `occupant_kind`/`user_id`
- `backend/app/modules/games/repo.py` -- `lock_game`, `clock_now`/`now` (`:340`). Add the proposal reads and writes here.
- `backend/app/modules/games/models.py` -- the table style (`game_checks` `:245`).
- `backend/app/modules/games/service.py` -- `StudentGame`, `database_now`, `table_status`. It re-exports the reads that `sessions` uses.
- `backend/app/platform/notify/__init__.py:110` `enqueue` -- emits `user`. It imports no module, so `games` may call it.
- `backend/app/platform/events/registry.py` -- `COMMAND_TOPICS`.
- `backend/app/modules/messaging/delivery.py:134–169` -- the kind pattern (`DEADLINE_REMINDER_KIND` plus its context in `sessions`). The templates sit in `app/platform/email/templates/kinds/` (`deadline_reminder.*`, `_deadline.j2` `when`).
- `backend/app/modules/sessions/service.py`:
  - `:1223` `_game_out`, `:1187` `_names_in`, `:1282` `_own_locked_game`
  - `:1455` `start_own_game` (the refusal and return pattern)
  - `:3014` `deadline_reminder_mail_context` (the mail context pattern)
- `backend/app/modules/sessions/schemas.py:406` `StudentGameOut`. `routes.py:696` `start_my_game` is the route pattern.
- `backend/migrations/versions/0048_*.py`; `backend/tests/test_migrations.py` (`HEAD`, the upgrade and downgrade asserts).
- Tests:
  - `backend/tests/games/test_registry.py` (`RUNNERS`, `CLASS_SETUP_EVENTS`, the exported set)
  - `tests/sessions/test_game_end.py` `short_game` (a started Class game with N Students and a fixed api clock)
  - `tests/games/helpers.py` `listening`
  - `tests/classes/test_invitation_counts.execute` (SQL)
- Frontend:
  - `modules/games/student-hjem.tsx` -- `GameBlock`, `primary` plumbing, `useServerNow`
  - `play-page.tsx` -- `Running` `:379` Setestatus, `NotRunning`
  - `api.ts` -- `myGameKey`, `startGame` pattern
  - `modules/sessions/lab-hours-panel.tsx` -- the in-place form, focus return and `halfTyped`
  - `modules/sessions/dates.ts` -- `fromOsloInput`, `osloDateText`
  - `components/text-field.tsx`, `lib/api/mutation.ts` `useAction`
  - `copy/nb.ts`
  - `lib/api/openapi.json` and `schema.ts` -- regenerate
- E2e:
  - `e2e/student-home.spec.ts` -- the `withSession` stub and `GAME`
  - `e2e/support/live-game.ts` `liveClassGame` -- 2 Students, `rule_based`
  - `support/classes.ts` `expectAccessible`

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0049_time_proposals.py`, `games/models.py` -- the two tables.
- `backend/app/modules/games/repo.py`, `commands.py`, `service.py` -- the writes, `propose_time`/`accept_time`, `open_time_proposal`, `proposal_row`.
- `backend/app/platform/events/registry.py` -- the two entries.
- `backend/app/modules/messaging/delivery.py`, `templates/kinds/time_proposed.{txt,html}.j2`, `sessions/service.py` (`time_proposal_mail_context`, `propose_own_time`, `accept_own_time`, `_game_out`), `schemas.py`, `routes.py`.
- `backend/tests/games/test_registry.py`, `tests/test_migrations.py`, `backend/tests/sessions/test_time_proposal.py` (new) -- the matrix rows, the AD-20 test and the mail context.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/modules/games/time-proposal.ts` (+ `time-proposal.test.ts`) -- pure checks and line text. `time-proposal.tsx`, `api.ts`, `student-hjem.tsx`, `play-page.tsx`, `copy/nb.ts`.
- `frontend/e2e/time-proposal.spec.ts` (new):
  - stubbed Hjem at 320, 360 and 1440 px: the line, the accept button, the form with only date and time fields, focus return on «Avbryt», the range error, keyboard only, no page scroll, one axe check per width
  - one live test with two Students: A proposes on Hjem, B's open Hjem shows it without a reload and accepts, and A sees «Godtatt av …»

**Acceptance Criteria:**
- Given a Student with a Seat in a Class game that is not finished, when they open «Foreslå tidspunkt» on Hjem, then a form opens in place with only a date and a time field, a primary button that states its effect, and «Avbryt» that returns focus to the control.
- Given a valid time, when sent, then one open proposal exists for the game, and every other Student sees the proposer's name and time on Hjem and the play screen and can accept with one press. All see who accepted.
- Given `propose_time` and `accept_time`, then `seat_turns` is unchanged.
- Given 320, 360 and 1440 px, then the form and the line have no page scroll and no axe violation, and they work by keyboard alone.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: blind hunter and edge-case hunter only (the orchestrator caps reviewers at two); verification-gap and intent-alignment were skipped.
- verdicts: 24 findings — high 0, medium 1, low 20, false 3, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: Hjem's primary stayed stepped back when the form unmounted without «Avbryt» or a send (the game finishes, the Seat is lost, the block goes). Fixed: `TimeProposalBlock` reports `open && canPropose` from an effect and reports `false` on unmount.
  - `[low]` `[patch]` blind: with forms open in two sessions, closing one cleared `proposing`, which could leave two primaries. Fixed: `StudentHjem` keeps a set of session ids.
  - `[low]` `[patch]` blind: a refused «Godta tidspunktet» (`proposal_gone`) reread the game, which unmounted the line and its error. Fixed: the accept action and its `ActionError` live in `TimeProposalBlock`, which stays mounted while there is an error.
  - `[low]` `[patch]` blind: the digest mail could ask a Student who had already accepted. Fixed: `time_proposal_mail_context` returns None for an accepter; a test asserts this.
  - `[low]` `[patch]` blind: the mail could go to a Student who no longer holds a Seat. Fixed: it returns None unless the user is in `proposal.seated`.
  - `[low]` `[patch]` blind: the proposer's other tabs got no `user:` event. Fixed: `propose_time` emits `user:<actor>`. The registry topics are unchanged, and the test asserts the event.
  - `[low]` `[patch]` blind: the seat rule was written twice (commands and service). Fixed: one `games.service.seated_students`.
  - `[low]` `[reject]` blind: `game_class_info` returns a bare tuple. It has one caller and causes no harm; it is naming only.
  - `[low]` `[reject]` blind: the Play deadline is read outside the Game lock. The race needs a Lecturer moving the deadline in the same milliseconds, and a stale bound is still a past Lecturer value. Locking the session row from `games` would invert the module order.
  - `[low]` `[reject]` blind: with no Play deadline the api has no upper bound. A locked session has its dates (`ck_class_sessions_date_order` and the lock's checks), and the UI offers no form then. The spec's Design Notes take this decision.
  - `[low]` `[patch]` blind: the form was offered after the Play deadline. Fixed: `canPropose` also needs `Date.parse(playDeadline) > now`.
  - `[false]` `[reject]` blind: the spec names `time-proposal.tsx`, but the code has `time-proposal-view.tsx` and `time-proposal.ts`. A fix would edit this build's spec, which is ruled out. The naming follows the module's `*-view.tsx` convention, recorded under Design Notes.
  - `[low]` `[reject]` blind: missing tests (accept on a finished game, takeover 403, AI-seat notices, every mail-context branch, the «En Student» fallback, no version bump). The checks behind these are shared:
    - `_scheduling_game` and the `seat_not_yours`→403 mapping are shared with propose, which is tested.
    - Notices go only to `seated_students` (Students).
    - The fallback is unit-tested in `time-proposal.test.ts`.
    - «No event» implies no `_commit_change`.
    Each extra test costs about 2.5 s of setup (founder rule: fast suite).
  - `[low]` `[patch]` blind: the `CLASS_SETUP_EVENTS` counts were unexplained. A breakdown comment was added.
  - `[low]` `[reject]` blind: the empty `role="status"` line is always rendered. This is the Lab hours pattern, where a live region must exist before its text arrives, and it is invisible when empty.
  - `[low]` `[reject]` blind: a wall time in the spring-forward gap. `fromOsloInput` moves it forward by the gap, as for Lab hours, and Class sessions run in the autumn. Rare, and the fix adds a branch.
  - `[low]` `[patch]` edge: `canPropose` turns false while the form is open. Same root and same fix as the first blind row.
  - `[low]` `[patch]` edge: the block unmounts while the form is open. Same fix.
  - `[low]` `[patch]` edge: two forms open. Same fix as the blind row.
  - `[low]` `[patch]` edge: the form is offered after the Play deadline. Same fix as the blind row.
  - `[low]` `[reject]` edge: the DST gap. Same as the blind row.
  - `[false]` `[reject]` edge: `fromOsloInput` returns null with both fields filled. Browsers give `date`/`time` inputs only well-formed values or "" (a half-typed value is caught by `badInput` first), so the branch is unreachable in practice.
  - `[low]` `[reject]` edge: the deadline is read outside the lock. Same as the blind row.
  - `[false]` `[reject]` edge (claim): the spec's file name. Same as the blind row.

## Design Notes

Founder-level calls, taken here with no human in the loop:
- All copy is draft:
  - «Godta tidspunktet»
  - «Send forslaget til gruppen»
  - «Dato» and «Klokkeslett»
  - the proposal and acceptance lines
  - the result line
  - the mail «Forslag om tidspunkt»
- The proposer counts as agreeing and is not listed under «Godtatt av».
- Only Students who hold a Seat now may propose or accept. A proposal stays shown after its proposer loses the Seat.
- The propose form is on Hjem only (per the AC). The play screen shows the line and the accept button.
- Validation uses the server clock. The upper bound is the Play deadline. A session with no Play deadline offers no form, but the api then has no upper bound.
- The digest mail rereads the proposal at send time. A replaced or passed proposal sends no mail.
- The component is `time-proposal-view.tsx`, with the pure helpers in `time-proposal.ts`, following the module's `*-view.tsx` convention. The spec's `time-proposal.tsx` names the same component.
- Built in the orchestrator's own context: the runbook says sub-agents stop at hand-back, so step 3's implementation sub-agent was not used.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/sessions/test_time_proposal.py tests/games/test_registry.py tests/test_migrations.py -q` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run src/modules/games` -- pass
- `cd frontend && npx playwright test e2e/time-proposal.spec.ts e2e/student-home.spec.ts e2e/homes.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** Students of a Class game can now propose a time to play (a date and a time, never text) and accept one with one press (FR-22).
- **Backend.**
  - Migration 0049 adds `time_proposals`, which holds one open proposal per Game, and `time_acceptances`.
  - There are two new `games.commands`: `propose_time` and `accept_time`. Each runs under the Game lock with a version bump, `game`/`session`/`user` events and the database clock.
  - A new proposal replaces the old one and clears its acceptances. Each other seated Student gets a `time_proposed` digest notice, keyed per proposal.
  - `StudentGameOut.time_proposal` is shown on Hjem and on the play route. It disappears once the time has passed or the game has finished.
  - The new routes are `POST /api/me/games/{id}/time-proposal` and `POST /api/me/games/{id}/time-proposal/{proposal_id}/accept`.
  - The proposal is never an input of `turn_times`. A test asserts that `seat_turns` does not change.
- **Frontend.**
  - On Hjem, under Setene: «Kari Nordmann foreslår å spille to. 26. nov. kl. 14:15.», «Godtatt av …» and «Godta tidspunktet».
  - «Foreslå tidspunkt» opens an in-place form. It has «Dato» and «Klokkeslett», the primary «Send forslaget til gruppen» and «Avbryt», and shows the range error «Velg et tidspunkt mellom nå og Spillfristen, {dato}.».
  - The play screen shows the line and the accept button.

**Files.**
- `backend/migrations/versions/0049_time_proposals.py` and `games/models.py` -- the tables.
- `games/repo.py`, `commands.py` and `service.py` -- the writes, the two commands, `open_time_proposal`, `time_proposal_by_id`, `seated_students` and `game_class_info`.
- `platform/events/registry.py` -- the two entries.
- `messaging/delivery.py` and `templates/kinds/time_proposed.{txt,html}.j2` -- the digest kind and its draft copy.
- `sessions/service.py`, `schemas.py`, `routes.py` and `README.md` -- the read, the routes and the mail context.
- `backend/tests/sessions/test_time_proposal.py` (new), plus `tests/games/test_registry.py` and `tests/test_migrations.py`.
- `frontend/src/lib/api/openapi.json` and `schema.ts` -- regenerated.
- `modules/games/time-proposal.ts` (+ test), `time-proposal-view.tsx`, `api.ts`, `student-hjem.tsx`, `play-page.tsx` and `copy/nb.ts` (drafts marked [ASSUMPTION]).
- `frontend/e2e/time-proposal.spec.ts` (new).

**Review.** Two layers (blind, edge case) reported 24 findings: high 0, medium 1, low 20, false 3.
- Patched:
  - 1 medium: Hjem's primary when the form unmounts
  - 7 low root causes: two open forms, the refused-accept message, the mail to an accepter or someone without a Seat, the proposer's own tabs, one seat rule, the form after the deadline, the registry comment
- Deferred: none.
- Rejected, each with its reason in the triage log:
  - a bare tuple
  - the deadline read outside the lock
  - no upper bound without a deadline
  - extra tests
  - the empty status line
  - the DST gap
  - the null `fromOsloInput` branch
  - the spec's file name

**Follow-up review:** false. One medium was patched (frontend state, covered by the rerun e2e), and nothing was high. Patched by verdict: medium 1, low 7 (root causes).

**Founder-level decisions taken (no human in the loop).**
- All UI and mail copy is draft [ASSUMPTION]: «Send forslaget til gruppen», «Godta tidspunktet», «Godtatt av … og deg.», «Ingen har godtatt ennå.», «Forslaget er sendt.», and the mail «Forslag om tidspunkt».
- The proposer counts as agreeing and is not listed under «Godtatt av».
- Only Students who hold a Seat now may propose or accept, and only they get the mail.
- Proposing happens on Hjem only. The play screen shows the line and the accept button.
- The range is checked on the server clock against the Play deadline, which is included. After the deadline no form is offered.
- A proposal is allowed before the game starts, from the Start date.
- While the form is open, Hjem's game action steps back from primary, so the form's send is the one primary.

**Verification.**
- Backend: the full suite passed (2744 passed, 4 skipped, 63 s). `ruff check`/`format` are clean. Migration 0049 is new; no earlier migration was changed.
- Frontend: `tsc`, Vitest (692), `check:copy` and the Next build (compose image, rebuilt after the patches) passed.
- Playwright after the patches: `time-proposal`, `student-home`, `homes`, `seat-status`, `game-start` and `game-end` passed (57). Before the patches, `game-card`, `order-confirm`, `live-updates`, `briefing` and `starting-task` also passed.
- New tests over 1 s:
  - each backend test's setup (`klass` fixture) takes about 2.4 s, and the calls about 1.9–2.1 s (one shared Class game each, as in `test_game_end.py`)
  - the e2e tests take 1.6–1.7 s (stubbed) and 3.4 s (live, two Students)
  - no fixed sleeps

**Residual risks.**
- The Play deadline is read before the Game lock, so a deadline moved at the same instant is checked against the old value.
- With no Play deadline, the api accepts any future time. Locked sessions always have one.

Visible screens changed: Hjem (the proposal line, «Godta tidspunktet», «Foreslå tidspunkt» and its form) and the play route (the proposal line and the accept button under Setestatus).
