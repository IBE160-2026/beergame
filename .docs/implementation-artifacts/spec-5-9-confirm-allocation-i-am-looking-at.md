---
title: 'Story 5.9: Confirm the allocation I am looking at'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '24bd4f5c02d9e013a98fd71d6f4554608888cd02'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-8-preview-random-allocation-run-again.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The stored draft of Story 5.8 can be previewed but never committed: no Class game, Seat or notice exists, the Lærerhjem cannot tell which sessions lack a confirmed allocation, and the games module cannot hold a Game without a settings snapshot or a Student occupant (FR-20, AD-2, AD-4, AD-13). Issue #106 also asks two visual fixes in the same panel.

**Approach:** Extend `games` (policy columns, nullable snapshot, `class_session_id`/`game_number`, `student` occupant with `user_id`, Class-session budget scope, `game_not_ready`) in migration 0038, then add `sessions.service.confirm_allocation(draft_id, revision)` that, in one transaction under the Class session row lock, checks the draft, drops removed Students (raising the revision, committing no Game), or creates one Class game per group and one Seat per Student through `games.commands` joined to that transaction, marks the draft confirmed and enqueues a digest notice per Student. The panel gets «Bekreft fordeling» as the page's primary button.

## Boundaries & Constraints

**Always:**
- `games.policy`: new fields `snapshot: Literal["at_creation","at_lock"]`, `student_occupants: bool`, `class_session_game: bool`. Simulation: `at_creation`, False, False. New `class` row: takeover, pause, playout, overview all True, `guided_weeks="settings"`, `scripted_occupants=False`, `at_lock`, True, True.
- `games.commands.create(purpose, settings=None, …, class_session_id=None, game_number=None, within=None)`: `at_lock` purpose refuses any settings/pattern/seed/model config/Effort level/parameter set (422 `settings_not_allowed`) and stores NULL `settings`, `demand_series`, `demand_seed`, `rules_version`, `session_runtime`; `at_creation` without settings → 422 `settings_required`. Seats from `engine.settings.ROLES` when no settings. `class_session_game` purposes need both ids, others refuse them (422 `class_session_required` / `class_session_not_allowed`). `rule_based_params`/`play_guard_params` default to None, resolved to today's defaults for `at_creation`.
- `assign_seat(…, *, user_id=None, within=None)`: `student` allowed where `student_occupants`; needs `user_id` (422 `user_id_required`), other kinds refuse it (422 `user_id_not_allowed`); a Student who already holds a Seat in a Game of the same Class session → 409 `student_already_seated`; `llm` on a Game without snapshot → 409 `game_not_ready`. `within` joins the caller's transaction (no own commit, no settle), as `place_order(within=)`.
- `start` → 409 `game_not_ready` while `settings` is NULL. Commands on a Game whose policy has `lecturer_overview` and that has a `class_session_id` also emit `session:<class_session_id>`; registry `games.create`/`games.assign_seat` stay `{"game"}` for simulation, a documented `session` addition for Class games is asserted in a test.
- `games.service.scope_of(purpose, runtime, class_session_id=None)`: a Game with `class_session_id` and a model config → `BudgetScope.class_session(id, effort_level)`; `budget_scope` passes it; `games_charged_to` answers running Games of that session for a `class_session` scope. `GameOverview` gains optional snapshot fields, `class_session_id`, `game_number`.
- Migration 0038: `games` snapshot columns nullable with CHECK `num_nulls(...) IN (0, 5)`; `class_session_id` uuid NULL (no FK: `games` sits below `sessions`), `game_number` int NULL, CHECK pair, UNIQUE (`class_session_id`, `game_number`); `seat_occupancy.user_id` uuid NULL (no FK: rows are append-only and ids only, AD-14), CHECK `occupant_kind = 'student' OR user_id IS NULL`; `allocation_drafts.confirmed_at` timestamptz NULL, `confirmed_by` FK users SET NULL.
- `POST /api/class-sessions/{id}/allocation/confirm` body `{draft_id, revision}` (`class_sessions.manage`): lock row; `is_locked` → 409 `session_locked` `{"allocation":"locked"}`; no draft / other id / other revision → 409 `allocation_changed` `{"draft":"changed"}`; already confirmed with the same id → 200 unchanged (idempotent); Students in the draft not registered now → remove their assignments, drop emptied games, renumber 1..n, revision+1 (none left → delete draft), emit `session`, commit, 409 `allocation_changed` `{"draft":"students_removed"}`; else create Games and Seats, set `confirmed_at/by`, notice `allocation_confirmed` (digest) per Student with key `allocation_confirmed:{draft_id}:{user}` and `ref` = session id, emit `session`; answer `AllocationOut` with `confirmed: true`.
- Redraw after confirmation → 409 `allocation_confirmed` `{"allocation":"confirmed"}`. `AllocationOut` gains `confirmed: bool`. Lærerhjem `SessionRef` gains `lacks: list["dates"|"allocation"]`; `allocation` when not confirmed and not locked.
- Mail `allocation_confirmed` (txt+html): names the Class only, «Du får Rolle og spill på startdatoen.» (Student sees game and Role from the Start date, founder decision 2026-11-12); context None when the session is gone, not confirmed, Class archived or the User no longer a registered Student.
- Web: panel shows «Bekreft fordeling» (primary) with «Ingen får beskjed før du bekrefter.» beside it when `can_manage && !locked && !confirmed`; «Lagre Klasseøkt» is secondary while it shows (`onOpenChange`). Success: panel closes, state line «Fordelingen er bekreftet.» (`tabindex=-1`) takes focus. 409 `allocation_changed`: refetch, panel stays on the new draft, message by `fields.draft`. Confirmed: no redraw, no confirm. Issue #106: a removed Student's cell is `paper` with a dashed `ink` outline (not `bar-base`); the selected frame is 1 px, 3 px only with keyboard focus.

