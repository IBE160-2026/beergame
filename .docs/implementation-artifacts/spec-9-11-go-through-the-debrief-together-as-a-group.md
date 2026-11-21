---
title: 'Story 9.11: Go through the Debrief together as a group'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '463a8ace67f655586906e1419faf15e9eec93755'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A shared step waits for every joined Student, and only the opener can move on, so a group whose opener has gone (closed the page, removed from the Class, account deleted) stays on its step.
    evidence: |-
      `commands._advance` waits for every member of `debrief_members`; `commands.move_on` accepts only `opener_id`, which is `ON DELETE SET NULL`. No `leave`, dropout or fallback exists on this branch. Story 9.12 adds `leave`, the 2-minute dropout through `touch` and the 48-hour Personal fallback, which settle it; until then the group's Students are stuck on a shared step (the gates themselves still hold).
    location: >-
      backend/app/modules/debrief/commands.py (move_on, _advance)
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Every Student goes through the Debrief alone: the Debrief session's step pointer never moves, nobody can join another's Debrief, and `debrief:<id>` events never reach a browser (FR-43).

**Approach:** In a Group-debrief Class session with at least two active Students in the finished Class game, the first open makes the Debrief session shared (opener joined, others told). Joined Students share one step pointer over the shared steps 1 to 3; it moves when every joined Student has finished the step, or when the opener moves on after a minimum wait. From the reflection questions on (pointer 4) each Student works alone. The event stream forwards `debrief:<id>` so pages follow without reload.

## Boundaries & Constraints

**Always:**
- Active Student = a Student whose game (`games.service.student_game`) is this Game and whose Seat's Decision log has ≥1 row with `decided_by = student` ([ASSUMPTION] open-assumptions). New read `games.service.game_students(session, game_id)` → each Student of the Game with Role and own-Order count.
- `commands.open(game_id, class_session_id, opener_id, shared, tell)`: on creation with `shared` the row stores `shared`, `opener_id`, `step_opened_at`, the opener as joined, and one `group_debrief_opened` notice per other Student of the Game (`tell`, dedupe `group_debrief_opened:<debrief>:<user>`, ref Class session) → `user:<id>`. Mode is fixed at creation; `shared` only when the session's `debrief_mode` is `group` and ≥2 active Students.
- Shared steps 1–3; pointer 4 = individual (reflection, step 4, finish, quiz). A Student finished step 1 when their Explanation is stored; steps 2/3 when `complete_step` stored their mark. `save_explanation`, `complete_step` advance the pointer while every joined Student has finished the pointer's step (to at most 4), setting `step_opened_at` to db now.
- `commands.complete_step(game_id, class_session_id, user_id, step, reflection=None)`: `reflection` given → the Story 9.6 answer path unchanged; else marks shared step `step` (must equal the pointer, joined only). `join(game_id, user_id)` and `move_on(game_id, user_id, wait)` each lock the row and emit `debrief:<id>` when they change something. `move_on`: opener only; 409 `too_early` with `fields.available_at` while db now < `step_opened_at + wait`; at pointer 4 nothing moves.
- Minimum wait: `Settings.debrief_move_on_wait_minutes` (PLACEHOLDER 5). Dev-only `POST /api/dev/debriefs/{id}/backdate` (not in OpenAPI, not mounted in production) moves `step_opened_at` back by the wait, through a commands function, for e2e.
- API gate in a shared Debrief, after the Explanation gate: steps 2/3 need pointer ≥ n, the reflection, step 4, summary, finish and quiz need pointer ≥ 4 → 403 `step_locked`. Personal Debriefs unchanged.
- `DebriefOut.group: GroupOut | null` (null = Personal): `step`, `joined`, `opener`, `step_opened_at`, `move_on_at`, and, for joined callers only, `members: [{name, you, sent, done}]` (Roster names read now, Students only, never Explanation text).
- Routes: `POST /api/debriefs/{id}/join` (`joinDebrief`), `POST /api/debriefs/{id}/steps/{step}/done` (`completeDebriefStep`), `POST /api/debriefs/{id}/move-on` (`moveDebriefOn`); policy `debriefs.own`; a non-Student of the Game → 403 `forbidden`; join/done/move-on on a Personal Debrief → 409 `not_group`; done/move-on by a non-joined → 403 `forbidden`; non-opener move-on → 403 `forbidden`; done of a step that is not the pointer → 409 `step_not_open`.
- Event stream: `Scope.debriefs` = Debrief sessions of Games in `authz.own_seat`; a `debrief:` id outside the scope resolves it again once per id (any User). `topics.ts` keeps `debrief` → `debriefsKey`.
- Hjem: Stegene's current Debrief step carries `group_open: true` while a shared Debrief of the Student's game exists that they have not joined (provider registered by `debrief`, like `register_quiz_changed`); note «pågår, Gruppedebriefen er i gang» (draft). Mail kind `group_debrief_opened` (immediate) whose context re-checks that rule.
- UI copy in `nb.ts`, draft `[ASSUMPTION]`. Migration `0110`.

