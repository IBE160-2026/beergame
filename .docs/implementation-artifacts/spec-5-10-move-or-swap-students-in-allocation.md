---
title: 'Story 5.10: Move or swap Students in the allocation'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '35bb77cc072bedd8f8ee9f7768cb3f091d207794'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-9-confirm-allocation-i-am-looking-at.md'
warnings: ['oversized', 'multiple-goals']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer can only redraw the whole allocation before confirming, and nothing at all after it; adjusting one group is impossible (FR-20). `games.commands` lacks the AD-2 command `move_seat`, and append-only occupancy has no way to say a Seat became free again. Issue #107: a confirmed allocation opened read-only does not say in the panel that it is confirmed.

**Approach:** One route edits the stored draft by draft id + revision: move the Student of one Seat to another Seat, swapping when the target holds a Student. Before confirmation only the draft changes (revision +1). After confirmation (before the lock) the same transaction also runs the new `games.commands.move_seat` on the Class games and notifies the affected Students. The panel gets labelled, drag-free move/swap buttons for the selected game, and a «Fordelingen er bekreftet {dato}.» line.

## Boundaries & Constraints

**Always:**
- Route `POST /api/class-sessions/{id}/allocation/move` (`class_sessions.manage`), body `AllocationMoveIn {draft_id, revision: StrictInt, from_game: StrictInt, from_role: Role, to_game: StrictInt, to_role: Role}` (`extra=forbid`), answers `AllocationOut`. Under the Class session row lock: `_writable` (409 `class_archived`); `is_locked` → 409 `session_locked` `{"allocation":"locked"}`; no draft / other id / other revision → 409 `allocation_changed` `{"draft":"changed"}`; then 422 `invalid_move` with `fields`: `{"to":"same"}` same Seat, `{"from":"unknown"}`/`{"to":"unknown"}` game number not in the draft, `{"from":"empty"}` no Student at `from`, `{"from":"last_student"}` the move would leave `from_game` (≠ `to_game`) with no Student.
- Effect on the draft: Student A of `from` takes `to`; Student B of `to`, if any, takes `from` (swap); `revision` +1, same id, `drawn_at` and seed unchanged; emit `session:<id>`. Not confirmed: nothing else.
- Confirmed (not locked): in the same transaction, `games.commands.move_seat(game_of(from_game), from_role, game_of(to_game), to_role, within=s)` on the Class games (ids by `games.service.class_game_ids`), then one `ALLOCATION_NOTICE` per moved Student with key `allocation_confirmed:{draft_id}:{revision}:{user}` (new revision), `ref` = session id. `CommandError` from it → 409 with its code, nothing committed.
- `games.commands.move_seat(game_id, role, to_game_id, to_role, *, within=None)`: locks the Game rows in id order; both `not_started` (409 `game_already_started`), both with the same non-null `class_session_id` (422 `class_session_mismatch`) and a policy with `student_occupants` (422 `occupant_kind_not_allowed`); same Seat 422 `same_seat`; source's current occupant must be `student` (409 `seat_not_student`); target free or `student` (else 409 `seat_occupied`). Appends `to` ← A (`student`, `initial`, from_week 1, A's id); `from` ← B the same way, or a free-Seat row (`occupant_kind` NULL, `user_id`/`policy_id` NULL, reason `moved`). Afterwards each moved Student holds exactly one Seat in the session (else 409 `student_already_seated`, rolled back). `_commit_change` per Game (version, `game`, `session`), and `user:<id>` per moved Student. Registry `games.move_seat: {"game","session","user"}`; `sessions.move_allocation: {"game","session","user"}`.
- Free Seat semantics: a Seat is free when it has no occupancy row or its latest row has NULL `occupant_kind`. `repo.has_occupant` reads the latest row; `seats_with_occupant` already reports None. `OccupancyRow.occupant_kind` becomes optional. `OccupancyReason.MOVED = "moved"`.
- Migration 0039: `seat_occupancy.occupant_kind` nullable; CHECK `ck_seat_occupancy_free` `(occupant_kind IS NULL) = (reason = 'moved')` and NULL kind ⇒ `policy_id IS NULL`; recreate `ck_seat_occupancy_reason` and `ck_seat_weeks_reason` with `moved`. Downgrade refuses nothing silently: it fails when free-Seat rows exist (documented, append-only).
- `AllocationOut` gains `confirmed_at: datetime | None`.
- Web (`can_manage && !locked`, confirmed or not, chart view): under the chart the selected game's Seats are a list, Fabrikk first, each row «Rolle — navn/KI-spiller». Idle: each Student row has a button «Flytt eller bytt {navn}, {Rolle} i Spill N». Picked: a status line says who is picked, the picked row's button becomes «Avbryt flyttingen», every other row of whatever game is selected gets «Bytt {A} ({Rolle}, Spill N) med {B} ({Rolle}, Spill M)» or «Flytt {A} ({Rolle}, Spill N) til ledig {Rolle} i Spill M»; selecting another column keeps the pick. Success: query data replaced, result in the `role="status"` line, focus on the button of A's new row (the target game is selected). 409 `allocation_changed`: refetch, pick cleared, `changed` message. `invalid_move`/others: inline `ActionError`. All copy in `nb.ts` `sessions.allocation`, [ASSUMPTION] draft copy. Tap targets ≥ 44 px.
- Issue #107: whenever `confirmed`, the open panel shows «Fordelingen er bekreftet {dato}.» (Europe/Oslo day and time) under the heading, for every viewer; when confirmed and editable, «De som flyttes eller byttes, får beskjed på e-post.» replaces «Ingen får beskjed før du bekrefter.».

