---
title: 'Story 11.14: Answer drawn Interactive items in a graph'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '349a815e542d0c5eaa9fe6d258f722021028c005'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-5-answer-table-and-number-interactive-items.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The content load refuses an item of type `drawn` (`unknown_item_type`), so a Lecturer's question set cannot hold an Interactive item where the Student draws a stock over time; the test page has no graph to answer in (FR-80, UX-DR38).

**Approach:** Add the item type `drawn`: a table Interactive item (same `interactive` spec, same answer shape, same `score_interactive`) whose spec also carries a value `axis`. The test page shows it as a week table laid out with Uker as columns (given rows, then the asked row of outlined cells) under one graph field of `GraphOverTable`: an 8 px `ink` point per answered Uke joined by a 2 px `ink` line, each point a `role="slider"`, placed by drag, tap or keyboard, writing into the same answer the cells write. No shipped content changes (the drawn items themselves are issue #16).

## Boundaries & Constraints

**Always:**
- Content: `ITEM_TYPES`, `INTERACTIVE_TYPES` and `QuestionSetItem.type` take `drawn`. A drawn item is answered on its own table: the load refuses it without `interactive` (`interactive_missing`), never takes `starting_task_item`. `InteractiveSpec.axis: {min, max} | None` (strict ints, `min < max`, both within ±1 000 000, `min >= 0` unless `negative`); required on a drawn item and refused on any other (schema error → `invalid_record`). `rule("drawn")` labels are the rows, like a table. A drawn item may carry `other-business`.
- Save: a drawn value is a table value (`len(rows)` entries, each null or a strict whole number, |v| ≤ 1 000 000, negative only when `negative`); anything else 422 `invalid_answer`. Values outside the axis are accepted (the table is the answer).
- Scoring: `tests.scoring.score_answer` scores a drawn item exactly like a table: `score_interactive` over the values only. A test proves a pointer-made and a keyboard-made answer with the same values score the same (same value in → same score; the api stores no input method).
- Api: `IndividualItemOut.type` and `QuestionItemOut.type` take `drawn`; a drawn item carries `table` (as a table item does) plus `TableOut.axis: {min, max} | None` (set only for drawn). Parts: `drawn` counts as `interactive` (`service.PARTS`); `_has_content` treats it as a table.
- Frontend: `DrawnItem` in `frontend/src/modules/tests/drawn-item.tsx`: prompt, hint, one `GraphOverTable` (region «Graf og tabell» naming, one field, `bleed={false}`) whose head is a «Uke» row with `th scope="col" data-col` per Uke (the row labels) and whose body is the given rows then the asked row (`th scope="row"`), each asked cell the 11.5 outlined numeric input named «<asked>, <Uke>», «Ikke besvart» (`ink-muted`) under an empty cell, «Skriv et helt tall.» on leaving an invalid cell, autosave line. Same autosave and `useFieldTexts` semantics as `TableItem` (an invalid text stores null for that Uke and is never sent).
- Graph: new `frontend/src/components/charts/point-graph.tsx`: SVG (fixed width/height from `FieldSize`, `<title>`, `aria-hidden`) drawing the 2 px `ink` polyline through consecutive answered Uker and an 8 px `ink` dot per answered Uke, `data-mark="point"` `data-week`; no point for an unanswered Uke. Over it, one HTML `role="slider"` per Uke (44 × 44 px hit target centred on its column at its value, or at its start value when unanswered), `aria-label` the row label («Uke 3»), `aria-valuemin/max` the shown domain, `aria-valuenow`, `aria-valuetext` «Uke 3: 14 enheter» or «Uke 3: ikke besvart», `focus-visible` ring. Keys: Up/Down ±1, PageUp/PageDown ±10, Home/End min/max, clamped to the domain; an unanswered point starts from the nearest answered Uke before it, else 0 clamped. Tab order: point 1 … point n, then the table's cells. Pointer: pressing in a column places that Uke's value from the y position (rounded, clamped to the axis), dragging moves it while pressed (`setPointerCapture`), `touch-action: pan-x` so a sideways swipe still scrolls the region. Domain: the axis widened to hold every answered value; ticks on multiples of 1/2/5×10ⁿ at least 1.4 lines apart (`scales.ts`), in the sticky label column. The field row holding sliders is not `aria-hidden` (`GraphField.interactive`), the plot reads as a group named «Graf over tabellen» [ASSUMPTION].
- Submitted view: a drawn item's answer shows read-only as the 11.5 answered table. Lecturer question-set block and item type lines name `drawn` («Graf» / «Tegn i grafen» [ASSUMPTION]). Copy only from `nb.ts`; no scoring in the browser.

**Never:** No change to the shipped question set or a new migration; no new table; no right/wrong state; no drag-only action; no chart library outside `components/charts`; no change to `ValueTable`'s vertical layout for table items.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Load set with drawn item | drawn item with `interactive` + `axis` | stored | — |
| Drawn item without `interactive` | — | nothing stored | `interactive_missing` |
| Drawn item without axis / axis on table | — | nothing stored | `invalid_record` |
| Save drawn | `[12, null, 9]` len = rows | 200 | — |
| Save drawn wrong shape | `12`, `[1.5]`, short list | nothing stored | 422 `invalid_answer` |
| Keyboard Up on point 3 at 14 | — | cell 3 shows 15, saved `[…,15,…]`, «Lagret» | — |
| Typed cell 3 = 20 | — | point 3 moves to 20, line redrawn | — |
| Tap in column 2 at y of 30 | — | cell 2 shows 30, saved | — |
| Unanswered Uke 4 | null | no point, slider valuetext «Uke 4: ikke besvart» | — |

</intent-contract>

## Code Map

- `backend/app/modules/content/schemas.py` (~162 `ITEM_TYPES`, ~167 `INTERACTIVE_TYPES`, ~187 `InteractiveSpec`, ~220 `rule`, ~247 type literal, ~262 `_key_or_rule`, ~293 `needs_interactive`) -- add `drawn`, `Axis`, axis validators.
- `backend/app/modules/content/service.py` (~143 `_item_types_known`) -- `own_table` includes `drawn`; `README.md` codes.
- `backend/app/modules/tests/commands.py` (~304 `_valid`) -- drawn = table shape.
- `backend/app/modules/tests/attempt.py` (~64 `_table`) -- drawn served with `table`, axis.
- `backend/app/modules/tests/schemas.py` (~85 `QuestionItemOut.type`, ~205 `TableOut`, ~296 `IndividualItemOut.type`) -- `drawn`, `AxisOut`.
- `backend/app/modules/tests/scoring.py` (~59) -- drawn like table. `service.py` (~200 `PARTS`, `_has_content`).
- Tests: `backend/tests/individual_test/test_interactive.py` (patterns: `commands._valid` with a hand-made `QuestionSetItem`, scoring of shipped items), `backend/tests/question_set/test_question_set.py` (~180–240 load codes via `__main__`; a fixture set loader), `backend/tests/games/helpers.py`.
- Frontend: `src/modules/tests/interactive-item.tsx` (export `useFieldTexts`, extract the cell input as `CellInput`), new `drawn-item.tsx`, `interactive.ts` (`isInteractive` drawn; pure `pointValue`, `startValue`, `stepValue`), `interactive.test.ts`, `individual-test-page.tsx` (~290), `submitted-items.tsx` (~121), `individual-test.ts` (unanswered: table-shaped), `copy/nb.ts` (~2915 types, ~3044 types, ~2941 interactive), `npm run api:generate`.
- Charts: `src/components/graph-over-table.tsx` (field rows `aria-hidden` at ~363: add `interactive` field flag), new `src/components/charts/point-graph.tsx`, `scales.ts` (`niceTicks`), `charts/README.md` row, `charts.test.tsx` for the import rule.
- e2e: `frontend/e2e/individual-test.spec.ts` (stand-in route pattern of 11.5) or new `e2e/drawn-item.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Backend content/commands/attempt/schemas/scoring/service + tests (load accepts a set with a drawn item through the content load; refusals; save shapes; score same values same; item out carries table + axis).
- `npm run api:generate`; frontend helpers + Vitest; `GraphOverTable.interactive`; `PointGraph`; `DrawnItem`; page, submitted view, copy, question-set block.
- e2e: stand-in test with one drawn item: point placed by keyboard (Tab into graph, Up/PageUp) and by pointer (tap and drag) at 320/360/1440 px and 320 px at 200 % text, axe per width, point x within 1 px of its `th[data-col]` centre, one scroll region holding graph and table, no page horizontal scroll, typing a cell moves the point, save bodies asserted.

**Acceptance Criteria:**
- Given a question set holding a `drawn` item, when the content load runs, then it is stored (api test), and a drawn item without its table is refused `interactive_missing`.
- Given a drawn item in an open attempt, when opened, then one graph shows over its week table with an 8 px `ink` point per answered Uke joined by a 2 px `ink` line and no point for unanswered Uker.
- Given a drag, a tap or a keypress on a point, when placed, then that Uke's cell shows the value and it is saved through `save_answer` with «Lagret HH:MM»; typing in a cell redraws the point.
- Given a keyboard user, when tabbing in, then each point is a `role="slider"` named «Uke n» with valuetext «Uke n: v enheter», Up/Down ±1, PageUp/PageDown ±10, Tab goes point to point and then into the table.
- Given equal values entered by pointer or keyboard, when scored, then `score_interactive` gives the same score (test).
- Given 320/360/1440 px and 200 % text, then axe passes, the points line up with their columns and graph and table scroll as one region.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, since the change routes a new item type through scoring and the content model). The generated `openapi.json`/`schema.ts` and this spec were left out of the review diff.
- verdicts: 38 findings — high 0, medium 2, low 24, false 12, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: the axis is not checked against the item's own expected values — a model-answer check against the rule is a new validator for content the founder writes (issue #16); a value off the axis is still answered in the table. Same root as 11.5's unsatisfiable-rule residual.
  - `[low]` `[patch]` Blind: keys and pointer clamp to different ranges, while `Axis` said both use the axis — the keys move within what the graph shows (spec); the `Axis` docstring now says the axis bounds the pointer and the keys move within the shown range.
  - `[low]` `[reject]` Blind: a typed outlier rescales the graph on each keystroke — the spec's choice (no point is ever cut); the table holds the typed value either way.
  - `[low]` `[patch]` Blind: no way to clear a point from the graph; Left/Right do nothing — Right/Left now step like Up/Down (the slider pattern). Clearing stays in the table cell (emptying it), which a branch for Delete would only duplicate.
  - `[low]` `[reject]` Blind: `touch-pan-x` keeps a vertical page scroll from starting on the graph — the vertical drag is the drawing gesture the contract keeps; the page scrolls from anywhere outside the 11 em graph, and the table answers without it. The accidental-write half is the edge row below (patched).
  - `[low]` `[patch]` Blind: modifier keys intercepted; `aria-valuenow` of an unanswered Uke is its start — keys with Ctrl, Alt or Meta are now left to the browser (e2e `Alt+ArrowUp`). `aria-valuenow` is required on a slider; `aria-valuetext` («Uke 3: ikke besvart») is what assistive technology reads.
  - `[low]` `[patch]` Blind: «1 enheter» — `valueText` now says «1 enhet» (Vitest). The unit is FR-80's «enheter» by rule.
  - `[false]` `[reject]` Blind: the `{min: 0, max: 10}` fallback hides a missing axis — the schema refuses a drawn item without an axis at load and at every read (`_key_or_rule`), so the api never serves one; the fallback only satisfies the type.
  - `[low]` `[patch]` Blind: the y scale is written twice (points and axis labels could drift) — one `scaleY` in `charts/scales.ts` now serves both (Vitest). The table markup is the transposed layout, not `ValueTable`'s (spec).
  - `[false]` `[reject]` Blind: a drag fires dozens of PUTs — `useAutosave.send` keeps one save in flight and sends the newest value after it (`use-autosave.tsx` `sending` ref).
  - `[low]` `[reject]` Blind: test gaps (negative axis, error path, Home/End, refusal, one long e2e) — Home/End and the negative axis are Vitest/pytest cases; the error path and refusal are the shared `CellInput`/`useAutosave` covered by 11.5's e2e; the parts and hand-in gaps are the verification rows below (patched).
  - `[low]` `[reject]` Blind: `niceTicks` does not label the axis ends — the same rule as `netTicks` (multiples of the step); the gridlines and points show the range.
  - `[low]` `[patch]` Blind: no shipped item and no author docs for `axis` — the content README now documents `drawn` and `axis`; no shipped item is the recorded decision (issue #16).
  - `[low]` `[reject]` Blind: the handed-in view shows a table, not the graph — the graph is a view of the table (AC); the read-only table holds every value.
  - `[low]` `[reject]` Blind: tests parse codes with `split(": ")`, `drawn_set` naming — the pattern of `test_question_set.py`'s load tests.
  - `[medium]` `[patch]` Edge: a touch press placed a value before the browser decided to scroll; `pointercancel` did not undo it — a touch or pen press now places on lifting (a tap) or once the finger moves 6 px vertically (a drag); a sideways swipe cancels and places nothing (e2e with touch pointer events).
  - `[low]` `[reject]` Edge: vertical swipe or pinch blocked on the graph — same as the Blind touch row.
  - `[low]` `[patch]` Edge: modified keys swallowed — same fix as the Blind row.
  - `[low]` `[patch]` Edge: a lost `pointerup` keeps the drag alive — a move with no button held now ends the press.
  - `[low]` `[patch]` Edge: a 44 px target at the range's ends overhangs the plot and is clipped by the region — the plot now keeps half a target (22 px) free above and below.
  - `[low]` `[reject]` Edge: the first key on an unanswered Uke moves 1 from the start value — the spec's rule; one more key places «same as before».
  - `[low]` `[patch]` Edge: several moves before a render place the same value more than once — the item remembers the last value a pointer placed per Uke and places each once.
  - `[low]` `[patch]` Edge: `niceTicks` with font size 0 or NaN builds a huge tick list — returns the low end only (Vitest).
  - `[low]` `[patch]` Edge: a range too small for its step gives no ticks — the ends are labelled then (Vitest).
  - `[false]` `[reject]` Edge: the `{0, 10}` axis fallback — same as the Blind row.
  - `[false]` `[reject]` Edge: `box.current` null in a pointer event — the handler now reads the event's own target; an event on the element means it is mounted.
  - `[medium]` `[patch]` Edge (claim): «a sideways swipe still scrolls the region» while a value was written — same fix as the touch row.
  - `[low]` `[patch]` Edge (claim): fewer labels than claimed on short plots — same fix as the tick row.
  - `[low]` `[patch]` Verification: `"drawn": "interactive"` in `PARTS` untested — `test_drawn.py` now checks the part is False with every point empty and True once one is answered.
  - `[low]` `[patch]` Verification: the hand-in view of a drawn item untested — e2e «a handed-in drawn item shows its values in its table, read-only».
  - `[false]` `[reject]` Intent 1: backend tests never touch the page — the repo's split; the page test reads the generated client's shapes.
  - `[false]` `[reject]` Intent 2: the e2e uses a stand-in, not the real api — the repo's pattern (11.5); the backend test asserts the same `table.axis` shape the stand-in carries.
  - `[false]` `[reject]` Intent 3: score equality holds by construction — that is the point: the api stores values only, the test proves the same values score the same, and the e2e proves both input methods store the list.
  - `[false]` `[reject]` Intent 4: no shipped drawn item — the story is optional for the pilot and nothing depends on it; real items are issue #16 (founder decision recorded).
  - `[false]` `[reject]` Intent 5: a transposed table rather than 11.5's vertical one — «the graph columns line up with the table columns» needs Uker as columns; the cells and their behaviour are 11.5's (`CellInput`, `useFieldTexts`).
  - `[false]` `[reject]` Intent 6: the sliders are exposed besides the table — the AC asks for focusable `role="slider"` points; focusable content may not be `aria-hidden`. The table alone answers the item.
  - `[false]` `[reject]` Intent 7: added surfaces untested — the axis is tested in pytest, the hand-in view now in e2e; the Lecturer label is one copy entry.
  - `[false]` `[reject]` Intent 8: alignment checked on the stand-in page only — the page is the real page; only the api answer is stood in.

## Design Notes

- Why a transposed table for drawn items: «the graph columns line up with the table columns» needs Uker as columns, which is the `GraphOverTable` pattern every other graph-over-table uses (measured `th[data-col]` centres, sticky label column, one scroll region). Table items keep 11.5's vertical `ValueTable`.
- Why an `axis` in content: a pointer maps y to a value and a slider needs a range; a stock drawn over time can exceed every given value, so the range is the content author's, not derived. Typed values beyond it widen the shown domain so no point is cut.
- Why no shipped drawn item: the story is optional for the pilot and real items are issue #16; the api and e2e tests use their own sets.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/question_set tests/content tests/analysis -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests src/components` -- pass
- `npx playwright test e2e/drawn-item.spec.ts e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The question set takes a fourth Interactive type, `drawn`: a table item (same `interactive` table and computed rule, same answer of one whole number or null per Uke) with a value `axis` for its graph, required on a drawn item and refused elsewhere; `axis` is left out of stored bodies when absent, so version 2 stays unchanged. The content load accepts a set holding one; `save_answer` takes the table's shape; `tests.scoring.score_answer` scores it with `score_interactive` over the values alone; it counts for the Interactive part. The Student's page shows a drawn item as one `GraphOverTable` region: a hand-made SVG (`components/charts/point-graph.tsx`) with an 8 px `ink` point per answered Uke, a 2 px `ink` line between answered neighbours, `hairline` grid lines and axis labels in the sticky column, over a table with the Uker as columns (given rows, then the asked row of 11.5's outlined cells). Each Uke is a `role="slider"` named «Uke 3» with «Uke 3: 14 enheter», Up/Right ±1, Page Up/Down ±10, Home/End; Tab runs point to point, then into the table. A mouse press places and drags; on touch a tap places on lifting, a vertical drag moves, and a sideways swipe scrolls the region and places nothing. Graph and table are one answer, autosaved through Story 11.4's path. The handed-in view shows the values in the read-only table.

**Files.**
- `backend/app/modules/content/{schemas,service}.py`, `README.md`: `drawn`, `TABLE_TYPES`, `Axis`, `InteractiveSpec.axis`.
- `backend/app/modules/tests/{commands,attempt,schemas,scoring,service}.py`: drawn saved, served (`TableOut.axis`, `AxisOut`), scored and counted as a table item.
- Tests: new `backend/tests/individual_test/test_drawn.py`; `test_interactive.py` (`axis: None`).
- Frontend: new `src/components/charts/point-graph.tsx`, `src/modules/tests/drawn-item.tsx`; `charts/scales.ts` (`niceTicks`, `scaleY`), `graph-over-table.tsx` (`GraphField.interactive`: the row is not `aria-hidden`), `modules/tests/{interactive.ts, interactive-item.tsx (CellInput, useFieldTexts exported), individual-test-page.tsx, submitted-items.tsx}`, `copy/nb.ts`, generated `lib/api/{openapi.json,schema.ts}`; Vitest in `charts.test.tsx`, `interactive.test.ts`.
- e2e: new `frontend/e2e/drawn-item.spec.ts`; `individual-test.spec.ts`: one pre-existing click race fixed (`check` → `click` where the refusal replaces the item at once; it failed 2 of 3 widths under load).

**Review.** Four sonnet reviewers, 38 findings: high 0, medium 2 (one entry), low 24, false 12. Patched the medium entry (a touch press wrote a value before the browser chose to scroll) and the low entries listed in the triage log; rejected the rest with their reasons there. Nothing deferred.

**Follow-up review: not recommended.** Patched: high 0, medium 1 entry, low 13 entries.

**Verification.**
- Backend: full suite `--maxprocesses=8`: 3674 passed, 4 skipped. `ruff check` and `ruff format --check` clean. No migration.
- Frontend: `tsc` clean, Vitest 1173 passed, `lint:colours` and `check:copy` pass; `next build` ran in the lane-2 frontend image build (healthy).
- Playwright on lane 2 (8081): drawn-item (×3 repeats, 18 passed), individual-test, graph-over-table, week-table, homes, student-home, game-insight, debrief-reveal: 133 passed after the race fix (the fixed test 9/9 over three repeats). Axe at 320, 360, 1440 px and 320 px with 200 % text.
- Screenshots at 320 px with 200 % text and 1440 px checked by eye: caption over the region, grid and points over their columns, the row labels sticky, «Ikke besvart» under empty cells, no sideways page scroll.
- New tests over 1 s: `test_drawn.py::test_a_drawn_item_is_served_with_its_table_and_axis_and_saved_as_a_table` about 1.3 s (locks a session and opens an attempt, like 11.5's).

**Decisions taken for the founder.**
- The graph's range is content: `axis {min, max}` on a drawn item; a typed value beyond it is still an answer and widens the graph; a pointer places within the axis, keys within what the graph shows.
- A drawn item's table has the Uker as columns (so the points stand over their cells); table items keep 11.5's vertical table.
- No drawn item in the shipped draft set (the story is optional; real items are issue #16). Nothing is behind a flag: the epic names none, and without content no Student meets the item.
- An unanswered Uke's point starts from the Uke before it (else 0); clearing a value is done in the table.
- Copy [ASSUMPTION]: type «Tegn i grafen» (Student) / «Graf» (Lecturer); «Dra eller trykk i grafen, bruk piltastene, eller skriv i tabellen. Grafen og tabellen er samme svar.»; region «Graf og tabell: <caption>»; group «Graf over tabellen»; «Uke 3: ikke besvart»; «1 enhet».

**Personal data.** No new table. Answers stay in `test_answers`.

**Residual risks.**
- On a touch screen a vertical page scroll cannot start on the graph (the vertical drag draws); the page scrolls from outside it.
- A content author can set an axis that does not hold the right answer; the content review (issue #16) catches it.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