**Never:** no presence, `touch`, `leave`, 48 h fallback or shared screen (9.12, 9.13); no other Student's Explanation, answers or moments; no names in events, notices or facts; no change to `players`; no growth of `test_explanation.py` or the shared Debrief api test beyond one-line fixes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Group open | group mode, 2 active, A opens | shared row, A opener+joined, B notice + `user` event, Hjem B `group_open` | — |
| One active / personal mode | 1 active, or `personal` | `group: null`, no gate on pointer | — |
| Join | B joins | B joined, `debrief:` event; B's `group_open` false | non-Student 403 `forbidden`; personal 409 `not_group` |
| Locked reveal | A sent, B not | A: members A sent, B not; A GET step 2 → 403 `step_locked` | B: `explanation_required` |
| All sent | B sends | pointer 2, `step_opened_at` now | — |
| Move on early | opener at pointer 2, < wait | unchanged | 409 `too_early`, `available_at` |
| Move on | after wait | pointer 3 | non-opener 403 |
| Late Explanation | pointer 3, C joined without Explanation | C step 2 → `explanation_required`; after save C reads step 3 | — |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/commands.py` -- `open:93`, `save_explanation:149`, `complete_step:205` (reflection; becomes the `reflection=` path), `_locked`, `DebriefRow`/`row_of`, `release` (notify pattern).
- `backend/app/modules/debrief/service.py` -- `open_mine:219`, `_own:230`, `_out:208`, `step:334`, `own_reflection:598`, `answer_mine:621`, `own_summary`, `finish_mine`, `own_quiz`, `submit_quiz_mine`: add the pointer gate and the group read.
- `backend/app/modules/debrief/{models,rules,schemas,routes}.py`, `README.md` -- tables, `available` (add `group_mode`), `group_open` provider, `GroupOut`, routes/error map.
- `backend/app/modules/sessions/service.py` -- `DebriefSession:1300`/`debrief_session_of:1309` (add `group`), `stegene:1204`, `enrolled_sessions:1119` (`changed` pattern), `register_quiz_changed:1276`, `student_name:1398` (add `student_names`), `debrief_released_mail_context:2248`; `schemas.py` `StepOut` (add `group_open`).
- `backend/app/modules/games/{service,repo}.py` -- `student_game:239`, `seats_with_occupant:101`; add `game_students`.
- `backend/app/platform/events/stream.py:47-162` (`Scope`, `allows`, resolve), `platform/authz.py:206` (`own_seat`; add `debriefs_of`), `events/registry.py:98-124`, `platform/config.py:51`.
- `backend/app/modules/messaging/delivery.py:154-200`, `platform/email/templates/kinds/quiz_changed.*` -- new kind pattern.
- `backend/app/modules/sessions/dev.py`, `main.py:110-112` -- dev route pattern.
- Tests: `tests/debrief/test_quiz.py:59` setup pattern (`confirmed`, `sweep.run(LOCKED)`, `play_week`, `finish`), `tests/games/helpers.py:41`, `tests/debrief/test_debrief.py:104` (open topics), `tests/platform/` stream tests.
- Frontend: `modules/debrief/{debrief-page.tsx:96 Steps, api.ts, explanation-step.tsx, reveal-step.tsx, chain-step.tsx}`, `modules/games/home.ts:36`, `copy/nb.ts` (`debriefEntry`, `homes.student`), `lib/api/topics.ts`; e2e `support/live-game.ts` (`liveClassGame`, `orderByApi`), `debrief-explanation.spec.ts` (stub pattern).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0110_group_debrief.py`, `debrief/models.py` -- `debrief_sessions.shared/opener_id/step_opened_at`, `debrief_members(debrief_id, user_id, joined_at)`, `debrief_step_marks(debrief_id, user_id, step 2..3, done_at)`.
- `backend/app/modules/games/{service,repo}.py` -- `game_students`.
- `backend/app/modules/debrief/{commands,service,rules,schemas,routes,dev}.py`, `README.md` -- open/join/complete_step/move_on/advance, gate, group read, provider, routes, dev backdate.
- `backend/app/modules/sessions/{service,schemas}.py`, `messaging/delivery.py`, templates `group_debrief_opened.{txt,html}.j2`, `platform/{authz,config}.py`, `events/{stream,registry}.py`, `main.py` -- wiring.
- `backend/tests/debrief/test_group.py` (new) -- matrix rows, registry topics for `open` (shared), `join`, `save_explanation`, `complete_step`, `move_on`; stream scope test; mail context.
- Frontend: `modules/debrief/group.tsx` (new: join panel, locked line, step bar, move-on), `debrief-page.tsx`, `api.ts`, `games/home.ts`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts`, Vitest for the pure helpers (names line, visible steps).
- `frontend/e2e/debrief-group.spec.ts` (new) -- two Students (360 and 1440 px, axe): open, Hjem join note, join, locked line, advance on second send, too early, backdate, opener's move-on; non-opener has no control and gets 403.

**Acceptance Criteria:**
- Given a joined Student who has sent while another writes, when the page shows step 1, then it reads «Avsløringen er låst til begge har sendt. Du har sendt, <navn> skriver.» and a writing time guide shows before sending.
- Given both joined Students on step 1, when the second sends, then both pages show step 2 without reload and a polite status announces it.
- Given the opener at a shared step before the wait, when they press «Gå videre for alle», then the page says when it becomes possible; after the wait the pointer moves for all.
- Given the pointer at 4, then each Student's reflection, step 4 and quiz work as in a Personal debrief.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-11.md` and `review-edge-9-11.md` in the scratchpad. The diff left out the generated `openapi.json`/`schema.ts` and `.docs` on purpose.
- verdicts: 28 findings — high 0, medium 3, low 19, false 6, maybe-false 0
- findings:
  - `[medium]` `[defer]` (blind 1) A group whose opener is gone, or with a joined Student who never finishes, cannot move on. Real: only the opener moves on and `opener_id` is SET NULL on delete. Leave, dropout and the 48 h fallback are Story 9.12; deferred with that note.
  - `[low]` `[reject]` (blind 2) The api lets a Student who has not joined read up to the pointer and work alone from 4. Same game, every gate (Explanation, pointer, Debrief, quiz) holds; only the web app's join panel is skipped, through the api alone. Adding a membership check to every read is more than a direct fix, and 9.12 changes who must be joined.
  - `[low]` `[patch]` (blind 3) The announcer said «Alle har sendt» when the opener moved 1→2. Now only when every joined Student has sent; else «Gruppen er nå på steg 2».
  - `[false]` `[reject]` (blind 4) Orders counted per Seat Role make two Students active. A Student whose Seat another Student held after them has no game there (`student_game` drops `later_student` rows), so only the current holder counts; the rule is the spec's per-Seat rule.
  - `[false]` `[reject]` (blind 5) Inactive Students are told and may join or open. They are Students of the game with their own Debrief; the spec tells every other Student of the game; a joined Student who never finishes is the opener's move-on case.
  - `[low]` `[patch]` (blind 6) `open_mine` read every Student of the game on each refetch. Now only when no Debrief session exists yet.
  - `[low]` `[reject]` (blind 7) Every stream resolves its scope once per new `debrief:` id. Bounded to once per id per stream life (10–13 min) and the spec's rule; a narrower trigger is a design change. Kept as a residual risk for scale.
  - `[low]` `[reject]` (blind 8) The dev back-dating route is public. Same mounting and exposure as the existing dev lock and mailbox (not mounted with `APP_ENV=production`; listed in `test_authz_rules`).
  - `[low]` `[reject]` (blind 9) `complete_step` returns a union. The story names `complete_step` for both; two asserts narrow it.
  - `[low]` `[patch]` (blind 10) The Personal open's topics assertion was weakened to `<=`. Now `== {"debrief"}`, a strict subset of the registry entry.
  - `[low]` `[reject]` (blind 11) Coverage suggestions (concurrency, removed member, deleted opener). Not defects; the row lock serialises the commands.
  - `[false]` `[reject]` (blind 12) Personal debriefs changed by the hard-coded step 1. No command moves a Personal pointer, so it is always 1; step 1 always renders as before.
  - `[low]` `[patch]` (blind 13) While the Explanation loaded, a Student who had sent saw the time guide. The group line now waits for the Explanation read.
  - `[false]` `[reject]` (blind 14) Generated client missing. Regenerated and in the tree; left out of the review diff only; typecheck passes.
  - `[low]` `[reject]` (blind 15) `move_on` is not audited. No requirement asks for it; a log line records it.
  - `[low]` `[reject]` (blind 16) Mail has no link; kind name repeated as a string. Same as every other notice kind.
  - `[low]` `[reject]` (blind 17) Times show no date. The wait is minutes; the date only matters around midnight.
  - `[low]` `[reject]` (blind 18) No check ties `shared` to `opener_id`/`step_opened_at`. `commands.open` is the only writer and sets them together.
  - `[false]` `[reject]` (edge 1) The opener alone moves to step 2 before others join. The AC lets one joined Student go through the whole Group debrief alone; later joiners are late joiners.
  - `[medium]` `[defer]` (edge 2) A removed member blocks the pointer. Same root as blind 1.
  - `[medium]` `[defer]` (edge 3) No mover once the opener is deleted. Same root as blind 1.
  - `[low]` `[reject]` (edge 4) Same as blind 2.
  - `[low]` `[patch]` (edge 5) Same as blind 6.
  - `[low]` `[reject]` (edge 6) Same as blind 7.
  - `[low]` `[patch]` (edge 7) Same as blind 3.
  - `[low]` `[patch]` (edge 8) Same as blind 13.
  - `[low]` `[patch]` (edge 9) `complete_step` answered 200 for a step the pointer had passed; the spec says 409 `step_not_open` for any step but the pointer's. Now refused; tests updated.
  - `[false]` `[reject]` (edge 10) Same as blind 2, worded as a claim; the pointer gate is in the api.

