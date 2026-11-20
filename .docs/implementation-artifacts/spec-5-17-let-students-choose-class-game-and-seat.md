---
title: 'Story 5.17: Let Students choose a Class game and a Seat (cut list, FEATURE_STUDENT_CHOICE)'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '180e257e2dfa83abbfb8f4b867052bd6f190115f'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-16-set-information-visibility.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred:
  - summary: >-
      After the lock, a Student who chose their own Seat sees the Story 4.5 Hjem line «Du får Rolle og spill på startdatoen.».
    evidence: |-
      homeLine returns null when the choice is closed and no Seat was drawn, so SeatChoiceStatus falls back to nb.homes.startDate. The same line shows after the start for every session today; Epic 6 rebuilds Hjem.
    location: >-
      frontend/src/modules/sessions/seat-choice-home.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** Every Class session is allocated at random (Stories 5.8–5.13); Students cannot pick the Class game and Seat they play in with people they arranged to play with (FR-21).

**Approach:** Behind `FEATURE_STUDENT_CHOICE` (`get_settings().feature_student_choice`, already in config and compose) the Lecturer picks the allocation method «Studentene velger» with Valgknapper and saves. That stores `class_sessions.allocation_method = 'student_choice'`, creates `ceil(n/4)` empty Class games, stores a confirmed empty draft (so every 5.8–5.13 rule that keys on «confirmed» holds) and notifies each registered Student. Students then take or change a Seat on a new «Velg spill og sete» screen until the lock; the lock draws a free Seat for each Student still without one.

## Boundaries & Constraints

