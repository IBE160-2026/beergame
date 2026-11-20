---
title: 'Story 5.16: Set Information visibility (cut list, FEATURE_INFO_VISIBILITY)'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'cd85b50b304d709835d0efe88efd301b2d3b394f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-15-set-shipping-capacity.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred:
  - summary: >-
      No frontend test sees the info_visibility problem path or the page-level feature_disabled save message.
    evidence: |-
      class-session-page.tsx maps feature_disabled to copy.edit.featureDisabled and InfoVisibilityFields shows iv.disabled; no unit or e2e test answers a save or check with feature_disabled. Reachable only when the flag changes between page load and save.
    location: >-
      frontend/src/modules/sessions/class-session-page.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot let Seats see their neighbours' inventory and backlog (FR-83): `engine.GameSettings` has no Information visibility field, and the Klasseøkt has no setting for it.

**Approach:** Add `info_visibility` (`upstream`, `downstream`, both off) to `engine.GameSettings` with a `schema_version` bump (1 → 2; version-1 settings read as off). Behind `FEATURE_INFO_VISIBILITY` (`get_settings().feature_info_visibility`) the Klasseøkt edits it with two Bryter controls, stores it in the session's `GameSettings` and the lock freezes it into every Class game's snapshot, exactly like Story 5.15's capacity.

## Boundaries & Constraints

**Always:**
- Engine: `InfoVisibility(upstream: StrictBool = False, downstream: StrictBool = False)`, frozen, `extra="forbid"`. `GameSettings.schema_version: Literal[1, 2] = 2`; a before-validator upgrades a version-1 dict to 2 with visibility off, and refuses a version-1 dict that carries `info_visibility`. `validate(..., info_visibility_enabled=False)` fails closed: any view on while not enabled is error `info_visibility_disabled` on `info_visibility`. No rule change; `RULES_VERSION` unchanged; golden traces unchanged.
- Callers of `validate` pass the flag: `games.commands._effective_settings`, `sim settings check`, and the sessions service.
- Sessions: `info_visibility` joins `EDITABLE_SETTINGS`. Flag off: a draft whose `info_visibility` differs from the stored one and has a view on → check error `info_visibility: {code: feature_disabled}`; save 422 `feature_disabled` with `fields {"info_visibility": "feature_disabled"}`; nothing stored. All-off or an unchanged stored value is accepted (switching off is always allowed). Locked session: 409 `session_locked` first. A non-object, unknown key or non-boolean → 422 `invalid_settings`, `info_visibility` `invalid`.
- `ClassSessionOut.info_visibility_enabled: bool`. Flag off: the screen shows no visibility field, row or help.
- Screen (flag on, unlocked, block open): section «Synlige naboer» with two Bryter, «Leddet oppstrøms» and «Leddet nedstrøms», off by default, each stating it shows current inventory and backlog; a help line gives the scope (all Class games of the session; Fabrikken has no upstream neighbour, Detaljisten no downstream) and promises no effect on learning or cost. Settings list row «Synlige naboer». All copy in `nb.ts` marked `[ASSUMPTION]`; the web holds no rule.

