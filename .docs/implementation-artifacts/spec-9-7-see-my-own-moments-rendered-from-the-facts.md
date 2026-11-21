---
title: 'Story 9.7: See my own moments, rendered from the facts'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '1ef3c112d2bcf24662035a0ff0be6f76af666c79'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** After the reflection questions the Debrief stops: step 4 has no content, so the Student never sees three of their own moments (Week, what they saw, what they ordered, what it cost later, the Detected pattern and its mechanism, what the other Roles saw) beside their own Explanation (FR-44, FR-41, UX-DR31).

**Approach:** A pure renderer `analysis.moments.render(fact_set, templates, patterns)` fills a new immutable content kind `moment_templates` (version 1 seeded by migration 0106, pinned at `sessions.lock`) with numbers from the stored facts set only. `GET /api/debriefs/{id}/steps/4` (behind the Explanation gate) gets the Seat's facts set through `games.facts.get_or_create`, stores its `fact_set_id` once per Student in a new `debrief_fact_sets` row (new `debrief.commands.record_facts`), and answers `moments`. The web app shows step 4 once every reflection question is answered: the code heading, one moment at a time with paging, and the Student's own Explanation beside the data.

## Boundaries & Constraints

**Always:**
- Every rendered text is `{text, ai_generated: false, llm_call_id: null}` and shown without the AI prefix. Numbers come from the facts set (`seat.moments`, `seat.patterns`), plus sums of them (Posisjon, Posisjon after the Order, the gap, the later Weeks' range); every slot is filled by code (AD-7).
- Templates: kind `moment_templates`, schema `MomentTemplates` in `analysis/sentences.py`: exactly the ids of `MOMENT_TEMPLATES`, each slot one of its allowed names, no «!», no cause word (`patterns._CAUSE`). Pattern name and definition come from the pinned `detected_patterns` version.
- Step heading = template `moments-heading` from the first moment (by Week), e.g. «Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden.»; «Dette regnet du» = «Posisjon 0 − 13 + 16 = 3. Med 24 ble den 27.».
- Each moment carries: its heading text, reckoning, later cost text, pattern+mechanism texts (or the gap text when `chosen_by = order_gap`), `others` (each other Role's Ordre inn, Lager, Restordre, På vei that Week from `others_seen`), and `seen`: the Seat's stored `state_seen` of that Week (the play screen's `SeatState`) for «Dette så du».
- `debrief_fact_sets`: key `(user_id, class_session_id)`, `game_id`, `fact_set_id` (FK `fact_sets.id`), `recorded_at`; stored once (trigger refuses UPDATE). `record_facts` locks the Debrief row, inserts if absent and emits `debrief:<id>` only on insert; registry `debrief.record_facts` → `{debrief}`.
- Fewer than 10 own Orders (`seat.sm_excluded`): `moments.mostly_ai = true`, `heading` null, `moments` []; the page says the game was played mostly by AI players and the moments come from the Replay; nothing blocks the rest of the Debrief.
- A Student reads only their own Seat's moments (the endpoint takes no Student or Seat).
- UI: step 4 section under the reflection section, after the last answer; «Øyeblikk 1 av 3» heading per moment, «Forrige»/«Neste» buttons (≥ 44 px), focus moves to the new moment's heading; «Dette så du» = `WeekTable` at that Uke with the Order at nå; «Din Forklaring» shows the caller's own Explanation. Copy in `nb.debrief.moments`, draft marked `[ASSUMPTION]`.

**Never:** no AI narration (9.14) or Kjedens regning (9.8); no step-pointer move; no change to `analysis.facts`, `ANALYSIS_VERSION` or stored facts sets; no new version of `sentence_templates`; no import of `modules/players`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Moments | ≥ 10 student Orders, Explanation sent | 200 `moments: {role, student_orders, mostly_ai: false, heading, moments: [3]}`; one `debrief_fact_sets` row | — |
| Repeat read | second GET | same body, same `fact_set_id`, no new row, no event | — |
| Mostly AI | < 10 student Orders | `mostly_ai: true`, `heading: null`, `moments: []`; row stored | — |
| No Explanation | none saved | 403 `explanation_required`, nothing stored | envelope only |
| Mate | other Student of the game | their own Seat's moments only | — |
| Last Week moment | `later_weeks = 0` | template `moment-later-none` | — |
| Pattern missing | occurrence id not in pinned pattern version | `ValueError` in the renderer | 500 (data error) |

</intent-contract>

## Code Map

- `backend/app/analysis/sentences.py` -- `SentenceTemplate`, `format_number`; add `MOMENT_TEMPLATES`, `MomentTemplates`, `format_money`.
- `backend/app/analysis/facts.py:177` -- `Moment`, `PatternOccurrence`, `Seen` (input of the renderer); `patterns.py` `_CAUSE`, `PatternSet.patterns` (name, definition, mechanism).
- `backend/app/modules/content/{models,service,schemas,README}` + `sessions/service.py:2684` -- mirror `reflection_questions` (kind, reader, pin, registration).
- `backend/migrations/versions/0105_reflection_questions.py` -- pattern for 0106 (kind check, literal v1, immutable trigger).
- `backend/app/modules/debrief/{service.py step(), commands.py, models.py, schemas.py, routes.py, README.md}`; `platform/events/registry.py`.
- `backend/app/modules/games/service.py:463` `fact_set` (= `facts.get_or_create`, returns `StoredFactSet.id`); `decision_log` rows carry `state_seen: SeatState`.
- Tests: `tests/debrief/test_explanation.py` (one played game; `played()` → student Orders), `tests/games/test_facts.py` (golden Takeover game has student moments), `tests/content/test_content.py:74`, `tests/sessions/test_lock.py:90`, `tests/test_migrations.py`.
- `frontend/src/modules/games/week-table-view.tsx` `WeekTable` (reuse; add optional `label`), `frontend/src/modules/debrief/{debrief-page.tsx, reflection-step.tsx, api.ts}`, `copy/nb.ts`; e2e stubs in `frontend/e2e/support/{reflection,chain,reveal}.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/sentences.py`, new `analysis/moments.py` (+ `__init__` docstring) -- templates schema, money format, pure `render`.
- `backend/app/modules/content/*`, `sessions/service.py` -- kind, reader, pin provider.
- `backend/migrations/versions/0106_moment_templates.py` -- kind check, v1 literal, `debrief_fact_sets` + trigger.
- `backend/app/modules/debrief/*`, `platform/events/registry.py` -- table, `record_facts`, step 4 content, schemas, docs.
- `backend/tests/analysis/test_moments.py` (new) -- synthetic facts: every template path, schema refusals, number check; `tests/games/test_facts.py` -- golden Games: every number in every rendered moment appears in the facts set and equals the `seat_weeks` rows (NFR-9); debrief api test: matrix rows; content/lock/migration tests.
- `frontend/src/modules/debrief/moments-step.tsx` (new), `api.ts`, `debrief-page.tsx`, `debrief.test.ts`, `games/week-table-view.tsx`, `copy/nb.ts`, regenerated `openapi.json`/`schema.ts`.
- `frontend/e2e/debrief-moments.spec.ts` (new) + `support/moments.ts` -- stubbed: paging by keyboard with focus on the new heading, mostly-AI line, Explanation shown, axe at 320/360/1440; other debrief specs stub step 4.

**Acceptance Criteria:**
- Given a Student with ≥ 10 own Orders who has answered every reflection question, when the Debrief shows, then step 4's heading is the code-rendered first moment and three moments are paged with «Dette så du», «Dette regnet du», «Dette kostet det senere» and «Dette så de andre i Uke N», beside the Student's own Explanation.
- Given the golden Games, when pytest runs, then every number in every rendered moment appears in the facts set (or is the documented sum of its numbers) and equals the `seat_weeks` rows.
- Given 320, 360 and 1440 px, when step 4 shows, then axe passes, no sideways page scroll, and paging works by keyboard alone with focus moving to the new moment's heading.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-7.md` and `review-edge-9-7.md` in the scratchpad.
- verdicts: 23 findings — high 0, medium 0, low 15, false 8, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) A recorded `fact_set_id` that differs from `get_or_create`'s gives a permanent 500. `fact_sets` is unique per (Game, Seat), refuses UPDATE, its FK blocks deleting the Game, and `get_or_create` returns a stored row whatever its versions (9.1), so the id never changes; the check guards an impossible state.
  - `[low]` `[reject]` (blind 2) Step 4 reads the Game and the whole Decision log per request, and `logged[week]` could KeyError. The facts are built from that log, which holds every Role in every Week (validated), so the key exists; `seen` (the full `SeatState` with history) is not in the facts set. One read per view is cheap.
  - `[low]` `[reject]` (blind 3) A GET writes and emits. The spec asks to store the `fact_set_id` at the first view; it emits only on that insert, and the `debrief:` topic is not forwarded yet (9.11).
  - `[low]` `[reject]` (blind 4) `debrief_fact_sets` has no cross-check of Game, user and set, no index, and DELETE then INSERT bypasses "once". Only `record_facts` writes it, from the set the service just got for the caller's Seat; deletes come from cascades only.
  - `[low]` `[reject]` (blind 5) The reflection order is checked in the web app only. The api gate is the Explanation (FR-41); the moments are the caller's own data, so a direct call leaks nothing.
  - `[low]` `[patch]` (blind 6) A template could drop a number's slot and still validate. `MomentTemplates` now requires exactly its values (`==`), with a test case.
  - `[low]` `[patch]` (blind 7) «Mekanismen er …» read as a claim about the Student's Week. The mechanism templates now say «Mønsteret hører til mekanismen …»; spine copy («Dette kostet det senere», «Og hva det kostet kjeden») stays.
  - `[low]` `[patch]` (blind 8) «Ingen av de tre mønstrene» hard-codes the pattern count. Now «Ingen av mønstrene passer denne uka.»
  - `[low]` `[reject]` (blind 9) The step's h2 stays on the first moment while paging. The AC renders the step heading from the first moment; each moment's own h3 carries its Uke.
  - `[false]` `[reject]` (blind 10) An empty list without `mostly_ai` shows the AI line. The facts give exactly three moments whenever the Seat is not excluded (`MOMENTS <= MIN_STUDENT_ORDERS`), so the state cannot occur; Replay is named, not linked, until Epic 10.
  - `[low]` `[patch]` (blind 11) «Bare du ser den her» could mislead, since staff may read Explanations. Now «Det du skrev før avsløringen, slik du sendte den.»
  - `[false]` `[reject]` (blind 12) A failed reflection read hides step 4 silently. The reflection section reads the same query and shows «Spørsmålene kunne ikke hentes.» with «Prøv igjen».
  - `[low]` `[reject]` (blind 13) Coverage gaps (two mates with moments, HTTP mapping of a missing pattern, a session locked before the pin, the kind CHECK, `loadFailed` e2e). The route takes no Student or Seat; the pre-pin path is the shared `pinned_version` tested in content; the CHECK accepts the seeded row; the 44 px targets are checked by `expectReflow` on phone.
  - `[low]` `[reject]` (blind 14) The NFR-9 check is a subset test and the regex may split groups. The regex matches U+00A0 (`\u00a0` in the pattern); slot order is fixed by the exact-string tests and the api test compares with the renderer.
  - `[low]` `[reject]` (blind 15) The e2e stubs mix states (the third moment reuses Uke 12's state as Uke 36). The stubs test layout, paging and focus; numbers are the backend tests'.
  - `[low]` `[reject]` (blind 16) The shared Debrief test now plays 14 Uker (about 4 s to about 7 s). Ten Student Orders after four Guided Uker are the minimum the moments need through the real commands; reported under Verification.
  - `[low]` `[reject]` (blind 17) «Forrige»/«Neste» vs «Forrige øyeblikk», `focus:outline-none` on the focused heading, no live region, `RenderedTextOut` duplicating `RenderedText`, the `games.service` import. Same patterns as the reflection step; the import is the allowed one (`test_imports`).
  - `[false]` `[reject]` (edge 1) `logged[moment.week]` KeyError. Same as blind 2: the key always exists.
  - `[false]` `[reject]` (edge 2) A replaced facts set makes step 4 fail forever. Same as blind 1: a set is never replaced.
  - `[low]` `[reject]` (edge 3) Every read locks the Debrief row. One short insert per read for at most four Students; checking first adds a branch for no felt cost.
  - `[false]` `[reject]` (edge 4) `mostly_ai` false with no moments. Same as blind 10.
  - `[false]` `[reject]` (edge 5) `sm_excluded` with moments. `analysis.facts` gives `moments=()` whenever `sm_excluded`.
  - `[low]` `[patch]` (edge 6) «de tre mønstrene». Same as blind 8; same fix.

## Design Notes

A new kind rather than `sentence_templates` version 2: sessions locked since 9.4 pinned version 1, which has no moment templates, and the test fixtures delete content versions above 1. The renderer takes the pattern set because the facts store pattern ids and mechanisms, not their wording. `debrief_fact_sets` is per Student, since `debrief_sessions` is one per Game (shared by its Students) while facts are per Seat. Draft templates (v1):
- `moment-later`: «I Uke {first_week} til {last_week} kostet leddet ditt {later_cost} kr.»
- `moment-pattern`: «Mønster: {name}. {definition}»; `mechanism-supply-line`: «Mønsteret hører til mekanismen varene på vei: det som er bestilt og ikke kommet, hører med i posisjonen.»
- `moment-gap-above`: «Ingen av mønstrene passer denne uka. Du bestilte {gap} mer enn ordren inn, som var {incoming_order}.»

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis tests/debrief tests/content tests/sessions/test_lock.py tests/test_migrations.py tests/games/test_facts.py` -- pass
- full `uv run pytest`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-moments`, other `debrief-*`, `homes`, play-screen specs -- pass

## Auto Run Result

Status: done

**Summary.** Debrief step 4 shows the Student's own moments. A pure renderer `analysis.moments.render(fact_set, templates, patterns)` fills the new content kind `moment_templates` (version 1 from migration 0106, pinned at `sessions.lock` under `pins["moment_templates"]`) with numbers from the stored facts set only: the step heading from the first moment («Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden.»), and per moment its heading, «Dette regnet du» (the Posisjon sum), «Dette kostet det senere», the Detected pattern by name and definition with its mechanism, or a gap sentence. `GET /api/debriefs/{id}/steps/4` (behind the Explanation gate) takes the Seat's set through `games.facts.get_or_create`, records its id once per Student in `debrief_fact_sets` (new `debrief.commands.record_facts`, Debrief row locked, `debrief:<id>` on insert), and answers `moments` with each text as `{text, ai_generated: false, llm_call_id: null}`, the other Roles' numbers and the Seat's `state_seen` of that Uke. With fewer than 10 own Orders it answers `mostly_ai` with no moments. The web app shows step 4 after the last reflection answer: the code heading, one moment at a time with «Forrige/Neste øyeblikk» (focus to the new moment's heading), «Dette så du» as the play screen's `WeekTable` at that Uke with the Order at nå, the others table and «Din Forklaring» beside the data.

**Files.**
- `backend/app/analysis/{sentences.py (MOMENT_TEMPLATES, MomentTemplates, format_money), moments.py (new), patterns.py (CAUSE_WORDS), __init__.py}`.
- `backend/app/modules/content/{models,schemas,service,__main__,README}`, `sessions/service.py`: kind, reader, pin provider.
- `backend/migrations/versions/0106_moment_templates.py` (new): kind check, version 1, `debrief_fact_sets` + UPDATE trigger.
- `backend/app/modules/debrief/{models,commands,service,routes,schemas}.py`, `README.md`; `platform/events/registry.py` (`debrief.record_facts`).
- Tests: `tests/analysis/test_moments.py` (new), `tests/games/test_facts.py` (golden render check), `tests/debrief/test_explanation.py` (step 4 api), `tests/content/test_content.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py`.
- `frontend/src/modules/debrief/{moments-step.tsx (new), api.ts, debrief-page.tsx, debrief.test.ts}`, `modules/games/week-table-view.tsx` (`label` prop), `copy/nb.ts` (`debrief.moments`, `debrief.aiPrefix`), regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/{debrief-moments.spec.ts (new), support/moments.ts (new), debrief-reflection.spec.ts (stubs step 4)}`.

**Deviations from the epic's wording.** The renderer is `analysis.moments.render(fact_set, templates, patterns)`, not `analysis.render(fact_set, template_ids)`: it needs the pattern set for names and definitions. The moment templates are their own content kind, not a second version of `sentence_templates` (Design Notes). The «Debrief record» that stores `fact_set_id` is a per-Student row, `debrief_fact_sets`, since `debrief_sessions` is shared by a Game's Students.

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), two review layers. Draft moment templates and UI copy (`[ASSUMPTION]`, Issue #31), including «Ingen av mønstrene passer denne uka» and the mechanism sentences. Later cost is the Seat's own cost over the following Weeks (the facts' `following_weeks`), not the chain's. Step 4 opens only after every reflection question is answered (in the web app; the api gates on the Explanation). Paging by buttons with «Øyeblikk n av 3»; the own Explanation sits in the text column; «Dette så de andre» is a table by Role, no names. With fewer than 10 own Orders the page names the Replay without a link (Epic 10). `debrief.aiPrefix` «KI-generert, kan ta feil:» added now so AI text (9.14) is only a flag away.

**Review.** 23 findings (high 0, medium 0, low 15, false 8): patched 4 root causes, all low (templates must use exactly their values; mechanism sentences say «Mønsteret hører til mekanismen …»; no pattern count in the gap sentences; the Explanation note makes no privacy claim); nothing deferred; the rest rejected with reasons above. followup_review_recommended: false (no high or medium patched). Migration 0106 was re-applied (downgrade 0105, upgrade head) on the lane's `olspillet` and `olspillet_test*` databases so they hold the patched text.

**Verification.**
- Full backend suite after the patches: 2906 passed and 2 cause-word test cases failed on their own new slot rule; fixed, then `tests/analysis/test_moments.py` 24 of 24. `ruff check`, `ruff format --check` clean.
- Frontend: typecheck, Vitest (55 files, 752 tests), `lint:colours`, `check:copy`, `next build` pass.
- Playwright on the rebuilt lane stack (8081), after the patches: `debrief-moments`, `debrief-reflection`, `debrief-chain`, `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`: 134 of 134. axe at 320, 360 and 1440 px for step 4.
- Failed once, passed on rerun: in the first e2e run (while two review agents ran), 10 tests in `chain-band`, `graph-over-table`, `order-confirm` and `student-home` failed; alone they passed 58 of 58, and the later full run passed 134 of 134. None touches step 4.
- Tests over 1 s: `test_step_one_the_one_send_the_gate_and_the_readers` grew from about 4 s to about 7 s (10 s under load), as the shared game now plays 14 Uker; new `test_every_number_of_every_rendered_moment_of_the_golden_games_is_a_row_value` about 3 s alone (reuses the played-once golden Games).

**Residual risks.** Draft templates and copy await Issue #31; pattern thresholds remain placeholders. The reflection order is not enforced by the api. A session locked before migration 0106 reads the latest moment templates (only local/test data).
