---
title: 'Story 6.21: See the neighbour numbers the Lecturer switched on (cut list, behind FEATURE_INFO_VISIBILITY)'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '60cb4e9fd24af2771c0e6e88d07f54a03695655e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-16-set-information-visibility.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 5.16 stores Information visibility (`GameSettings.info_visibility`, upstream/downstream) in every Class game's snapshot, but `seat_state.neighbour_numbers` is always empty and nothing shows a neighbour's numbers (FR-83, UX-DR24).

**Approach:** The engine computes a Seat's neighbour numbers from the open Week's state and the snapshot's views. `games.views.build_seat_state` fills them only while `FEATURE_INFO_VISIBILITY` is on, so the play screen, the Decision log's `state_seen` and the AI player all read the same `SeatState`. The Kjedebånd draws them at the neighbour's end. A new `player_order/v2` prompt lets an LLM player read them.

## Boundaries & Constraints

**Always:**
- Engine `neighbour_numbers(settings, state: WeekState, role)` is pure. It returns `NeighbourNumber`s for each view that is on: upstream first (the Role after `role` in `settings.roles`), then downstream (the Role before). Each view gives inventory, then backlog, with `week = state.week`, read from that neighbour's Seat in the open Week. The last Role (Fabrikk) has no upstream and the first (Detaljist) no downstream, so those give nothing. `seat_view` and `seat_detail` stay unchanged. Engine coverage stays at 100 %.
- `build_seat_state(..., neighbours: bool | None = None)`: None reads `get_settings().feature_info_visibility`. Flag off, or both views off, gives `neighbour_numbers == []`. Every caller goes through it: the play/Hjem view, `place_order`'s `state_seen`, and `turns.pending_turn`, which feeds the AI.
- `checks._decision_log` rebuilds the expected state with `neighbours=bool(seen.neighbour_numbers)`, so a flag change after play is no violation. Numbers on a Game whose views are off still differ.
- No `SeatState.schema_version` change, because the field exists since Story 1.8. No migration. No change to `RULES_VERSION` or the golden traces.
- LLM: `build_inputs` adds `neighbours`, an English sentence from `seat_state.neighbour_numbers` alone. With none, it reads exactly `You do not see the numbers of any other business.` New `prompts/player_order/v2.md` = v1 with that sentence replaced by `$neighbours`. v2 is added to `hashes.json`, and v1 is untouched. A config on v1 ignores the extra value. Model configs and the mock seed stay on v1.
- Kjedebånd (frontend): `BandState` adds `neighbour_numbers`. While a view shows, that end's label reads «Distributør, Uke 11». Two more labels, «Lager 12» and «Restordre 3» (weight 400, ink), sit at that end on the middle row and wrap under the band on their own side by the layout's existing rule. Nothing ever overlaps. The screen-reader sentence adds «. Distributør, Uke 11: Lager 12, Restordre 3» per neighbour, upstream first, after the Seat's own numbers. Roles come from `roleName`, and only a number whose Role is an end neighbour is drawn. Copy goes in `nb.games.play.band`, marked [ASSUMPTION].

**Never:** No neighbour Orders, cost, Supply line or any other quantity. No Seat other than the direct neighbour. No client arithmetic. No change to «class-of-1994» or to the Klasseøkt setting (Story 5.16). No Replay (Story 10.9). No edits to model configs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Off | views off, flag on | `neighbour_numbers == []`; band as Story 6.9 | — |
| Flag off | views on in snapshot, flag off | `[]` on play, Hjem and AI; band unchanged | — |
| Upstream | Grossist, upstream on, Uke 6 | `[{distributor,6,inventory,n},{distributor,6,backlog,m}]` = Distributør's own inventory/backlog in Uke 6 | — |
| Both, Fabrikk | factory, both on | only the distributor's two numbers | — |
| Both, Detaljist | retailer, both on | only the wholesaler's two numbers | — |
| Decision log | played with views and flag on | `state_seen.neighbour_numbers` as shown; `verify_finished` ok, also after the flag goes off | — |
| LLM | wholesaler, both on | prompt v2 names the distributor (supplier) and retailer (customer) inventory and backlog | v1 renders unchanged |

</intent-contract>

## Code Map

