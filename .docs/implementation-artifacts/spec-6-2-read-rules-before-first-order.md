---
title: 'Story 6.2: Read the rules before the first Order'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '7c52230c5ae85457040916c024e836fc6d003161'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-6-1-see-class-game-role-seats-on-hjem.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The briefing's worked Uke is a single-column table, not the mockup's graph over week columns with a «Nå» line and the Order landing four columns later.
    evidence: |-
      Visual review against mockup 09-alle-sider («Regler før første ordre» panel). Graf over tabell and the chart module arrive with Stories 6.6/6.7; reuse them here then.
    location: >-
      frontend/src/modules/games/briefing-page.tsx
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A seated Student's Hjem (Story 6.1) shows the Class game but has no way to the rules: there is no «Regler før første ordre» screen, so a Student would meet the game without the objective, the delays, the must-ship rule, the Guided Weeks or the no-discussion rule (FR-84, FR-14, UX-DR63).

**Approach:** Add the briefing screen at `/spill/{gameId}/regler`, fed by the Student's own game read `GET /api/me/games/{id}`, which gains the game's frozen rules (delays, Guided Weeks, cost rates) and `briefing_first` (true until `progress` has `starting_task`). Hjem's one primary button «Les reglene» leads to it while `briefing_first`; afterwards a Lenke «Regler før første ordre» stays. The screen's one primary button returns to Hjem (Story 6.3 retargets it to the Startoppgave).

## Boundaries & Constraints

**Always:**
- `StudentGameOut` (both `/api/me/class-sessions` `game` and `/api/me/games/{id}`) adds `briefing_first: bool` (= not `progress` `starting_task` for the Student in that Class session; computed in the api, AD-10) and `rules: GameRulesOut` = `order_delay, shipping_delay, production_delay, guided_weeks` (ints) and `holding_cost, backorder_cost` (decimal strings). Read from the Class session's frozen `snapshot["settings"]` (set at the lock), else its `game_settings` (identical once locked; edits are refused with `session_locked`). Never `weeks`, demand, seed, `max_order` or anything derived from a reference Order.
- Nothing is stored for "briefing read" (no table, no column, no localStorage).
- Briefing screen (`frontend/src/modules/games/briefing-page.tsx`), copy in `nb.games.briefing` (new top-level, pre-Debrief section; draft strings marked `[ASSUMPTION]`): h1 «Regler før første ordre»; «Til Hjem» PageLink; a lead naming the Student's Role and game; sections (h2) for the objective (lowest Total cost for the whole chain, with the game's two cost rates), one Week (all Seats order in the same Week; ship what you have up to what is owed; the rest becomes Restordre), the delays from `rules` for the Student's Role (Fabrikk: order delay + production delay; other Roles: order delay + shipping delay, «tidligst»), Veiledede uker (count from `rules.guided_weeks`; a separate line when 0), how to play together (play as if the business continues; you may arrange when to play, never discuss Orders or numbers). A worked Uke as an HTML table (Term · Uke 11 · what it means) using Levering, Ordre inn, Sendt, Lager, Restordre, På vei with fixed synthetic numbers that obey the engine's Week rule (on hand = Lager + Levering; Sendt = min(on hand, Ordre inn + old Restordre)), caption naming the Week, and «Demodata» in `caption` `ink-muted` (UX-DR70); its cost line uses only `rules.backorder_cost` as given (1 restordre × rate = rate), no client arithmetic.
- One primary button «Jeg har lest reglene» (draft) navigating to Hjem. Loading Skjelett, page error + «Prøv igjen», and 403 → the Epic 3 permission-denied page state, as other Student pages (`seat-choice-page.tsx` pattern).
- Hjem `GameCard`: while `briefing_first`, a primary button-styled link «Les reglene» to the screen (only the first such session on the page is primary; any further one is a Lenke, so Hjem keeps one primary button); otherwise a standalone Lenke «Regler før første ordre».
- Copy: «enheter», never «øl»; no exclamation mark, praise, recommended order, number of Weeks, «Beer Game» or «bullwhip». `check-copy.mjs` already scans `nb.ts`; add a test proving the `games` section is held to the pre-Debrief rules.

