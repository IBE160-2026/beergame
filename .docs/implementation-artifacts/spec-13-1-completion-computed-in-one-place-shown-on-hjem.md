---
title: 'Story 13.1: Completion is computed in one place and shown on the Student''s Hjem'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '995b5fb1acb9c3be763c9293100b8f5f18ecbd20'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The reporting scope does not yet exclude Control test Class sessions or test students; its two hooks default to none until Epic 12 (Stories 12.7, 12.8) is merged.
    evidence: |-
      reports/scope.py register_control_test_sessions and register_test_students default to empty reads, because sessions.service kind and identity.service is_test_student do not exist on this branch. Tests prove the exclusion through the hooks only. Story 12.5's staff list of AI assessments is not on this branch either and does not yet read through scope.reporting_students.
    location: >-
      backend/app/modules/reports/scope.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Nothing computes whether a Student has met the requirement of an Obligatory class session (FR-17). Stegene shows step events only, so a Student whose Class game ended with too few own Orders, whose Explanation is too short, or whose auto-submitted test is empty, sees «ferdig» and never learns the requirement is not met; the Oversikt funnel counts test data.

**Approach:** Add a pure `analysis.completion` and one assembler `reports.service.completion_status(user_id, class_session_id)` in a new `modules/reports`, with `reports.scope.reporting_games()` / `reporting_students()`. Hjem (in `sessions`) and the Oversikt funnel reach the assembler and `reports.service.funnel` through providers that `reports` registers in `sessions` (the existing register-provider pattern; `sessions` never imports `reports`).

## Boundaries & Constraints

**Always:**
- `analysis.completion(steps, decision_log_summary, corrections, settings) -> CompletionStatus` is pure: no I/O, no clock, no AI assessment or Indicative letter input; `assessment_ready` in the step events is ignored.
- Steps: `class_game`, `debrief`, `quiz_passed`, `replay`, `test_submitted`. Each carries `recorded`, `recorded_at`, `done`, `corrected`.
- Class game share = own Orders / Weeks after the Guided Weeks (`settings.weeks - guided_weeks` of the Game snapshot). An own Order is a `seat_weeks` row of the Student's Seat (Role of `games.service.student_game`) with week > guided, `decided_by = student` and `reason` not a Takeover reason (`takeover_inactivity`, `takeover_staff`, `takeover_peer`) and not `playout`. Unplayed Weeks count as not ordered. Compare exactly (`ordered*100 >= required*total`), never by rounded percent. Result also carries the playout share (rows with `reason = playout` after guided / total).
- Required share = adjusted share from `sessions.service.get_adjustment` when set, else `sessions.service.required_share(row)`.
- Debrief done only when recorded and the Explanation length >= `COMPLETION_EXPLANATION_MIN_LENGTH` (placeholder 50 characters). Test done only when recorded and, if the attempt is `auto_submitted`, every part listed in `COMPLETION_TEST_REQUIRED_PARTS` (placeholder: all four parts `choice, interactive, long, adapted`) that the attempt holds has content (`tests.service.parts_with_content`). A Student's own submit counts as is. Both settings in `app/platform/config.py`, marked `[ASSUMPTION]`.
- Latest correction per step (by `at`) sets `done` and `corrected`; the corrections table comes in Story 13.3, so the assembler passes none now.
- `requirement_met` is `None` when the session is not obligatory, else all five steps `done`.
- `reporting_students` = registered Students of the Class minus test students; `reporting_games` = Games of the Class session with purpose in {class, replay, makeup}, each with `purpose` and `end_reason`; nothing for a Control test Class session. Control test sessions and test students come from Stories 12.7/12.8 (other lane): scope reads them through two provider hooks `reports.scope.register_control_test_sessions` / `register_test_students`, defaulting to "none"; tests register fakes.
- Student-facing Hjem gets only per-step `counts` (bool | None) and `requirement_met`; never share percents, Week counts or a reason.
- `progress` still imports no feature module; `progress.funnel` unchanged.

