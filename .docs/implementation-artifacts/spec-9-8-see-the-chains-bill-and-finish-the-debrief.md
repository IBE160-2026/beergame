---
title: 'Story 9.8: See the chain''s bill and finish the Debrief'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '839d7438ebeb249368dd497f60fa37b62bcc227c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Register the Debrief's Spillinnsikt link provider unconditionally and add the wiring test once epic-7 (Story 7.7) and epic-9 meet.
    evidence: |-
      register_insight_links exists only on epic-7. Until the merge, debrief.insight.register() registers only when games.service exposes the hook (one guard, marked TODO(merge epic-7)). The provider function insight.links is tested directly in tests/debrief/test_explanation.py. The team lead takes the change at the merge.
    location: >-
      backend/app/modules/debrief/insight.py:register
    severity: low
---

<intent-contract>

## Intent

**Problem:** Debrief step 4 ends after the moments: the Student never sees Kjedens regning with the Debrief's extra rows (restordre share, «Simulert, samme kunder», the AI-held share), cannot finish the Debrief (no `debrief` progress step, no summary), and staff cannot read a Student's Debrief summary (FR-44, FR-47, UX-DR36).

**Approach:** A pure `analysis.simulated.simulate(...)` runs `engine.advance` over the Game's settings (checked against the stored demand series) with the Rule-based rule and the Game's frozen parameter set, twice (only the viewer's Seat counts På vei, β = 0 for the others; all four count). `analysis.facts` stores it in `SeatFacts.simulated` (`ANALYSIS_VERSION` 2). Step 4 answers a `bill` block from the facts set; the web app reuses `ChainBill` + `ChainCostChart` (game result endpoint, as Story 6.18) and fills `extraRows`. New `debrief.commands.finish` stores a `debrief_summaries` row and records `progress` `debrief` in the same transaction. Staff read it through `debrief.service.staff_summary` on a new page; `modules/debrief` offers an insight-link provider for Spillinnsikt.

## Boundaries & Constraints

**Always:**
- Simulation: Guided Weeks order `guided_order`; later Weeks `rule_based.order` with the Game's frozen set (`session_runtime.rule_based_params`, version must match, else `simulated` None); row `own`: viewer β = set's β, others β = 0; row `all`: every Seat the set's β. Each row: chain `holding_cost`, `backorder_cost`, `total_cost` (sum of every Seat's Week costs, split inventory × h / backlog × b). Refuse (`ValueError`) when `demand_series(settings)` differs from the stored series. Pure: no I/O.
- Stored facts sets of version 1 stay valid (`simulated` defaults None) and are never rebuilt; the Simulert block is then absent.
- `bill` (step 4): `backorder_share_percent` (chain backorder / total, whole percent half-up, None when total 0), `backorder_costs_double` (settings' backorder = 2 × holding), `ai_held_cost`, `ai_held_share_percent` (facts' `ai_held_share` × 100 half-up), `simulated` {params_id, rows[2]} or None. Numbers from the facts set only.
- UI under the moments (also with `mostly_ai`): ChainBill with the viewer's «(deg)» row, Kjeden row, then the Simulert rows in the `extraRows` slot (rendered after Kjeden), «Simulert viser sammenhengen, ikke en fasit.», the restordre line («Restordre er 60 % av kjedens regning, fordi den koster dobbelt.»; without «fordi …» when not double), the AI line only when `ai_held_cost` > 0, then ChainCostChart. No copy says «optimal»/«fasit» as a claim.
- Finish: `POST /api/debriefs/{id}/finish` behind the gate; 409 `debrief_incomplete` until every pinned reflection question is answered and the facts set is recorded (step 4 seen); 409 `test_deadline_passed` when `effective_test_deadline` has passed (checked against database time inside the command); stores once `(user_id, class_session_id)` → `game_id`, `fact_set_id`, `moment_ids` (fact ids), `reflection` (question id, version, text), `finished_at` (db time), trigger refuses UPDATE; records `progress.record_step(debrief, finished_at)` in the same transaction; emits `debrief:<id>` (registry `debrief.finish` → debrief, session, user). A repeat returns the stored summary unchanged, no event. `GET /api/debriefs/{id}/summary` → own `{summary: …|null}`.
- Finished Debrief: every step still reads; the finish button gives way to «Debriefen er fullført» with the time; nothing is editable.
- Staff: `GET /api/class-sessions/{sid}/students/{uid}/debrief-summary` with new action `debrief_summaries.read` (Lecturer, Assistant; Class roles owner, assistant): Explanation (or null), summary (or null) with `finished_at`, `late` (finished_at > effective Debrief deadline), moments rendered from the stored facts set (heading, reckoning, later, patterns), reflection prompts with answers; 403 `forbidden` for anyone else (Admin unattached, Students). Page `/klasseokter/[sessionId]/studenter/[studentId]/debrief`.
- Insight links: `debrief.insight.links(session, game_id)` returns, per Student-held Seat, `explanation` and `debrief_summary` hrefs to that page; registered with `games.service.register_insight_links` only when that exists (it lands with Story 7.7 on `epic-7`); `games` imports nothing from `debrief`.