**Never:** No Startoppgave (6.3), no `/spill/{id}` play screen or Start button (6.5/6.6), no SSE (6.4), no `games.policy` columns (6.18). No capacity text (6.22). No change to Epic 5 behaviour or the demo Class. No edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First open | seated, locked, no `starting_task` | `briefing_first: true`, `rules` classic (2,2,2,4,"0.5…","1.0…"); Hjem primary «Les reglene» | — |
| After Starting task | `starting_task` recorded | `briefing_first: false`; Hjem Lenke «Regler før første ordre»; screen still opens | — |
| Changed settings | session saved with delays 3/1/2, guided 0 | `rules` carries 3/1/2/0; screen says those numbers and the no-Guided-Weeks line | — |
| Hidden info | any | answer has no `weeks`, `demand*`, `max_order` key | — |
| Not own game | other's / unknown / malformed id, before lock | — | 403 `forbidden` (unchanged); screen shows permission denied |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/schemas.py:366` `StudentGameOut` -- add `briefing_first`, `rules: GameRulesOut` (new model next to it).
- `backend/app/modules/sessions/service.py:1186` `_student_card`, `:1197` `_game_out`, `:1212` `student_game_of` -- pass the session row's settings and the done steps; `_game_out` builds `rules` and `briefing_first`. `enrolled_sessions:1087` already reads `progress.steps_of` (`done`) -- reuse it for the card.
- `backend/app/modules/sessions/repo.py:83` `enrolled_sessions` -- also select `snapshot` and `game_settings` (only used to build `rules`; docstring updated).
- `backend/app/engine/settings.py:73` `GameSettings` -- field names and Classic defaults; `rules/v1/__init__.py` docstring is the Week rule the worked Uke must obey.
- `backend/app/modules/progress/service.py` -- `Step.STARTING_TASK`, `record_step` (tests record it).
- Tests: `backend/tests/sessions/test_student_home.py` (helpers there; add rows of the matrix).
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate (`npm run` script used in 6.1).
- `frontend/src/copy/nb.ts` -- new `games.briefing` block; `homes.student.readRules`, `rulesLink`.
- `frontend/src/modules/games/briefing.ts` (new, pure: delay lines, guided line, worked-week rows) + `briefing.test.ts`.
- `frontend/src/modules/games/briefing-page.tsx` (new) + `frontend/src/modules/games/api.ts` (new: `myGameKey`, `useMyGame` like `sessions/api.ts:227`); route `frontend/src/app/(app)/spill/[gameId]/regler/page.tsx` (pattern `klasseokter/[sessionId]/velg-sete/page.tsx`); `rulesPath` in `frontend/src/modules/identity/homes.ts`.
- `frontend/src/modules/games/student-hjem.tsx` `GameCard` -- button/Lenke; `buttonClassName("primary")` from `components/button.tsx` on `Link`/NextLink.
- `frontend/scripts/scripts.test.mjs` -- pre-Debrief test for `games` section.
- E2E: `frontend/e2e/briefing.spec.ts` (new) -- real data via API setup (`frontend/e2e/support/`), seated fresh Student; axe at 320/360/1440; one primary button; heading order; Hjem button → screen → button → Hjem; Lenke after `starting_task` via answer overlay (as `student-home.spec.ts`).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/{schemas,repo,service}.py` -- `GameRulesOut`, `briefing_first`, `rules`.
- `backend/tests/sessions/test_student_home.py` -- matrix rows (first open, after Starting task, changed settings, hidden keys, both endpoints).
- `frontend/...` -- regenerate api, copy, `briefing.ts` + tests, `api.ts`, page + route, Hjem button/Lenke, copy-check test, e2e.

**Acceptance Criteria:**
- Given a seated Student without `starting_task`, when Hjem opens, then its one primary button «Les reglene» leads to «Regler før første ordre», which is the first screen of the game.
- Given the briefing, when read, then it states the chain objective, same-Week ordering, the game's delays, the must-ship rule, the Veiledede uker, the no-discussion rule and «play as if the business continues», explains one Uke with Ordre inn, Levering, Sendt, Lager, Restordre and På vei labelled «Demodata», says «enheter», and states no number of Weeks.
- Given the briefing, when its primary button is pressed, then Hjem opens; and once `starting_task` is recorded Hjem shows the Lenke «Regler før første ordre» instead of the button.
- Given `npm run check:copy`, when the briefing copy held «Beer Game», «bullwhip» or «!», then it fails (test).
- Given Playwright with axe at 320, 360 and 1440 px, when the briefing renders, then no page-level horizontal scroll, one primary button, h1 then h2s, no axe violation.

## Spec Change Log

### 2026-11-20 — Review loop 1
- Trigger: visual review (medium) — the worked Uke used invented numbers (Restordre 1) while the spine's canonical Uke 11 (Ordre inn 8, Levering 4, Lager 0, Restordre 13, På vei 16) is what the Startoppgave (6.3) shows next; blind review — the example's numbers were written twice (constant and copy).
- Amended: Design Notes' worked-Uke bullet (canonical numbers, numbers from `EXAMPLE` into the copy, cost line in enheter with the game's rate and no product).
- Known-bad state avoided: a Student meeting two different «Uke 11» columns in briefing and Startoppgave; copy drifting from the constant.
- KEEP: the backend fields (`briefing_first`, `rules` from the snapshot, else `game_settings`) and their tests; the route `/spill/{gameId}/regler`; the section order goal → week → delays → worked Uke → Veiledede uker → together; Hjem's single primary button with Lenke otherwise; the copy-check test; the e2e structure with `afterEach(unrouteAll)`.

## Review Triage Log

### 2026-11-20 — Review pass (loop 0)
- verdicts: 36 findings — high 0, medium 2, low 24, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` edge: capacity is not stated, though a capped Seat ships less. Capacity can only be set with `FEATURE_CAPACITY` on, and the capacity line in the briefing is cut-list Story 6.22's (epics), which the intent ("build only this story") leaves out.
  - `[false]` `[reject]` edge: rules read from the session snapshot, not the Game row. `open_games` gives every Class game exactly the session's snapshot (`test_open_games.py` asserts `game.settings == snapshot["settings"]`).
  - `[low]` `[patch]` edge: `home.test.ts` hid the new fields behind `as unknown as Game`. The fixture now has `briefing_first` and `rules` and is typed.
  - `[false]` `[reject]` edge (claim): a second un-briefed game gets a Lenke. Intended: Hjem keeps one primary button (UX-DR8); now tested.
  - `[low]` `[reject]` blind: «Jeg har lest reglene» leads back to Hjem, which offers «Les reglene» again. The AC prescribes both (back to Hjem until 6.3; the briefing shows again until `starting_task`).
  - `[low]` `[bad_spec]` blind: the worked Uke's numbers were written twice (constant and copy). Grouped with the canonical-Uke entry: the lines now take their numbers from `EXAMPLE`; a test checks every line.
  - `[low]` `[reject]` blind: På vei 16 has no derivation. It is the stock of open orders, explained in words; the spine's Uke 11 uses 16 too.
  - `[low]` `[patch]` blind: Hjem's read loaded the whole snapshot (demand, seed). `repo.enrolled_sessions` now selects only `snapshot['settings']` as `snapshot_settings`.
  - `[false]` `[reject]` blind: `KeyError` on a snapshot without `settings`. `build_snapshot` always writes it, and `ck_class_sessions_lock` ties snapshot to `locked_at`.
  - `[low]` `[patch]` blind: the fallback to `game_settings` was untested. Added `test_the_rules_come_from_the_settings_until_the_lock_has_stored_its_snapshot`.
  - `[false]` `[reject]` blind: a delay of 0 reads badly. `Delay` is `ge=1`, range 1–3.
  - `[false]` `[reject]` blind: Fabrikk is not told the shipping delay. In rules v1 the Fabrikk's goods slots are `production_delay` long; shipping delay does not apply to it.
  - `[low]` `[reject]` blind: the Detaljist is not told its orders come from customers. «den som bestiller fra deg» is true for every Role.
  - `[low]` `[patch]` blind: same as the edge `home.test.ts` row.
  - `[false]` `[reject]` blind: the page can stay loading on 404/422. The route takes a string and `student_game_of` answers 403 for every non-own id; there is no ready-without-data phase.
  - `[false]` `[reject]` blind: another primary button on Hjem (seat choice). Story 5.17's entry is a `Link`, not a button.
  - `[false]` `[reject]` blind: the copy-check test has no source change. `check-copy.mjs` already reads all of `nb.ts`; `games` is not in `POST_DEBRIEF_SECTIONS`.
  - `[false]` `[reject]` blind: `openapi.json` is missing from the diff. It was left out of the review diff on purpose (generated); it carries `GameRulesOut` with string decimals.
  - `[low]` `[patch]` blind: no test with two games to brief. Grouped with the verification-gap row.
  - `[low]` `[patch]` verification-gap: primary-vs-Lenke on Hjem never asserted. New e2e with two locked sessions: the first «Les reglene» has the Knapper look, the second is a Lenke.
  - `[low]` `[patch]` verification-gap: the Distributør's supplier line untested. `briefing.test.ts` asserts «Ordren din kommer fram til Fabrikk …».
  - `[low]` `[reject]` intent: "shown before anything else" is met by Hjem's button, not a gate on a game route. No other game surface exists; the AC says "from Hjem", and Design Notes leave the `/spill/{id}` redirect to 6.5/6.6.
  - `[low]` `[reject]` intent: e2e lays answers over the api. The repo's pattern (6.1, 5.17); a locked game needs the Start date; the api states are pinned by pytest against real data.
  - `[low]` `[reject]` intent: no UI check that no number of Weeks is stated. `rules` has no `weeks` (tested) and the copy has no count; a text scan would only re-test the copy.
  - `[false]` `[reject]` intent: copy check tested on a fixture only. CI runs `npm run check:copy` over the real `nb.ts` (passes).
  - `[medium]` `[defer]` visual: the briefing has no graph-over-table strip with a «Nå» line as in mockup `09`. The shared Graf over tabell and the chart module come with Stories 6.6/6.7 (the chart spike); building a second chart here would break "one chart importer". Deferred.
  - `[medium]` `[bad_spec]` visual: the worked Uke differed from the spine's canonical Uke 11 that the Startoppgave shows next. Design Notes amended (loop 1); code re-derived with Lager 0, Restordre 13, På vei 16.
  - `[low]` `[patch]` visual: column header «Tall» named the terms column. Now «Rad».
  - `[low]` `[patch]` visual: cost line counted «restordre» not enheter. Now «Denne uka: 13 enheter i restordre, hver til 1,00 kr. Lager 0 gir ingen lagerkostnad.» (no product; AD-1).
  - `[low]` `[reject]` visual: rows say «Grossisten» while prose says «du». Deliberate: the worked Uke is Demodata, not the Student's Seat.
  - `[low]` `[patch]` visual: «Målet» repeated in its first sentence. Now «Dere skal få lavest mulig totalkostnad for hele kjeden, ikke bare for hvert sete.»
  - `[low]` `[patch]` visual: «legger inn én ordre selv» awkward. Now «legger selv inn én ordre».
  - `[low]` `[reject]` visual: «Uka går videre når alle har åpnet den» unclear. It is the rule (FR-24: viewing the Week counts); «sett» is less exact.
  - `[low]` `[reject]` visual: add «etter siste uke du spiller». That hints at an end, against FR-14.
  - `[low]` `[patch]` visual: Role order differed from Setene. The lead now lists Fabrikk, Distributør, Grossist og Detaljist.
  - `[low]` `[reject]` visual: loose rhythm at 1440 px. The reviewer asks for no change; the right-aligned «Demodata» matches the mockup.