**Never:** moves after the lock or in a started game; moving into a new game or creating/deleting Class games; drag-and-drop as the only way; deleting or updating occupancy rows; names in games tables; naming game or Role to a Student; touching the demo Class; comparing DB time with host time; late registrants (5.13), lock and AI occupants (5.11/5.12).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Move, draft | 5 Students (game 2 has 1), move game 1 Fabrikk → game 2 Grossist | same id, rev 2, A at 2/Grossist, 1/Fabrikk empty, `session` event | – |
| Swap, draft | two Students | positions exchanged, rev+1 | – |
| Role change | same game, free Role | moved within game | – |
| Stale | old revision / other id | nothing changes | 409 `allocation_changed` |
| Invalid | same Seat; unknown game; empty from; last Student out | nothing | 422 `invalid_move` + field |
| Confirmed move | confirmed, to free Seat | draft rev+1; Games' Seats match draft; old Seat free (`moved` row); notice to A only; `game`,`session`,`user` events | – |
| Confirmed swap | two Students in two games | both Games changed, both notified | – |
| Confirm after edit | unconfirmed, edited to rev 2 | confirm with rev 2 commits the edited groups | rev 1 → 409 |
| Locked / Assistant / archived | – | nothing | 409 `session_locked` / 403 / 409 `class_archived` |
| move_seat guards | started Game; other session; AI source; AI target | nothing appended | 409/422 codes above |
| Free Seat reuse | after a move | `assign_seat` takes the freed Seat; `student_seated` false for nobody left | – |

</intent-contract>

## Code Map

- `backend/app/modules/games/schemas.py:38,47,275` -- `OccupantKind`, `OccupancyReason` (+`MOVED`), `OccupancyRow.occupant_kind` optional.
- `backend/app/modules/games/models.py:110` -- `seat_occupancy.occupant_kind` nullable, new CHECK; `seat_weeks` reason CHECK follows the enum (`_in`).
- `backend/app/modules/games/repo.py:66` `has_occupant` → latest row kind not null; `_latest_occupancy` :100; `student_seated` :117 (reuse for a count `student_seat_count`); new `class_game_ids(session, class_session_id) -> dict[int, uuid]`.
- `backend/app/modules/games/commands.py` -- `__all__` :68; `_commit_change` :190; `_transaction` :206; `_policy`; `_append_initial` :497 (pattern for the rows); `assign_seat` :426 (guards pattern). New `move_seat` after `assign_seat`. `test_commands_never_branch_on_purpose` forbids purpose compares.
- `backend/app/modules/games/service.py` -- export `class_game_ids` (sessions never imports `games.repo`).
- `backend/app/platform/events/registry.py` -- `games.move_seat`, `sessions.move_allocation`.
- `backend/migrations/versions/0039_free_seats.py` (new, revises 0038); `tests/test_migrations.py` HEAD "0039", fold a CHECK assertion into `test_0037_and_0038_…` (:736).
- `backend/app/modules/sessions/schemas.py:346` `AllocationOut` (+`confirmed_at`), new `AllocationMoveIn`; `service.py:1272` `_allocation_out`, :1420 `confirm_allocation` (lock/stale pattern), :1487 `_commit_allocation` (notice pattern), new `move_allocation` + `InvalidMove(_FieldsError)` code `invalid_move` (422); `routes.py:337` confirm route pattern → new move route; `README.md`.
- Tests: `backend/tests/games/test_move_seat.py` (new; helpers in `tests/games/helpers.py`, Class game creation as `test_class_games.py`), `tests/games/test_registry.py` (runner for `move_seat` on a Class game; the simulation-only `session` assertion skips it), `backend/tests/sessions/test_allocation_move.py` (new; helpers/fixtures from `test_allocation_confirm.py`).
- Web: `frontend/src/modules/sessions/api.ts` (`moveAllocation`), `allocation.ts` (+test: label helpers `moveLabel`, `seatRows`), `allocation-panel.tsx` (Preview: seat list, pick state, confirmed line), `copy/nb.ts` `sessions.allocation`; `dates.ts:90` `osloDayAndTime` for the date; regenerate `src/lib/api/openapi.json` + `schema.ts` (same script as 5.9).
- E2e: `frontend/e2e/class-session-allocation.spec.ts` (helpers `sessionWithStudents`, `storedAllocation`, `expectAccessible`).

