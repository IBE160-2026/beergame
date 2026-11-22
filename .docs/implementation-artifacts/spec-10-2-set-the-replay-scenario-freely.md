---
title: 'Story 10.2: Set the Replay scenario freely'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '86a4606d600120a46814ec9d53974d1a4d1426b3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-1-get-a-default-replay-scenario-that-differs-per-student.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 10.1 gave every Class session the default Replay scenario only; FR-49 lets a Lecturer set every Game setting of the Replay freely (including the Class game's exact settings), with non-blocking warnings for changes that probably make the Replay easier, frozen at the Start date.

**Approach:** Store an own `engine.ReplayTemplate` (JSONB `class_sessions.replay_template`, choice `own`) through `sessions.save_session` («Lagre Klasseøkt»), judged by `validate_template`; one warning function `replay_warnings(template, class_settings)`; a draft check endpoint; the pin provider pins the own template; `copy_from` copies choice and template. The Klasseøkt Replay block gets Valgknapper «Standard» / «Eget scenario» and, for own, the Game settings fields prefilled from the Class session's settings, Weeks and change Week each with an optional «til» bound (a range drawn per Student).

## Boundaries & Constraints

**Always:** the template is the one model for default and own; the default is never stored. An own template carries `roles`, `capacity` and `info_visibility` from the Class session's Game settings at save (not editable here; Story 10.9 owns visibility). Field errors reuse `SettingProblem` and the keys of Game settings (`weeks`, `demand.change_week`, `demand.start` …) so `problemText` renders them with the range. Warnings never block a save. Once locked (`is_locked`), any change of choice or template answers `409 session_locked`; the same unchanged body still saves. Assistants read, no controls (`can_manage`). UI copy only in `nb.ts`; one column below `lg`.

**Never:** no change to `engine/scenario.py` resolution rules; no Replay Game creation (10.3); no seed field in the Replay form (every Replay draws its own); no ranges for fields other than Weeks and change Week in the form (the api accepts any `Ranged` field the template allows); no info-visibility editing; no tests that play a Game.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Class game's exact settings | own, template = Classic values fixed (Weeks 36, change Week 5, step spread 0, Guided 4) | stored as `own` with fixed values; warning `replay_guided_weeks` only | — |
| Single step Week and Weeks | change Week 8, Weeks 30 | accepted, stored fixed | — |
| Ranged | Weeks 30–40, change Week 5–12 | stored as `IntRange`s | — |
| Back to default | choice `default` | `replay_scenario=default`, `replay_template` NULL; view derives the default | — |
| Bad value | Weeks `"abc"` / order delay 9 | — | 422 `invalid_replay_scenario`, `fields.weeks`/`order_delay` = `{code, minimum, maximum}` |
| Rule across draws | Weeks 20–40, change Week 25 | — | 422, `demand.change_week` `demand_change_week_outside_game` |
| `own` without template | `replay_scenario: own`, no template, none stored | — | 422 `invalid_replay_scenario` `{replay_template: {code: required}}` |
| Locked change | locked session, own template differs | — | 409 `session_locked` `{replay_scenario: locked}` |
| Copy (FEATURE_RERUN on) | source `own` | copy holds `own` and the same template (re-validated; invalid now → copy falls back to `default`, logged) | — |

</intent-contract>

## Code Map