**Never:** move/swap (5.10); lock, snapshot or AI occupants of empty Seats (5.11/5.12); late registrants (5.13); naming game or Role to a Student; names in games tables; a second set of Games; touching the demo Class; comparing DB time with host time.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Confirm | 5 Students, current id/rev | 2 Class games (numbers 1,2, purpose class, no settings), 5 student occupants equal to the draft; 5 notices; `session` + `user` events | – |
| Idempotent | confirm twice | second 200, same counts | – |
| Stale | other revision / id / no draft | nothing committed | 409 `allocation_changed` `changed` |
| Removed | 1 of 5 removed after preview | draft rev 2 without them, no Game | 409 `allocation_changed` `students_removed` |
| Locked | Start date passed | nothing | 409 `session_locked` |
| Redraw after confirm | confirmed | unchanged | 409 `allocation_confirmed` |
| Assistant / archived | – | nothing | 403 / 409 `class_archived` |
| Class game start | no snapshot | – | 409 `game_not_ready` |
| Class create with settings | – | – | 422 `settings_not_allowed` |
| Student twice | same session | – | 409 `student_already_seated` |
| Budget scope | Class game with config | `class_session` scope | – |
| Lærerhjem | unconfirmed / confirmed | named with `allocation` / not | – |

</intent-contract>

## Code Map

- `backend/app/modules/games/policy.py` -- `GamePolicy` + `class` row. Tests `tests/games/test_policy.py` (asserts only simulation so far: update).
- `backend/app/modules/games/models.py:56,94` -- `games`, `seat_occupancy` columns/checks.
- `backend/app/modules/games/commands.py` -- `create` :193, `_occupant` :288, `assign_seat` :315, `start` :538, `_commit_change` :185, `_cost_limited` :381 (pass `class_session_id`). `test_commands_never_branch_on_purpose` forbids purpose compares/literals there.
- `backend/app/modules/games/repo.py` -- `stored_rules_versions` :341 must skip NULL; new `student_seated(session, class_session_id, user_id)` (distinct_on latest occupancy, as `seats_with_occupant` :82); `running_games_of_session`.
- `backend/app/modules/games/service.py` -- `get_game` :94, `scope_of` :126, `games_charged_to` :148; `schemas.py:123` `GameOverview`.
- `backend/migrations/versions/0038_class_games.py` (new, revises 0037); `tests/test_migrations.py` HEAD → 0038, fold constraint checks into the 0037 test.
- `backend/app/platform/events/registry.py` -- `sessions.confirm_allocation: {"session","user"}`.
- `backend/app/modules/sessions/` -- `models.py` (draft columns), `repo.py` (`confirm_draft`, `update_draft`, `staff_sessions` + confirmed flag), `schemas.py` (`AllocationConfirmIn`, `confirmed`, `SessionRef.lacks`), `service.py` (`confirm_allocation`, `allocation_mail_context`, `ALLOCATION_NOTICE`, redraw guard in `draw_allocation` :1280, `lecturer_overview` :922), `routes.py` (confirm route; map `AllocationChanged`, `AllocationConfirmed`), `README.md`.
- `backend/app/modules/messaging/delivery.py:94` -- `ALLOCATION_KIND` digest with context; templates `platform/email/templates/kinds/allocation_confirmed.{txt,html}.j2` (pattern `class_session_obligatory`).
- Tests: `tests/games/test_class_games.py` (new: create/assign/start/scope/policy), `tests/sessions/test_allocation_confirm.py` (new; helpers from `test_allocation.py`; fixtures `games_db`, `ai_db`, `mail_db`), `tests/sessions/test_dates.py` or overview test for `lacks`.
- Web: `frontend/src/modules/sessions/{api.ts,allocation-panel.tsx,class-session-page.tsx,lecturer-home-sessions.tsx,allocation.ts(+test)}`, `copy/nb.ts` `sessions.allocation` + `home.lacks`; regenerate `lib/api/openapi.json` + `schema.ts`.
- E2e: `frontend/e2e/class-session-allocation.spec.ts` (confirm, focus, primary swap, stale 409, removed cell look), `class-session-dates.spec.ts:107-140` (Lærerhjem lines).