- `backend/app/engine/view.py:22` `NeighbourNumber`, `:99` `seat_view` (its docstring says the numbers stay empty: update it); add `neighbour_numbers`; export from `backend/app/engine/__init__.py:45,74`. Tests go in `backend/tests/engine/test_view.py`.
- `backend/app/engine/settings.py:55` `InfoVisibility`; `settings.roles` runs downstream first (`:41`).
- `backend/app/modules/games/views.py:56` `build_seat_state` — the one fill. Callers: `:137` `seat_state`, `commands.py:1203` (`state_seen`), `turns.py:84`, `checks.py:162`.
- `backend/app/modules/games/schemas.py:190` `SeatState` docstring ("empty until …"): update it.
- `backend/app/modules/players/llm.py:120` `build_inputs`; `backend/app/ai/prompts/player_order/v1.md:3`; `hashes.json` (run `uv run python -m app.ai.cli prompts lock`). Tests: `tests/players/test_llm_prompt.py`, `tests/ai/test_prompt_files.py`.
- Flag: `get_settings().feature_info_visibility`. Tests set it as `tests/sessions/test_info_visibility.py:37` `flag()` does.
- Shared fixtures: `tests/games/helpers.py` (`played_once`, `play_to_end`). Class-session api flow: `tests/sessions/test_play.py` (`play`, `played_to`, `keys`), `test_info_visibility.py` (`save`, `confirmed`, `sweep.run(START + MINUTE)`), and `test_start_game.py` (`task_done`, `start`).
- Frontend: `src/modules/games/chain-band.ts` (`BandState`, `bandEnds`, `bandLabels`, `bandSentence`), `src/components/charts/chain-band-layout.ts` (`BandLabels`, `LabelKey`, the `wanted` list at `:196`), `chain-band.tsx` (renders labels generically), `chain-band-view.tsx`, and `src/copy/nb.ts:1774`.
- Frontend tests: `src/modules/games/chain-band.test.ts` (the scale test over `fixtures/chain-band-classic.json`; its 120 states give each neighbour's numbers by Role and Uke) and `e2e/chain-band.spec.ts` (`openPlay`, `labelProblems`, `expectAccessible`).

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/view.py`, `__init__.py`, `tests/engine/test_view.py` -- `neighbour_numbers` and its tests (each view, both, the ends, off).
- `backend/app/modules/games/views.py`, `checks.py`, `schemas.py` -- the fill behind the flag, the check rule, the docstrings.
- `backend/tests/games/test_neighbour_numbers.py` (new) -- a simulation Game with both views on (flag on, `played_once`): `seat_state` per Role in an open Week equals the neighbours' own inventory and backlog, and holds no other Role and no other quantity. Flag off gives `[]`. The Decision log rows carry the numbers, and `verify_finished` passes with the flag on and off.
- `backend/tests/sessions/test_neighbour_numbers.py` (new) -- one api test: a Class session with upstream on, locked and started, played to Uke 6. `GET /api/me/games/{id}/play` gives each Role exactly its upstream neighbour's two numbers (none for the Fabrikk), and no key of the envelope names Orders, cost or Supply line in `neighbour_numbers`. With the flag off, the same call gives `[]`.
- `backend/app/modules/players/llm.py`, `app/ai/prompts/player_order/v2.md`, `hashes.json`, `tests/players/test_llm_prompt.py` -- the `neighbours` value, and a v2 rendered with and without numbers.
- `frontend/src/modules/games/chain-band.ts`, `src/components/charts/chain-band-layout.ts`, `src/copy/nb.ts` -- labels and sentence.
- `frontend/src/modules/games/chain-band.test.ts` -- the scale test with both views on (every Uke, all four Roles, 288/328 px, 13/26 px text), plus labels and sentence for one end and for both ends.
- `frontend/e2e/chain-band.spec.ts` -- Uke 30 with both views on at 320, 360 and 1440 px: the band fits, the labels are apart and readable, and axe passes (one check per width). One 360 px test asserts the end label, the numbers and the sentence.

**Acceptance Criteria:**
- Given the flag off or both views off, when the play screen renders, then the Kjedebånd shows no neighbour numbers and `seat_state.neighbour_numbers` is empty.
- Given the flag on and a view on, when the Grossist's play screen renders, then the Distributør's «Lager» and «Restordre» show at the left end under «Distributør, Uke N» (the Detaljist's at the right for the downstream view). Screen readers hear them after the own numbers.
- Given both views on, when the 6.9 scale test runs, then every Uke fits at 320 and 360 px with no overlapping labels, and axe finds nothing at 320, 360 and 1440 px.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: the runbook allows two reviewers, so only the blind hunter and the edge-case hunter ran. The verification-gap and intent-alignment layers were skipped.
- verdicts: 22 findings — high 0, medium 0, low 18, false 4, maybe-false 0
- findings (blind):
  - `[low]` `[reject]` The check rebuilds with `neighbours=bool(seen.neighbour_numbers)`, so it cannot detect numbers stripped from a row. A strip needs an edit past the append-only triggers. The fix would store the flag per Game or row, which means a new column and a migration. Added numbers are caught (`test_numbers_a_game_without_views_never_showed_fail_the_check`). This is a recorded Design Notes decision.
  - `[low]` `[reject]` The flag is read live, so toggling it mid-game changes what Seats see from one Week to the next. That is AC1's "flag off → none", and a Design Notes decision. Only an operator toggles it.
  - `[false]` `[reject]` `flag()` would leak a cached `get_settings`. `tests/conftest.py::_fresh_settings` runs `reset_caches()` (which includes `get_settings.cache_clear()`) before and after every test.
  - `[low]` `[patch]` The LLM text said "two numbers of each business next to you", even with one view on. Fixed: it now says "the business next to you listed here" (or "businesses"). Asserted.
  - `[low]` `[patch]` `values.get(q, 0)` would write a 0 the state never held. Fixed: a missing quantity is left out, as the web does. Asserted.
  - `[low]` `[reject]` Supplier and customer come from the Classic `ROLES` order. `roles` is not editable (`EDITABLE_SETTINGS`), and the module already assumes the Classic chain (`CUSTOMER_FACING`, `PRODUCING`).
  - `[false]` `[reject]` "Every LLM game moves to v2 at deploy". `gateway.run` resolves the version from the model config's pin (`_resolve`). Only the config-less `preview` takes the newest file. Configs stay on v1.
  - `[low]` `[reject]` The engine raises a bare `KeyError` when the state and settings disagree. Every caller passes the same Game's states and snapshot, so this is unreachable.
  - `[low]` `[patch]` A block row wider than the band could start at a negative x. Fixed: x is clamped at 0. Every Uke fits at 288 px and 26 px text.
  - `[low]` `[patch]` There was no layout test with one view on. Added: every Uke, each side, 288/328 px, 13/26 px text, and the plain end label stays on the other side.
  - `[low]` `[reject]` The e2e tests stub the api. The real fill, order and week are pinned by `tests/sessions/test_neighbour_numbers.py` and `tests/games/test_neighbour_numbers.py`. Every play e2e test stubs the envelope (Story 6.9 pattern).
  - `[low]` `[reject]` The sessions test imports helpers from other test modules. This is the existing pattern (`test_play.py`, `test_info_visibility.py`). Moving them into conftest is wider than this story.
  - `[low]` `[patch]` The README said the Decision log "reads" the numbers. Now it says they are recorded in `state_seen`, and that a v1 config does not print them.
- findings (edge case):
  - `[low]` `[reject]` The check cannot see stripped numbers. Same root cause and reason as the first blind row.
  - `[low]` `[reject]` A flag flip between `pending_turn` and `place_order` could make `state_seen` differ from the prompt. This is a narrow operator race. v1 configs do not print the numbers anyway.
  - `[low]` `[reject]` Supplier and customer come from `ROLES`, not `settings.roles`. Same as the blind row.
  - `[low]` `[patch]` A missing quantity was written as 0. Same fix as the blind row.
  - `[low]` `[patch]` A block wider than the band could get a negative x. Same fix as the blind row.
  - `[low]` `[patch]` Stacked blocks had only 2 px between them. Fixed: the second block gets the same 0.4 em space above it.
  - `[false]` `[reject]` Numbers would silently not be drawn when `seatRoles` lacks the own Role. The envelope's `game.seats` always holds all four Roles, the viewer's included.
  - `[low]` `[reject]` (claim) The spec says the numbers sit on the middle row, but the code draws a block under the band. This was a deliberate change after the builder's own 360 px screenshot, recorded in Design Notes. The only fix would be a spec edit, and the intent-contract is read-only.
  - `[false]` `[reject]` (claim) "A flag change after play is no violation" implies the check is faithful. The claim holds as written. Stripped numbers are the first blind row.

## Design Notes

Founder-level calls, taken here with no human in the loop:
- The flag is read at read time, so switching it off hides numbers even for a snapshot that has views on (AC1, "or").
- The checker accepts the state as it was recorded, with or without numbers.
- Draft copy [ASSUMPTION]: the end label «Distributør, Uke 11» replaces the plain Role while a view shows. The numbers use the spine terms «Lager» and «Restordre», and both always show, zero included.
- Band layout, changed from the plan after the builder's own screenshot at 360 px: placed one by one, the numbers and the end label split up. «Lager 14» stayed on the middle row while «Restordre 0» and «Distributør, Uke 11» wrapped apart. So a neighbour whose numbers show gets a block under the band, kept together. The end label is on its own row, then its «Lager», «Restordre» row (it wraps only if the width needs it). Upstream blocks keep to the left edge and downstream blocks to the right, side by side when both fit, else stacked. The row-0 end label is not drawn for that end. The 6.9 non-overlap and fit checks are unchanged and pass.
- LLM: a v2 prompt, with configs left on v1. Calibrated configs keep the text they were measured with. An operator moves a config to v2 with the existing `config edit` path. Until then an LLM player does not read the numbers, although its `seat_state` and `state_seen` carry them.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/engine/test_view.py tests/games/test_neighbour_numbers.py tests/sessions/test_neighbour_numbers.py tests/players/test_llm_prompt.py tests/ai/test_prompt_files.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run && npm run build` -- pass
- `cd frontend && npx playwright test e2e/chain-band.spec.ts` plus the play-screen specs -- pass

## Auto Run Result

Status: done

**Summary.** Behind `FEATURE_INFO_VISIBILITY`, each Seat now sees the inventory and backlog of the neighbours the Lecturer switched on (FR-83, UX-DR24).
- **Engine.** `neighbour_numbers(settings, state, role)` gives the upstream neighbour, then the downstream one, with inventory then backlog of the open Week. The Fabrikk has no upstream neighbour and the Detaljist no downstream one.
- **`games.views.build_seat_state`.** It fills `SeatState.neighbour_numbers` while the flag is on, so the play envelope, Hjem, the AI turn and the Decision log `state_seen` carry the same numbers. There is no schema or version change and no migration.
- **The finished-game check** rebuilds a state with or without numbers, as it was recorded.
- **LLM.** `build_inputs` adds `neighbours`. The new prompt `player_order/v2` (locked; v1 untouched) prints the neighbours, or exactly v1's sentence when there are none. Model configs and the mock seed stay on v1.
- **Kjedebånd.** For each neighbour shown, a block sits under the band at that neighbour's side: «Distributør, Uke 11» over «Lager 14  Restordre 0». Upstream keeps to the left edge and downstream to the right. The two blocks sit side by side when both fit, else stacked. The screen-reader sentence adds «. Distributør, Uke 11: Lager 14, Restordre 0» after the own numbers. Copy is draft [ASSUMPTION].

**Files.**
- `backend/app/engine/{view,__init__}.py`: `neighbour_numbers`.
- `backend/app/modules/games/{views,checks,schemas}.py`: the fill behind the flag, the check rule and the docstring.
- `backend/app/modules/players/llm.py`, `app/ai/prompts/player_order/v2.md` (new), `hashes.json`: the prompt value and v2.
- `backend/app/modules/sessions/README.md`.
- Backend tests:
  - `tests/engine/test_view.py`
  - `tests/games/test_neighbour_numbers.py` (new)
  - `tests/sessions/test_neighbour_numbers.py` (new)
  - `tests/players/test_llm_prompt.py`
  - `tests/test_sim_prompt.py` (the newest file is now v2)
- `frontend/src/modules/games/chain-band{.ts,-view.tsx}`, `src/components/charts/chain-band-layout.ts`, `src/copy/nb.ts`: labels, blocks and sentence.
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated (docstring only).
- `frontend/src/modules/games/chain-band.test.ts` and `frontend/e2e/chain-band.spec.ts`: the tests.

**Review.** Two layers reported 22 findings: low 18, false 4.
- Patched (low, 6 entries):
  - the LLM wording with one view
  - a missing quantity written as 0
  - the block x clamp
  - the stacked-block gap
  - a one-view layout test
  - the README wording
- Deferred: none.
- Rejected, with reasons in the triage log:
  - stripped numbers are invisible to the check
  - the flag is read live
  - the Classic `ROLES` order
  - the bare `KeyError`
  - the stubbed e2e
  - the test imports
  - the flag race
  - the spec's "middle row" wording
- Follow-up review: false. Nothing patched was medium or high.

**Verification.**
- Backend: full suite 2770 passed in 65.8 s. `ruff check` and `ruff format --check` are clean.
- Frontend: `tsc`, Vitest (699 passed), `check:copy`, and the Next build (the compose frontend image, rebuilt after the patches).
- Playwright after the patches: `chain-band`, `order-field`, `order-confirm`, `graph-over-table`, `week-transition`, `seat-status` and `test-game` all passed (65). Before the patches, `order-failures`, `week-table`, `week-advance`, `guided-week`, `cost-panel`, `game-start` and `game-end` also passed (119 in that run).
- New tests over 1 s:
  - `tests/sessions/test_neighbour_numbers.py`: 2.9 s call plus 3.6 s setup (one Class session locked, started and played to Uke 6).
  - `tests/games/test_neighbour_numbers.py`: the views test takes 1.2 s the first time it plays its 10-Week Game. The tamper test reuses the shared Classic Game (6.7 s only when run alone).
  - There are no fixed sleeps.
- The builder looked at screenshots of the band with both views at 320, 360 and 1440 px. No independent visual reviewer was run; the orchestrator runs its own visual check.

**Residual risks.**
- An LLM player prints the numbers only once its model config references `player_order/v2`. Today every config is on v1.
- Stripped neighbour numbers in a stored `state_seen` pass the finished-game check.
- Switching the flag mid-game changes what Seats see from the next read.

Visible screens changed: the play screen's Kjedebånd, only when the flag is on and the Game's snapshot has a view switched on.
