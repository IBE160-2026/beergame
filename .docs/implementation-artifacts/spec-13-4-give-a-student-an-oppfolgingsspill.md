---
title: 'Story 13.4: Give a Student an Oppfølgingsspill'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '5c2d48bd3746ab491cf6211865d9909db2643ed3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-3-correct-a-students-completion-status-with-a-reason.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student who fell short, was ill or registered late has no way to complete the Class game step: nothing creates a make-up game, `games.policy` has no `makeup` row, and Completion reads only the Class game (FR-17, FR-20, UX-DR54).

**Approach:** A Lecturer-only command `POST /api/class-sessions/{id}/students/{user_id}/makeup` (`giveMakeup`, policy `makeup.give`) in `modules/reports` creates a `purpose=makeup` Game through `games.commands` on the Class session's frozen snapshot, seats the Student and three AI players, stores a `makeup_games` row, audits and notifies, in one transaction. The `makeup` policy row closes it at the Test deadline through the existing sweep action; Completion takes the make-up's Decision log beside the Class game's; Hjem shows it as a Spillkort «Oppfølgingsspill» on the reused play screen.

## Boundaries & Constraints

**Always:**
- Policy row `makeup`: `snapshot=at_creation`, no Takeover/Pause/playout, `lecturer_overview=False`, Guided Weeks from settings, `student_occupants`, `class_session_game`, no `game_number`, not `played_by_staff`, `pre_play_gate=True`, `records_class_game_step=False`, `projection=False`, `staff_insight=False` [ASSUMPTION], `closes_at_test_deadline=True` (so the sweep's `games.close_at_test_deadline` closes it with `reason=test_deadline`, idempotently), `believability="always"`. New column `own_round: Literal["none","replay","makeup"]` replaces `_own_round`'s derivation; `StudentGame` and `StudentGameOut` gain `makeup: bool`. No command compares a purpose.
- Table `makeup_games` (migration `0302`, Revises `0301`): `id` uuid7, `user_id` FK users CASCADE, `class_session_id` FK class_sessions CASCADE, `game_id` FK games CASCADE UNIQUE, `given_by` FK users SET NULL, `given_at` timestamptz; UNIQUE (`user_id`, `class_session_id`). One make-up per Student per Class session [ASSUMPTION]: any second press returns it.
- Command `reports.makeup.give`: reach through `sessions.student_target(…, "makeup.give")` (owners only; None → 403 one body). Refusals, nothing written: archived → 409 `class_archived`; no frozen snapshot (`sessions.lock` not run) → 409 `session_not_locked`; Student's effective Test deadline None → 409 `no_test_deadline`; passed (`auth.utcnow()`) → 409 `test_deadline_passed`. Under the session row's share lock: create (`games.commands.create("makeup", snapshot=row["snapshot"] unchanged, class_session_id, within=s)`), Student in their `student_game` Role else `secrets.choice` of the roles, other Seats `llm` when the snapshot's runtime has a model config else `rule_based`; insert the row (conflict → roll back, return existing); `audit.record(actor, "makeup.given", {class_session_id, user_id, game_id}, {role})`; `notify.enqueue(student, "makeup_given", "makeup_given:<row id>", ref=class_session_id)`; emit `user:<student>`, `session:<id>`. Not started: the Student starts it through Story 6.5's flow after the pre-play gate. Answers `StudentRecordOut`.
- Registry `reports.give_makeup` with the topics the command emits, asserted by a test.
- Notice kind `makeup_given`: digest, templates `makeup_given.{txt,html}.j2`, context `sessions.makeup_given_mail_context` (Class name, effective Test deadline in Oslo); None when the make-up is gone or finished, the deadline passed, the Class archived, or the User no longer a registered Student.
- Completion: `analysis.completion(…, makeup_log=None)`; `class_game` done = recorded and (Class share met or make-up share met); the figures shown are the game with the higher exact ratio (tie → Class game); `CompletionStatus.share_game` is `"class"`/`"makeup"` when a make-up log is passed, else None. The assembler reads the make-up via `scope.reporting_games(s, id, [Purpose.MAKEUP])` and the Student's `makeup_games` row. Per-Class-game reads stay `purpose=class` / `lecturer_overview`.
- Record: `StudentRecordOut.makeup: {game_id, given_at, open_until, state} | null`, `can_give_makeup` (owner, not archived, snapshot, deadline set and not passed, no make-up), `test_deadline` (effective). `CompletionOut.share_game`.
- Hjem: `EnrolledSessionOut.makeup: StudentGameOut | null` (via a provider `reports` registers in `sessions`); `debrief` None on it. The own-round checks (time proposals) refuse a make-up; the Starting task route allows it.
- Web: Klassespill row ends in secondary «Gi oppfølgingsspill» when `can_give_makeup`; form in place (shared `Editing` key `makeup`): consequence «<Navn> får et eget Klassespill mot tre KI-spillere, åpent til Testfristen fr. 18. des. <Navn> får beskjed på Hjem og på e-post.», primary «Gi oppfølgingsspill», «Avbryt»; focus to the primary on open, back to the opener on Avbryt; after: «Oppfølgingsspill gitt 12. des. Åpent til fr. 18. des.» takes focus (`role=status`), state line under it. Share line names the game when `share_game` is set. Hjem: the make-up block titled «Oppfølgingsspill · Du er Grossist», running → Spillkort titled «Oppfølgingsspill», no time proposal; one primary across game, make-up, Replay. Play screen: title variant, «Spillet er ferdig» as for any Game; closed at the deadline → «Oppfølgingsspill stengt». Copy in `nb.ts`, draft `[ASSUMPTION]`.

**Never:** no change to `games.service.student_game`, the Debrief, Replay or test game choice (13.5); no `class_game` step from a make-up; no new due action (the policy column drives the existing one); no Assistant lecturer action; no make-up on the overview wall, in class cost, Spillinnsikt lists or group results.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Give | locked, before deadline, seated Student | Game `makeup` not started, own Role, 3 AI Seats; row, audit, notice, `user`+`session` | — |
| Late registrant | no Seat | random Role; Klassespill «ikke gjort» with the button | — |
| Second press | make-up exists (any state) | same game, nothing new written | 200 |
| Before lock / no deadline / after deadline / archived | — | nothing written, not offered | 409 `session_not_locked` / `no_test_deadline` / `test_deadline_passed` / `class_archived` |
| Others | Assistant, other Lecturer, Admin, Student, unknown | nothing written | 403 `forbidden`, one body |
| Completion | Class 3/5 own, make-up 5/5 own, `class_game` recorded | done; figures from make-up, `share_game=makeup` | — |
| Deadline sweep | unfinished make-up, deadline passed | closed `test_deadline`, no playout; second run no-op | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/policy.py` -- `POLICIES`, `BoolColumn`, `purposes_with`; add row + `own_round`.
- `backend/app/modules/games/service.py:848` `_own_round`, `:854` `own_game` (held-role path), `:1381` `class_game_head`, `:488` `StudentGame`, `:509` `student_game` (unchanged), `:546` `seat_log`, `:1080` `due_test_deadline_closes`.
- `backend/app/modules/games/commands.py:334` `create(snapshot=…, within=)`, `:545` `assign_seat`, `:2853` `close`; `repo.py:33` `_listed`.
- `backend/app/modules/replay/service.py:152` `start` -- the pattern to copy (snapshot, AI kind, `_Taken` conflict).
- `backend/app/modules/sessions/service.py`: `:1463` `enrolled_sessions`, `:1786` provider pattern `register_replay_game`, `:2398` `_student_card`/`:2433` `_game_out`, `:2563` `_own_locked_game`, `:2962/2997/3066` own-round checks, `:2113` `student_target`, `:750` `effective_test_deadline`, `:1928` `replay_session_of` (share lock), `:3487` mail context pattern; `schemas.py` `StudentGameOut`, `EnrolledSessionOut`.
- `backend/app/analysis/completion.py` -- `_class_game_counts`, `completion`.
- `backend/app/modules/reports/{service,studentside,schemas,routes,corrections,scope}.py`, README.
- `backend/app/modules/messaging/delivery.py` `KINDS`; `platform/email/templates/kinds/_deadline.j2`; `platform/authz.py:168/206`; `platform/events/registry.py:151`.
- `backend/migrations/versions/0301_completion_corrections.py` (head); `tests/test_migrations.py` (`HEAD`, `HEAD_TABLES`, downgrade block).
- Tests to reuse: `tests/reports/test_corrections.py` (call/record/refusal shapes), `test_completion_status.py`, `tests/sessions/test_game_end.py` `short_game`, `play_weeks`, `test_lock.dated`, `test_allocation.students`, `classes/test_student_registration.set_clock`, `tests/games/test_policy.py`.
- Web: `frontend/src/modules/reports/{completion-block.tsx,record.ts,api.ts,student-page.tsx}`, `modules/games/{student-hjem.tsx,home.ts,game-end.tsx,play-page.tsx}`, `modules/replay/{replay-closed.tsx,replay.ts}`, `components/game-card.tsx`, `copy/nb.ts`; e2e `frontend/e2e/studentside.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0302_makeup_games.py`, `reports/models.py` -- table.
- `games/policy.py`, `games/service.py`, `sessions/{service,schemas}.py` -- row, `own_round`, `makeup` flag, Hjem `makeup`, provider, mail context, own-round checks.
- `analysis/completion.py` -- make-up log, `share_game`.
- `reports/{makeup,service,studentside,schemas,routes}.py`, README; `platform/{authz,events/registry}.py`; `messaging/delivery.py` + templates.
- Tests: `tests/reports/test_makeup.py` (matrix, audit, notice, topics, Completion, sweep close, exclusions); `tests/analysis/test_completion.py` cases; `tests/games/test_policy.py`; `test_migrations.py`; Hjem shape tests as needed.
- Web: `nb.ts`, reports `api.ts`/`record.ts`/`completion-block.tsx` (+ `record.test.ts`), games `student-hjem.tsx`/`home.ts` (+ test)/`play-page.tsx`/`game-end.tsx`, `replay-closed.tsx`; `npm run api:generate`.
- `frontend/e2e/studentside.spec.ts` -- Lecturer gives a make-up (focus rules, result line), Student's Hjem shows «Oppfølgingsspill»; axe.

**Acceptance Criteria:**
- Given a locked session before the Test deadline, when the Lecturer presses «Gi oppfølgingsspill», then the form opens with the consequence and focus on the primary, Avbryt returns focus, and confirming shows the focused line «Oppfølgingsspill gitt …. Åpent til ….».
- Given a given make-up, when the Student opens Hjem, then a block «Oppfølgingsspill» leads through the briefing to the reused play screen, and once running a Spillkort titled «Oppfølgingsspill» shows.
- Given a make-up, when the Lecturer overview, class games and group results are read, then the make-up is absent.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: four (blind, edge case, verification gap, intent alignment) on Sonnet, as the lane brief directs for creating games and Completion.
- verdicts: 38 findings — high 0, medium 0, low 34, false 3, maybe-false 1 (intent-alignment rows are descriptive divergences, graded low)
- findings:
  - `[low]` `[reject]` Blind: no guard on obligatory, a step already done or a running Class game. Decision: the story offers the action after the lock and before the Test deadline only; a make-up is also the late registrant's path to the later steps (13.5) in any session. Recorded as a founder decision.
  - `[low]` `[patch]` Blind: a given but unstarted make-up shows «Bestilte i 0 % … i Oppfølgingsspillet». The assembler now passes the make-up's log only once it has started (the story: «a finished or partly played make-up»).
  - `[low]` `[patch]` Blind: `_better` re-counts own Orders beside `_class_game_counts`. `_class_game_counts` now uses `_own_weeks`, one count.
  - `[low]` `[reject]` Blind: a finished make-up ends on «Spillet er ferdig» with «Gå til Debrief». The story says «as for any Game», and Story 13.5's AC presses «Gå til Debrief» on that screen; which game the Debrief uses is 13.5's.
  - `[low]` `[patch]` Blind: the reused GameBlock repeats the drawn-Seat line of Student choice under the make-up. Hidden for the make-up. Deadlines and the Takeover note are per session or impossible (no Takeover policy).
  - `[low]` `[reject]` Blind: frontend unit tests thin (precedence, form states). The e2e drives the form; closed-screen and copy tests were added below. More would add test surface for rare states.
  - `[low]` `[patch]` Blind: concurrent presses untested. Added two simultaneous presses: one row, one Game, one notice, one audit row, same `game_id`.
  - `[low]` `[reject]` Blind: LLM seat branch and gate untested. LLM branch is the Replay's tested pattern; the gate is now tested (Verification row below).
  - `[low]` `[patch]` Blind: mail kind, templates and worker loading untested. Added a test: kind equals `NOTICE`, digest mode, rendered subject and text, `reports.service` in `TASK_MODULES`.
  - `[low]` `[reject]` Blind: data lifetime when the row cascades. The same as `replays`; Games of a deleted Class session go with it. Epic 15's deletion owns erasure.
  - `[low]` `[reject]` Blind: no link to the make-up and no withdraw. Not in the story; `staff_insight` off is a recorded decision.
  - `[low]` `[reject]` Blind: a hidden button has no explanation. The Fullføring row's status already says what the Lecturer needs; a line per refusal adds copy for rare states.
  - `[low]` `[patch]` Blind: `own_round` had a default. Now required; every row names it. (`"party"` still tests an unknown purpose.)
  - `[low]` `[reject]` Blind: providers return None silently. The Replay's established pattern; the worker now loads `reports.service` and a test asserts it.
  - `[low]` `[reject]` Blind: e2e one viewport, start via api. The Studentside's other test runs axe and reflow at all three widths; the Student's start is Story 6.5's tested flow.
  - `[low]` `[reject]` Blind: small naming points (`data-makeup` twice on different pages, the `MAKEUP` key, optional `makeup` in `Titled`, generated files outside the review diff). No harm; `schema.ts`/`openapi.json` were regenerated with `npm run api:generate` and the typecheck passes.
  - `[low]` `[patch]` Edge: «mai» has no full stop, so the consequence and given lines ran on. A `sentence()` helper in `nb.ts` ends each day with one; tested.
  - `[low]` `[reject]` Edge: finished make-up shows «Gå til Debrief». Same as the Blind row.
  - `[low]` `[reject]` Edge: a test student or Control test session can get one by direct POST. Counts nowhere and the UI never offers it; a guard adds a branch for a crafted call.
  - `[false]` `[reject]` Edge: `can_give_makeup` needs obligatory. False: it needs `completion is not None`, which holds in any session for a counted Student.
  - `[low]` `[reject]` Edge: a Student whose Seat another Student later took gets a drawn Role. `student_game` returns the Seat they moved to; the case is a move, rare, and a drawn Role is harmless.
  - `[maybe-false]` `[reject]` Edge: removing the Test deadline leaves the make-up open. Would need checking whether a locked session can drop its Test deadline (`test_dates.py` refuses `required` in some states); if true, low.
  - `[false]` `[reject]` Edge: focus effect races the cache update. False: `setQueryData` and `setGiven` commit in one render; the e2e asserts the focus.
  - `[low]` `[reject]` Edge: `_makeup_card` silent without a provider. Same as the Blind provider row.
  - `[low]` `[reject]` Edge: a make-up Seat no longer held drops its log. The `makeup` policy has no Takeover; only a staff action could do it.
  - `[false]` `[reject]` Edge (claim): a late registrant cannot complete the step in 13.4. True by design and not a defect: the step event comes from Story 13.5 (`records_class_game_step` on).
  - `[low]` `[patch]` Verification: concurrent `_Taken` path. Same patch as the Blind row.
  - `[low]` `[patch]` Verification: `makeup_given` delivery wiring. Same patch as the Blind row.
  - `[low]` `[patch]` Verification: time proposals in a make-up untested. Added propose and accept, both 403.
  - `[low]` `[patch]` Verification: `endTitle`/`ReplayClosed` make-up variants untested. Added to `replay.test.tsx`.
  - `[low]` `[patch]` Verification: `can_give_makeup` with an archived Class untested. Added the assertion.
  - `[low]` `[patch]` Verification (filed defer): late registrant through the gate. Added: `briefing_first` true, `start` refused `starting_task_required`, Starting task route answers the make-up id.
  - `[low]` `[reject]` Verification (other): no reporting-scope check in `give`. Same as the Edge row.
  - `[low]` `[reject]` Verification (other): finished make-up end screen. Same as the Blind row.
  - `[low]` `[reject]` Intent: UI expectations rest on one e2e and pure-function tests. The e2e asserts the form, focus, result line and Hjem card with axe; the rest is api-tested.
  - `[low]` `[reject]` Intent: no browser play to «Spillet er ferdig». The play screen is unchanged code; the api test plays the make-up to its result.
  - `[low]` `[reject]` Intent: `can_give_makeup` adds conditions (counted Student, not archived, none yet). Each mirrors a refusal of the command or the one-per-Student rule.
  - `[low]` `[reject]` Intent: the due action is the policy column, not a new action. Commands never branch on purpose (AD-13); the existing action closes any `closes_at_test_deadline` Game, and the test runs it.

## Design Notes

`own_round` keeps one derived notion per policy instead of `_own_round`'s shape test, which would have called a make-up a Replay (titles, end screen, Starting task refusal). The make-up is not started at creation so the Student passes the pre-play gate as in a Class game.

## Verification

**Commands:**
- `uv run pytest tests/reports tests/analysis/test_completion.py tests/games/test_policy.py tests/test_migrations.py tests/test_imports.py tests/test_authz_rules.py -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/reports src/modules/games` -- pass
- `npx playwright test e2e/studentside.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can give a Student an Oppfølgingsspill from the Studentside (FR-17, FR-20, UX-DR54). The Klassespill row of «Fullføring» ends in «Gi oppfølgingsspill» while the Class session is locked and before the Student's Test deadline. It opens in place with the consequence, primary «Gi oppfølgingsspill» and «Avbryt» (focus to the primary; Avbryt returns it; one form at a time with corrections and the other blocks). Once given, «Oppfølgingsspill gitt 12. des. Åpent til fr. 18. des.» takes focus with a state line under it.

`POST /api/class-sessions/{id}/students/{user_id}/makeup` (`giveMakeup`, policy `makeup.give`, owners only) runs in one transaction under the session row's share lock: `games.commands.create("makeup")` on the session's frozen snapshot unchanged; the Student in their Class game Role (drawn for a late registrant); AI players of the session's AI mode in the other three Seats; a `makeup_games` row (one per Student and session); audit `makeup.given`; the digest notice `makeup_given` (mail templates added); `user:`, `session:` and `game:` events. Refusals: 409 `session_not_locked`, `no_test_deadline`, `test_deadline_passed`, `class_archived`; 403 one body for everyone else.

The `makeup` row of `games.policy`: snapshot at creation, no Takeover, Pause or playout, not on the overview wall, pre-play gate on, no `class_game` step (13.5), closed at the Test deadline by the existing sweep action `games.close_at_test_deadline`. A new column `own_round` (`none`/`replay`/`makeup`) replaces the shape test that would have called a make-up a Replay. Completion takes the started make-up's Decision log beside the Class game's: the step is done when either meets the share; `share_game` names the game the figures come from, and the share line says so. Hjem shows the make-up as its own block («Oppfølgingsspill · Du er Grossist») with a Spillkort titled «Oppfølgingsspill» while it runs, through the reused play screen; a make-up closed at the deadline reads «Oppfølgingsspill stengt».

**Files.**
- Backend: `migrations/versions/0302_makeup_games.py`; `reports/{makeup,models,repo}.py` (new), `reports/{routes,schemas,service,studentside}.py`, README; `games/{policy,service}.py`; `sessions/{service,schemas}.py` (Hjem `makeup`, provider, mail context, `makeup_session_row`, own-round checks); `analysis/completion.py`; `messaging/delivery.py` and `templates/kinds/makeup_given.*.j2`; `platform/{authz,events/registry,jobs/__init__}.py`; `migrations/env.py`.
- Backend tests: `tests/reports/test_makeup.py` (new), `tests/analysis/test_completion.py`, `tests/games/{test_policy,test_create}.py`, `tests/test_{migrations,imports}.py`, `tests/sessions/test_dates.py`.
- Frontend: `copy/nb.ts`; `modules/reports/{api,record,completion-block}.ts(x)` and `record.test.ts`; `modules/games/{home,student-hjem,game-end,play-page}.ts(x)` and tests; `modules/replay/replay-closed.tsx`, `replay.test.tsx` (renamed from `.ts`); regenerated `lib/api/{openapi.json,schema.ts}`; `e2e/studentside.spec.ts`.

**Review.** Four layers (data model, access and deadlines). 38 findings: 0 high, 0 medium, 34 low, 3 false, 1 maybe-false. Patched 14 low rows (11 fixes): the 0 % line for an unstarted make-up, one own-Order count, the drawn-Seat line under the make-up, `own_round` required, the «mai» full stop, and tests for concurrent presses, the mail kind and worker loading, time proposals, the closed screen, the archived offer and the late registrant's gate. Nothing deferred. Every rejection and its reason is in the Review Triage Log. Follow-up review: **false** (no high or medium patched).

**Verification.**
- Full backend suite (8 processes): 3741 passed, 4 skipped. ruff check and format pass.
- New tests over 1 s: `test_a_lecturer_gives_a_makeup_that_the_student_plays_and_completion_reads` about 5.6 s (plays a short Class game and the make-up), `test_a_late_registrant_gets_a_drawn_role_and_refusals_write_nothing` about 3 s.
- Frontend: typecheck, Vitest 1200 passed, lint:colours, check:copy; the build passes inside the image.
- Playwright (4 workers) on the lane stack: `studentside`, `homes`, `student-home`, `game-card`, `order-field`, `replay-close`, `replay-play`, `playout`: 65 passed. The new test checks the form's focus rules, one form at a time, the focused given line, the Student's Hjem block arriving live, and the Spillkort after the start; axe with the form open, after giving, and on Hjem.

**Decisions taken for the founder [ASSUMPTION].**
- One Oppfølgingsspill per Student and Class session; any second press answers it, also after it finished or was closed.
- Offered in any Class session, obligatory or not, and whether or not the step is already done; not for a Student the reports leave out.
- Not started at creation: the Student starts it from Hjem after the pre-play gate, as a Class game.
- No Spillinnsikt for staff (`staff_insight` off) and no link from the Studentside to it.
- The share figures shown are the game with the higher share (the Class game on a tie); an unstarted make-up is not counted.
- The consequence names the Student's full name as stored.
- 409 `no_test_deadline` when the session has none.
- The make-up reuses «Spillet er ferdig» with «Gå til Debrief» unchanged; which game the Debrief uses is Story 13.5's.
- All new copy (mail, state lines, refusals, closed screen) is draft.

**Personal data.** New table `makeup_games`: `user_id` (the Student) and `given_by` (the Lecturer). No free text. The registry of Story 15.2 must list it.

**Residual risks.**
- A late registrant's make-up cannot complete the Class game step until Story 13.5 records the step event.
- Removing a Test deadline after giving a make-up (if a locked session allows it) would leave it open.
- A test student can get one by a direct api call; it counts nowhere.