## Tasks & Acceptance

**Execution:**
- games: schemas, models, repo, commands (`move_seat`), service, registry, migration 0039 -- the AD-2 command and free Seats.
- sessions: schemas, service (`move_allocation`), routes, README -- the draft edit and the confirmed path with notices.
- Backend tests: every matrix row; Games' Seats equal the draft after confirmed edits; lock order of `move_seat` (FOR UPDATE statements in id order); registry; migration head.
- Web + regenerated types + e2e: move and swap by keyboard (Enter/Space only), focus return, confirmed edit, Issue #107 line, axe at 320/360/1440.

**Acceptance Criteria:**
- Given an open unconfirmed preview, when the Lecturer picks a Student and presses «Flytt … til ledig …» or «Bytt … med …», then the request carries draft id and revision, the chart shows the change, the revision rises under the same id, focus is on the moved Student's row, and «Bekreft fordeling» then commits the edited groups.
- Given a confirmed allocation before the Start date, when a swap is done in the panel, then the Class games' Seats change accordingly, the affected Students get the allocation notice, and the panel keeps showing «Fordelingen er bekreftet {dato}.».
- Given a locked session or an Assistant lecturer, then no move control is shown, and the route answers 409 `session_locked` / 403.
- Given a confirmed allocation opened read-only, then the panel says «Fordelingen er bekreftet {dato}.» (Issue #107).

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 30 findings — high 0, medium 2, low 24, false 4, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) A free-Seat row could carry a `user_id`: `ck_seat_occupancy_user_student` is NULL for a NULL kind. `ck_seat_occupancy_free` now also requires `user_id IS NULL` (model and 0039); a test case was added.
  - `[low]` `[reject]` (blind) A Student removed from the Roster can still be moved after the confirmation. The notice is dropped at send time (`allocation_mail_context` needs a registered Student), and freeing removed Students' Seats is Story 5.13's job; a guard would add a branch for a rare case.
  - `[false]` `[reject]` (blind) `games[wanted.from_game]` can raise `KeyError`. After the confirmation every draft game has its Class game: moves never drop a game (`last_student`), and removals only change the draft before the confirmation.
  - `[false]` `[reject]` (blind) 0039 widens `ck_seat_weeks_reason` for no reason. The model builds both checks from the one `OccupancyReason` enum, and `test_the_check_constraints_list_exactly_the_enum_values` requires them to match.
  - `[false]` `[reject]` (blind) Other readers may misread a NULL-kind row. They read the latest row through `seats_with_occupant`, which reports None for a free Seat as before; `start` fills Seats whose kind is None (`commands.py:818`).
  - `[low]` `[reject]` (blind) Each move sends the notice again. It is a `digest` kind: at most one mail per Student per day.
  - `[low]` `[reject]` (blind) Some refusal codes (404 `game_not_found`, `seat_occupied`, `student_already_seated`, `class_session_mismatch`) reach the client as «Prøv igjen». None is reachable through the draft path, whose draft mirrors the Games; `class_archived` is mapped globally.
  - `[low]` `[patch]` (blind) The pick was stored by game and Role, so a draft read again (window focus) could move another Student. The pick now keeps the Student's id and is dropped when another holds the Seat.
  - `[low]` `[reject]` (blind) No Escape to cancel, no focus jump to the Seat list, two status regions. The cancel button and Tab order work; these are refinements beyond the story.
  - `[low]` `[reject]` (blind) Untested: concurrent moves, `student_already_seated` in `move_seat`, magic numbers in two tests. The lock order is tested; the duplicate check guards corrupt data only.
  - `[low]` `[patch]` (blind) `confirmed_at` was optional in the TypeScript type. It is now a required nullable field.
  - `[low]` `[reject]` (blind) The 0039 downgrade fails with free-Seat rows present. Documented in the migration, as 0038 does for Class games.
  - `[low]` `[reject]` (edge) Removed Student moved after confirmation. As row 2.
  - `[low]` `[patch]` (edge) Free-Seat CHECK misses `user_id` in the model. As row 1.
  - `[low]` `[patch]` (edge) Same in migration 0039. As row 1.
  - `[low]` `[reject]` (edge) Downgrade with free rows. As row 12.
  - `[false]` `[reject]` (edge) `KeyError` on a missing Class game. As row 3.
  - `[low]` `[patch]` (edge) Pick keyed by Seat moves another Student. As row 8.
  - `[low]` `[reject]` (edge) After a `session_locked` answer the move buttons stay until reload. Every press then says the session has started; the Start date passing while the panel is open is rare.
  - `[medium]` `[patch]` (edge, claim) The e2e never swapped in the panel after the confirmation. The confirmed step is now a swap.
  - `[low]` `[patch]` (edge, claim) Space was never pressed. The keyboard test now picks with Space.
  - `[low]` `[reject]` (intent) The `last_student` refusal goes beyond the story's text. Recorded as a decision (Design Notes): Class games are never dropped after confirmation.
  - `[low]` `[reject]` (intent) `student_already_seated` in `move_seat` is not reached by a test. As row 10.
  - `[low]` `[reject]` (intent) Only `game_already_started` is tested as a command refusal inside the route. It shows the shared path: nothing committed, no notice.
  - `[low]` `[reject]` (intent) The hidden controls when locked are tested with a stubbed `locked: true`. The real lock is tested at the API; this is the pattern of Stories 5.8 and 5.9.
  - `[low]` `[reject]` (intent) Issue 107's read-only view is tested with a stubbed `can_manage: false`. As row 25.
  - `[low]` `[patch]` (intent) The move controls skipped the 400 % zoom size. The tap test now runs at all four sizes.
  - `[low]` `[reject]` (intent) The label tests use the same functions as the e2e. The unit tests pin the literal Norwegian strings.
  - `[low]` `[reject]` (intent) The notice says nothing about the move. Founder decision 2026-11-12: no game or Role is named to a Student before the Start date.
  - `[medium]` `[patch]` (verification-gap) The panel's handling of a stale move (409 `allocation_changed`) was untested. New e2e «a move on a draft changed meanwhile is refused, and the current draft is shown».

