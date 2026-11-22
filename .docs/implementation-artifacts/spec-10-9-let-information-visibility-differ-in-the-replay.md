---
title: 'Story 10.9: Let Information visibility differ in the Replay (cut list, FEATURE_INFO_VISIBILITY)'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '5dbad27528d9301bcb45773b48c227f657400b43'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-2-set-the-replay-scenario-freely.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-16-set-information-visibility.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** An own Replay scenario (Story 10.2) always takes the Class session's Information visibility, so a Lecturer cannot let Students try the same chain with more or less to see (FR-83, FR-49).

**Approach:** `info_visibility` becomes an editable field of the own `engine.ReplayTemplate` (already a template field, resolved by `replay_settings` and pinned by Story 10.1's provider), prefilled from the Class session, gated by `FEATURE_INFO_VISIBILITY` exactly as Story 5.16 gates the Game settings. `replay_warnings` gains the rule «more views than the Class games». The Klasseøkt's own-scenario form shows the two Bryter of Story 5.16 with Replay-scoped help text, only while the flag is on. Play, `seat_state`, LLM prompt and Decision log already read the Game's snapshot settings (Story 6.21) and need no change.

## Boundaries & Constraints

**Always:**
- `REPLAY_EDITABLE` includes `info_visibility`. `judge_replay_template(settings, draft, *, kept_views=None)`: base views = draft's, else `kept_views` (the stored own template's), else the Class session's. Flag off: a draft that switches on a view that is off in that base is `info_visibility` `feature_disabled` (via `_shows_a_new_neighbour`); sent back unchanged or switched off is allowed. Malformed → `invalid`.
- Save refusal is 422 `invalid_replay_scenario` with `fields.info_visibility.code = feature_disabled`; the check endpoint answers the same error; locked → 409 first (unchanged 10.2 order).
- `replay_warnings(..., info_visibility_enabled)` adds `replay_neighbour_visible` (field `info_visibility`, `values {"view": side}`) per view on in the template and off in the Class settings; only while the flag is on (GET, check and save).
- A stored own view is kept when the Class settings change (the Replay's own field) and when the flag goes off (hidden, frozen at lock, as 5.16). A copy (`_copied_replay`) drops it while the flag is off.
- Frontend: `ReplayDraft.infoVisibility` only while `item.info_visibility_enabled`; `replayTemplateBody` sends it only then; own form renders the exported `InfoVisibilityFields` with Replay ids and help copy; read-only own rows add «Synlige naboer» only with the flag. All copy in `nb.ts` `[ASSUMPTION]`.

**Never:** no engine change, no migration, no play-screen or prompt change, no change of the default template (it follows the Class session), no flag check at Replay start (the read gate of 6.21 hides numbers when the flag is off), no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Flag on, view more | own, `info_visibility` upstream, Class off | stored; warning `replay_neighbour_visible` upstream; Class settings unchanged | — |
| Flag on, both | both on | two warnings | — |
| Same as Class | Class upstream, template upstream | no warning | — |
| Left out | draft without `info_visibility` | stored own's, else Class's | — |
| Flag off, new view | own, upstream on, stored off | nothing stored | 422 `invalid_replay_scenario` `info_visibility` `feature_disabled` |
| Flag off, kept | stored upstream, screen draft without the key | saved, upstream kept, no warning shown | — |
| Flag off, GET | stored upstream | `replay_warnings` without the visibility warning; screen shows no field or row | — |
| Copy, flag off | source own upstream | copy template views off | — |
| Replay with views | pinned template both on | snapshot settings both on; `seat_state.neighbour_numbers` filled; Decision log rows of all 4 Seats record them; flag off → none shown | — |
| Bad value | `{"upstream": "yes"}` | — | `info_visibility` `invalid` |

</intent-contract>

## Code Map

- `backend/app/engine/scenario.py:140,209,280,451` -- `ReplayTemplate.info_visibility`, default from settings, resolved into `GameSettings`, admitted by Play guard; read-only.
- `backend/app/modules/sessions/service.py` -- `REPLAY_EDITABLE` (~3237), `replay_warnings` (~3300), `judge_replay_template` (~3337), `_replay_to_store`, `check_replay_scenario`, `_copied_replay`, `get_session` replay warnings (~857); reuse `_shows_a_new_neighbour`, `VIEWS`, `info_visibility_enabled` (~468–486).
- `backend/app/modules/sessions/{routes.py save docstring, README.md}`.
- `backend/app/modules/replay/service.py:130,185` -- snapshot from `replay_settings(pinned template)`; unchanged.
- `backend/app/modules/games/views.py:64` `build_seat_state` -- neighbour numbers from snapshot settings behind the flag; unchanged.
- `frontend/src/modules/sessions/{replay-scenario.ts, replay-scenario-block.tsx, settings-form.tsx (InfoVisibilityFields ~434), settings.ts (InfoVisibilityDraft), sessions.ts (infoVisibilityText)}`; `frontend/src/copy/nb.ts` `sessions.replay`.
- Tests: `backend/tests/sessions/test_replay_own.py` (helpers), `tests/games/test_neighbour_numbers.py` (`flag`, `NEIGHBOURS`), `tests/replay/test_start.py` (`passed`, `start`); `frontend/src/modules/sessions/replay-scenario.test.ts`; `frontend/e2e/class-session-replay.spec.ts`, `class-session-info-visibility.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/service.py` -- editable field, flag gate, kept views, warning rule, copy rule.
- `backend/app/modules/sessions/routes.py`, `README.md` -- document.
- `backend/tests/sessions/test_replay_info_visibility.py` (new) -- warning rule, judging with flag on/off, kept views, pin, api save/check/GET/copy.
- `backend/tests/replay/test_info_visibility.py` (new) -- one Replay with views: snapshot, `seat_state`, Decision log, flag off.
- `frontend/src/modules/sessions/settings-form.tsx` -- export `InfoVisibilityFields` with `idPrefix`, `help`, `notes`.
- `frontend/src/modules/sessions/replay-scenario.ts` -- draft/body/rows/warning text with the flag.
- `frontend/src/modules/sessions/replay-scenario-block.tsx` -- the field in the own form; flag passed.
- `frontend/src/copy/nb.ts` -- help and warning copy; `open-assumptions.md` draft-copy line.
- `frontend/src/modules/sessions/replay-scenario.test.ts` -- draft/body/rows/warnings with flag on and off.
- `frontend/e2e/class-session-replay.spec.ts` -- flag on: switch a view, see the warning, save, reload; flag off (answer rewritten): no field; axe 320/1440 both states.

**Acceptance Criteria:**
- Given the flag off, when a Lecturer opens the own Replay scenario, then no Information visibility field, row or warning is shown, and a PUT switching a view on answers 422.
- Given the flag on, when the Lecturer edits the own scenario, then «Synlige naboer» shows prefilled from the Class session, can differ from it, is stored in the template and pinned at the lock.
- Given more views than the Class games, when the form is shown or saved, then a warning names the view and says it probably makes the Replay easier.
- Given a Replay from a template with views on, when the Student plays, then the snapshot carries them, `seat_state` shows the neighbour numbers, and the Decision log records what each of the four Seats saw.
- Given the form at 320 and 1440 px with axe, flag on and off, then both pass, and the field's help text states its scope.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Two layers (sonnet, per the runbook): blind hunter and edge-case hunter. Both hand-backs failed; findings were read from `review-{blind,edge}-10-9.md` in the scratchpad.
- verdicts: 15 findings — high 0, medium 0, low 13, false 2, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind 1) the 10.2 line in `open-assumptions.md` still said Information visibility follows the Game settings — trimmed to «the chain and capacity».
  - `[low]` `[patch]` (blind 2) `_replay_to_store` docstring said visibility follows the Game settings — now says it is the Replay's own and kept.
  - `[low]` `[patch]` (blind 3) the Replay help line («ikke vist at innstillingen gir bedre læring eller lavere kost») contradicted the warning's «trolig lettere» — that sentence removed from the Replay help line.
  - `[low]` `[reject]` (blind 4) the walkthrough's «Ikke like for like.» reasons do not name a different visibility — not in this story's AC; adding a reason is a new branch in the 10.7 renderer for a flagged, cut-list setting.
  - `[low]` `[reject]` (blind 5) only more views warn, and the Replay stops following the Class views silently — the AC asks for the «more» warning; following stops by recorded decision (1), and the help line says the field can differ.
  - `[low]` `[reject]` (blind 6) own templates stored before 10.9 keep the views they had — they equal the Class views at their last save, which is what the form shows; recorded decision (1).
  - `[false]` `[reject]` (blind 7) `replay_warnings` defaulting to no visibility warning — both callers (`get_session`, `judge_replay_template`) pass the flag; the default fails closed, as AD-17 asks.
  - `[low]` `[patch]` (blind 8) the warning notes under the switches were not in their description — the switches' `aria-describedby` now includes the notes; the identical names in the two blocks are told apart by their labelled regions (rejected part).
  - `[false]` `[reject]` (blind 9) the e2e assumes the flag is on — `feature_info_visibility` defaults to true and the local stack runs with it, as Story 5.16's spec; the flag-off screen is tested by rewriting the answer.
  - `[low]` `[reject]` (blind 10) test hygiene (shared fixtures, `None` session in the pin test, `[::2]`, no flag-off-at-start test, no prompt test) — the repo's established patterns; the read gate and the prompt's use of `seat_state` are pinned by Story 6.21's tests.
  - `[low]` `[reject]` (blind 11) decisions and copy not under «Choices … to confirm» — they are in the assumptions bullet and the draft-copy list, and in this spec's decisions.
  - `[low]` `[reject]` (edge 1) a partial `info_visibility` map resets the omitted view — the same map-replace rule as Story 5.16 (its triage); the screen always sends both views.
  - `[low]` `[patch]` (edge 2) an unknown `view` was worded as upstream — an unknown view now gets the generic warning line; Vitest case added.
  - `[low]` `[patch]` (edge 3) = blind 2.
  - `[low]` `[reject]` (edge 4) an untouched prefill is stored as the Replay's own and later Class changes do not reach it — recorded decision (1).