The five reviewers (blind, edge case, verification gap, intent alignment, and a visual reviewer standing in for the founder's eye) finished; their reports were read from their transcripts.

### 2026-11-20 — Review pass (loop 1)
- verdicts: 34 findings — high 0, medium 0, low 29, false 5, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: Fabrikk not told a shipping delay. carried — rules v1 gives the Fabrikk `production_delay` slots; no shipping delay applies.
  - `[false]` `[reject]` blind: delay 0 or large reads oddly. carried — `Delay` is 1–3; `guided_weeks` ≤ 20 and `countWord` writes 13+ as digits.
  - `[low]` `[reject]` blind: a malformed stored setting would fail all of Hjem. Settings are validated on every save and version 1 is upgraded; a corrupt row is not reachable through the product.
  - `[low]` `[patch]` blind: the cost line hard-coded «Lager 0». Grouped with the edge row: `exampleCostLine` passes `EXAMPLE.rows.inventory`.
  - `[low]` `[reject]` blind: «Jeg har lest reglene» changes nothing. carried — the AC's behaviour until Story 6.3.
  - `[false]` `[reject]` blind: two primary buttons on Hjem. carried — Story 5.17's entry is a `Link`; `Button` is the retry of the page error.
  - `[low]` `[reject]` blind: no unit test of the primary selection across Classes. The e2e covers the rule (first listed gets it); more cases add test weight for a three-line `find`.
  - `[false]` `[reject]` blind: the table may overflow at 320 px. `expectAccessible` asserts no horizontal page scroll at 320 and 360 px, and passes.
  - `[low]` `[reject]` blind: 5xx and retry untested on this page. The shared `PageShell`/`usePageState` path is Story 3.4's, tested there.
  - `[low]` `[reject]` blind: `game_settings` is read in the Student path. It stays in service memory; the answer is the `GameRulesOut` schema, whose key set is tested.
  - `[false]` `[reject]` blind: the real `nb.ts` is not shown to pass the copy check. `npm run check:copy` passes and CI runs it.
  - `[low]` `[reject]` blind: every Role sees a Grossist's worked Uke. It is labelled Demodata with the Role in the caption; per-Role examples are not asked for.
  - `[low]` `[patch]` edge: the delay lines lacked «tidligst», which the spec names. Added «Det du bestiller nå, kommer altså tidligst fram etter begge forsinkelsene, og senere hvis leverandøren mangler enheter.» (Fabrikk: without the supplier clause); no sum (AD-1).
  - `[low]` `[patch]` edge: the cost line's «Lager 0» would not follow `EXAMPLE`. Fixed as above.
  - `[low]` `[patch]` verification-gap: snapshot vs settings never told apart through the api. `test_the_briefing_states_the_sessions_own_rules` now overwrites `game_settings` after the lock and still expects the snapshot's rules on both endpoints.
  - `[low]` `[reject]` intent: Hjem flow tested on overlaid answers. carried — repo pattern; api states pinned by pytest.
  - `[low]` `[reject]` intent: no gate on other game routes. carried — none exists yet; 6.5/6.6.
  - `[low]` `[reject]` intent: praise and recommended orders not checked by machine. Not mechanisable by a word list; the AC's CI clause is «Beer Game»/«bullwhip» (tested); reviewers read the copy.
  - `[low]` `[reject]` intent: no number of Weeks asserted in the UI. carried.
  - `[low]` `[reject]` visual: show the cost product («13 × 1,00 = 13,00 kr»). The web app computes no game quantity (AD-1); the line gives count and rate.
  - `[low]` `[patch]` visual: the game's table shows Netto lager, the briefing did not. Added row «Netto lager −13» («Lager minus restordre: 0 − 13. Under null betyr restordre. …»), tested against the Week rule.
  - `[low]` `[patch]` visual: row order differed from the game (Ordre inn first). Swapped.
  - `[low]` `[patch]` visual: the two delays were never joined. Same fix as the «tidligst» row.
  - `[low]` `[patch]` visual: «ikke bare for hvert sete» illogical. Now «ikke bare for ditt eget sete».
  - `[low]` `[patch]` visual: «Alle setene bestiller i samme uke» ambiguous. Now «Alle setene legger inn ordre for den samme uka.»
  - `[low]` `[patch]` visual: supplier in indefinite form. Now «Grossisten», «Distributøren», «Fabrikken» (`delays.supplier`).
  - `[low]` `[patch]` visual: «legger selv inn én ordre» stiff. Now «legger inn én egen ordre».
  - `[low]` `[patch]` visual: «skal Grossisten sende» → «må Grossisten sende».
  - `[low]` `[patch]` visual: «Uke 11» twice (caption and header). Header now «Tall».
  - `[low]` `[reject]` visual: move «Demodata» next to the caption. DESIGN.md's `demo-label` sits bottom right of a card; kept.
  - `[low]` `[patch]` visual: loose leading in the meaning column. `leading-snug`.
  - `[low]` `[patch]` visual: gap under «Til Hjem». Wrapper `mt-4`.
  - `[low]` `[reject]` visual: 1440 px narrow column. The reviewer asks for no change.
  - `[low]` `[reject]` visual: Hjem button. No finding (placement confirmed).

All five reviewers of this pass finished; reports were read from their transcripts.

## Design Notes

Founder-level decisions taken here:
- Address `/spill/{gameId}/regler`: a stable target for Hjem now and the play screen's Lenke (6.6); 6.5/6.6 redirect `/spill/{id}` here while `briefing_first`.
- The delays, Guided Weeks and cost rates come from the game's own frozen settings, so a Lecturer's changed delays are never misstated. These are not hidden information (the Kjedebånd shows the pipe); the number of Weeks and demand stay out.
- `briefing_first` is the server's answer (AD-10), so 6.18 can AND it with the policy's pre-play gate column without a web change.
- Primary button label «Jeg har lest reglene», back to Hjem until 6.3.
- Worked Uke (Demodata, Grossist, Uke 11) is the spine's canonical Uke 11 (EXPERIENCE.md walkthrough, mockup `09` Startoppgave panel), so the Startoppgave of Story 6.3 meets the same column: Lager før 0, Restordre før 9, Levering 4 (på hånd 4), Ordre inn 8 (å sende 17), Sendt 4, Lager 0, Restordre 13, På vei 16. The explanation texts take their numbers from the `EXAMPLE` constant (no number written twice). Cost line in enheter and without client arithmetic: «Denne uka: 13 enheter i restordre, hver til {rate} kr. Lager 0 gir ingen lagerkostnad.»

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_student_home.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run build && npx playwright test --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** A seated Student's Hjem shows the primary button «Les reglene» while the briefing comes first, leading to «Regler før første ordre» at `/spill/{gameId}/regler`; once the Starting task is recorded, Hjem keeps the Lenke «Regler før første ordre». The briefing states the objective (lowest Total cost for the whole chain, with the game's own rates), how a Week goes (same-Week ordering, must ship what you have, the rest becomes Restordre), the game's own delays for the Student's Role (supplier in definite form, «tidligst»), a worked Uke 11 for a Grossist labelled «Demodata» (the spine's column: Ordre inn 8, Levering 4, Sendt 4, Lager 0, Restordre 13, Netto lager −13, På vei 16, each with what it means), the Veiledede uker (count, or none), and «Spill som om virksomheten fortsetter» with the no-discussion rule. No number of Weeks, no recommended Order. Its one primary button «Jeg har lest reglene» returns to Hjem until Story 6.3.
- **api:** `StudentGameOut` (both `/api/me/class-sessions` `game` and `/api/me/games/{id}`) adds `briefing_first` (not `progress` `starting_task`; nothing stored for "briefing read") and `rules` (`GameRulesOut`: three delays, `guided_weeks`, two rates), read by `sessions.service.game_rules` from `snapshot['settings']`, else `game_settings`.

**Files.**
- `backend/app/modules/sessions/{schemas,repo,service}.py`, `README.md` -- `GameRulesOut`, `briefing_first`, `rules`, `game_rules`; repo selects `game_settings` and `snapshot['settings']`.
- `backend/tests/sessions/test_student_home.py` -- briefing-first flip, Classic and changed rules on both endpoints (snapshot wins), fallback unit test.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated.
- `frontend/src/copy/nb.ts` -- new `games.briefing` section, `homes.student.readRules`/`rulesLink` (draft copy `[ASSUMPTION]`).
- `frontend/src/modules/games/{api.ts,briefing.ts,briefing.test.ts,briefing-page.tsx}` (new), `frontend/src/app/(app)/spill/[gameId]/regler/page.tsx` (new), `frontend/src/modules/identity/homes.ts` (`gamePath`, `rulesPath`), `frontend/src/modules/games/student-hjem.tsx` (`RulesEntry`, one primary per page), `home.test.ts` (fixture).
- `frontend/scripts/scripts.test.mjs` -- the `games` section is held to the pre-Debrief rules.
- `frontend/e2e/briefing.spec.ts` (new); `student-home.spec.ts`, `student-choice.spec.ts` (fixtures carry the new fields).

**Review.** Pass loop 0: 36 findings (medium 2, low 24, false 10): 1 medium bad_spec (canonical Uke 11, Design Notes amended, loop 1), 1 medium deferred (graph strip waits for Graf over tabell, 6.6/6.7), 12 low patched, the rest rejected with reasons. Pass loop 1: 34 findings (low 29, false 5): 17 low patched (copy, Netto lager row, «tidligst» line, snapshot-wins test), the rest rejected with reasons. Patched counts by verdict: loop 1 — high 0, medium 0, low 17.

**Follow-up review:** false. No high and no medium was patched in the final pass; the canonical-Uke change was reviewed in loop 1, including a fresh visual review of the screenshots.

**Founder-level decisions taken (no human in the loop).** Route `/spill/{id}/regler`; rules from the game's frozen settings (delays, Veiledede uker, rates) rather than fixed Classic copy; `briefing_first` computed in the api; button label «Jeg har lest reglene»; one primary «Les reglene» per Hjem, further ones as Lenke; the spine's Uke 11 as the worked Uke with a Netto lager row; no client-side cost product (count and rate only); all briefing copy drafted and marked `[ASSUMPTION]`.

**Verification.**
- Backend: 2613 passed (72 s); ruff check and format clean. New tests each under 1 s.
- Frontend: typecheck, Vitest 473 passed, `check:copy`, build; compose stack rebuilt; Playwright full run `--workers=2`: 297 passed (6.1 min). Targeted runs of `briefing.spec.ts`, `student-home.spec.ts`, `student-choice.spec.ts` passed after each patch.
- No migration in this story.

**Residual risks.** Draft copy awaits the founder's copy review (Issue #31). The e2e lays api answers over the demo Student's (a locked game needs the Start date); the api states are pinned by pytest. No gate on `/spill/{id}` yet (no play screen until 6.5/6.6). Deferred: the mockup's graph strip.