**Never:** no new table or migration; no change to step events or gates (`has_step`); no time spent or constant Orders as inputs; no share line on Hjem; no Studentside, corrections, export or report work (13.2+); no edit of Epic 12 code.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output |
|---|---|---|
| Share at limit | 8 of 10 Weeks after guided own, required 80 | class_game done |
| Takeover / playout | 7 own + 1 `takeover_inactivity` + 2 `playout` of 10 | not done; share 70, playout 20 |
| Adjusted | 6 of 10, required 80, adjusted 60 | done |
| No game snapshot | decision summary None, class_game recorded | not done |
| Auto-submitted empty part | `auto_submitted`, parts {choice: True, long: False} | test not done |
| Own submit with empty part | `submitted`, same parts | test done |
| Short Explanation | length 49, min 50 | debrief not done (recorded true) |
| Correction | class_game not done, latest correction done=True | done, corrected |
| Not obligatory | all done | requirement_met None |
| AI ready | `assessment_ready` recorded | identical result |

</intent-contract>

## Code Map

- `backend/app/analysis/` -- pure analysis modules (e.g. `class_cost.py`); add `completion.py`.
- `backend/app/modules/progress/service.py` -- `steps_of`, `funnel(session, id, student_ids)`, `FUNNEL_STEPS`; add `step_events(session, user_id, class_session_id) -> dict[Step, datetime]` (read only, no feature import).
- `backend/app/modules/sessions/service.py:610` `required_share`, `:638` `get_adjustment`, `:1439` `enrolled_sessions` (Hjem; builds `steps=stegene(...)`), `:1546` `stegene`, `:1604` `register_debrief_state` (provider pattern to copy); `:849` `class_id_of`.
- `backend/app/modules/sessions/overview.py:133-135` -- funnel call to replace with the registered `reports.service.funnel`.
- `backend/app/modules/sessions/schemas.py:772` `StepOut` (add `counts`), `EnrolledSessionOut` (add `requirement_met`).
- `backend/app/modules/sessions/repo.py` -- session row (has `obligatory`, `required_share_percent`, `class_id`).
- `backend/app/modules/games/service.py:503` `student_game`; add `decision_log_summary(session, game_id, role)` and `session_games(session, class_session_id)` (id, purpose, end_reason) in service + `repo.py` (`:1139` `student_orders_by_role` shows the seats join).
- `backend/app/modules/games/schemas.py` -- `Purpose`, `DecidedBy`, `OccupancyReason`, `EndReason`.
- `backend/app/modules/debrief/service.py:514` `_stored` -- add public `explanation_length(user_id, class_session_id) -> int | None`.
- `backend/app/modules/tests/service.py:225` `parts_with_content`; add `submission_kind(user_id, class_session_id) -> str | None` (attempt status).
- `backend/app/modules/classes/service.py` -- `registered_students(class_id)`.
- `backend/app/main.py` -- import `modules/reports/service` so its providers register.
- `backend/tests/test_imports.py` -- add reports import rule.
- `frontend/src/modules/games/home.ts:47` `stepItems`, `frontend/src/modules/games/student-hjem.tsx:194` Stegene + adjustment lines; `frontend/src/copy/nb.ts` (Hjem copy near `adjustment`).
- `frontend/e2e/support/live-game.ts` `liveClassGame` / `lockedClassGames`; `frontend/e2e/playout.spec.ts` (dev playout route pattern).

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/completion.py` -- dataclasses `StepInputs` (events, explanation_length, test_status, test_parts), `DecisionLogSummary`, `Correction`, `CompletionSettings`, `CompletionStep`, `CompletionStatus`; function `completion(...)`.
- `backend/tests/analysis/test_completion.py` -- table-driven matrix above plus branch cases; assessment_ready invariance.
- `backend/app/platform/config.py` -- two `[ASSUMPTION]` settings.
- `backend/app/modules/progress/service.py`, `games/service.py`+`repo.py`, `debrief/service.py`, `tests/service.py` -- the small reads listed in Code Map.
- `backend/app/modules/reports/{__init__,scope,service}.py` + `README.md` -- scope, `completion_status`, `funnel(class_session_id, *, session=None)`, provider registration in `sessions`.
- `backend/app/modules/sessions/service.py`, `overview.py`, `schemas.py` -- `register_completion`, `register_funnel`; Hjem fills `counts`/`requirement_met`; overview funnel via provider.
- `backend/tests/reports/` -- assembler, scope exclusions (lecturer_test, simulation, control test session, test student; replay with end_reason), five funnel equalities, Hjem API.
- `frontend/src/copy/nb.ts`, `modules/games/home.ts`, `student-hjem.tsx` -- not-counted notes and requirement line; Vitest for `stepItems`; `npm run api:generate`.
- `frontend/e2e/completion.spec.ts` -- obligatory live game played out: Hjem shows the not-counted Klassespill note and «Kravet er ikke oppfylt.», no Week numbers; axe at phone and desktop.

**Acceptance Criteria:**
- Given an obligatory session, when the Student opens Hjem, then Stegene keeps its states and a done step that does not count says so, and one line says whether the requirement is met, with no Week number.
- Given a non-obligatory session, when Hjem loads, then no requirement line and no not-counted note.
- Given one Class session, when the Oversikt funnel is read, then each of the five stage counts equals the Students whose status has that step recorded, and test students are excluded.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- verdicts: 44 findings — high 0, medium 3, low 26, false 13, maybe-false 2
- findings:
  - `[low]` `[reject]` Blind: an auto-submitted attempt with empty parts, or parts that share none with the configured list, counts by default — an auto-submitted attempt always holds its frozen items' parts (`parts_with_content`), so the case is a misconfiguration only, and a guard would add a branch.
  - `[low]` `[reject]` Blind: COMPLETION_TEST_REQUIRED_PARTS is not checked against PARTS — this is a configuration typo only, in a placeholder setting, and a check would add new surface.
  - `[false]` `[reject]` Blind: NOT_OWN_REASONS can drift and count a non-own reason — `decided_by = student` only occurs under a Student occupancy (initial, reclaim, takeover_peer). guard_switch, cost_limit and moved rows are decided by an AI player or have no occupant.
  - `[false]` `[reject]` Blind: duplicate rows per Week inflate the share — `uq_seat_weeks_game_week_seat` allows one row per Seat and Week.
  - `[low]` `[reject]` Blind: seat_log reads by Seat role, so a late registrant could be credited with the earlier Student's Orders in that Seat — this needs a Student removed mid-game and a late registrant placed in that same Seat (Story 5.13). The fix needs an occupancy join; recorded as a residual risk.
  - `[false]` `[reject]` Blind: a makeup game never counts — no code creates `makeup` Games before Story 13.4, which extends the assembler.
  - `[low]` `[reject]` Blind: an obligatory session where the Student has no game shows no requirement line — before a game nothing can be met. The line follows the game card by design, and a test now pins it.
  - `[low]` `[reject]` Blind: an exception in the assembler takes down Hjem — no failing input was shown, and a catch-all guard would hide errors.
  - `[false]` `[reject]` Blind: the provider registration fails outside main or on reload — only the api serves Hjem and the Oversikt, and it imports reports in app/main.py. The full suite passes, and nothing reloads modules.
  - `[low]` `[reject]` Blind: each Hjem load runs the assembler (separate sessions, a roster read) — a Student has one or two obligatory sessions, at about ten small queries each.
  - `[medium]` `[defer]` Blind: the AD-27 exclusions are not enforced on this branch until Epic 12 registers the hooks — this is the seam the orchestrator allowed. Deferred and named in the report.
  - `[false]` `[reject]` Blind: a corrected quiz or replay that does not count says «ferdig» — corrections arrive in Story 13.3. Today quiz and replay count whenever they are done.
  - `[low]` `[reject]` Blind: «Kravet er ikke oppfylt.» shows from day one and reads as a verdict — this is draft [ASSUMPTION] copy for the founder, and it is true and neutral.
  - `[low]` `[reject]` Blind: explanation_length trims white space while the stored length does not — trimming is intended so white space cannot meet the minimum, and there is one reader.
  - `[low]` `[reject]` Blind: ties between corrections and naive datetimes — no corrections are passed before Story 13.3.
  - `[low]` `[patch]` Blind: the CompletionStatus docstring is wrong for a session with no Week after the Guided Weeks — docstring corrected. The RUF022 part is false: that rule is not selected, and ruff passes.
  - `[low]` `[reject]` Edge: the requirement line shows before the Student could act — same as the day-one copy finding.
  - `[low]` `[reject]` Edge: one failing session breaks Hjem — same as the exception finding.
  - `[false]` `[reject]` Edge: a process without reports fails — same as the registration finding.
  - `[low]` `[reject]` Edge: N+1 queries on Hjem — same as the cost finding.
  - `[false]` `[reject]` Edge: the makeup purpose is filtered out — same as the makeup finding.
  - `[false]` `[reject]` Edge: unlisted reasons count as own — same as the NOT_OWN_REASONS finding. A whitelist would wrongly drop the Seats of late registrants.
  - `[low]` `[reject]` Edge: empty parts count by default — same as the Blind finding.
  - `[low]` `[reject]` Edge: a typo in the required parts — same as the Blind finding.
  - `[false]` `[reject]` Edge: a game with no Week after the Guided Weeks counts as done — the settings check refuses `guided_weeks >= weeks` (`guided_weeks_leave_no_weeks_to_play`), so this cannot happen.
  - `[medium]` `[defer]` Edge: the hooks default to none in a real run — grouped with the AD-27 deferral.
  - `[low]` `[reject]` Edge: the scope hooks are overwritten silently — they are merge-time wiring, with one caller each.
  - `[low]` `[reject]` Edge: inputs read in separate sessions can mix states during an auto-submit — the window is milliseconds, once per Student, and the next read is right.
  - `[low]` `[reject]` Edge: trimmed versus stored length — same as the Blind finding.
  - `[maybe-false]` `[reject]` Edge: re-importing with new function objects raises at startup — this would need a reload, and none happens. At most low.
  - `[low]` `[reject]` Edge (claim): the spec names register_funnel, but the code has one register_completion(provider, funnel) — no caller exists, and the README documents the one call.
  - `[medium]` `[defer]` Edge (claim): test students are not excluded from the funnel in production — grouped with the AD-27 deferral.
  - `[low]` `[reject]` Edge (claim): the trimmed length differs from the spec's wording — the spec's minimum is on the Explanation, and white space is not content.
  - `[low]` `[patch]` Verification: no test pins the Oversikt's Trakt to the scope — the scope test now reads the Oversikt with each hook and asserts that the registered count drops.
  - `[low]` `[patch]` Verification: an obligatory locked session where the Student has no game is untested — added test_an_obligatory_session_without_a_game_shows_no_requirement_yet.
  - `[low]` `[reject]` Verification (other): the purity test is textual — it also checks every import against an allow-list, and test_play_guard checks the folder's roots.
  - `[low]` `[reject]` Verification (other): no frontend test renders the «met» line — it is asserted at the api (requirement_met True), and the template branch is one ternary.
  - `[false]` `[reject]` Verification (other): other readers of registered_students are not moved to the scope — the story names only the assembler, the funnel and 12.5's list.
  - `[false]` `[reject]` Intent: the title says Studentside — the epics file heading and the ACs say the Student's Hjem. The staff Studentside is Story 13.2.
  - `[false]` `[reject]` Intent: dates and shares reach no surface — FR-14 keeps them from the Student, and Story 13.2 shows them to staff.
  - `[low]` `[reject]` Intent: no browser test re-checks the adjusted-share line — the line is unchanged from Story 8.9 and covered by tilrettelegging.spec and the api test.
  - `[false]` `[reject]` Intent: no requirement line before a game — same as the Blind finding.
  - `[maybe-false]` `[reject]` Intent: Stegene keeps its own states and adds `counts` on top — the states drive the gates read through progress.has_step (AD-16), so the overlay is required. Story 13.3 settles this when corrections show in Stegene.
  - `[low]` `[defer]` Intent: the Control test and test students are verified only through the hooks, and the 12.5 list is not on this branch — grouped with the AD-27 deferral.

## Design Notes

Hjem copy, draft `[ASSUMPTION]`: requirement line «Kravet er oppfylt.» / «Kravet er ikke oppfylt.» (neutral, true after the deadline too); not-counted notes «ferdig, men du bestilte selv for sjelden» (no «uke» in Student copy), «ferdig, men Forklaringen er for kort», «levert, men en del mangler svar». Shown under Stegene before the Tilrettelegging lines, only when the session is obligatory and the Student has a game.

## Verification

**Commands:**
- `uv run pytest tests/analysis/test_completion.py tests/reports -q` (lane env vars) -- pass
- `npm run typecheck && npx vitest run src/modules/games` -- pass
- `npx playwright test e2e/completion.spec.ts e2e/homes.spec.ts e2e/student-home.spec.ts e2e/overview.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** This story adds the pure `analysis.completion` and the one assembler `reports.service.completion_status`, together with `reports.scope.reporting_games`, `reports.scope.reporting_students` and `reports.service.funnel`. In Obligatory sessions, Hjem gets per-step `counts` and `requirement_met`. The Oversikt's Trakt now reads through the scope. `sessions` reaches `reports` through providers that `reports` registers. There is no migration and no new table. The builder did the implementation in its own context, as the lane brief requires, instead of handing it to a subagent.