## Design Notes

Decisions for the founder: shared steps are 1–3 and the pointer stops at 4 (the AC makes the reflection, step 4 and the quiz individual); a non-joined Student of a shared Debrief sees only the join panel (9.12 adds the alone path); the pointer gate is enforced in the api, not only the UI; the move-on wait is a setting (5 min placeholder) and e2e shortens it through a dev-only route; the opened notice is an immediate mail (the group is meeting now) dropped at send time once the Student joined; the locked line counts in words («begge», «alle tre», «alle fire») and names the viewer «Du».

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief/test_group.py tests/platform` -- pass
- full backend `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-group`, `debrief-*`, `homes`, `live-updates`, play-screen specs `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Group debrief. In a Class session with Debrief mode Group debrief, the first open of a finished Class game that at least two active Students played (a Student of the game whose Seat has an Order with `decided_by = student`, `games.service.game_students`) makes its Debrief session shared: the opener is joined and may move on, and each other Student of the game gets an immediate `group_debrief_opened` notice (`user:<id>`), so Hjem's Debrief step reads «pågår, Gruppedebriefen er i gang» and leads to the page, where «Bli med i Gruppedebriefen» joins (`debrief.commands.join`). Joined Students share the step pointer over steps 1 to 3: step 1 is finished by the Explanation, steps 2 and 3 by «Ferdig med steget» (`complete_step` without a reflection); once every joined Student has finished, the pointer moves (`_advance` inside `save_explanation` and `complete_step`). The opener's «Gå videre for alle» (`move_on`) moves it after the minimum wait (`DEBRIEF_MOVE_ON_WAIT_MINUTES`, placeholder 5), otherwise 409 `too_early` with `available_at`; anyone else gets 403. At pointer 4 each Student works alone. In the api a shared Debrief refuses every read after the pointer with 403 `step_locked`, after the Explanation gate, so a Student without an Explanation still gets `explanation_required` and enters the current step once they have saved. `DebriefOut.group` carries the pointer, the move-on time and, for joined callers only, the members' Roster names with sent/done (never text). The event stream now forwards `debrief:<id>` (scope `authz.debriefs_of`, resolved again once per unknown id). The page shows the time guide, the locked line («Avsløringen er låst til begge har sendt. Du har sendt, Ida skriver.»), the waiting line, a polite announcement when the step moves, and moves focus to step 1 after joining. Personal debriefs and games with one active Student are unchanged.