## Design Notes

Founder-level decisions: (1) An own template's views are the Replay's own once set: they no longer follow later changes of the Class settings (10.2's rebase keeps them), so the form shows what the Replay runs. (2) The flag-off refusal stays inside the Replay's own error shape (`invalid_replay_scenario` with field code `feature_disabled`) so the screen places it like every other Replay error. (3) The default scenario keeps following the Class session's views. (4) With the flag off a Replay is not stripped of stored views at start; the existing read gate shows no numbers (same as Class games under 5.16/6.21). (5) One warning per view the Class games do not show.

## Verification

**Commands:**
- `uv run pytest -n0 tests/sessions/test_replay_info_visibility.py tests/sessions/test_replay_own.py tests/replay/test_info_visibility.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/sessions` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** Behind `FEATURE_INFO_VISIBILITY` an own Replay scenario has its own Information visibility. `info_visibility` is editable in `replay_template` (`REPLAY_EDITABLE`), prefilled from the Class session, kept as stored when the Class settings change, stored in the template and pinned at the lock by Story 10.1's provider. With the flag off a view switched on is refused (422 `invalid_replay_scenario`, `info_visibility` `feature_disabled`; the check answers the same error), a stored view is kept and hidden, no warning shows, and a copy leaves it out. `replay_warnings` gains `replay_neighbour_visible` (one per view the Class games do not show, only with the flag on). The Klasseøkt's own-scenario form shows the two Bryter of Story 5.16 («Synlige naboer») under Replay ids with a Replay-scoped help line and the warnings; the read-only list adds the row. Play needed no change: the Replay's snapshot carries the views, and `seat_state`, the AI players and the Decision log read them (Story 6.21).

**Files.**
- `backend/app/modules/sessions/service.py`: editable field, flag gate, `kept_views`, warning rule, copy rule, docstrings.
- `backend/app/modules/sessions/{routes.py,README.md}`: documented.
- `backend/tests/sessions/test_replay_info_visibility.py` (new): the warning rule, judging with the flag on and off, kept views, the pin, the api's save, check, GET and copy.
- `backend/tests/replay/test_info_visibility.py` (new): one Replay with both views: snapshot, `seat_state`, Decision log of all four Seats, flag off.
- `frontend/src/modules/sessions/{settings-form.tsx (InfoVisibilityFields exported; idPrefix, help, notes), replay-scenario.ts, replay-scenario-block.tsx, sessions.ts}`, `frontend/src/copy/nb.ts`: the field, rows, body and warning text.
- `frontend/src/modules/sessions/replay-scenario.test.ts`, `frontend/e2e/class-session-replay.spec.ts`: unit and e2e tests.
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated (route docstring).
- `open-assumptions.md`: decision and draft-copy lines. `epic-10-context.md`: recompiled (stale against `open-assumptions.md`).

**Decisions the founder would otherwise take.** (1) Once saved, an own template's views are its own: they no longer follow later Class changes. (2) The flag-off refusal uses the Replay's own error shape (`invalid_replay_scenario` with field code `feature_disabled`), not a top-level `feature_disabled`. (3) The default scenario keeps following the Class session's views. (4) With the flag off a Replay is not stripped of stored views at start; the read gate shows no numbers. (5) One warning per view the Class games do not show; fewer views do not warn. (6) The Replay help line leaves out 5.16's «not shown to give better learning or lower cost», which contradicts the «probably easier» warning. (7) A copy with the flag off leaves the views out, as `_copied_settings`. (8) Implementation in this context, not a sub-agent (runbook). Two review layers.

**Review.** 15 findings (blind and edge case, sonnet): 6 patched (all low: the stale assumption line, the `_replay_to_store` docstring, the help line, the notes in `aria-describedby`, unknown-view wording; one duplicate), 0 deferred, 9 rejected (7 low, 2 false), reasons in the triage log. `followup_review_recommended: false` (no medium or high patched). Patched by verdict: low 5 entries.

**Verification.** Full backend suite (`-n 8 --maxprocesses=8`): 3160 passed in 132 s. ruff check and format clean. Frontend typecheck, `check:copy`, `lint:colours` and build passed. Full Vitest: one run (alongside the backend suite and the build) had 1 failure of 1043. Its name was not captured, and four reruns passed 1043 of 1043. Stack rebuilt after the last frontend change. Playwright `--workers=4`: class-session-replay, class-session-info-visibility, homes and the five replay specs passed 75 of 75. The play-screen specs (chain-band, graph-over-table, order-field, order-confirm, game-start, game-card, cost-panel, guided-week) passed 82 of 82. axe ran at 320 and 1440 px with the flag on and off, and at 200 % text with the flag on. New test times: `test_a_replay_with_views_shows_and_records_the_neighbours_numbers` 1.56 s (over 1 s: it locks a session, starts a Replay and places one Order). The api test took 0.55 s, and the pure tests under 0.05 s each.

**Residual risks.** A Lecturer who raises the Class views after saving an own scenario keeps the Replay's fewer views without a warning (decision 1). A view stored while the flag was on survives a later flag-off. It is hidden and frozen, as in Story 5.16.