**Files.**
- `backend/app/analysis/completion.py`: the pure rules.
- `backend/app/modules/reports/{__init__,scope,service}.py` and `README.md`: the assembler, the scope and the funnel.
- `sessions/service.py`, `schemas.py`, `overview.py`: the providers, `completion_terms`, the Hjem fields and the Trakt.
- `progress/service.py`: `step_events`.
- `games/service.py`, `repo.py`: `seat_log` and `session_games`.
- `debrief/service.py`: `explanation_length`.
- `tests/service.py`: `attempt_status`.
- `platform/config.py`: two [ASSUMPTION] minimums.
- `main.py`: the import that registers the providers.
- Frontend: `copy/nb.ts`, `modules/games/home.ts`, `student-hjem.tsx`, the regenerated api client, `e2e/support/live-game.ts` (an `obligatory` option) and `e2e/completion.spec.ts`.
- Tests: `backend/tests/analysis/test_completion.py`, `backend/tests/reports/` and `test_imports.py`. Five exact-shape expectations now include `counts` or `requirement_met`.

**Review.** Four layers ran: blind, edge case, verification gap and intent alignment.
- Patched: 3 low findings (two tests and one docstring).
- Deferred: 1 group, medium. The AD-27 exclusions wait for Epic 12.
- Every rejected finding and its reason is in the Review Triage Log.
- Follow-up review: false. No high finding was patched, and fewer than two medium ones were.

**Verification.**
- Full backend suite (8 processes): the first run had 3681 passed and 1 failure. An analysis-folder import rule caught `datetime` in the pure module. Fixed. After the review patches the rerun had 3717 passed. No new test is slow beyond the existing short-game fixtures: the `tests/reports` tests take 1.5 to 3 s each, like `tests/sessions/test_game_end.py`.
- Frontend build: passes.
- Frontend: typecheck, Vitest (1186 passed), lint:colours and check:copy pass.
- Playwright: `completion`, `homes`, `student-home`, `overview`, `playout`, `game-card`, `order-field` and `tilrettelegging` ran on 4 workers, 54 passed. The `completion` spec runs axe at 320 px, at 1280 px with 200 % text, and at 1440 px.

**Residual risks.**
- The Decision log is read per Seat role. A late registrant placed in the Seat of a Student removed mid-game is credited with that Student's earlier Orders.
- The scope hooks must be wired at the Epic 12 merge.
- Hjem runs the assembler once per Obligatory session, at about ten small queries each.