**Always:**
- Migration 0042: `allocation_method TEXT NOT NULL DEFAULT 'random'`, CHECK `IN ('random','student_choice')`. Existing rows are random.
- Save (`ClassSessionSaveIn.allocation_method`, None keeps). Order: archived, then a *changed* method → flag off and target `student_choice`: 422 `feature_disabled` `{"allocation_method": "feature_disabled"}`; locked: 409 `session_locked` `{"allocation_method": "locked"}`; a confirmed draft exists: 409 `allocation_confirmed` `{"allocation_method": "confirmed"}` (so once saved, Student choice is final, and random cannot switch after a confirm). Unchanged values are never judged.
- Switching to Student choice (same transaction): an unconfirmed draft is replaced by a draft with `assignments: []`, fresh seed, `drawn_by`/`confirmed_by` = Lecturer, `confirmed_at` = now; `ceil(registered/4)` games through `games.commands.create(CLASS, …, within=s)`; one `student_choice_open` digest notice per registered Student (key `student_choice_open:{session}:{user}`, ref session); `user:<id>` per registered Student.
- The draft always mirrors the Seats: every Seat change through this story updates `assignments` and raises `revision`. Seats placed by draw carry `"drawn": true` in their assignment.
- Student routes (`class_sessions.read_enrolled`): `GET /api/me/class-sessions/{id}/seat-choice` and `PUT` same path `{game_number, role}`. 404 `not_found` when the flag is off, the id is malformed or unknown, the User is not a registered Student of its Class, or the method is random. Answer `SeatChoiceOut`: `class_name`, `number`, `start_at`, `open` (not `is_locked`), `my_seat` `{game_number, role}|null`, `drawn` bool, `games[]` each `{number, seats[]}` in Fabrikk-first order, seat `{role, holder: free|student|ai, name|null, mine}` (names via `classes.service.student_names`; a removed Student's Seat reads `student` with name null).
- PUT under the Class session row lock: archived 409 `class_archived`; locked 409 `session_locked`; unknown game or role 422 `invalid_seat`; own Seat → unchanged 200; held by anyone else (or command `seat_occupied`) → 409 `seat_taken`. No Seat yet → `games.commands.assign_seat(student)`; else `games.commands.move_seat` in the same request. Then draft mirror, `user:<id>` for every registered Student, `session:<id>`.
- Sweep due action `sessions.offer_student_choice` (after `sessions.seat_late_registrant`): items `(session_id, user_id)` for each registered Student of an unlocked, writable Student-choice session who has no `student_choice_open` notice yet (`notify.used_keys`); the action adds Class games until `4·games ≥ |seated ∪ registered|` and enqueues the notice. `late_registrants` skips unlocked Student-choice sessions.
- Lock: for a Student-choice session (and not archived) the lock's transaction places each registered Student without a Seat in a random free Seat of a random `not_started` game, or a new game when none is free; assignment `"drawn": true`; `allocation_confirmed` notice keyed `…:{draft}:{revision}:{user}`; then `open_games` as before. After the lock, a late registrant seated by 5.13 in a Student-choice session is also `drawn`.
- `GET /api/me/class-sessions` items add `seat_choice_open` (flag on, Student choice, not locked) and `drawn_seat` (`{game_number, role}` when locked and the Student's Seat is `drawn`), both false/null with the flag off.
- `ClassSessionOut` adds `allocation_method` and `student_choice_enabled`. `AllocationOut` adds `method`; for Student choice before the open its games are the Class games as their Seats hold them (empty games included), `missing_count` = registered without a Seat.
- Screens: Klasseøkt (flag on, can manage, unlocked, method random and not confirmed): Valgknapper «Fordelingsmåte» «Tilfeldig» / «Studentene velger» in the Fordeling block, sent on «Lagre Klasseøkt». With Student choice the block reads «Studentene velger spill og sete selv.» and its panel is read-only (no draw, confirm or move). Student: route `/klasseokter/[id]/velg-sete` per UX-DR62; Hjem shows a «Velg spill og sete» Lenke while open and «Du fikk et sete ved trekning: Grossist i Spill 17.» once drawn. All copy in `nb.ts`, new strings `[ASSUMPTION]`.

**Never:** No change to random allocation behaviour or to the demo Class. No Student-choice Seat after the lock. No Lecturer move UI in Student choice. No topics.ts refetch (Story 6.4). No edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Switch on | 5 registered, flag on, unlocked | 2 empty games, confirmed empty draft, 5 notices, `allocation_method` student_choice | — |
| Flag off | save student_choice | nothing stored | 422 `feature_disabled` |
| After confirm | random confirmed, save student_choice | nothing stored | 409 `allocation_confirmed` |
| Back to random | student_choice stored, save random | nothing stored | 409 `allocation_confirmed` |
| Take | free Seat | Seat held, draft mirrors it, `user` events | — |
| Change | Student holds a Seat, takes another free one | moved via `move_seat`, old Seat free | — |
| Taken | Seat held by another | unchanged | 409 `seat_taken` |
| Race | two PUTs on one free Seat | one 200, one 409 `seat_taken` | — |
| Route off | flag off / random / not a Student | — | 404 `not_found` |
| Late registrant | 9th Student registers, 2 games full of 8 | sweep adds game 3, notice once; not seated | — |
| Lock | 2 of 5 chose | 3 drawn into free Seats (`drawn`), AI fills rest; `drawn_seat` on Hjem | — |
| Locked PUT | after Start date | unchanged | 409 `session_locked` |

</intent-contract>

## Code Map

- `backend/migrations/versions/0042_allocation_method.py` -- new; `backend/app/modules/sessions/models.py:31` column + CHECK.
- `backend/app/modules/sessions/service.py` -- `save_session:780` (new kw `allocation_method`, judged before `repo.save`); `get_session:702`; `enrolled_sessions:1039`; `_allocation_out:1403`/`_opened_out:1458`/`allocation_of:1500` (Student-choice games); `_allocate_at_lock:1995` (branch for Student choice); `late_registrants:2207` skip; `seat_late_registrant:2268` drawn flag; new section «Student choice (Story 5.17)»: `student_choice_enabled`, `_open_student_choice`, `seat_choice`, `take_seat`, `offer_student_choice_due`/`student_choice_offers`, `student_choice_mail_context`. Reuse `_open_seats`, `_seated`, `_students_of`, `_rng`, `SEAT_ORDER`.
- `backend/app/modules/sessions/repo.py:188` `save` (allocation_method), `enrolled_sessions:80` (method), `drafts_of(ids)` new.
- `backend/app/modules/sessions/schemas.py` -- `AllocationMethod`, `SeatChoiceOut`, `SeatChoiceIn`, `SeatRef`; fields on `ClassSessionOut`, `ClassSessionSaveIn`, `EnrolledSessionOut`, `AllocationOut`.
- `backend/app/modules/sessions/routes.py` -- pass `allocation_method`; map `AllocationConfirmed`; two Student routes.
- `backend/app/modules/games/commands.py:641` `move_seat` -- reused unchanged; `assign_seat:463` raises `seat_occupied`.
- `backend/app/platform/notify/__init__.py` -- `used_keys(session, keys)`.
- `backend/app/modules/messaging/delivery.py:131` -- `student_choice_open` DIGEST kind + context; templates `backend/app/platform/email/templates/kinds/student_choice_open.{txt,html}.j2`.
- `backend/app/modules/ops/sweep.py:59` -- due action; `backend/app/platform/events/registry.py:60` -- `sessions.choose_seat`, `sessions.offer_student_choice`.
- Tests: new `backend/tests/sessions/test_student_choice.py` (helpers from `test_late_registrants.py`, `test_open_games.py`, `test_capacity.py` flag pattern; Student calls via `tests.classes.test_staff.call(email, …)`), `tests/ops/test_sweep.py` action list.
- Frontend: `frontend/src/lib/api/{openapi.json,schema.ts}` regenerate; `frontend/src/modules/sessions/api.ts` (hooks, `ChoicesBody` + `allocation_method`); `choices.ts`; `class-session-page.tsx:345` (pass method); `allocation-panel.tsx` (method choice, read-only Student-choice panel); new `seat-choice.ts` (pure helpers) + `seat-choice-page.tsx`; route `frontend/src/app/(app)/klasseokter/[sessionId]/velg-sete/page.tsx`; `frontend/src/modules/identity/homes.ts` path; `frontend/src/modules/classes/student-home.tsx` + `frontend/src/app/(app)/hjem/page.tsx` (slot for the sessions' line); `frontend/src/copy/nb.ts`.
- Frontend tests: `seat-choice.test.ts`, `choices.test.ts`; e2e `frontend/e2e/student-choice.spec.ts` (fresh Class via `frontend/e2e/support/classes.ts`, Students `student2@`…`student8@`).

## Tasks & Acceptance

**Execution:**
- Migration, models, repo -- column and reads.
- Service, schemas, routes, notify, delivery, templates, sweep, registry, README -- behaviour above.
- `backend/tests/sessions/test_student_choice.py` -- every matrix row; flag via `monkeypatch.setenv("FEATURE_STUDENT_CHOICE", …)` + `get_settings.cache_clear()`.
- Frontend api regenerate, copy, Lecturer method choice, Student page, Hjem line; unit tests of pure helpers; e2e: Lecturer switches to Student choice and saves; a Student opens «Velg spill og sete», presses a free Seat, sees «Ta setet …», takes it; a stale Seat answer shows the focused conflict line; axe at 320/360/1440 px.

**Acceptance Criteria:**
- Given the flag off, when the Klasseøkt renders, then no method choice shows, and the Student route answers 404.
- Given Student choice saved, when a Student opens «Velg spill og sete», then each Klassespill lists four Seats as «Grossist, ledig» or the holder's name, a free Seat pressed shows primary «Ta setet Grossist i Spill 17», and taking it holds the Seat.
- Given a conflict, when the PUT answers `seat_taken`, then the list is refetched and focus is on «Setet ble tatt av en annen. Velg et annet.» (`tabindex="-1"`) above it.
- Given the Start date, when the lock runs, then every registered Student has a Seat, AI fills the rest, and a drawn Student's Hjem shows «Du fikk et sete ved trekning: …».

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 48 findings — high 0, medium 5, low 31, false 12, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: the Lecturer's draw, confirm and move routes do not refuse a Student-choice session. Draw and redraw already refuse (the draft is confirmed), and a confirm is a no-op; a move did go through. Fixed: `move_allocation` answers 409 `allocation_confirmed` `{"allocation": "student_choice"}`; test `test_the_lecturer_moves_no_seat_the_students_chose`.
  - `[false]` `[reject]` blind: game numbers collide when Class games outlive the draft. Class games exist only under a confirmed draft (5.9 creates them in the confirm; the only draft deletion, in a confirm with removed Students, happens before any game exists), and a confirmed draft refuses the switch.
  - `[false]` `[reject]` blind: a Role with no seat row reads free but is refused. `games.commands.create` always inserts the four Seats (`repo.insert_seats`); the `None` branch is defensive only.
  - `[false]` `[reject]` blind: `ClassArchived` from the PUT becomes a 500. It is mapped app-wide in `main.py` to 409 `class_archived` (README, Rules).
  - `[low]` `[reject]` blind: membership is read before the row lock. A Student removed in that window keeps a Seat until the lock, whose open gives it to an AI player (5.12); not worth a second registry read.
  - `[low]` `[reject]` blind: a removed Student's chosen Seat stays taken until the lock. The open replaces it with an AI player (5.12); freeing it earlier needs a new sweep action.
  - `[false]` `[reject]` blind: the offer's dedupe breaks if notice rows are pruned. No code deletes `notices` rows.
  - `[low]` `[reject]` blind: the offer finder costs a few queries per open session each minute. Same shape as 5.13's finders; Student-choice sessions are few.
  - `[low]` `[defer]` blind: after the lock a Student who chose sees the Story 4.5 line «Du får Rolle og spill på startdatoen.» on Hjem. The same line shows for every session after its start today; Epic 6 rebuilds Hjem.
  - `[low]` `[reject]` blind: the mail carries no link. As every digest kind of the epic (allocation, obligatory, Lab hours).
  - `[low]` `[patch]` blind: `invalid_seat` and `class_archived` fall back to «Prøv igjen». Fixed: `invalid_seat` has its own line and refetches the list; `class_archived` is in the shared messages.
  - `[low]` `[patch]` blind: no test of the allocation notice for drawn Students. Same as the first verification-gap row.
  - `[low]` `[patch]` blind: Hjem's two fields used two lock predicates. Fixed: the drafts are read for sessions `is_locked`.
  - `[false]` `[reject]` blind: `user:<id>` goes to every registered Student, not those who can still choose. Before the lock every registered Student can still choose or change, which is the only time a Seat changes.
  - `[low]` `[reject]` blind: `SeatChoiceIn.role` is a string. Deliberate, so an unknown Role answers 422 `invalid_seat` like an unknown game.
  - `[low]` `[reject]` blind: downgrading 0042 forgets Student choice. Downgrades are a development tool; no data migration guards elsewhere either.
  - `[false]` `[reject]` edge: an unmapped `CommandError` from `assign_seat`/`move_seat` gives a 500. The reachable codes are mapped: `game_already_started` needs a game started, which needs the open after the lock (refused first); the game and Role come from the session's own games.
  - `[medium]` `[patch]` edge: a Lecturer move rearranges chosen Seats. Same entry as the first blind row.
  - `[low]` `[patch]` edge: a switch to random would open Student choice. Unreachable (refused while a draft is confirmed) but a direct correction: only a switch to `student_choice` opens it.
  - `[low]` `[patch]` edge: a queued `student_choice_open` mail goes out after the flag is switched off. Fixed: the mail context leaves it out while the flag is off; test added.
  - `[low]` `[patch]` edge: after `session_locked` the stale list stays pressable. Fixed: `session_locked` and `invalid_seat` refetch the list.
  - `[low]` `[reject]` edge: a locked session with games half opened shows the choosing panel. Lasts until the next sweep minute finishes the open (5.12); not worth a branch.
  - `[low]` `[patch]` edge: the method choice flashed for a confirmed session while the block loaded. Fixed: shown only once the block is read.
  - `[false]` `[reject]` edge (claim): the lock finds no draft for a Student-choice session. The save writes the confirmed draft in its transaction and nothing deletes a confirmed one.
  - `[low]` `[patch]` verification-gap: no test that only drawn Students get the allocation notice. Added to `test_the_lock_draws_a_seat_for_each_student_who_chose_none`.
  - `[low]` `[patch]` verification-gap: the `student_choice_open` mail is never rendered. Added `test_the_digest_tells_each_student_they_may_choose` (digest sweep, `mails()`).
  - `[low]` `[patch]` verification-gap: no post-lock late registrant marked `drawn`. Added `test_a_student_registering_after_the_lock_gets_a_drawn_seat`.
  - `[low]` `[patch]` verification-gap: nothing pins that the panel offers no move in Student choice. The e2e test now asserts no Seat list and no «Flytt eller bytt».
  - `[medium]` `[patch]` verification-gap (other): `move_allocation` accepts moves in Student choice. Same entry as the first blind row.
  - `[false]` `[reject]` intent: the flag-off screens are tested with rewritten answers. The screens read only `student_choice_enabled` and the 404; the real flag is tested at the api, as Stories 5.15 and 5.16 did.
  - `[false]` `[reject]` intent: the race serialises on the Class session row, not the Game row. The commands still take the Game row lock; the session lock is what keeps the draft mirror right, and the outcome (one 200, one 409 `seat_taken`) is the AC's and is tested.
  - `[false]` `[reject]` intent: Hjem (Story 4.5) is changed. It is the only Student entry point to the route the story builds; Epic 6 rebuilds Hjem on the same api fields.
  - `[false]` `[reject]` intent: a session saved with the flag on keeps Student choice after the flag goes off. Recorded design decision, as 5.15/5.16; AC1 holds for every session while the flag is off from the start.
  - `[false]` `[reject]` intent: the drawn line on Hjem is tested in e2e through a rewritten answer. The lock's draw and `drawn_seat` are tested at the api; the screen reads only that field.
  - `[medium]` `[patch]` visual: Hjem showed «Du får Rolle og spill på startdatoen.» while the sessions loaded (the screenshot caught it). Fixed: nothing while loading; the Start-date line only when no session line applies.
  - `[low]` `[patch]` visual: the conflict line used `restordre` as an accent. Now an `ink` rule: taking a Seat someone else got is no error of the Student's.
  - `[low]` `[reject]` visual: no screenshot of the drawn line. The e2e test asserts it on Hjem at 360 px with axe.
  - `[medium]` `[patch]` visual: free Seats looked inactive (grey, hover-only cue). Free Seats are now `ink` with a «Velg» mark in `lager`; held Seats `ink-secondary`; the button's name stays «Grossist, ledig».
  - `[low]` `[patch]` visual: «Ditt sete» and «Du har tatt setet» said the same twice. The status line is gone; the focused «Ditt sete: …» is the result.
  - `[low]` `[patch]` visual: three intro lines repeating «startdatoen». Merged into one: «Velg før startdatoen ti. 24. nov. kl. 10:00. Du kan bytte til et annet ledig sete fram til da.»
  - `[low]` `[patch]` visual: «Grossist, deg» reads awkwardly. Now «Grossist, ditt sete».
  - `[low]` `[patch]` visual: a move gives no warning. Under «Ta setet …» a Student holding a Seat reads «Du gir fra deg Grossist i Spill 1.»
  - `[low]` `[patch]` visual: bold meant both own and picked. Picked is the frame only.
  - `[low]` `[patch]` visual: «valget» meant two things. Now «Fordelingsmåten kan ikke endres etter at den er lagret.»
  - `[low]` `[reject]` visual: the save hint «Du kan lagre uten å endre noe.» while a method change waits. Earlier stories' hint, true of the save itself.
  - `[low]` `[reject]` visual: Student choice can be saved with no Start date. Dates are set separately, often later; the Student screen says «Velg før startdatoen» until one is set.
  - `[low]` `[reject]` visual: «Ikke bekreftet.» above the method choice. The block's state line is true until a method is saved.
  - `[low]` `[patch]` visual: «Klassespill og sete» vs «spill og sete». The help now says «spill og sete».

The five reviewers finished, but their completion notices did not reach this builder; their reports were read from their transcripts. The visual reviewer stood in for the founder's eye check; the builder re-captured the Student screen at 360 px after the patches (free Seats with «Velg», own Seat bold, move warning under the button).

## Design Notes

Founder-level decisions taken here:
- The method is a stored column, final once Student choice is saved (switching back would need games deleted, which `games.commands` cannot do).
- Student choice reuses the confirmed-draft machinery: the confirmed empty draft keeps the Lærerhjem «Venter», the lock's auto-allocation and Story 5.13 correct without new branches beyond the lock's draw and the pre-lock late-registrant skip.
- Holders' names are shown to classmates as UX-DR62 asks; AI players appear only after the lock.
- The Hjem link and drawn line are added to the current (Story 4.5) Hjem; Epic 6 rebuilds Hjem on the same api fields.
- A flag switched off after a session chose Student choice keeps it (like 5.15/5.16): the lock still draws, but the Student route answers 404.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_student_choice.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run build && npx playwright test` -- pass

## Auto Run Result

Status: done

**Summary.** Behind `FEATURE_STUDENT_CHOICE` (already in config and compose, default on) a Lecturer can let the Students choose their Class game and Seat.
- **Klasseøkt:** Valgknapper «Fordelingsmåte» («Tilfeldig» / «Studentene velger») in the Fordeling block until an allocation is confirmed, saved with «Lagre Klasseøkt». Saving Student choice stores `class_sessions.allocation_method = 'student_choice'` (migration 0042), a confirmed empty draft, `ceil(n/4)` empty Class games and one `student_choice_open` digest notice per registered Student. It is final once saved (409 `allocation_confirmed`); flag off 422 `feature_disabled`; locked 409 `session_locked`. The block then reads «Studentene velger spill og sete selv.» and its panel is read-only (the api refuses a Lecturer move too).
- **Student:** `GET|PUT /api/me/class-sessions/{id}/seat-choice` (404 `not_found` with the flag off, for a random session or a non-Student) and the screen `/klasseokter/{id}/velg-sete` «Velg spill og sete»: each Klassespill with four Seats in words («Grossist, ledig», names, «Grossist, ditt sete»), a pressed free Seat shows the primary «Ta setet Grossist i Spill 17»; a Student holding a Seat is moved through `move_seat`; 409 `seat_taken` refetches and focuses «Setet ble tatt av en annen. Velg et annet.» (`tabindex=-1`). Hjem gets the «Velg spill og sete» Lenke while open and «Du fikk et sete ved trekning: …» once drawn.
- **Sweep and lock:** new due action `sessions.offer_student_choice` tells late registrants and adds games when Seats run short; Story 5.13 seats nobody in such a session before the lock. The lock draws each Student without a Seat into a free Seat (new games if none), marks it `drawn` in the draft and sends the allocation notice; the open fills the rest with AI players.

**Files.**
- `backend/migrations/versions/0042_allocation_method.py` (new), `backend/app/modules/sessions/{models,repo,schemas,service,routes}.py`, `README.md`: method, Student choice section, routes.
- `backend/app/platform/notify/__init__.py` (`used_keys`), `backend/app/modules/messaging/delivery.py` + `templates/kinds/student_choice_open.{txt,html}.j2`, `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py`.
- Tests: `backend/tests/sessions/test_student_choice.py` (new, 15 tests), `tests/test_migrations.py` (0042 folded into the 0037–0041 test), shape updates in `test_allocation.py`, `test_allocation_confirm.py`, `test_dates.py`.
- `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated; `frontend/src/copy/nb.ts` (`[ASSUMPTION]` draft copy); `frontend/src/modules/sessions/{api,allocation,choices,seat-choice}.ts`, `allocation-panel.tsx`, `class-session-page.tsx`, `seat-choice-page.tsx` (new), `seat-choice-home.tsx` (new); `frontend/src/app/(app)/klasseokter/[sessionId]/velg-sete/page.tsx` (new), `hjem/page.tsx`; `frontend/src/modules/classes/student-home.tsx` (`status` slot); `frontend/src/modules/identity/homes.ts` (`seatChoicePath`).
- Frontend tests: `seat-choice.test.ts` (new), fixture updates; `frontend/e2e/student-choice.spec.ts` (new, 6 tests).

**Review.** 48 findings: medium 5 (three entries), low 31, false 12. Patched: Lecturer move refused in Student choice; a switch only to Student choice opens it; no choice mail while the flag is off; one lock predicate for Hjem; stale list refetched on `session_locked`/`invalid_seat`; method choice hidden until the block loads; Hjem shows no Start-date line while loading; the Student screen redesigned per the visual review (free Seats `ink` with «Velg», one intro line, «ditt sete», move warning, no duplicate status, `ink` conflict rule); copy fixes; four test gaps closed. One low deferred (Hjem line after the lock for Students who chose). Rejections and reasons are in the triage log. Patched counts by entry verdict: medium 3, low 13.

**Follow-up review:** true. Three medium entries were patched. The specific unverified risk: the redesigned free-Seat rows and the Hjem loading state were looked at only in the builder's own screenshots after the patches, not by an independent visual reviewer.

**Verification.**
- Backend: 2606 passed (72 s); ruff check and format clean.
- Frontend: typecheck, Vitest 452 passed, `check:copy`, build (in the compose image). Playwright: full run before the review patches 267 passed, 6 failed under load (admin-audit, roster-upload, student-registration) and passed on `--last-failed`. Full run after the patches: 257 passed; 3 failures were this spec's own button-text assertion (fixed: accessible names) and 7 others (class-session-allocation, registration-status, student-registration) passed when re-run; `student-choice.spec.ts` 6/6 and `homes.spec.ts` 23/23 after the last change.
- Tests over 1 s: `test_the_lock_draws_a_seat_for_each_student_who_chose_none` (1.1 s), `test_the_digest_tells_each_student_they_may_choose` (1.1 s), `test_a_late_registrant_gets_the_offer_and_more_games_once` (1.0 s).
- Migration 0042 is new; it ran once on the shared test databases and was not changed after.

**Residual risks.** A view of other Students' names on «Velg spill og sete» follows UX-DR62. The `user:<id>` events are emitted but the screen refetches only on open and after own actions until Story 6.4. A flag switched off after a session chose Student choice keeps it (the lock still draws; the Student route answers 404). The builder's screenshot run registered demo Students in two fresh local Classes; they were taken off those Rosters again so the demo Student's Hjem is unchanged.

**Process note.** Per the autobuild runbook, the builder implemented the spec in its own context rather than in an implementation subagent, and applied the review patches itself. A fifth, visual reviewer stood in for the founder's eye check.
