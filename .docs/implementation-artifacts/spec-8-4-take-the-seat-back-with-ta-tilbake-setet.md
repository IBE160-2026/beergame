---
title: 'Story 8.4: Take the Seat back with «Ta tilbake setet»'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'c33db0d13224db2c3076703805d9b06b58c4a648'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** After a Takeover (Story 8.2) the Student only reads «KI-spiller har bestilt for deg.»; nothing lets them take the Seat back, so they can no longer play or count toward the requirement. The visual check of 8.2 also found two play-screen defects in that state: «Alle rader og kostnad» drops under the note at 390 px and is gone at 1280 px, and the Kjedebånd labels the AI player's Order «Din ordre 9» in the Student's own bold.

**Approach:** A new command `games.commands.request_reclaim(game, seat, *, actor)` stores a queued Reclaim (new table `seat_reclaims`, migration 0055) without touching occupancy; `_step`, which every Week opening runs through, turns a queued Reclaim into an occupancy row (`student`, reason `reclaim`, `actor_user_id` = the Student) from the new Week and deletes the request. `POST /api/me/games/{game_id}/seats/{role}/reclaim` exposes it; Spill and Hjem show «Ta tilbake setet» under the note, then a focused result line. The two defects are fixed in the same note area and the Kjedebånd.

## Boundaries & Constraints