## Tasks & Acceptance

**Execution:**
- games: `policy.py`, `models.py`, `schemas.py`, `repo.py`, `commands.py`, `service.py`, migration 0038 -- Class games, Student occupants, budget scope.
- sessions + messaging: models, repo, schemas, service, routes, README, registry, delivery, templates -- confirm, notice, Lærerhjem.
- Backend tests: every matrix row; committed Games/Seats equal the draft Student by Student; registry topics; migration head.
- Web + regenerated api types + e2e -- the confirm flow and Issue #106 fixes; axe at 320/360/1440.

**Acceptance Criteria:**
- Given an open preview, when «Bekreft fordeling» is pressed, then the request carries draft id and revision, Games and Seats equal the draft, the panel closes to «Fordelingen er bekreftet.» with focus on it, and «Lagre Klasseøkt» is primary again.
- Given a co-owner's redraw or a removed Student, when confirm is pressed, then nothing is committed and the preview shows the current draft with a reason.
- Given the Lærerhjem, then an unconfirmed, unlocked session is named as lacking a confirmed allocation, and stops being named once confirmed.
- Given a removed Student in the preview, then the cell is visibly different from a seated one; the selected column's frame is 1 px, 3 px with keyboard focus.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 31 findings — high 0, medium 3, low 24, false 4, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) Registered Students are read before the Class session lock. Roster writes never take that lock, so reading inside it closes no race; the window is milliseconds and Story 5.13 replaces removed Students (as Story 5.8's triage).
  - `[low]` `[patch]` (blind) `student_seated` read every occupancy row. The subquery now reads only the Seats of the session's Games.
  - `[low]` `[reject]` (blind) One Seat per Student per session is enforced in code only. The command checks it under the session lock; occupancy is append-only history, which a unique index cannot express.
  - `[medium]` `[patch]` (blind) A session in a Class with no registered Student was named as lacking an allocation forever. `allocation` now needs a registered Student; `test_dates` pins both cases.
  - `[low]` `[reject]` (blind) A repeat confirm after the lock answers 409. The story asks 409 `session_locked` for any confirm once locked.
  - `[low]` `[patch]` (blind) Confirm mapped `allocation_confirmed`, which it never answers. Mapping removed.
  - `[false]` `[reject]` (blind) `class_archived` reads «Prøv igjen». `SHARED_MESSAGES` maps it for every action.
  - `[low]` `[reject]` (blind) Students who leave or join after the confirmation. Late registrants are Story 5.13, removals of a seated Student Story 5.13/Epic 8, both outside this story.
  - `[low]` `[reject]` (blind) The digest mail does N+1 reads and may arrive after the Start date. Digests leave within a day; the reads match the other digest kinds.
  - `[low]` `[reject]` (blind) The 0038 downgrade fails with Class games present. Documented in the migration; occupancy is append-only.
  - `[low]` `[patch]` (blind, edge) `create` turned an empty parameter set id into the default. Now `is None`.
  - `[low]` `[reject]` (blind) A malformed `class_session_id` answers `class_session_required`. Internal callers only.
  - `[low]` `[patch]` (blind) `onConfirmShown` stayed true if the block unmounted. The effect reports false on cleanup.
  - `[false]` `[reject]` (blind) The removed-Student tests miss the body and a fresh confirm. They assert revision 2, renumbering, the deleted draft and a successful second confirm.
  - `[low]` `[reject]` (blind) The registry lists `user` and `game` for every confirm. It lists the topics a confirm may emit, as `sessions.save` does.
  - `[low]` `[reject]` (edge) Roster read outside the lock. As row 1.
  - `[medium]` `[patch]` (edge) With every Student removed the panel closed without a reason. The block now keeps and shows the reason.
  - `[medium]` `[patch]` (edge) No-Student session waits forever. As row 4.
  - `[low]` `[patch]` (edge) A Class game accepted `batch_id`. It is refused with `settings_not_allowed`; tested.
  - `[low]` `[patch]` (edge) Empty parameter set id. As row 11.
  - `[low]` `[reject]` (edge) Class games for an unknown session (no FK). Only `sessions.confirm_allocation` creates them, under the session lock (Design Notes).
  - `[false]` `[reject]` (edge) A `CommandError` inside confirm gives a 500. The draft holds each Student once and each Role once per game, so `seat_occupied`/`student_already_seated` cannot occur.
  - `[low]` `[reject]` (edge) The seed no longer reproduces an edited draft. Story 5.10's edits do the same; the revision marks it.
  - `[low]` `[reject]` (edge, claim) Removal detection is not atomic with the Roster. As row 1.
  - `[low]` `[patch]` (edge, claim) The reason is lost when the draft goes. As row 17.
  - `[low]` `[patch]` (verification-gap) Renumbering after an emptied first game was untested. `test_an_emptied_first_game_is_dropped_and_the_rest_numbered_from_one`.
  - `[low]` `[patch]` (verification-gap) The digest mail was never rendered. `test_the_digest_tells_the_student_without_naming_the_game_or_role` sweeps and checks the text and a removed Student.
  - `[low]` `[patch]` (verification-gap) `stored_rules_versions` NULL filter untested. A Class game added to `test_every_stored_rules_version_has_a_package`.
  - `[low]` `[patch]` (verification-gap) The Lærerhjem invalidation after confirm was untested. The e2e now returns through the breadcrumb.
  - `[false]` `[reject]` (intent) The removed-Student path drops emptied games and renumbers, beyond "leave that Seat free". Freed Seats are what the draft shows; a game with no Student left has no Seat to free and would only be an all-AI game. Recorded as a founder decision.
  - `[low]` `[reject]` (intent) Issue 106 checked by attributes on a 3-game stub only. Screenshots at 1280 and 390 px were reviewed (dashed `ink` cell, 1 px frame); the dense 100-game chart was not shot.