- `backend/app/engine/scenario.py` -- `ReplayTemplate`, `IntRange`, `RANGED_FIELDS`, `CHANGE_WEEK`, `validate_template(template, capacity_enabled, info_visibility_enabled)` → `SettingsError`s with field keys; read-only here.
- `backend/app/modules/sessions/service.py` -- `judge_settings` (~470, pattern for parse errors → `_problem`), `_parse_problem`, `_problem`, `range_of`; `get_session` (~743) builds `ClassSessionOut` (`replay_scenario`, `replay_template`); `save_session` (~852, locked-diff dict, `repo.save`); `check_settings` (~1080); `replay_template` / `replay_template_pin` (~2943); `_copied_settings` / `copy_from` (~4238); `InvalidSettings` (~325).
- `backend/app/modules/sessions/{repo.py:225 save, insert_session, models.py, schemas.py:363 ClassSessionSaveIn, SettingsCheckIn/Out ~82, routes.py:~279 save, ~563 settings-check}`.
- `backend/migrations/versions/0114_replay_scenario.py` -- constraint `ck_class_sessions_replay_scenario`; new 0115.
- `backend/tests/sessions/test_replay_scenario.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py` (HEAD, downgrade walk), copy tests (`grep -l copy_from backend/tests/sessions`).
- `frontend/src/modules/sessions/{replay-scenario.ts, replay-scenario-block.tsx, settings.ts (EDITABLE, draftOf, demandBody, problemText, warningsBySetting), settings-form.tsx (DemandFields: add a no-seed option and export), class-session-page.tsx (save body, error map), api.ts (saveClassSession, checkClassSessionSettings)}`.
- `frontend/src/copy/nb.ts:1105` `sessions.replay`; `frontend/e2e/class-session-replay.spec.ts`; `frontend/e2e/support/{auth,classes}.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0115_replay_own_scenario.py` -- check `IN ('default','own')`; `replay_template jsonb NULL`; check `(replay_scenario = 'own') = (replay_template IS NOT NULL)`; downgrade resets own rows to default. `test_migrations.py` HEAD.
- `backend/app/modules/sessions/{models,repo}.py` -- column; `save(..., replay_scenario=, replay_template=)` (sentinel: unchanged); `insert_session` takes both.
- `backend/app/modules/sessions/service.py` -- `judge_replay_template(class_settings, draft) -> (template|None, problems, warnings)`; `replay_warnings(template, class_settings) -> list[SettingWarning]` (rules in Design Notes); `InvalidReplayScenario`; `save_session(..., replay_scenario=, replay_template=)`; `check_replay_scenario`; `replay_template(row)` (pin → own → derived); pin provider pins own; `get_session` adds `replay_warnings`; `copy_from` copies.
- `backend/app/modules/sessions/{schemas,routes}.py` -- `ClassSessionSaveIn.replay_scenario: Literal['default','own'] | None`, `replay_template: dict | None`; `ClassSessionOut.replay_warnings`; `POST /class-sessions/{id}/replay-scenario-check` (`checkReplayScenario`, 409 once locked); 422 `invalid_replay_scenario` mapping in save.
- `backend/tests/sessions/test_replay_own.py` (new) -- matrix rows over the api with one module-scoped Class session where possible; `replay_warnings` one test per rule; pin of own at lock; copy with rerun on.
- `frontend/src/modules/sessions/replay-scenario.ts` -- `ReplayDraft` (SettingsDraft + `weeksTo`, `changeWeekTo`), `replayDraftOf(template | settings)`, `replayTemplateBody(draft)`, own-scenario rows, `replayWarningText`.
- `frontend/src/modules/sessions/replay-scenario-block.tsx` + `settings-form.tsx` + `class-session-page.tsx` + `api.ts` -- Valgknapper, form (fields, demand without seed, errors/warnings under fields, check on leave), read-only rows with warnings; body sent with «Lagre Klasseøkt»; refusals shown.
- `frontend/src/copy/nb.ts` -- copy; `open-assumptions.md` draft-copy line.
- `frontend/src/modules/sessions/replay-scenario.test.ts` -- body and draft mapping, warning text.
- `frontend/e2e/class-session-replay.spec.ts` -- choose own, set a shorter delay → warning, save, reload shows own; single values accepted; bad value inline; assistant read-only; axe 320/1440 with the form open.
- regenerate api client; spine/epic notes untouched except `open-assumptions.md`.