**Always:**
- Only `games.commands` writes `seat_reclaims` and occupancy, through `repo`, under the Game row lock, one transaction; `request_reclaim` calls `_commit_change` (version, `game_summaries`, `game`, `session`) and emits `user:<actor>`; registry `games.request_reclaim: {game, session, user}`; it joins `test_registry` RUNNERS/CLASS_SETUP_EVENTS and the 7.1 recomputation test.
- Eligible actor: the Seat's latest `student` row's user (`repo.seat_histories` `last_student`) while the Seat is `taken_over` (AI-held after a Takeover row since that Student row). Refusals (409): `game_finished`, `game_not_running` (not started), `seat_not_yours` (anyone else, including another Student of the game). 404 `game_not_found`/`seat_not_found`.
- Idempotent: a request already queued, or a Seat the actor already holds again, returns False and writes nothing (no version, no event). One queued row per Seat (PK `seat_id`).
- Apply in `_step` after the engine step, before `seats_with_occupant`/`_open_week`, for the new Week only (not when the Game finishes): append the row only while the Seat's latest occupant is not a Student; delete the request either way. The new turn gets no wait/due times (they start only when another Student orders). The callers' `user` events must include the returning Student (`view_week` rereads Seats after `_step`).
- Earlier `seat_week` rows are never touched; Spillinnsikt keeps AI Weeks marked through `marks.seat_mark`. A later Takeover of a Seat with a `guard_switch` in its history gets `rule_based` (existing `_takeover_occupant`).
- Views: `TableSeat`/`TableSeatOut.reclaim_queued` (True only on the viewer's own Seat with a queued request). Copy in `nb.ts` with `[ASSUMPTION]` for new strings; regenerate `openapi.json`/`schema.ts`.
- UI: secondary `Button` «Ta tilbake setet», min 44 px, full width below 1024 px; on success the button is replaced by «Du får setet tilbake når neste Uke åpner.» (`tabindex=-1`, focused, `role="status"`); refusals inline via `ActionError`, button stays active. Not shown unless the game is `running`.
- Defects: on Spill the taken-over block puts «Alle rader og kostnad» right-aligned on its own line above the note at every width (as the Confirmed Ordrefelt does on phone), with the block spaced from the table; the Kjedebånd order label reads «KI-ordre 9» at weight 400 when the own Seat is taken over.

**Never:** no Takeover by staff or peers, Pause, playout or clearing of Reclaims at the Play deadline (8.5–8.14); no change to earlier occupancy or `seat_week` rows; no audit record (not a staff action); no change to the demo Class; no waiting on real time in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Request | own Seat taken over, Week 3 open | one `seat_reclaims` row, occupancy unchanged, version +1 | — |
| Repeat | already queued, or Seat held again | returns False, nothing written | — |
| Week opens | queued, Week 3 completes | row `student`/`reclaim`/actor = Student from Week 4; request gone; Week 4 turn no times; `user:<student>` | — |
| Guided view opens it | Week completes by `view_week` | same, and the Student gets `user` | — |
| Game finishes | queued at last Week | no row; game finished | — |
| Other Student / never held | another Student posts for the Seat | — | 409 `seat_not_yours` |
| Not taken over | own Seat still Student-held | — | 409 `seat_not_yours` |
| Finished game | lifecycle finished | control hidden | 409 `game_finished` |
| Guard then reclaim then lost | `guard_switch` in history | later Takeover occupant `rule_based` | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `_step` (1126) apply point; `takeover` (1671) as the model for lock/refusal/`_commit_change`; `view_week` (1418) rereads seats for `told`; `__all__`.
- `backend/app/modules/games/repo.py` -- `seat_histories` (541), `append_occupancy` (91); add `queue_reclaim`, `queued_reclaims(game_id)`, `delete_reclaim`.
- `backend/app/modules/games/models.py:122-161` -- new `seat_reclaims` table; `backend/migrations/versions/0055_seat_reclaims.py`.
- `backend/app/modules/games/views.py:296-358` `table_status`, `schemas.py` `TableSeat` -- `reclaim_queued`.
- `backend/app/modules/sessions/{service.py:1376-1391 _seats_out, schemas.py:381 TableSeatOut, routes.py ~897}` -- field, `reclaim_own_seat`, route returning `StudentGameOut`.
- `backend/app/platform/events/registry.py` -- topics.
- `frontend/src/modules/games/{api.ts, seat-status-view.tsx TakenOverNote, play-page.tsx:352-364, student-hjem.tsx:229, chain-band-view.tsx, chain-band.ts bandLabels}`, `components/charts/chain-band-layout.ts:224` (order weight), `copy/nb.ts:396-408`.
- Tests: `backend/tests/games/test_takeover.py` (`class_game`, `due_of`) as setup; `tests/games/test_registry.py`, `test_game_summaries.py`; `tests/sessions/test_takeover_view.py` api pattern; `frontend/e2e/takeover.spec.ts` stub pattern.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0055_seat_reclaims.py`, `models.py` -- table `seat_reclaims(seat_id PK FK seats, game_id FK games, user_id, requested_at default now())`.
- `repo.py`, `commands.py`, `registry.py` -- `request_reclaim`, apply in `_step`, `view_week` told fix.
- `views.py`, `games/schemas.py`, `sessions/{schemas,service,routes}.py` -- `reclaim_queued`, endpoint.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/...` -- `reclaimSeat` api, `TakenOverNote` with control and result line, play-page layout, Kjedebånd label, copy.
- Backend tests `tests/games/test_reclaim.py` (matrix rows, events, summary, AD-15 via `insight`), api test in `tests/sessions/test_takeover_view.py` style; Vitest for chain band label and note; e2e `frontend/e2e/reclaim.spec.ts` (press → focused line; 409 inline; axe and no horizontal scroll at 320, 360, 1440; link visible at 1440 and 390) and fix `takeover.spec.ts` exact-text assertion.

**Acceptance Criteria:**
- Given a Student whose Seat is taken over in a running Class game, when they open Spill or Hjem, then «Ta tilbake setet» shows under «KI-spiller har bestilt for deg.» with a ≥ 44 px target.
- Given they press it, when the api commits, then the button is replaced by the focused line and the occupancy is unchanged until the next Week opens, when the Seat is theirs again.
- Given 320, 360 and 1440 px, when the taken-over state, button and result line show, then no horizontal scroll and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter, edge-case hunter, verification gap, intent alignment (Sonnet, as the orchestrator asked). All four hand-backs dropped; findings read from `review-{blind,edge,verification,intent}-8-4.md` in the session scratchpad. The diff was staged against HEAD `2483f20` (the orchestrator committed sprint and log files on the branch after the baseline `c33db0d`; those are not this change).
- verdicts: 29 findings — high 0, medium 0, low 19, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` blind-1: a request in the last Week is accepted and promises «neste Uke» — refusing it, or wording it differently, would tell the Student it is the last Week (FR-14); the game then ends and the Student is led to its result.
  - `[low]` `[patch]` blind-2: a request queued in the last Week stayed in `seat_reclaims` after the finish — `_step` now deletes the Game's requests when it finishes (`repo.delete_reclaims`); the last-Week test asserts none is left.
  - `[false]` `[reject]` blind-3: FKs without `ON DELETE CASCADE` break a purge — no code deletes games or seats (grep over `backend/app`); `requested_at` is the request's own record, like `created_at` on occupancy.
  - `[low]` `[reject]` blind-4: the WeekTable row «Din ordre» still holds the AI's 9 — the intent names the chain (Kjedebånd); the table row is the Seat's Order history across occupants, unchanged since Story 6.7.
  - `[low]` `[reject]` blind-5: the band's sentence for screen readers does not say «KI-ordre» — the sentence never names the Order as the Student's («På vei 16 pluss 9»), so it tells nothing wrong.
  - `[low]` `[patch]` blind-6: no api assertion of 403 for a game not the caller's — `test_reclaim_view.py` now posts as an outsider and with an unknown game id (403 `forbidden`, nothing queued).
  - `[low]` `[reject]` blind-7: no tests for two Seats in one step or the defensive branches — one request per Seat by primary key; no path makes a queued Seat Student-held mid-game.
  - `[false]` `[reject]` blind-8: ambiguous idempotency — both no-ops are "nothing to do", and the answer is the game as it stands, which says which state holds.
  - `[low]` `[reject]` blind-9: no mail when the Seat comes back — the AC asks for `game:` and `user:` events only; the Student's pages read again on `user:`.
  - `[false]` `[reject]` blind-10: no clock on the returned Seat stalls the game — the AC requires it; the wait starts when another Student orders (`_start_waits`), as in every Week; with no other order nothing happens until the Play deadline (FR-36).
  - `[low]` `[reject]` blind-11: `queued_reclaims` read on every `table_status` — one indexed query of a handful of rows.
  - `[low]` `[reject]` blind-12: `ReclaimControl` keeps the line if the answer says not queued — after a success the answer is queued or the Seat is back (the note then unmounts); `as Record` was removed before review; 403 reads the fallback line.
  - `[low]` `[reject]` blind-13: tests import `taken_over` from `test_reclaim`; `RECLAIM_SETUP = -3` — the same pattern `test_registry` already uses for `takeover`; the negative count is documented and exact.
  - `[false]` `[reject]` blind-14: draft copy ships unsigned — marked `[ASSUMPTION]` in `nb.ts`, the project's convention for draft copy.
  - `[low]` `[patch]` edge-1: as blind-2; patched with it.
  - `[low]` `[reject]` edge-2: as blind-1.
  - `[low]` `[reject]` edge-3: a dropped request leaves no trace — only reachable if the Seat were Student-held at opening, which no command does mid-game.
  - `[false]` `[reject]` edge-4: stale `user_id` hands the Seat to the wrong Student — `request_reclaim` stores the Seat's last Student, and no command changes that while an AI player holds the Seat.
  - `[low]` `[reject]` edge-5: bare «KI-ordre» while the LLM job is pending — the same as «Din ordre» without a number before an Order; the label names the line, not a placed Order.
  - `[low]` `[patch]` edge-6: the spec asks for `role="status"` on the result line, the code had none — added; focus still reads it.
  - `[low]` `[patch]` edge-7: as blind-2.
  - `[low]` `[patch]` verification-1: as blind-6.
  - `[low]` `[reject]` verification-2: the one-connection test does not list the route — the service closes its read session before the command (no live defect); the setup needs a Takeover in an already heavy test.
  - `[low]` `[patch]` verification-other-1: as edge-6.
  - `[low]` `[patch]` verification-other-2: as blind-2.
  - `[false]` `[reject]` intent-1: Defect 1 tested at 320/360/1440 rather than 390/1280 — the layout changes only at the 1024 px breakpoint; 320/360 and 1440 sit on both sides of it.
  - `[false]` `[reject]` intent-2: the WeekTable row (D2-b) — as blind-4.
  - `[false]` `[reject]` intent-3: e2e on stand-in envelopes — the real command and route run in `test_reclaim.py` and `test_reclaim_view.py`; the runbook's e2e pattern.
  - `[false]` `[reject]` intent-4: `actor=` keyword instead of `user` — the same three inputs (Game, Seat, Student).
- Matrix audit: Request, Repeat — `test_the_request_is_queued_and_changes_no_occupancy`; Week opens and Seat held again — `test_the_seat_is_the_students_again_when_the_next_week_opens`; Guided view — `test_a_guided_view_that_opens_the_week_hands_the_seat_back`; Game finishes — `test_the_last_week_finishes_the_game_with_no_reclaim_row`; Other Student / never held / not taken over — `test_only_the_student_whose_seat_was_taken_over_may_ask` and `test_reclaim_view.py`; Finished game — the last-Week test (409) and `reclaim.spec.ts` (no control on Hjem); Guard then reclaim — `test_a_play_guard_switch_outlasts_the_reclaim`. All ran and passed.

## Design Notes

A separate `seat_reclaims` table (not a column on `seats`) keeps `seats` static and gives Story 8.14 one thing to clear. Applying inside `_step` covers every Week opening (Order, guided view, Takeover's settle, `advance`) with no new caller. The endpoint names the Seat by Role so another Student of the game reaches the command and gets `seat_not_yours`; a User with no Seat in the game gets 403 `forbidden` like every `/me/games` route (FR-5).

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_reclaim.py tests/games/test_registry.py tests/games/test_game_summaries.py tests/games/test_takeover.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before commit: full backend `--maxprocesses=8`; typecheck, Vitest, `lint:colours`, `check:copy`, build; rebuilt stack; Playwright `--workers=4` reclaim, takeover, seat-status, live-updates, homes, student-home, play-screen specs.

## Auto Run Result

Status: done

**Summary.** A Student whose Seat an AI player took over can take it back. «Ta tilbake setet» stands under «KI-spiller har bestilt for deg.» (and the requirement warning) on Spill and Hjem, a secondary button at least 44 px, full width below 1024 px. A press calls `POST /api/me/games/{id}/seats/{role}/reclaim`, whose command `games.commands.request_reclaim` queues one request per Seat in the new table `seat_reclaims` (migration 0055) under the Game row lock and changes no occupancy (version bump, `game_summaries` row, `game`/`session`/`user:<student>`). The button is replaced by «Du får setet tilbake når neste Uke åpner.», which takes focus. The command that opens the next Week (`_step`, reached by an Order, a Guided view, a Takeover's settle or `advance`) appends an occupancy row `student`/`reclaim` with the Student as `actor_user_id` from that Week and deletes the request; the Student's new turn has no clock running; a request left when the Game finishes is dropped. Another Student, a User who never held the Seat, or the Student's own Seat not taken over get 409 `seat_not_yours`; a finished game 409 `game_finished`; a User with no Seat in the game 403. Earlier `seat_week` rows are untouched and Spillinnsikt keeps the AI Weeks marked; a Seat the Play guard switched gets a Rule-based player when taken over again. The two defects of the Story 8.2 visual check: «Alle rader og kostnad» now sits right-aligned above the note at every width, and the Kjedebånd labels the AI player's Order «KI-ordre 9» at regular weight.

**Files changed**
- `backend/migrations/versions/0055_seat_reclaims.py`, `backend/app/modules/games/models.py` -- the queued-Reclaim table.
- `backend/app/modules/games/commands.py` -- `request_reclaim`, `_apply_reclaims` in `_step`, requests dropped at the finish, `view_week` tells the returning Student.
- `backend/app/modules/games/repo.py` -- `queue_reclaim`, `queued_reclaims`, `delete_reclaim`, `delete_reclaims`.
- `backend/app/modules/games/{schemas,views}.py`, `backend/app/modules/sessions/{schemas,service,routes}.py` -- `reclaim_queued` on the own Seat; `reclaim_own_seat`; the route.
- `backend/app/platform/events/registry.py` -- `games.request_reclaim` topics.
- `frontend/src/modules/games/reclaim-view.tsx` (new), `seat-status-view.tsx`, `play-page.tsx`, `student-hjem.tsx`, `api.ts` -- the control, the line, the layout fix.
- `frontend/src/modules/games/{chain-band.ts,chain-band-view.tsx}`, `frontend/src/components/charts/chain-band-layout.ts` -- «KI-ordre», weight 400.
- `frontend/src/copy/nb.ts` -- `reclaim`, `reclaimQueued`, `reclaimRefusals`, `reclaimFailed`, `band.aiOrder` (draft copy `[ASSUMPTION]` except «Ta tilbake setet»).
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated.
- Tests: `backend/tests/games/test_reclaim.py` (new), `tests/sessions/test_reclaim_view.py` (new), `tests/games/test_registry.py`, `test_game_summaries.py`, `tests/test_migrations.py`, `tests/sessions/test_play.py`, `test_seat_status.py`; Vitest `seat-status.test.tsx`, `chain-band.test.ts`, `home.test.ts`; e2e `frontend/e2e/reclaim.spec.ts` (new), `takeover.spec.ts`.

**Review.** Four Sonnet reviewers (blind, edge case, verification gap, intent alignment): 29 findings — 0 high, 0 medium, 19 low, 10 false. Patched (low): a request left at the finish is deleted; api 403 for a game not the caller's; `role="status"` on the result line. Deferred: none. Rejected: the rest, each with its reason in the Review Triage Log. Follow-up review: not recommended (patched: high 0, medium 0, low 3).

**Verification** (after the patches)
- Backend full suite `--maxprocesses=8`: 2927 passed; ruff check and format clean.
- Frontend: typecheck, Vitest 844 passed, `lint:colours`, `check:copy`, `next build` pass.
- Stack rebuilt after the last frontend change; Playwright `--workers=4`: reclaim, takeover, takeover-overview, seat-status, live-updates, homes, student-home, chain-band, order-confirm, order-field, order-failures, week-table, week-advance, guided-week, game-card, cost-panel, graph-over-table, week-transition, time-proposal: 168 passed, none failed or retried. axe at 320, 360 and 1440 px on the taken-over play screen with the button; reflow checked after the press.
- New tests over 1 s: `tests/sessions/test_reclaim_view.py::test_the_student_takes_the_seat_back_from_the_next_uke` (about 2.3 s; a real Class game, a sweep Takeover and several api calls) and `tests/games/test_reclaim.py::test_a_play_guard_switch_outlasts_the_reclaim` (about 1.3 s; three Weeks of an LLM-mode game).

**Decisions taken instead of the founder.**
- Queued Reclaims live in their own table `seat_reclaims` (one per Seat), deleted when applied or when the Game finishes.
- The route names the Seat by Role (`/me/games/{id}/seats/{role}/reclaim`), so another Student of the game gets 409 `seat_not_yours`; a User with no Seat in the game gets 403 `forbidden`, like every `/me/games` route (FR-5).
- A repeat after the Seat came back answers 200 with nothing changed; the Student's own Seat never taken over is 409 `seat_not_yours`.
- A request in the last Week is accepted and lapses at the finish: refusing it would reveal the last Week (FR-14).
- «Alle rader og kostnad» shows above the note at every width when the own Seat is taken over (in the Ordrefelt state, laptop still opens Alle rader from Totalkostnad only).
- The AI player's Order on the Kjedebånd reads «KI-ordre 9» at weight 400; the WeekTable's «Din ordre» row is unchanged.
- Draft copy `[ASSUMPTION]`: «Du får setet tilbake når neste Uke åpner.», the refusals, the failure line, «KI-ordre».
- Implemented in the builder's own context, as the orchestrator instructed.

**Residual risks.**
- A Seat whose Student has left the Class still gets the `reclaim` row (no path removes a Student mid-game today).
- The visual check of the new state is left to the separate visual agent.