## Design Notes

- Confirm runs the game commands inside its own transaction (`within=`), so "commits nothing" and idempotency hold under the Class session row lock; the UNIQUE (`class_session_id`, `game_number`) is the backstop.
- No FKs from `games` to `class_sessions`/`users`: `games` is below `sessions`, and append-only occupancy rows cannot take `SET NULL` (AD-5, AD-14).
- Removed Students are found by comparing the draft with `classes.registered_students` at confirm; emptied games are dropped and the rest renumbered so «Spill N» stays contiguous.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_class_games.py tests/sessions/test_allocation_confirm.py tests/games/test_policy.py tests/games/test_registry.py -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** «Bekreft fordeling» commits the stored draft the Lecturer is looking at. `POST /api/class-sessions/{id}/allocation/confirm` takes `{draft_id, revision}` and, under the Class session row lock in one transaction, creates one Class game per group through `games.commands.create` (purpose `class`, session id and game number, no settings) and one `student` Seat per Student through `assign_seat` (both joined to the transaction with `within=`). It then marks the draft confirmed, enqueues a digest `allocation_confirmed` notice per Student and emits `session`. A stale id or revision answers 409 `allocation_changed` and commits nothing. Students who have left the Roster are taken out of the draft (revision raised, emptied games dropped and the rest renumbered) with the same 409. A repeat confirm changes nothing, a redraw after it answers 409 `allocation_confirmed`, and a locked session answers 409 `session_locked`. `games` gains `policy.snapshot/student_occupants/class_session_game` and the `class` row, a nullable snapshot, `class_session_id`/`game_number`, `seat_occupancy.user_id`, `start` → 409 `game_not_ready`, and a Class-session budget scope (migration 0038). On the screen, «Bekreft fordeling» is the primary button while the panel is open («Lagre Klasseøkt» secondary). It closes the panel to «Fordelingen er bekreftet.», which takes focus. The Lærerhjem names each session by what it lacks (`dates`, `allocation`). Issue 106: a removed Student's cell is `paper` with a dashed `ink` outline, and the selected frame is 1 px, 3 px only under keyboard focus.