**Never:** no merge of `epic-7`; no change to stored facts sets; no LLM text; no import of `modules/players`; no step-pointer move or quiz (9.9); no names in the api payloads (ids only).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Bill | step 4, facts v2 | `bill` with share, AI share, 2 simulated rows | — |
| Old facts | stored v1 set | `bill.simulated` null; rest shown | — |
| Finish | all answered, step 4 read | 200 summary; one row; `debrief` step | — |
| Finish again | stored | same body, no event | — |
| Too early | a question unanswered or step 4 not read | nothing stored | 409 `debrief_incomplete` |
| After Test deadline | db now > deadline | nothing stored | 409 `test_deadline_passed` |
| Staff read | owner/assistant | 200 with summary or null | other callers 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/analysis/facts.py` -- `SeatFacts`, `facts()`, `ANALYSIS_VERSION`; `facts.md` documents rules.
- `backend/app/engine/{rule_based.py (order, RuleBasedParams), view.py:99 seat_view, week.py advance/initial_state, guided.py, settings.py demand_series}`; `app/sim.py:230` `rule_based_policy` (pattern to follow).
- `backend/app/modules/games/facts.py` `_build` -- give `facts()` the simulation input (settings, `rules_version`, stored `demand_series`, params from `platform.parameter_sets`).
- `backend/app/modules/debrief/{service.py step()/_moments, commands.py, models.py, schemas.py, routes.py, README.md}`; `platform/events/registry.py`; `platform/authz.py:116-141`.
- `backend/app/modules/sessions/service.py:562` `effective_debrief_deadline`, `effective_test_deadline`, `class_staff_may`; `progress.Step.DEBRIEF`.
- `backend/migrations/versions/0106_moment_templates.py` -- pattern for 0107 (`debrief_summaries` + trigger).
- epic-7 `games/insight.py` contract: `InsightLink(role, kind, href)`, provider `(AsyncSession, game_id) -> Sequence[InsightLink]`.
- Tests: `tests/debrief/test_explanation.py` (one played game; add bill/finish/staff parts), `tests/games/test_facts.py` + `tests/golden/facts/*.json` (`UPDATE_GOLDEN=1`), new `tests/analysis/test_simulated.py`, `tests/test_migrations.py`.
- Frontend: `components/chain-bill.tsx` (`extraRows`), `components/chain-cost-chart.tsx`, `modules/games/{result.ts gameEnd, api.ts useGameResult}`, `modules/debrief/{debrief-page.tsx, moments-step.tsx, api.ts}`, `copy/nb.ts`, `modules/identity/homes.ts`, `app/(app)/klasseokter/[sessionId]`; e2e `support/{moments,chain,reveal,reflection}.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/simulated.py` (new), `facts.py`, `facts.md`, `__init__.py` -- pure simulation, `SeatFacts.simulated`, version 2.
- `backend/app/modules/games/facts.py` -- simulation input from the Game's snapshot.
- `backend/migrations/versions/0107_debrief_summaries.py` (new), `debrief/models.py` -- table + trigger.
- `backend/app/modules/debrief/{commands,service,schemas,routes,insight}.py`, `README.md`, `platform/events/registry.py`, `platform/authz.py` -- bill, finish, own summary, staff summary, link provider.
- Tests: `tests/analysis/test_simulated.py` (rows, β split, guided Weeks, demand mismatch, purity of cost split); `test_facts.py` goldens regenerated + simulated rows equal a re-run; `test_explanation.py` bill numbers vs facts, finish matrix, staff readers, link provider; migrations.
- Frontend: `modules/debrief/bill-step.tsx` (new), `api.ts`, `debrief-page.tsx`, `components/chain-bill.tsx` (extra rows after Kjeden), `modules/debrief/summary-page.tsx` (new) + route, `homes.ts`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts`, `debrief.test.ts`, `components.test.tsx`.
- e2e: `frontend/e2e/debrief-bill.spec.ts` (new) + `support/bill.ts` -- stubbed bill, finish, finished state, staff summary page, axe at 320/360/1440.

**Acceptance Criteria:**
- Given step 4 after the moments, when the bill shows, then Kjedens regning lists Detaljist to Fabrikk with «(deg)», the Kjeden row, the two Simulert rows, the restordre line, and the Lager / Restordre / Sum numbers stand beside each split bar.
- Given a Game with AI-held Weeks, when the bill shows, then a line states their share of the chain's cost from the facts set.
- Given a finished Debrief, when the Student returns, then every step reads and nothing can be changed or sent.
- Given 320, 360 and 1440 px, when the bill and the staff summary page show, then axe passes with no sideways page scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-8.md` and `review-edge-9-8.md` in the scratchpad.
- verdicts: 31 findings — high 0, medium 0, low 21, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) A simulation failure (demand mismatch, settings) is outside `_build`'s try and fails the whole facts set. The stored series is drawn from the same settings at creation and a finished Game always holds a valid snapshot; the state cannot be reached, and failing loudly on corrupt data is the 9.1 rule.
  - `[false]` `[reject]` (blind 2) The cost-split check hard-codes holding plus backorder. Rules version 1 is frozen and charges exactly that; a new cost kind is a new rules package, and the check would then fail loudly, as it should.
  - `[low]` `[reject]` (blind 3) Eight simulations per Game, the `all` row stored four times. Measured 15 ms per simulation, once per Game; storing per Seat keeps each set self-contained (AD-7).
  - `[low]` `[patch]` (blind 4) `own > all` asserted a direction that holds only for the placeholder parameters. Assertion removed; the per-Seat difference and the beta-0 oracle stay.
  - `[low]` `[reject]` (blind 5) The `own` row has no independent oracle and the API test never sees AI-held cost or non-double costs. The `own` mapping is checked by the beta-0 case and the per-Seat difference; non-zero AI share is the golden Takeover facts' (9.1); the wording branches are Vitest and e2e cases.
  - `[low]` `[patch]` (blind 6) A tiny AI-held share renders «0 %». `aiHeld` now needs a share of at least 1 % after rounding; Vitest case added. Restordre 0/100 % is honest rounding (rejected).
  - `[low]` `[reject]` (blind 7) `late` follows a later change of the deadline. «Derivable from the stored time» is read against the effective Debrief deadline, so an Epic 11 extension applies as intended.
  - `[false]` `[reject]` (blind 8) `KeyError` in `_summary` when a moment id is missing. The ids come from the same immutable set the render reads; templates change texts, never ids. An unknown Student id answering nulls leaks nothing.
  - `[low]` `[reject]` (blind 9) `moment_ids_of` opens a second connection under the row lock; no questions means no finish. The cited set exists, so it is one short read; a pinned question set is never empty (content schema).
  - `[low]` `[reject]` (blind 10) The soft coupling to Story 7.7 (no log, duck-typed link). Deliberate (Design Notes), tested with a patched hook; 7.7's `InsightLink` has exactly `role, kind, href`.
  - `[low]` `[reject]` (blind 11) No index on `game_id`/`fact_set_id`, no JSONB checks, DELETE not blocked. Same pattern as 0103 to 0106; deletes come from cascades only.
  - `[low]` `[patch]` (blind 12) A failed summary read hides «Fullfør Debriefen» silently. Now «Det kunne ikke hentes om Debriefen er fullført.» with «Prøv igjen»; e2e case added.
  - `[false]` `[reject]` (blind 13) `scope="rowgroup"` outside a row group. The label row is the first row of its own `tbody`, the row group it heads; axe passes at three widths.
  - `[low]` `[reject]` (blind 14) Focused status line without outline, double announcement. Same pattern as the reflection step's closing line.
  - `[low]` `[reject]` (blind 15) `SIMULATED_NOTE` is a second literal. A drift fails loudly: the copy check flags «fasit», and a Vitest case pins the nb text.
  - `[low]` `[patch]` (blind 16) Two files end without a newline. Added. The summary route's documented codes are complete (no 409 there); generated files left out of the review diff on purpose.
  - `[low]` `[reject]` (blind 17) Coverage gaps (concurrent finish, Takeover role, mostly-AI finish, Assistant in e2e, `simulated: null` in e2e). The row lock serializes finish; the Assistant reads in the API test; a Seat's Role cannot change after the game finished.
  - `[low]` `[reject]` (edge 1) Same as blind 1.
  - `[low]` `[reject]` (edge 2) A transient read error stores a set without Simulert rows. The set is a local config file read; a transient failure is not a realistic case.
  - `[low]` `[reject]` (edge 3) `OSError` not caught. Same reason as edge 2.
  - `[false]` `[reject]` (edge 4) Role from `student_game` differs from the summary's Seat. After the game finished no Seat moves; `student_game` keeps the last held Seat after a Takeover.
  - `[false]` `[reject]` (edge 5) `KeyError` on moment ids. Same as blind 8.
  - `[false]` `[reject]` (edge 6) `_bill` raises when settings are missing. A finished Game always holds its settings; `_chain` has the same guard.
  - `[false]` `[reject]` (edge 7) Both costs 0 claims «dobbelt». The chain then costs nothing, `backorder_share_percent` is null and no line shows.
  - `[low]` `[patch]` (edge 8) Same as blind 6; same fix.
  - `[low]` `[patch]` (edge 9) Same as blind 12; same fix.
  - `[low]` `[reject]` (edge 10) No loading state for the bill. Same as the moments step; the page's own loading covers the first view.
  - `[false]` `[reject]` (edge 11) 7.7's `InsightLink` may have other fields. It has exactly `role, kind, href` (read on `epic-7`).
  - `[false]` `[reject]` (edge 12) Double registration duplicates links. 7.7's `register_insight_links` ignores a provider already registered.
  - `[low]` `[reject]` (edge 13) DELETE not blocked. Same as blind 11.
  - `[false]` `[reject]` (edge 14) Guided Weeks untested. The `all` row equals the trace runner's policy, which orders the starting demand in Guided Weeks; the cost-split raise guards an unreachable state.

## Design Notes

The bill's Role rows and Kjedens kostnad over tid reuse Story 6.18's game result (same Decision log), so the Debrief draws exactly the end screen's numbers; only the Debrief's extra lines come from the facts set. `ChainBill` renders `extraRows` in a second `tbody` after the Kjeden row so «Simulert» never sits between the Roles and their sum. Insight links: Story 7.7 lives on `epic-7`; the provider is written to its contract and registers itself through `getattr(games, "register_insight_links", None)`, so it wires up when the branches meet.

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis tests/debrief tests/games/test_facts.py tests/test_migrations.py` -- pass
- full backend suite `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-*`, `homes`, play-screen specs with `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** Debrief step 4 now ends with Kjedens regning and «Fullfør Debriefen». A pure `analysis.simulated.simulate` plays the Game again from Week 1 with `engine.advance` over its settings (checked against the stored demand series) and rules version, every Seat ordering by the Rule-based rule with the Game's frozen parameter set (Guided Weeks order the starting demand): row `own` with only the viewer's Seat counting På vei (β = 0 for the others), row `all` with all four. `analysis.facts` stores it in `SeatFacts.simulated` (`ANALYSIS_VERSION` 2; a version-1 set reads with `simulated` null and is never rebuilt). `GET /api/debriefs/{id}/steps/4` answers `bill` from the stored facts set: chain total and backorder cost, the restordre share (whole percent, half up), whether backlog costs twice inventory, the AI-held cost and share, and the two Simulert rows. The web app reuses `ChainBill` and `ChainCostChart` with the game result (as «Spillet er ferdig»), puts «Simulert, samme kunder» in the `extraRows` slot after «Kjeden», then «Simulert viser sammenhengen, ikke en fasit.», the restordre line and the AI line (only when the share rounds to 1 % or more). `POST /api/debriefs/{id}/finish` (`debrief.commands.finish`, Debrief row locked) stores one `debrief_summaries` row (moment ids, reflection answers with version, cited `fact_set_id`, `finished_at` in database time; trigger refuses UPDATE) and records `progress` `debrief` at that time in the same transaction; 409 `debrief_incomplete` before every answer and step 4, 409 `test_deadline_passed` past the effective Test deadline (judged in the database). A finished Debrief reads every step with nothing to send. Staff read the Explanation and summary (moments rendered from the cited set, answers with prompts, time, `late` against the effective Debrief deadline) through `debrief.service.staff_summary` (`debrief_summaries.read`: owners and Assistant lecturers) on `/klasseokter/[sessionId]/studenter/[studentId]/debrief`. `debrief.insight.links` offers Spillinnsikt one Explanation and one summary link per Student-held Seat.

**Files.**
- `backend/app/analysis/{simulated.py (new), facts.py (SeatFacts.simulated, version 2), facts.md, __init__.py}`.
- `backend/app/modules/games/facts.py`: simulation input from the Game's snapshot and frozen parameter set.
- `backend/migrations/versions/0107_debrief_summaries.py` (new); `debrief/models.py`.
- `backend/app/modules/debrief/{commands.py (finish), service.py (bill, finish_mine, own_summary, staff_summary), schemas.py, routes.py, insight.py (new), README.md}`; `sessions/service.py` (`student_deadlines`); `platform/authz.py` (`debrief_summaries.read`); `platform/events/registry.py` (`debrief.finish`).
- Tests: `tests/analysis/test_simulated.py` (new), `tests/games/test_facts.py` + regenerated `tests/golden/facts/*.json`, `tests/debrief/test_explanation.py` (bill, finish matrix, staff readers, links), `tests/test_migrations.py`.
- `frontend/src/modules/debrief/{bill-step.tsx (new), summary-page.tsx (new), api.ts, debrief-page.tsx, debrief.test.ts}`, `components/chain-bill.tsx` (extra rows after «Kjeden»), `components/components.test.tsx`, `copy/nb.ts` (`debrief.bill`, `debrief.staffSummary`), `modules/identity/homes.ts` (`studentDebriefPath`), route `app/(app)/klasseokter/[sessionId]/studenter/[studentId]/debrief/page.tsx`, regenerated `lib/api/{openapi.json,schema.ts}`, `scripts/{check-copy.mjs,scripts.test.mjs}`.
- `frontend/e2e/{debrief-bill.spec.ts (new), support/bill.ts (new)}`.

**Deviations from the epic's wording.** Story 7.7 (`register_insight_links`, Spillinnsikt's `links` slot) is on `epic-7`, not `epic-9`: the provider is written to its contract and registers itself when the hook exists, so Spillinnsikt shows the links once the branches meet; until then the staff page is reachable by its URL only. The restordre and AI lines are worded in the web app from numbers the api computes, not code-rendered sentence templates.

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), two review layers. Not merging `epic-7` (team lead told). The copy check now allows «Simulert viser sammenhengen, ikke en fasit.» word for word (the spine's line, required by the AC) and still fails every other «fasit». «Simulert» row labels «Bare du teller på vei» / «Alle fire teller på vei» (the spine's with «du» for the name). The Simulert rows sit in a body of their own after «Kjeden» (`ChainBill` keeps `tfoot` when there are none). The simulated rows use the Game's frozen Rule-based set; with the placeholders the chain costs are far above the mockup's 1 341,00. AI-held means `occupant_kind ≠ student` (9.1's rule): Rule-based Orders placed for a seated Student are not AI-held. `late` is judged against the effective Debrief deadline at read time (an extension applies). Finish after the Test deadline is refused; reading stays open. The staff page names no Student (ids and Roles only). Draft copy `[ASSUMPTION]` in `nb.debrief.bill` and `nb.debrief.staffSummary` (Issue #31).

**Review.** 31 findings (high 0, medium 0, low 21, false 10): patched 4 root causes, all low (the `own > all` assertion removed; the AI line needs a share that rounds to 1 % or more; a failed summary read shows a line and «Prøv igjen»; two missing trailing newlines); nothing deferred; the rest rejected with reasons above. followup_review_recommended: false (no high or medium patched).

**Verification.**
- Backend, after the patches: full suite `--maxprocesses=8` 2912 passed, 4 skipped; `ruff check`, `ruff format --check` clean. Migration 0107 applied to the lane's `olspillet`; test databases migrate per session.
- Frontend: typecheck, Vitest (55 files, 757 tests), `lint:colours`, `check:copy`, `next build` (in the lane's image build) pass.
- Playwright on the rebuilt lane stack (8081), after the patches, `--workers=4`: `debrief-bill` (axe at 320, 360, 1440 px for the bill and the staff page), `debrief-moments`, `debrief-reflection`, `debrief-chain`, `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`: 144 of 144.
- Failed once, passed on rerun: none. The first image build failed on a type error in `debrief.test.ts`, fixed before any e2e run.
- Tests over 1 s: `test_step_one_the_one_send_the_gate_and_the_readers` grew from about 7 s to about 9 s alone (12 s under load: bill, finish and staff reads on the shared played game). No new test over 1 s; `test_simulated.py`'s 1.6 s is the shared database fixture's setup.

**Residual risks.** Simulated rows use placeholder Rule-based parameters (issues #8, #17). Spillinnsikt links unverified until `epic-7` and `epic-9` meet. Facts sets stored before this change (local and test data only) show no Simulert rows.