**Never:** No filling of `seat_state` neighbour fields, no play-screen display, no LLM prompt or Decision log change (Story 6.21). No Replay change (Story 10.9). No migration. No change to the demo Class. No edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | new session, flag on | `game_settings.info_visibility` = both false, `schema_version` 2, `info_visibility_enabled: true`, row «Av» | — |
| Old row | stored v1 dict without the field | reads as v2, both off | — |
| Upstream on | save `{"info_visibility": {"upstream": true, "downstream": false}}` | stored; `is_classic` false | — |
| Both | both true | stored; row names both | — |
| Bad value | `{"upstream": "yes"}`, `{"left": true}`, `5` | nothing stored | 422 `invalid_settings`, `info_visibility` `invalid` |
| Flag off | save upstream on | nothing stored | 422 `feature_disabled` |
| Flag off, off | save both false + weeks change | saved | — |
| Flag off later | stored on, flag off, save weeks | saved, visibility kept | — |
| Locked | stored on, lock runs | every game snapshot `settings.info_visibility` = stored; change → 409 `session_locked` | — |
| Engine gate | `games.commands.create` with a view on, flag off | 422 `invalid_settings` `info_visibility_disabled` | — |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py:43` `GameSettings` -- add `InfoVisibility`, field, version bump, before-validator; `:221` `validate` -- new kw `info_visibility_enabled`; export from `backend/app/engine/__init__.py`. 100 % coverage gate: tests in `backend/tests/engine/test_settings.py` (`:10` dump, `:56` `{"schema_version": 2}` invalid case → 3) and `test_validation.py`.
- `backend/app/analysis/play_guard.py:105` `is_calibrated` -- profiles are v1 JSON, upgraded on read; verify still calibrated (test exists).
- `backend/app/modules/games/commands.py:140`, `backend/app/sim.py:367` -- pass `feature_info_visibility`.
- `backend/app/modules/sessions/service.py:277` `FeatureDisabled` doc; `:391` `EDITABLE_SETTINGS`; `:397` add `info_visibility_enabled()`; `:407` `judge_settings` flag gate mirroring capacity; `:725` `get_session` field; `:932` `_settings_to_store` already generic on `feature_disabled`.
- `backend/app/modules/sessions/schemas.py:209` -- `info_visibility_enabled`.
- `backend/app/modules/sessions/routes.py:141` docstring; `README.md:73` section.
- Tests with `schema_version == 1` to update: `tests/games/test_create.py:49,57`, `tests/games/test_start.py:182` (input; ok), `tests/sessions/test_class_sessions.py:77`, `tests/sessions/test_settings.py:237` (`{"schema_version": 1}` stays `not_editable`). New `backend/tests/sessions/test_info_visibility.py` modelled on `test_capacity.py` (flag via `monkeypatch.setenv` + `get_settings.cache_clear()`, lock via `sweep` as there).
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate as Story 5.15 did.
- `frontend/src/modules/sessions/settings.ts` -- `InfoVisibilityDraft`, `draftOf(settings, capacityEnabled, infoVisibilityEnabled)`, `settingsBody` adds `info_visibility` when present; `problemText` `feature_disabled` stays capacity text, visibility problem worded in its own section.
- `frontend/src/modules/sessions/settings-form.tsx` -- `InfoVisibilityFields` after `CapacityFields` (pattern `:276`), `otherErrors` skips `info_visibility`; `ReadOnlyRows` passes the flag.
- `frontend/src/modules/sessions/sessions.ts` -- `settingRows(..., infoVisibilityEnabled)` row `info_visibility`, `infoVisibilityText`.
- `frontend/src/modules/sessions/class-session-page.tsx:138,169,210` -- pass `item.info_visibility_enabled`; `feature_disabled` save message becomes a generic line.
- `frontend/src/copy/nb.ts:708–872` -- copy.
- Tests: `settings.test.ts`, `sessions.test.ts`, new `frontend/e2e/class-session-info-visibility.spec.ts` modelled on `class-session-capacity.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/settings.py`, `__init__.py`, engine tests -- field, version, gate; 100 % coverage.
- `backend/app/modules/games/commands.py`, `backend/app/sim.py` -- pass the flag.
- `backend/app/modules/sessions/{service,schemas,routes}.py`, `README.md` -- gate, judging, `info_visibility_enabled`.
- `backend/tests/sessions/test_info_visibility.py` + updated version assertions -- every matrix row.
- `frontend/src/lib/api/*` -- regenerate.
- `frontend/src/copy/nb.ts`, `sessions.ts`, `settings.ts`, `settings-form.tsx`, `class-session-page.tsx` -- UI.
- `settings.test.ts`, `sessions.test.ts`, `class-session-info-visibility.spec.ts` -- unit tests of draft/body/rows; e2e: switch upstream on, save, see the row; flag off (answer rewritten) shows nothing; axe clean.

**Acceptance Criteria:**
- Given the flag on and an unlocked session, when the Lecturer opens the settings, then «Synlige naboer» shows two Bryter, both off, with the help line; switching «Leddet oppstrøms» on and saving stores `{"upstream": true, "downstream": false}` and the list row names it.
- Given the flag off, when the screen renders, then no visibility text appears, and a PUT that switches a view on answers 422 `feature_disabled`.
- Given a saved view and the Start date passes, when the lock runs, then every Class game's snapshot settings carry the same `info_visibility`, and a change answers 409 `session_locked`.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 28 findings — high 0, medium 2, low 16, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: a partial `info_visibility` map replaces the stored one rather than merging (BOTH stored, `{"upstream": true}` sent turns downstream off). Same map-replace rule as capacity; the screen always sends both views; a missing view is off.
  - `[medium]` `[patch]` blind: with the flag off, switching one view of two off was refused as `feature_disabled`. Fixed: only a view going from off to on counts (`_shows_a_new_neighbour`, and the engine gate in `judge_settings` uses the same test); test `test_with_the_flag_off_one_view_of_two_can_be_switched_off`.
  - `[low]` `[reject]` blind: with the flag off a stored view is hidden from the screen and cannot be cleared there. Needs the flag switched off while a session holds a view; same recorded decision as Story 5.15's capacity (kept, frozen, hidden); the api still clears it.
  - `[low]` `[patch]` blind: with the flag off a malformed value with a view on answered `feature_disabled`, not `invalid`. Fixed: a map with unknown keys or non-boolean values is left to the engine; parametrised test added.
  - `[low]` `[reject]` blind: `null` is refused, while capacity takes null as off. `info_visibility` is not nullable in the engine; the screen never sends null; the route doc states that anything but the two booleans is `invalid`.
  - `[low]` `[reject]` blind: `schema_version: Literal[1, 2]` makes the output type `1 | 2` though a parsed model never holds 1. Harmless widening; `Literal[1, 2]` is the spec's contract.
  - `[false]` `[reject]` blind: a locked version-1 row looks changed on an unchanged save. `_settings_to_store` compares parsed models (`settings == stored`), both version 2 after the upgrade; version-1 golden files and game rows are read by the existing replay and golden tests, which pass.
  - `[false]` `[reject]` blind: flag helpers leave a stale cached `get_settings`. `tests/conftest.py::_fresh_settings` clears the cache before and after every test, so the first `setenv` in `test_create` is read fresh.
  - `[low]` `[reject]` blind: the README says `seat_state`, the LLM prompt and the Decision log read the frozen value. They read the snapshot settings, which is AC3's own wording; filling them is Story 6.21's, as the same sentence says.
  - `[low]` `[reject]` blind: the help copy describes behaviour (play screen, AI players) that Story 6.21 builds. The story asks for this help text; it is `[ASSUMPTION]` draft copy; same pattern as Story 5.15's briefing line.
  - `[low]` `[defer]` blind: no frontend test of the `info_visibility` problem path or of the new `featureDisabled` save message. Same as the verification-gap row below.
  - `[false]` `[reject]` blind: the effect in `InfoVisibilityFields` has no dependencies and may skip a check. Each switch changes state, so a render and the effect follow; it is the reviewed capacity pattern, and the e2e test waits on the check after a click.
  - `[low]` `[patch]` blind: the `infoVisibilityText` docstring said «Ingen» while the copy is «Av». Fixed the docstring; «Av» is the matrix's own wording.
  - `[low]` `[patch]` edge: `schema_version: true` was accepted and skipped the upgrade. Fixed: the before-validator refuses a version that is not an int; engine test cases added.
  - `[low]` `[patch]` edge: `schema_version: 1.0` with `info_visibility` skipped the version-1 refusal. Same fix as the row above.
  - `[medium]` `[patch]` edge: flag off, BOTH stored, switching one off refused. Same root cause and fix as the second blind row.
  - `[low]` `[patch]` edge: a malformed map with a view on answers `feature_disabled` with the flag off. Same fix as the fourth blind row.
  - `[false]` `[reject]` edge (claim): README "switching views off is always allowed" did not hold. Holds after the patch above; test added.
  - `[false]` `[reject]` edge (claim): parity with capacity broken on partial removal. Holds after the patch above.
  - `[low]` `[patch]` verification-gap: `sim settings check` passes `FEATURE_INFO_VISIBILITY` untested. Added `tests/test_sim.py::test_settings_check_takes_information_visibility_from_its_flag` (off: exit 1 `info_visibility_disabled`; on: OK).
  - `[low]` `[defer]` verification-gap: the page-level `feature_disabled` message (`copy.edit.featureDisabled`) is not seen by any test. Reachable only when the flag changes between page load and save; the gap predates this story for capacity.
  - `[low]` `[patch]` verification-gap (other): Play guard calibration with a view on was unpinned. Decision: a neighbour's numbers change what a player sees, so it is not the calibrated profile; asserted in `tests/analysis/test_play_guard.py`.
  - `[false]` `[reject]` intent (a): a view stored while the flag was on survives a later flag-off and is frozen at the lock. Recorded design decision, identical to Story 5.15 (a stored setting runs whatever the flag says now); AC1 holds for every session while the flag is off from the start.
  - `[false]` `[reject]` intent (b): the help text promises unbuilt behaviour. Same as the blind row above.
  - `[false]` `[reject]` intent (c): AC3 tested only to the snapshot. AC3's own next line puts filling `seat_state` and showing the numbers in Story 6.21; the three consumers already read the snapshot settings.
  - `[false]` `[reject]` intent (d): the flag-off screen is tested with a rewritten answer. The screen reads only `info_visibility_enabled`; the real flag is tested at the api, as in Story 5.15.
  - `[false]` `[reject]` intent (e): simulation and CLI answer `invalid_settings`/`info_visibility_disabled`, not `feature_disabled`. AC1 names the Klasseøkt settings request; the engine gate keeps the existing simulation contract (as capacity's `capacity_disabled`).
  - `[low]` `[reject]` intent (f): the shared `feature_disabled` save message changed for capacity too. Deliberate: one message now covers both cut-list settings; wording only.

The four reviewers finished, but their completion notices never reached this builder; their reports were read from their transcripts. No independent visual reviewer was run; the builder looked at screenshots of the new section at 1440 and 360 px (two Bryter side by side, stacked on the phone, help line below). The orchestrator runs its own visual check of `frontend/`.

## Design Notes

Founder-level decisions taken here:
- Version bump with upgrade-on-read: every `GameSettings` now dumps `schema_version: 2` and `info_visibility`; stored v1 rows (games, sessions, golden files, parameter sets) load as v2 with both views off, so no migration and no data rewrite.
- The engine gate fails closed (`info_visibility_disabled`), like capacity, so simulation games also obey the flag (AD-17).
- Flag-off refusal and keeping a stored value follow Story 5.15 exactly; switching views off is always allowed.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/engine tests/sessions/test_info_visibility.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run build && npx playwright test` -- pass

## Auto Run Result

Status: done

**Summary.** Information visibility is a Game setting of the Klasseøkt behind `FEATURE_INFO_VISIBILITY`.
- **Engine:** `GameSettings.info_visibility` (`InfoVisibility{upstream, downstream}`, strict booleans, both off); `schema_version` 1 → 2, version-1 settings read as version 2 with both views off (no migration); `validate(..., info_visibility_enabled=False)` fails closed with `info_visibility_disabled`. Rules version and golden traces unchanged; engine coverage 100 %.
- **Callers:** `games.commands.create` and `sim settings check` pass the flag.
- **Klasseøkt api:** `info_visibility` is editable; `ClassSessionOut.info_visibility_enabled`. Flag off: switching on a view that is off as stored answers 422 `feature_disabled`; switching views off and resending a stored view are allowed; 409 `session_locked` first once locked. Malformed values are `invalid`. The lock freezes it into every Class game's snapshot.
- **Screen:** section «Synlige naboer» with two Bryter («Leddet oppstrøms», «Leddet nedstrøms»), off by default, each naming the inventory and backlog it shows; a help line with the scope and no promised effect; a list row. The `feature_disabled` save message is now one generic line for both cut-list settings.

**Files.**
- `backend/app/engine/{settings,__init__}.py`: field, version upgrade, gate.
- `backend/app/modules/games/commands.py`, `backend/app/sim.py`: pass the flag.
- `backend/app/modules/sessions/{service,schemas,routes}.py`, `README.md`: gate, judging, `info_visibility_enabled`.
- Tests: `tests/engine/test_{settings,validation}.py`, `tests/games/test_create.py`, `tests/sessions/test_info_visibility.py` (new), `tests/sessions/test_class_sessions.py`, `tests/test_sim.py`, `tests/analysis/test_play_guard.py`.
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `frontend/src/copy/nb.ts` (`[ASSUMPTION]` draft copy), `frontend/src/modules/sessions/{settings,sessions}.ts`, `settings-form.tsx`, `class-session-page.tsx`.
- `settings.test.ts`, `sessions.test.ts`, `frontend/e2e/class-session-info-visibility.spec.ts` (new).

**Review.** 28 findings: medium 2 (one root cause), low 16, false 10. Patched: the flag-off switch-off rule, malformed values with the flag off, non-int `schema_version`, the CLI flag test, the Play guard calibration assertion, a docstring. One low deferred (frontend test of the `feature_disabled` messages). Rejections and reasons are in the triage log. Follow-up review: false (one patched entry at medium, its two members share one root cause, no high; pinned by a new test). Patched counts by entry: medium 1, low 5.

**Verification.**
- Backend: 2591 passed (72 s); ruff check and format clean. One earlier full run had a single failure in `tests/games/test_place_order.py::test_an_order_writes_one_decision_log_row_with_the_state_seen` that passed alone and in the next two full runs (flaky, unrelated).
- Frontend: typecheck, Vitest 445 passed, build, `check:copy`, Playwright 267 tests: 255 passed in the full run right after the rebuild; the 12 others all timed out waiting for a mail (`e2e/support/auth.ts:127`, none in this story's screens) and passed on `--last-failed`. An earlier full run before the review patches passed 267 of 267.
- New slow test: `test_the_lock_freezes_the_views_into_every_class_game` takes about 1.0 s (it seats 5 Students and runs the lock).
- No migration; `GameSettings` dumps now carry `schema_version: 2` and `info_visibility`.

**Residual risks.** A view stored while the flag was on is kept, frozen and hidden if the flag is later switched off (same as capacity). Nothing shows the neighbour numbers until Story 6.21, although the flag defaults to on.

**Process note.** Per the autobuild runbook, the builder implemented the spec in its own context rather than in an implementation subagent, and applied the review patches itself.