**Files.**
- `backend/migrations/versions/0110_group_debrief.py` (new), `debrief/models.py`: `shared`, `opener_id`, `step_opened_at`; `debrief_members`; `debrief_step_marks`.
- `backend/app/modules/debrief/{commands,service,rules,schemas,routes}.py`, `dev.py` (new): open/join/complete_step/move_on, the pointer gate, `GroupOut`, three routes, the `group_open` rule, the local dev back-dating route.
- `backend/app/modules/games/{service,repo}.py`: `game_students`.
- `backend/app/modules/sessions/{service,schemas,repo}.py`: `DebriefSession.group`, `register_group_open`, `StepOut.group_open`, `student_names`, mail context.
- `backend/app/platform/{authz,config}.py`, `events/{stream,registry}.py`, `messaging/delivery.py`, templates `group_debrief_opened.{txt,html}.j2`, `main.py`: wiring.
- Tests: `tests/debrief/test_group.py` (new); one-line updates in `test_debrief.py`, `test_quiz_exclusions.py`, `sessions/test_student_home.py`, `test_authz_rules.py`, `test_migrations.py` (head 0110).
- Frontend: `modules/debrief/group.tsx` (new), `debrief-page.tsx`, `api.ts`, `explanation-step.tsx`, `games/home.ts`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`; Vitest in `debrief.test.ts`, `home.test.ts`; e2e `frontend/e2e/debrief-group.spec.ts` (new).

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), two review layers. (1) Shared steps are 1 to 3; the pointer stops at 4, where the reflection questions, step 4 and the quiz are individual. (2) A Student of a shared Debrief who has not joined sees only the join panel (9.12 adds the alone path). (3) The pointer gate is in the api (403 `step_locked`). (4) «Ferdig med steget» goes through `complete_step` (the story names it), so that command now also takes the reflection answer as an argument object. (5) One joined Student alone moves on by finishing (the AC lets one Student go through alone). (6) Move-on wait 5 minutes, a placeholder setting; e2e shortens it through a local-only dev route. (7) The opened notice is an immediate mail, dropped at send time once the Student has joined; every other Student of the game is told, active or not. (8) The locked line counts in words and names the viewer «Du». (9) Mode is fixed at the first open. All copy is draft `[ASSUMPTION]`.

**Review.** 28 findings (high 0, medium 3, low 19, false 6). Patched 5 root causes, all low (the announcer's «Alle har sendt» only when all have; the active Students read only at creation; the Personal open's topic assertion strict again; no group line while the Explanation loads; `complete_step` refuses any step but the pointer's). Deferred 1 root cause (medium: a group whose opener is gone cannot move on; settled by Story 9.12). The rest rejected with reasons in the triage log. followup_review_recommended: false (no high or medium patched; patched counts: low 5).

**Verification.**
- Backend after the patches: full suite `--maxprocesses=8` 2939 passed, 4 skipped (100 s); `ruff check`, `ruff format --check` clean. Migration 0110 applied to the lane's `olspillet`; the migration walk covers it up and down.
- Frontend: typecheck, Vitest (55 files, 773 tests), `lint:colours`, `check:copy`, `next build` (in the lane image build) pass.
- Playwright on the rebuilt lane stack (8081), `--workers=4`: `debrief-group` (two Students at 360 and 1440 px with axe: open, Hjem's join note, join with focus on step 1, the locked line, the step-2 move over the event stream, too early, back-dated, the opener's move-on to step 3, no control and 403 for the other), all `debrief-*`, `homes`, `student-home`, `game-end`, `order-confirm`, `week-advance`, `game-card`, `live-updates`, play specs: 118 of 118.
- One full-suite run hung with idle workers while the docker image build ran beside it; it was stopped and rerun alone, which passed. No test failed and then passed.
- Tests over 1 s: `test_group.py::test_the_group_shares_a_step_pointer` about 4.1 s call plus about 2.6 s setup; `test_a_personal_debrief_shares_nothing` about 1.5 s; `test_one_active_student_opens_a_personal_debrief` about 1.2 s (each a Class session with a lock and a two-Uke game through the api).

**Residual risks.** A group whose opener is gone stays on a shared step until Story 9.12 (deferred). Every event stream resolves its scope once per new `debrief:` id it sees, which costs a few reads per stream per Debrief at scale. The "active Student" definition is still an unconfirmed assumption. Draft copy awaits review (Issue #31 pattern).
