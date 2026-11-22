---
title: 'Story 9.4: See the reveal of customer demand'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e6c6c8552a991a6af1168a034152aab52f9b7452'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['multiple-goals', 'oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** After sending the Explanation the Student has no step 2: `steps/2` answers only its number, so the customer demand is never revealed next to what they saw and ordered. Also, on step 1 «Vis som tabell» has no height cap, so 36 rows push the writing field far down on a phone (`screenshots/9.3/steg1-tabell-390.png`).

**Approach:** `GET /api/debriefs/{id}/steps/2` (behind `require_explanation`) answers the reveal: a heading rendered by code from the Game's stored demand series with a pinned, versioned sentence-template record (`content` kind `sentence_templates`, migration 0104, pinned by `sessions.lock`), and per Uke Kundene / Ordre inn / Din ordre plus the largest own Order. The web app shows step 2 under step 1 once the Explanation is saved: Etterspørselsbånd (new hand-made SVG in `components/charts`) over the table Uke / Kundene / Ordre inn / Din ordre in one `GraphOverTable` region, and «Øvelsen heter Beer Game.» from a new post-reveal `nb.debrief` section. The step-1 table gets a capped height and scrolls inside its region.

## Boundaries & Constraints

**Always:**
- Numbers come from the api only: Kundene = the Game's stored `demand_series[week-1]` (new `games.service.demand_series(game_id)`, no change to `GameOverview`); Ordre inn = own row's `state_seen.incoming_order`; Din ordre = own row's `order`; one entry per logged Uke of the Student's own Role, by Uke. The largest own Order (first Uke of the maximum) is computed by the api.
- Heading rendering is pure (`app/analysis/sentences.py`, AD-1): variant chosen from the series and the pattern — constant series → `demand-flat`; exactly one change and constant after → `demand-step` («Kundene bestilte 4, så 8. Etter det endret de seg aldri.»); `step+noise` → `demand-step-noise`; `random` (or `step+noise` with no change in the game) → `demand-random`; anything else → `demand-varied`. Numbers in the text use the Norwegian format (no-break space thousands, true minus).
- `SentenceTemplates` schema (in `analysis`, validated by `content` on publish/read): unique ids, no «!», every demand id present, each template's placeholders only from its id's allowed set. Version 1 stored by migration 0104 as a literal; lock pins it under `pins["sentence_templates"]`; reader takes the pinned version or the latest for older sessions.
- `steps/2` keeps the 9.2/9.3 refusals (`debrief_not_open`, `debrief_held`, `forbidden`, `explanation_required`) with the envelope only. Steps 3–5 still answer only their number.
- «Beer Game» lives only in `nb.debrief` (already in `POST_DEBRIEF_SECTIONS`); `nb.debriefEntry` stays pre-Debrief and checked.
- The band: `lager-fill` step area behind Kundene, «Kundenes etterspørsel: N» (last Uke's Kundene) in `ink` weight 600, Ordre inn a thin line, Din ordre `ink` bars, «Din ordre, 24 i Uke 11» at the largest bar; key «Ordre inn: det eneste du så» in the field caption. `aria-hidden` with a `<title>`; the table is its alternative; not interactive. Band and table scroll sideways together with the sticky label column; no page-level horizontal scroll.

**Never:** no step-pointer move or Group-debrief logic (9.11); no step 3+ content; no other Seat's numbers; no names of other Students; no number computed in the web app; no edit of an existing content record or migration; no import of `modules/players` or of `games` other than `games.service`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Reveal | `GET …/steps/2` with Explanation | 200 `{debrief_id, step: 2, reveal: {heading, template_id, role, weeks:[{week, demand, incoming_order, order}], largest_order:{week, order}}}` | — |
| No Explanation | same, none saved | 403 `explanation_required`, no `reveal` | envelope only |
| Steps 3–5 | with Explanation | 200 `{debrief_id, step, reveal: null}` | — |
| Classic step 4→8 at Uke 5 | series 4,4,4,4,8… | «Kundene bestilte 4, så 8. Etter det endret de seg aldri.» | — |
| Flat / step past last Uke | constant series | `demand-flat` «Kundene bestilte 4 hver uke. Det endret seg aldri.» | — |
| Noise / random / fixed | seeded or arbitrary series | `demand-step-noise` / `demand-random` / `demand-varied` with low/high from the series | — |
| Session locked before 0104 | no pin | latest template version | — |
| Bad template version | «!», unknown placeholder, missing demand id | publish refused (ValidationError) | — |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/{service.py:222 step, schemas.py:63 DebriefStepOut, routes.py:164, README.md}` -- fill step 2 behind `require_explanation`; `_own` gives row + `StudentGame(role)`.
- `backend/app/modules/games/service.py:406 get_game` (settings.demand, session_runtime.pins), `views.decision_log` (own rows' `state_seen.incoming_order`, `order`), `repo.get_game` (`demand_series` column) -- add `demand_series(game_id)`.
- `backend/app/engine/demand.py` -- pattern kinds (`step`, `step+noise`, `random`, `fixed`) and their levels.
- `backend/app/modules/content/{models.py Kind, schemas.py, service.py, README.md, __main__.py}` + `backend/migrations/versions/0101_*.py` -- the pattern for a new kind, its check constraint, v1 literal and pin provider.
- `backend/app/modules/sessions/service.py:2678` -- `register_pin_provider`.
- `backend/app/analysis/{__init__.py,patterns.py}` -- pure layer owning stored shapes (stdlib, pydantic, `app.engine` only).
- `backend/tests/debrief/test_explanation.py` -- module-scoped Class-session setup (`confirmed`, `start`, `play_week`), `call`, `refused`.
- `frontend/src/components/graph-over-table.tsx` + `modules/games/week-table-view.tsx:210` -- graph field over week columns, sticky labels, `AxisLabels`, `ROW_LABEL`, `WEEK_COL`.
- `frontend/src/components/charts/{cost-bars.tsx,axis-labels.tsx,palette.ts,README.md}` -- SVG conventions.
- `frontend/src/modules/debrief/{debrief-page.tsx,explanation-step.tsx,api.ts}`, `components/{net-over-game-chart.tsx,scroll-region.tsx}`, `copy/nb.ts`, `scripts/check-copy.mjs`.
- `frontend/e2e/{debrief-explanation.spec.ts,support/live-game.ts}` -- stubs and live game pattern.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/sentences.py`, `analysis/__init__.py` -- `SentenceTemplates`, `render`, `demand_heading(pattern, series, templates)`.
- `backend/migrations/versions/0104_sentence_templates.py` -- kind `sentence_templates`, v1 (five demand templates).
- `backend/app/modules/content/{models,schemas,service,README,__main__}.py` -- kind, `sentence_templates(version)`, `sentence_templates_pin`.
- `backend/app/modules/sessions/service.py` -- register the pin.
- `backend/app/modules/games/service.py` -- `demand_series(game_id)`.
- `backend/app/modules/debrief/{service,schemas,routes,README}` -- `RevealOut`, step 2 content.
- `backend/tests/analysis/test_sentences.py`, `tests/debrief/test_explanation.py` (`revealed`, on the same played game as step 1, so the setup is paid once), `tests/content/test_content.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py` -- variants, schema refusals, api numbers equal stored series and `seat_weeks`, gate, pin.
- `frontend/src/components/charts/demand-band.tsx` (+ `charts.test.tsx`) -- the band SVG.
- `frontend/src/modules/debrief/{reveal-step.tsx,api.ts,debrief-page.tsx,debrief.test.ts}`, `copy/nb.ts` (`debrief` section), regenerated `openapi.json`/`schema.ts`.
- `frontend/src/components/{scroll-region.tsx,net-over-game-chart.tsx}` -- capped, vertically scrolling step-1 table with sticky header.
- `frontend/scripts/scripts.test.mjs` -- `debrief` exempt, `debriefEntry` not.
- `frontend/e2e/debrief-reveal.spec.ts` (+ `support/reveal.ts`) -- stubbed step 2 at 320/360/1440 + 200 % text with axe and scroll checks; `debrief-explanation.spec.ts` -- step-1 table cap, and in the live game step 2 appears after send with the api's numbers.

**Acceptance Criteria:**
- Given a saved Explanation, when the Debrief page shows, then step 2 shows under step 1 with the api's heading, the band, the table Uke / Kundene / Ordre inn / Din ordre (`th` scopes) and «Øvelsen heter Beer Game.»; without one, step 2 is absent.
- Given 36 Uker at 320/360 px or 200 % text, when step 2 shows, then band and table scroll together in one region, the label column stays, and the page does not scroll sideways; axe passes at 320, 360 and 1440 px.
- Given step 1 with «Vis som tabell» at 390 px, when the table shows 36 rows, then the table region is capped and the writing field is in reach below it.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), following the orchestrator's two-reviewer rule; verification-gap and intent-alignment were skipped for the same reason. Both reviewers' hand-back failed; their findings were read from the scratchpad files they wrote (`review-blind-9-4.md`, `review-edge-9-4.md`).
- verdicts: 27 findings — high 0, medium 2, low 17, false 8, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind 1) A template slot with a format spec, conversion or nested slot (`{before:d}`, `{before!r}`, `{before:{after}}`) passed the validator and would fail at render, a 500 for every session pinning that version. `SentenceTemplate` now refuses any slot that is not a bare name; three refusal cases added to `test_sentences.py`.
  - `[low]` `[patch]` (blind 2) `RenderedText`'s docstring named an `ai_generated` field it does not have. Docstring corrected.
  - `[false]` `[reject]` (blind 3) Bare `StopIteration`/`KeyError` in `text_of`/`render`. The validator guarantees every demand id is present and uses only the values its id is given, and `demand_heading` passes every allowed value for each id; no reachable path asks for an unknown id or omits a slot.
  - `[low]` `[patch]` (blind 4) `debrief.service.reveal` was public with the gate only in a docstring. Renamed `_reveal`; `step()` is its only caller, after `require_explanation`.
  - `[low]` `[reject]` (blind 5) `_reveal` reads the game twice and the whole Decision log. Two small reads per view (at most 4 × 52 rows); other Seats' rows never leave the process. A refactor adds parameters for no user-visible gain.
  - `[false]` `[reject]` (blind 6) Missing demand series or pinned version gives a 500. A finished Class game always has its snapshot (settings, series) from the lock; a pinned version is removed only by a migration downgrade, an administrative act.
  - `[low]` `[reject]` (blind 7) Downgrade 0104 deletes every `sentence_templates` version. Same as 0101's precedent; downgrades are administrative.
  - `[false]` `[reject]` (blind 8) Template copy: «hver uke» is the generic lower-case use the product copy already has («i hver uke av spillet»); `demand-step` is the spine's exact sentence; the exercise name is allowed after the reveal, and «!» is refused.
  - `[low]` `[reject]` (blind 9) «Nesten alle grupper svinger slik. Struktur gir atferd …» is fixed copy: the mockup's line (`07-debrief.png`) without names, marked `[ASSUMPTION]` for the copy review (Issue #31).
  - `[low]` `[patch]` (blind 10) «ordrene fra Detaljist» needs the definite form. `nb.debrief.reveal.definite` added («fra Detaljisten»); the downstream Role mapping stays in the web app (a Role, not a number).
  - `[low]` `[reject]` (blind 11) No loading state for step 2. One small read after a page already shown; the step appears below step 1 a moment later. Adds a branch for a short wait.
  - `[low]` `[reject]` (blind 12) The largest Order is bold only in the table. The table holds every number, so the largest is readable; an sr-only addition changes the cell text for a highlight the band also shows.
  - `[low]` `[reject]` (blind 13) Ticks computed twice; demand and peak labels may overlap. `demandAxis` is idempotent on its own top (unit-tested values); an overlap needs the largest Order near the last Uke's demand level, and both labels carry a `paper` halo.
  - `[low]` `[patch]` (blind 14) The charts README had no Etterspørselsbånd row. Row added.
  - `[low]` `[reject]` (blind 15) Test gaps (a v2 not changing a v1-pinned session, decreasing step, empty series, two Roles). `pinned_version` and the reader fallback are tested in `test_content.py`; publishing a v2 in the shared test database would change what other tests lock; a decreasing step takes the same single-change branch.
  - `[false]` `[reject]` (blind 16) The step-1 table cap is "unrelated". It is part of the invocation intent (Story 9.3's visual-check defect).
  - `[low]` `[reject]` (blind 17) `role` and `template_id` are returned but not read by the UI. `template_id` records which template rendered the text (AD-7 provenance, later AI layering); dropping it changes the contract for no gain.
  - `[low]` `[patch]` (blind 18) `scripts.test.mjs` derived its path by hand from `import.meta.url`. Uses `fileURLToPath` now.
  - `[medium]` `[patch]` (edge 1) Same as blind 1; same fix.
  - `[low]` `[patch]` (edge 2) Every own Order 0 drew «Din ordre, 0 i Uke 1» on the empty baseline. `largest_order` is now null when the largest Order is 0.
  - `[false]` `[reject]` (edge 3) A logged Uke past the series. A finished game logs exactly `settings.weeks` Uker, the length of the stored series (`games.checks`).
  - `[false]` `[reject]` (edge 4) Null settings or series on a finished game. Same as blind 6.
  - `[low]` `[reject]` (edge 5) No pending state. Same as blind 11.
  - `[false]` `[reject]` (edge 6) A failed Explanation read hides step 2 with no retry. Step 1 shows «Dette steget kunne ikke hentes.» with «Prøv igjen» for that same query; a retry brings step 2.
  - `[low]` `[reject]` (edge 7) Label overlap at the right edge. Same as blind 13.
  - `[low]` `[reject]` (edge 8) The demand label on the baseline when the last Uke's demand is 0. It stays readable over its `paper` halo; a last-Uke demand of 0 is a rare fixed series.
  - `[false]` `[reject]` (edge 9) Axis ticks computed in the web app contradict "no number computed". Ticks are the drawing's scale, as on the play screen (`costAxisTop`); every data number is the api's.

## Design Notes

Decisions for the founder: step 2 is shown under step 1 once the Explanation is saved (the page reads top to bottom like `07-debrief.png`, the Explanation stays beside the data); the step pointer is not moved (9.11). The «Ordre inn: det eneste du så» key sits in the field caption, not on the plot, so it never collides with bars at 320 px. The band carries no links, so the `ink` underlined link rule has nothing to apply to here. Draft copy (`[ASSUMPTION]`): the four non-step heading variants, the role line («Det du så, var ordrene fra Detaljist, ikke kundene.» / for Detaljist «Du så kundenes ordrer selv, men bare én uke om gangen.»), the closing line «Nesten alle grupper svinger slik. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.» (from the mockup, without names), SVG title, table caption.

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis/test_sentences.py tests/debrief tests/test_migrations.py tests/test_imports.py` -- pass
- full `uv run pytest`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, play-screen specs on the lane stack -- pass

## Auto Run Result

Status: done

**Summary.** Debrief step 2 reveals the customer demand. `GET /api/debriefs/{id}/steps/2` (behind the 9.3 Explanation gate) answers `reveal`: the heading rendered by code (`analysis.sentences.demand_heading`, pure) from the Game's stored demand series with the sentence templates the Class session pinned at the lock (new content kind `sentence_templates`; version 1 by migration 0104: flat, step, step with noise, random, other series), the own Seat's Kundene / Ordre inn / Din ordre per logged Uke, and the largest own Order. The web app shows step 2 under step 1 once the Explanation is saved: the heading, the new Etterspørselsbånd (hand-made SVG) over the table Uke / Kundene / Ordre inn / Din ordre in one `GraphOverTable` region (sticky labels, sideways scroll on phones), then «Øvelsen heter Beer Game.» from the new post-reveal `nb.debrief` section, which the copy check already exempts. Step 1's «Vis som tabell» is now capped at about ten rows and scrolls inside its region under a sticky header (the 9.3 defect).

**Files.**
- `backend/app/analysis/sentences.py` (new), `analysis/__init__.py`: template shape, `render`, `demand_heading`, Norwegian number format.
- `backend/migrations/versions/0104_sentence_templates.py` (new): the kind and version 1.
- `backend/app/modules/content/{models,schemas,service,__main__}.py`, `README.md`: kind, reader, pin provider.
- `backend/app/modules/sessions/service.py`: pin registration. `backend/app/modules/games/service.py`: `demand_series(game_id)`.
- `backend/app/modules/debrief/{service,schemas,routes}.py`, `README.md`: `RevealOut` on step 2.
- Tests: `tests/analysis/test_sentences.py` (new), `tests/debrief/test_explanation.py` (step 2 against SQL; the Student is now one who shares a game), `tests/content/test_content.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py`.
- `frontend/src/components/charts/demand-band.tsx` (new), `charts.test.tsx`, `charts/README.md`.
- `frontend/src/modules/debrief/{reveal-step.tsx (new), api.ts, debrief-page.tsx, debrief.test.ts}`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts`.
- `frontend/src/components/{scroll-region.tsx, net-over-game-chart.tsx}`: the step-1 table cap.
- `frontend/scripts/scripts.test.mjs`; `frontend/e2e/{debrief-reveal.spec.ts (new), support/reveal.ts (new), debrief-explanation.spec.ts}`.
- `.docs/implementation-artifacts/screenshots/9.4/`: step 2 at 320, 360, 360 with 200 % text and 1440 px; step 1's table at 390 px.

**Deviations and decisions.** The builder implemented in its own context, as the orchestrator instructed, instead of a step-03 subagent, and ran two review layers (orchestrator rule). Decisions for the founder (also in Design Notes): step 2 shows under step 1 once the Explanation is saved, and the step pointer does not move (9.11); the heading variant is chosen from the shape of the series first, then the pattern (a noisy pattern states its level from the settings and its range from the series); the four non-step variants, the role line, the closing line, the region name and SVG titles are draft copy marked `[ASSUMPTION]`; the «Ordre inn: det eneste du så» key sits in the caption over the band, not on the plot; the band carries no links, so the `ink`-underlined link rule has nothing to apply to; `largest_order` is null when every Order is 0; the mockup's start label «4» on the band is left out (heading and table carry it); the step-1 table cap is 22 em of the caption size (about ten rows). The existing test's Student is now chosen among those who share a game: the random allocation sometimes left Student 0 alone, which failed the test under xdist.

**Review.** 27 findings (high 0, medium 2, low 17, false 8): 7 entries patched (medium: template slots must be bare names, from both reviewers; low: docstring, `_reveal` private, definite Role form, charts README row, `fileURLToPath`, no largest label when every Order is 0); nothing deferred; the rest rejected with reasons in the triage log. followup_review_recommended: false (no high, one medium entry patched).

**Verification.**
- Full backend suite after the review patch: 2884 passed in 69 s; `ruff check` and `ruff format --check` clean; the migration walk covers 0104 up and down.
- Frontend: typecheck, Vitest (55 files, 732 tests), `lint:colours`, `check:copy`, `next build` pass.
- Playwright on the rebuilt lane stack (port 8081) after the review patch: `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`: 117 passed. Before the patch one run had a `week-advance` timing failure (2 s budget under parallel load) that passed alone; play screens were not touched.
- Screens checked by eye at 360, 360 with 200 % text and 1440 px (step 2) and 390 px (step 1 table); a clipped key line at 200 % text and a 38 px sideways scroll at 1440 px were fixed before review.

Tests over 1 s: none new; `test_step_one_the_one_send_the_gate_and_the_readers` (about 3 s) now also covers step 2 on the same played game.

**Residual risks.** Draft copy awaits the founder's copy review (Issue #31). Sentence templates are immutable: a wording change is a new version through the content CLI, used by sessions locked after it. A game longer than about 38 Uker scrolls sideways on a 1440 px laptop too. The screenshots predate the review patch (the role line now reads «fra Detaljisten»).