**Files changed**
- Backend games: `policy.py`, `models.py`, `schemas.py`, `repo.py`, `commands.py`, `service.py`. Migration `0038_class_games.py` (new).
- Backend sessions: `models.py`, `repo.py`, `schemas.py`, `service.py`, `routes.py`, `README.md`. Also `messaging/delivery.py`, `events/registry.py`, and the templates `allocation_confirmed.{txt,html}.j2` (new).
- Backend tests: `games/test_class_games.py` and `sessions/test_allocation_confirm.py` (new). Updated: `test_policy`, `test_create`, `test_verify`, `test_allocation`, `test_dates`, `test_migrations` (head 0038, folded into the 0037 test).
- Frontend: `allocation-panel.tsx`, `allocation.ts(+test)`, `api.ts`, `class-session-page.tsx`, `lecturer-home-sessions.tsx`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts`. E2e: `class-session-allocation.spec.ts`, `class-session-dates.spec.ts`.

**Review findings.** 31 rows: 0 high, 3 medium, 24 low, 4 false. Patched 14 rows (2 medium root causes, the rest low). Rejected rows carry their reasons in the triage log, and nothing was deferred.

**Follow-up review recommended: false.** Two medium entries were patched (the no-Student Lærerhjem rule and the lost reason). Both are direct, test-pinned fixes, so no unverified risk can be named.

**Verification**
- Backend: 2482 passed, 4 skipped (78 s); ruff check and format clean. The new tests run under 1 s each. `test_every_stored_rules_version_has_a_package` takes about 1.0 s, as before (it plays a finished game).
- Frontend: typecheck, Vitest 428, `check:copy`, `lint:colours` and build pass. Playwright 245/245 on the rebuilt stack.
- Matrix audit: every I/O row has a passing test (`test_allocation_confirm.py`, `test_class_games.py`, `test_dates.py`).
- Screenshots at 1280 and 390 px (scratchpad, not committed): the open panel, the removed cell, the confirmed line and the Lærerhjem.
- Migration 0038 is new. It ran on the shared test databases and was not changed after it ran.
- Implementation and fixes were done in this context (caller's instruction). The four reviewers were sub-agents; their findings were read from their transcripts.

**Decisions taken in place of the founder**
- Removed Students: their Seats are freed, a game left with no Student is dropped and the rest renumbered 1..n, and the revision rises. With nobody left the draft is removed. Answer: 409 `allocation_changed` `{"draft": "students_removed"}`.
- The confirmation is stored on the draft (`confirmed_at`, `confirmed_by`). A confirmed allocation can still be opened read-only and is never drawn again (409 `allocation_confirmed`).
- No foreign keys from `games` to `class_sessions` or `users` (layering; append-only occupancy).
- `assign_seat` refuses a second Seat for a Student in the same Class session (`student_already_seated`).
- Class-game commands also emit `session:<id>` (policy `lecturer_overview`).
- The Lærerhjem names an allocation as missing only for unlocked sessions of a Class with a registered Student.
- Mail copy [ASSUMPTION]: subject «Du er med i et spill», body «Du er satt i et spill i Klassen {klasse}. Du får Rolle og spill på startdatoen.» It names no game or Role.
- UI copy [ASSUMPTION]: «Bekrefter …», the changed and students-removed lines, «Fordelingen ble ikke bekreftet. Prøv igjen.», the locked and redraw-confirmed lines, and «… mangler datoer og bekreftet fordeling».
- Button order follows mockup 03: «Kjør fordeling på nytt», «Bekreft fordeling», then the notice line, which wraps under the buttons in the narrow column.

**Residual risks**
- A Student removed in the milliseconds between the Roster read and the lock still gets a Seat; Story 5.13 frees removed Students' Seats.
- The removed-cell dash was checked on a 3-game chart, not at the 10 px columns of a 100-game chart.
- The allocation read is not refetched on `session:<id>`; the revision check guards the confirm.