**Acceptance Criteria:**
- Given a Lecturer before the Start date, when they pick «Eget scenario», then every listed Game setting shows prefilled from the Class session's settings, out-of-range values show inline with the range, and «Lagre Klasseøkt» stores it; reloading shows «Eget scenario» with its values.
- Given an own scenario with a shorter delay, lower or less variable demand, Guided Weeks or more starting inventory than the Class game, when the form is shown or saved, then a warning names the change and says it probably makes the Replay easier, and the save succeeds.
- Given a locked session, when anyone opens the block, then it is read-only and the lock pinned the own template (or the default); a changed save answers 409 `session_locked`.
- Given an Assistant lecturer, when they open the block, then they read it with no Valgknapper or fields.
- Given the block at 320 and 1440 px with 200 % text, then the form is one column at narrow widths and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Two layers (sonnet, per the runbook's default): blind hunter and edge-case hunter. Both hand-backs failed; findings were read from `review-{blind,edge}-10-2.md` in the scratchpad.
- verdicts: 26 findings — high 0, medium 2, low 19, false 5, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) the check judges against the stored Game settings, the save against the edited ones — only when both blocks are edited in one go; the save gives the right warnings, and passing draft settings to the check adds an api parameter.
  - `[low]` `[reject]` (blind 2) a copy falls back to the default with only a log line — a recorded decision (I/O matrix); reaching it needs a template the engine refuses after a rule change.
  - `[medium]` `[patch]` (blind 3) a stored own template keeps a stale chain, capacity and Information visibility when the Game settings change in a save that does not send the scenario — `_replay_to_store` now judges the stored fields again for the saved settings, and `save_session` does it whenever the Game settings change on an own scenario; test `test_a_stored_own_template_follows_the_game_settings_and_a_locked_change_is_refused`.
  - `[low]` `[reject]` (blind 4) `replay_template` without `own` is ignored with 200 — api-only, documented as left out; the screen always sends the pair.
  - `[low]` `[reject]` (blind 5) a range error stands under the «minst» field — the api keys range errors by the setting (`weeks`), which is the first field; the text names the range.
  - `[low]` `[patch]` (blind 6) switching to «Standard» and back drops what was typed — `setChoice` keeps the draft and only judges it again.
  - `[false]` `[reject]` (blind 7) a check in flight after switching to «Standard» — its answer only sets state of the hidden form, and choosing «Eget scenario» judges again.
  - `[low]` `[patch]` (blind 8) the Story 5.3 JSDoc in `api.ts` sat above the new type — moved back above `checkClassSessionSettings`.
  - `[false]` `[reject]` (blind 9) more rules could warn (backlog, costs, `max_order`, Weeks, later change Week, reversed step) — the story's AC lists the warned changes; the list is a recorded decision in `open-assumptions.md`.
  - `[low]` `[reject]` (blind 10) a warning on a range shows only its easier end — the number shown is the one that triggers the warning; adding the range is copy polish.
  - `[low]` `[reject]` (blind 11) warnings are not live regions — same pattern as the Game settings warnings (Story 5.3); axe passes.
  - `[false]` `[reject]` (blind 12) the diff carries Story 10.1 screenshots — they are commit 61e87f8 by another run after the baseline, not this change.
  - `[low]` `[reject]` (blind 13) editable fields listed twice (backend and web) — the api refuses an unknown key as `not_editable`, so a drift shows at once.
  - `[false]` `[reject]` (blind 14) migration `JSONB()` vs model `JSONB(none_as_null=True)` — the DDL is the same; `none_as_null` is ORM binding only, and the save test stores SQL NULL through the model (it failed before the flag).
  - `[low]` `[reject]` (blind 15) no size bound on the check body — staff-only endpoint, pydantic parses it once; same as `settings-check`.
  - `[low]` `[reject]` (blind 16) `repo.save`'s `replay` docstring reads ambiguous — it says None keeps both.
  - `[low]` `[reject]` (blind 17) further tests (assistant check 403, archived class) — covered by the shared `class_sessions.manage` guard and its existing tests.
  - `[medium]` `[patch]` (edge 1) = blind 3.
  - `[low]` `[patch]` (edge 2) `ownHiddenLine` said «same values» with only the change Week ranged (reachable in the form) — new line `hiddenChange`; Vitest case added.
  - `[low]` `[reject]` (edge 3) a fixed series with a spread (api-only) loses its spread when saved from the form — the form never sets one; api-only.
  - `[low]` `[patch]` (edge 4) a demand warning could stand beside a `demand.*` error — warnings are dropped when any problem key is the field or under it; test added.
  - `[low]` `[reject]` (edge 5) = blind 4.
  - `[low]` `[patch]` (edge 6) locked default + `own` with no template answered 422 `required` instead of 409 — locked is checked first.
  - `[false]` `[reject]` (edge 7) `_copied_replay` 500 on an unparseable stored template — only `_replay_to_store` writes it, from a validated template; the check constraint holds the pair.
  - `[low]` `[reject]` (edge 8) = blind 5.
  - `[low]` `[patch]` (edge 9) = blind 6.

## Design Notes