## Design Notes

- A Seat freed before the start needs a fact in an append-only table: a row with NULL `occupant_kind` and reason `moved` says «nobody from Week 1» without updating or deleting history (AD-5, AD-14). Readers that already treat "no row" as free (`seats_with_occupant`, `start`'s fill) read it the same way; Story 5.12's snapshot fill uses the same readers.
- The draft stays the one picture of the allocation after confirmation: every confirmed edit changes the draft and the Games in one transaction under the session lock, so the preview equals the Seats.
- «last_student» refusal: Class games are never dropped after confirmation, and before it a game left with no Student would be an all-AI game; free Seats outside the small group only exist after removals, so the refusal costs little.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_move_seat.py tests/sessions/test_allocation_move.py tests/games/test_registry.py -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Lecturer can move a Student to a free Seat or swap two, before and after «Bekreft fordeling», until the lock. `POST /api/class-sessions/{id}/allocation/move` takes `{draft_id, revision, from_game, from_role, to_game, to_role}`. It edits the stored draft under the same id, raises the revision by one and emits `session`. Once the allocation is confirmed, the same transaction runs the new AD-2 command `games.commands.move_seat` on the Class games and sends each moved Student the allocation notice again. `move_seat` locks the Games in id order, emits `game`, `session` and `user`, and checks that each Student holds one Seat per Class session. A Seat left free gets an append-only occupancy row with no occupant kind and reason `moved` (migration 0039). Refusals: 409 `allocation_changed` (stale), 422 `invalid_move` (`same`, `unknown`, `empty`, `last_student`), 409 `session_locked`, 403, 409 `class_archived`, and the command's own codes. Nothing is committed on a refusal. In the panel, the selected game's Seats form a list with «Flytt eller bytt», then «Bytt» / «Flytt» on the targets. The buttons work by keyboard and touch, need no drag, have accessible names that give the Student, Role and Klassespill, and return focus to the changed row. Issue 107: the open panel says «Fordelingen er bekreftet {dag} kl. {tid}.» whenever the allocation is confirmed (`AllocationOut.confirmed_at`).

**Files changed**
- Backend games: `schemas.py` (`MOVED`, optional kind on `OccupancyRow`), `models.py` (nullable kind, `ck_seat_occupancy_free`), `repo.py` (`has_occupant` by latest row, `student_seat_count`, `class_game_ids`), `commands.py` (`move_seat`), `service.py` (`class_game_ids`). Migration `0039_free_seats.py` (new).
- Backend sessions: `schemas.py` (`AllocationMoveIn`, `confirmed_at`), `service.py` (`move_allocation`, `InvalidMove`, `SeatCommandRefused`), `routes.py` (move route), `README.md`. Also `platform/events/registry.py` (`games.move_seat`, `sessions.move_allocation`).
- Backend tests: `games/test_move_seat.py` and `sessions/test_allocation_move.py` (new). Updated: `test_registry`, `test_allocation`, `test_allocation_confirm`, `test_migrations` (head 0039, folded into the 0037/0038 test).
- Frontend: `allocation-panel.tsx` (Seat list, pick state, confirmed line), `allocation.ts` (+test), `api.ts`, `copy/nb.ts`, and the regenerated `openapi.json` and `schema.ts`. E2e: `class-session-allocation.spec.ts`.

**Review findings.** 30 rows: 0 high, 2 medium, 24 low, 4 false. Ten rows were patched (2 medium, 8 low). Nothing was deferred. The rejected rows and their reasons are in the triage log.

**Follow-up review recommended: false.** The two medium patches are added e2e tests (a confirmed swap, a stale move). Both pass. No unverified risk remains to name.

**Verification**
- Backend: 2501 passed (75 s). Ruff check and format are clean. Each new test runs in under 1 s.
- Frontend: typecheck, Vitest 430, `check:copy`, `lint:colours` and build pass. Playwright 252/252 on the rebuilt stack, with axe at 320, 360, 1440 px and 400 % zoom for the move controls.
- Matrix audit: every I/O row has a passing test in `test_allocation_move.py`, `test_move_seat.py` or the e2e.
- Screenshots at 1440 and 360 px were checked in the scratchpad (not committed): open, picked, picked on another game, moved, and confirmed and opened again. The picked line was moved under «Seter i Spill N», and the Seat rows now use one button column (one full-width button on phones).
- **Migration 0039 was changed after it ran.** `ck_seat_occupancy_free` gained `user_id IS NULL`. The constraint was re-created by SQL on the databases that had already run 0039: the shared `olspillet_test*` databases and the local `olspillet`. No database was dropped.
- The implementation and fixes were done in this context, on the caller's instruction. The four reviewers were sub-agents, and their reports were read from their transcripts.

**Decisions taken in place of the founder**
- A freed Seat is an occupancy row with no occupant kind and the new reason `moved`. Occupancy stays append-only, and AD-5's kinds are unchanged; its reason list gains `moved`.
- One route covers both actions. If the target Seat holds a Student, the two swap; if it is free, the Student moves. A move may change the Role within one game.
- A move that would leave a game with no Student is refused (`last_student`). A swap is always allowed. Games are never added or removed by a move.
- After the confirmation the draft remains the picture of the Seats. Each move changes the draft and the Class games together.
- Moved Students get the 5.9 notice again, keyed by the revision, as a digest (one mail a day at most). Students whose game-mates changed are not told.
- UI: the pick-then-target flow on the selected game's Seat list. Visible «Flytt eller bytt» / «Bytt» / «Flytt» / «Avbryt flyttingen»; the full sentence is the accessible name. All new copy is [ASSUMPTION] draft in `nb.ts`.
- Issue 107: the line shows for every viewer of a confirmed allocation, with weekday, date and time in Oslo time. When the allocation can still be edited, «De som flyttes eller byttes, får beskjed på e-post.» replaces the pre-confirm notice line.

**Residual risks**
- Moving a Student who has left the Roster is allowed. Story 5.13 frees such Seats.
- The panel is not refetched on `session:<id>`. The revision check guards every move, and a stale pick is dropped.
