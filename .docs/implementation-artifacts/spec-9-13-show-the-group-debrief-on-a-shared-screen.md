---
title: 'Story 9.13: Show the Group debrief on a shared screen'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'b1439ac0410841c07dd9ebcf272ab48a47f9500f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Group debrief (Stories 9.11, 9.12) has no way to put the chain on one screen in the room: every chart lives on each Student's own page, beside their Explanation and moments, which must never be projected (FR-74, FR-43).

**Approach:** A joined Student opens «Delt skjerm: hele kjeden» from their Debrief page: their own session in display mode (no header with their name), in the laptop layout, fed only by a new anonymised endpoint `GET /api/debriefs/{id}/shared` that returns the chain by Role, never a name, an Explanation, an answer or a moment, and nothing at all of the chain while a joined Student has not sent.

## Boundaries & Constraints

**Always:**
- `GET /api/debriefs/{id}/shared` (`getSharedDebrief`, policy `debriefs.own`): the caller must be a Student of the Debrief's game (`service._own`) and joined to a shared session (member without a `debrief_alone` row). Anyone else, a Personal debrief, an alone Student, a non-Student, an unknown or malformed id: the same 403 `forbidden` envelope (UX-DR59, AD-12).
- `SharedOut`: `debrief_id`, `class_session_id`, `game_number`, `step` (the pointer), `locked: bool`, `chain: SharedChainOut | null`. `locked` is true and `chain` null while any joined Student has no saved Explanation in the Class session (FR-43, AD-21). `SharedChainOut`: `last_week`, chain `holding_cost`/`backorder_cost`/`total_cost`, `roles` Fabrikk first; `SharedRoleOut`: `role`, `amplification`, `holding_cost`, `backorder_cost`, `total_cost`, `weeks: [SharedWeekOut]` (`week`, `order`, `incoming_order`, `inventory`, `backlog`, `supply_line`, `net_inventory`, from the Decision log's `state_seen`). Costs and Forsterkning from the stored facts set's chain part (AD-7, read via `games.fact_set`, never rebuilt). No `str` field anywhere in the schema (Role is an enum).
- The web route `/delt-skjerm/[debriefId]` (GuardedPage `home`, PageShell without `user`): h1 «Delt skjerm: hele kjeden», «Spill N», the group's step line, and either the locked line (no names) or: Ukeskrubber local to the device (starts at the last Uke) over the four-Role Kjedebånd (no own Role marked) with a polite reading after 300 ms; «Netto lager» per Role (Fabrikk at the top, the shared `NetOverGame` with a dashed marker at the chosen Uke) with «Vis som tabell» (Rolle × Uke Netto lager); «Kostnad, kr» per Role through `ChainBill` (Lager, Restordre, Sum per Role, «Kjeden» total). The query key sits under `debriefsKey`, so `debrief:<id>` refetches it. The only debrief/game data call is the shared endpoint.
- The Debrief page shows the link «Delt skjerm: hele kjeden» to a joined Student (`group.joined`, not alone) under the home link.
- Copy in `nb.ts`, draft `[ASSUMPTION]`; numbers via the Norwegian formatter.

**Never:** no names, Explanations, reflection answers, moments, own-Role marking or free text on the endpoint or the screen; no synced scrubber; no new table or migration; no change to 9.11/9.12 step rules; no edit of `group.tsx`/`reveal-step.tsx` (another agent's uncommitted work); no growth of `test_group.py`/`test_group_alone.py` beyond one-line fixes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Locked | A, B joined; A sent, B not | A: 200 `locked: true`, `chain: null` | — |
| Open | both sent | 200 `locked: false`, four Roles Fabrikk first, costs summing to the chain total | — |
| Late joiner | C joins at pointer 2 without Explanation | locked again until C sends | — |
| Not joined | C never joined; C went alone; Personal debrief; Lecturer; outsider; unknown id | identical 403 `forbidden` | — |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/service.py` -- `_own:361` (whose Debrief), `_group:257` (joined = members − alone), `_chain:674` (Decision log per Role, Fabrikk first via `reversed(settings.roles)`), `require_explanation:526`; add `shared_mine`.
- `backend/app/modules/debrief/schemas.py:137-176` -- `ChainWeekOut`/`ChainRoleOut` pattern; add `SharedWeekOut`, `SharedRoleOut`, `SharedChainOut`, `SharedOut`.
- `backend/app/modules/debrief/routes.py:133 _answer`, `:240` step route pattern; add the route and docstring lines; `README.md`.
- `backend/app/analysis/facts.py:125-157` -- `RoleFacts` costs, `ChainFacts.total_cost`.
- `backend/tests/debrief/test_group.py:49 played()`, `tests/debrief/test_debrief.py` (`open_`, `refused`), `tests/classes/test_staff.call`, `tests/sessions/test_dates.OUTSIDER`.
- Frontend: `modules/debrief/chain-step.tsx` (`chainBandInput`, `chainReading`, `FourRoleBand`), `components/charts/net-over-game.tsx` (add `marker`), `components/chain-bill.tsx` (add `title`), `modules/games/result.ts:34 gameEnd` (row/bar pattern), `components/week-scrubber.tsx`, `modules/identity/page-shell.tsx` (PageShell without user = no name), `modules/debrief/debrief-page.tsx:140` (link), `app/(app)/debrief/[sessionId]/page.tsx` (route pattern), `copy/nb.ts` (`debriefEntry.group`).
- E2E: `e2e/debrief-alone.spec.ts` (two-Student setup with `liveClassGame`, `live()`), `e2e/support/classes.ts expectAccessible`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/debrief/{schemas,service,routes}.py`, `README.md` -- the endpoint, schema and `shared_mine`.
- `backend/tests/debrief/test_shared.py` (new, module-scoped game) -- matrix rows; a schema test walking `SharedOut.model_json_schema()` that no property is named like a person or text (`user_id`, `name`, `text`, `explanation`, `answer`, `moments`, `members`) and no property is a plain string; a response with a known chain total.
- `frontend/src/components/charts/net-over-game.tsx`, `components/chain-bill.tsx` -- optional `marker`, `title`.
- `frontend/src/modules/debrief/{chain-step.tsx,api.ts,shared-screen.tsx (new),debrief-page.tsx}`, `app/(app)/delt-skjerm/[debriefId]/page.tsx` (new), `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}` -- the screen, hook, link; `chainBandInput` takes an optional own Role.
- `frontend/src/modules/debrief/debrief.test.ts` -- Vitest for the pure shared-screen helpers (cost rows Fabrikk first with bars, net table rows).
- `frontend/e2e/debrief-shared.spec.ts` (new) -- two Students: Sara opens and Ida joins; Sara's shared screen at 1440 px shows the locked line; Ida sends over the api; the screen unlocks without reload (after `data-live`); band, four net charts, cost table with Lager/Restordre and «Kjeden» total equal to the game result's; scrubber keys move only this screen; only `/shared` among `/api/debriefs`/`/api/games` requests; axe at 1440 and 320 px; a Lecturer and an unknown id get the same 403.

**Acceptance Criteria:**
- Given a joined Student in a Group debrief, when they open «Delt skjerm: hele kjeden», then the page shows the chain, Netto lager per Role, «Kostnad, kr» per Role with Lager and Restordre beside each total, and the chain total (e.g. «Kjeden … 2 266,00»), with no name on the page.
- Given the shared screen while a joined Student has not sent, then it states the reveal is locked until all joined Students have sent, without names, and shows no chart.
- Given the shared screen, when the last joined Student sends, then it refetches over `debrief:<id>` and shows the charts without reload.
- Given the shared screen at 1440 and 320 px, then axe passes, the page has no horizontal scroll, and every chart has its text or table alternative.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-13.md` and `review-edge-9-13.md` in the scratchpad. The diff left out the generated `openapi.json`/`schema.ts` and `.docs`.
- verdicts: 24 findings — high 0, medium 0, low 13, false 11, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind 1) A Student who loses access (leaves, drops out) while the screen is open kept the cached chart: `AccessDenied` showed only without data. Now any `forbidden` answer shows the denial page.
  - `[false]` `[reject]` (blind 2) Blank screen when `last_week < 1`. A finished game has at least one Uke; the shared read exists only for a finished game.
  - `[false]` `[reject]` (blind 3) `by_role[...]` may raise `KeyError`. The facts set is built from the same Game's Roles (`ChainFacts.by_role` holds all of them); `_chain` relies on the same.
  - `[false]` `[reject]` (blind 4) Fabrikk-first assumes the settings order. Same convention as step 3's `_chain`; the api test asserts the order.
  - `[false]` `[reject]` (blind 5) Chain Lager/Restordre sums may not add to the stored total. `RoleFacts` checks holding + backorder = week cost per row and `ChainFacts.total_cost` sums the same week costs, so they agree.
  - `[low]` `[patch]` (blind 6) Layout constants duplicated in the class string and the width maths; the step copy hard-coded 4 and 5. The grid now takes its columns from `LABEL_EM`/`GAP_EM`; `copy.step` takes `INDIVIDUAL_STEP` and `DEBRIEF_STEPS`.
  - `[low]` `[reject]` (blind 7) Each `debrief:` event makes every shared screen re-read the chain. One screen per group, a few reads per event; same pattern as step 3.
  - `[low]` `[patch]` (blind 8) The schema test only rejected `str` leaves. It now allows only ids, ints, flags, Decimals, the Role enum and the shared models (catches `Any`, `dict`).
  - `[low]` `[reject]` (blind 9) No `/shared` test for `debrief_not_open`/`held`, the sweep's dropout, `amplification` None. A joined Student's Debrief is always open; dropout and fallback go through the same alone row the `leave` test covers.
  - `[low]` `[reject]` (blind 10) axe not run on the locked state or the table at 320 px. The locked state is one paragraph; the table is the shared `ScrollRegion` pattern. Not worth more e2e time.
  - `[low]` `[reject]` (blind 11) Projector idle behaviour (session expiry, wake lock). Outside the story; the app's session rules apply to every page.
  - `[false]` `[reject]` (blind 12) Fixture re-export via `__all__` is a smell. It is the repo's pattern (`test_group_alone.py`).
  - `[low]` `[reject]` (blind 13) Thin unit coverage of rendering; a hard-coded tick in the marker test. The page is covered end to end; the tick follows the documented 20-step scale.
  - `[low]` `[patch]` (blind 14) «Gruppa» beside «Gruppen», «Hver svarer videre på egen enhet», README without a final newline. Copy now says «Gruppen» and «Nå svarer hver på sin egen enhet.»; README ends with a newline. The bare Uke numbers on the small charts are kept (the mockup's).
  - `[low]` `[patch]` (edge 1) Same as blind 1.
  - `[low]` `[reject]` (edge 2) The chain shows at pointer 2 once everyone has sent, ahead of step 3's pointer gate. Intended: the story's only lock is the Explanation (Design Notes); the screen is «hele kjeden».
  - `[false]` `[reject]` (edge 3) A non-open or held Debrief answers `debrief_not_open`/`held`, not `forbidden`. Unreachable: a Debrief session exists only once it has opened, and `_own` refuses any other game's id as `forbidden` before the availability check.
  - `[low]` `[reject]` (edge 4) At 320 px with 200 % text the charts get narrow (about 54 px). Still positive; 200 % text is a step-1 requirement and the shared screen is the laptop layout.
  - `[false]` `[reject]` (edge 5) Marker on a Role without Uker. Every Role of a finished game has every Uke.
  - `[false]` `[reject]` (edge 6) Same as blind 2.
  - `[false]` `[reject]` (edge 7) The scrubber's Uke may exceed a changed `last_week`. A finished game's `last_week` never changes.
  - `[false]` `[reject]` (edge 8) Same as blind 5.
  - `[false]` `[reject]` (edge 9, claim) The chain sums may not match. Same as blind 5.
  - `[low]` `[patch]` (edge 10, claim) README said «No write», but `games.fact_set` stores the facts set on its first use. Reworded: no Debrief write and no event; the facts set may be stored on first use, as in step 3.

## Design Notes

Decisions: the lock is the AC's (any joined Student without an Explanation); once open, the whole chain shows at any pointer, since the reveal gate is the Explanation and the screen is titled «hele kjeden». `step` is on the response so the screen can say where the group is. The screen is a separate page reached by a link, not a mode of the Debrief page, so no private query is ever loaded in that tab. `class_session_id` is on the response for the link back to the Student's own Debrief.

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief/test_shared.py` -- pass
- full backend `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-shared`, `debrief-*`, `homes`, `live-updates`, play-screen specs `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** «Delt skjerm: hele kjeden». A joined Student of a Group debrief gets the link «Delt skjerm: hele kjeden» under the home link on their Debrief page. It opens `/delt-skjerm/<debrief id>`: their own session in display mode (the page shell without the user, so no header with their name), laptop layout, reading only the new `GET /api/debriefs/{id}/shared` (`getSharedDebrief`, `service.shared_mine`). The endpoint answers a Student joined to the shared session (member without an alone row) with `SharedOut`: ids, game number, the shared pointer, `locked`, and, once every joined Student has a saved Explanation, the chain: every Role's Uker from the Decision log (Order, Ordre inn, Lager, Restordre, På vei, Netto lager), Fabrikk first, Forsterkning and cost per Role and the chain's cost from the stored facts set. The schema has no text field. Everyone else (not joined, alone, Personal debrief, staff, outsider, unknown or malformed id) gets the same 403 `forbidden`. The screen shows the locked line (no names) or: the four-Role Kjedebånd at a Uke the screen's own Ukeskrubber chooses (polite reading, a screen-reader table at that Uke), «Netto lager» per Role on one scale with the chosen Uke dashed and «Vis som tabell» (Uke × Role), and «Kostnad, kr» through Kjedens regning's table (Lager, Restordre, Sum per Role, «Kjeden» total). It refetches on `debrief:<id>` and announces the unlock; losing access while open shows the denial page.

**Files.**
- `backend/app/modules/debrief/{schemas,service,routes}.py`, `README.md`: `SharedOut` and its models, `shared_mine`/`_shared_chain`/`_joined`, the route.
- `backend/tests/debrief/test_shared.py` (new): the schema test and the matrix (locked, open, late joiner, alone, never joined, Lecturer, outsider, unknown/malformed id, Personal debrief).
- `frontend/src/modules/debrief/shared-screen.tsx` (new), `app/(app)/delt-skjerm/[debriefId]/page.tsx` (new): the screen and route.
- `frontend/src/modules/debrief/{api.ts,chain-step.tsx,debrief-page.tsx,debrief.test.ts}`: the hook and pure helpers, the band and reading take a chain without an own Role, the link, Vitest.
- `frontend/src/components/charts/net-over-game.tsx` (`marker`, `scaleWith`), `components/chain-bill.tsx` (`title`), `charts.test.tsx`; `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/debrief-shared.spec.ts` (new).

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), two review layers. (1) The lock is the AC's only: any joined Student without an Explanation; once open, the whole chain shows at any pointer (step 2 included). (2) Only joined Students may open it; a Student who goes alone, and staff, get `forbidden`. (3) The screen is a separate page reached by a link (same tab), not a mode of the Debrief page, so no private read happens in that tab; it shows no header with the Student's name. (4) The response carries `step` (the screen says where the group is) and `class_session_id` (the link back). (5) The four Netto lager charts share one scale; the chosen Uke is a dashed line on each. (6) «Kostnad, kr» reuses Kjedens regning's table, Fabrikk first, no Role marked as the viewer's. (7) The locked line gives no names or counts. All copy is draft `[ASSUMPTION]`.

**Review.** 24 findings (high 0, medium 0, low 13, false 11). Patched 5 root causes, all low (denial page also with cached data; layout constants and step copy from constants; a stricter schema test; copy wording and README newline; README wording on the facts-set write). Nothing deferred. The rest rejected with reasons in the triage log. followup_review_recommended: false (patched: low 5).

**Verification.**
- Backend after the patches: full suite `--maxprocesses=8` 2949 passed, 4 skipped (95 s); `ruff check`, `ruff format --check` clean. No migration.
- Frontend: typecheck, Vitest (55 files, 780 tests), `lint:colours`, `check:copy`, `next build` (in the lane image build) pass.
- Playwright on the lane stack (8081), rebuilt after the last frontend change, `--workers=4`: `debrief-shared` (1440 and 320 px with axe), every `debrief-*`, `homes`, `student-home`, `live-updates`, `game-end`, `order-confirm`, `week-advance`, `game-card`, `order-field`, `seat-status`, `guided-week`: 138 of 138.
- During the build, `debrief-shared` failed twice on real page overflow at 320 px (an `sr-only` class on a table, then a chart box lost after «Vis som tabell»); both fixed in the code. No test failed and then passed on rerun.
- Tests over 1 s: `test_shared.py::test_the_shared_screen_shows_the_chain_to_joined_students_only` about 1.8 s; `test_a_personal_debrief_has_no_shared_screen` about 1.4 s (each plays a two-Uke Class game through the api); the file's first test pays about 2.6 s of shared setup.

**Residual risks.** At 320 px with 200 % text the small Netto lager charts are narrow. Each `debrief:` event makes an open shared screen re-read the chain. The first shared read may store the game's facts set (as step 3 does). Draft copy awaits review.