Warning rules (`replay_warnings`, vs the Class session's current Game settings; a ranged value counts by the end that makes it easier): `replay_delay_shorter` per delay whose template minimum is below the Class value; `replay_demand_lower` when the template's peak level (step: max(start, new_level); random: mean; fixed: max(values)) is below the Class game's; `replay_demand_less_variable` when the template's spread is below the Class game's spread (step 0, fixed 0) or the Class demand changes level (step with start ≠ new_level, fixed non-constant) and the template's does not; `replay_guided_weeks` when the template's maximum Guided Weeks is above 0 (the default has none); `replay_inventory_higher` when the template's maximum starting inventory is above the Class value. `values` carry the numbers as decimal strings.

Draft parsing mirrors `judge_settings`: base = Class `roles`, `capacity`, `info_visibility`; editable keys = `RANGED_FIELDS`, `demand`, `holding_cost`, `backorder_cost` (others `not_editable`); pydantic errors map to the Game-settings key with `ranged=True`; then `validate_template` errors via `_problem`. A Game-settings-shaped demand (`step`/`step+noise`/`random`/`fixed`) is mapped by the web app to the template kinds (`step+noise` → `step` with its spread; `step` → spread 0; fixed → spread 0).

## Verification

**Commands:**
- `uv run pytest tests/sessions/test_replay_own.py tests/sessions/test_replay_scenario.py tests/sessions/test_lock.py tests/test_migrations.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/sessions` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** A Class session can now hold an own Replay scenario: `class_sessions.replay_template` (0115, JSONB, there exactly when `replay_scenario = 'own'`) stores an `engine.ReplayTemplate` judged by `sessions.service.judge_replay_template` (the draft laid over the Class game's exact settings, `engine.validate_template`, errors keyed and ranged as the Game settings'). `replay_warnings` is the one function of changes that probably make the Replay easier. «Lagre Klasseøkt» (`PUT /api/class-sessions/{id}`) takes `replay_scenario` and `replay_template` (422 `invalid_replay_scenario`, 409 `session_locked` once locked). `POST /replay-scenario-check` judges a draft as a field is left. The lock pins the own template. `copy_from` copies it, judged again, or falls back to the default. The Klasseøkt block has Valgknapper «Standard» / «Eget scenario». The own form reuses the Game settings fields, without a seed, with «minst/høyst» for Weeks and «tidligst/senest» for the change Week. Errors stand inline with the range and warnings under the field. Read-only (locked or Assistant), the scenario stands as a list with its warnings.

**Files.** Backend: `migrations/versions/0115_replay_own_scenario.py` (new), `modules/sessions/{models,repo,schemas,routes,service}.py`, tests `sessions/test_replay_own.py` (new), `sessions/test_replay_scenario.py`, `test_migrations.py`. Frontend: `modules/sessions/{replay-scenario.ts,replay-scenario-block.tsx,replay-scenario.test.ts,settings-form.tsx (DemandFields exported, ids/labels/extra/notes/seed props),class-session-page.tsx,api.ts}`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/class-session-replay.spec.ts`. Docs: `open-assumptions.md` (draft copy, warning rules).

**Decisions the founder would otherwise take.** (1) Warning rules, compared with the Class game and with a range counted by its easier end: a shorter delay, a lower peak demand level, a smaller spread, a change of level removed, any Guided Weeks, a higher starting inventory. (2) Only Weeks and the change Week take a range in the form; the api accepts a range for every whole-number field the template allows. (3) The chain, capacity and Information visibility of an own scenario always follow the Game settings, and are re-based when they change. (4) The own form opens on the Class game's exact settings, so the Classic Guided Weeks (4) warn at once. (5) Switching back to «Standard» drops the stored own template on save. (6) A copy whose own template no longer validates gets the default, with a log line only. (7) `ClassSessionOut.replay_default` was added so the screen can describe the default before saving. (8) The implementation was done in this context rather than by a sub-agent (runbook), with two review layers (blind, edge case) per the runbook's default.

**Review.** 26 findings (two sonnet layers): 7 patched (1 medium entry: own template re-based on settings changes; lows: draft kept across choice toggles, JSDoc placement, `hiddenChange` line, demand warning beside a demand error, 409 before 422 when locked), 0 deferred, the rest rejected with reasons in the triage log. `followup_review_recommended: false`: one medium entry patched, with its own test.

**Verification.** Full backend suite `--maxprocesses=8`: 3064 passed (after the patches). An earlier full run, started while review agents ran, produced no output before its 20-minute timeout. It was not rerun for diagnosis; the rerun passed in 112 s. ruff clean. Frontend typecheck, Vitest 794 passed, `check:copy`, `lint:colours`, and build (in the image) passed. Stack rebuilt after the last frontend change. Playwright `--workers=4` on class-session*, homes and the play-screen specs: 268 passed, including axe at 320 px, 200 % text and 1440 px with the own form open. No new test over 1 s. No test failed once and then passed on rerun.

**Residual risks.** The check endpoint judges against the saved Game settings, so with both blocks edited at once the warnings settle on save. API-only inputs, such as a fixed series with a spread or a range on other fields, are accepted, but the form cannot show them.
