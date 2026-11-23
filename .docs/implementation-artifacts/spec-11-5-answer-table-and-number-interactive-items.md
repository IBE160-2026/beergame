---
title: 'Story 11.5: Answer table and number Interactive items'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'a2804362e9d9b067ddf76c359f6f285ec1ff27d2'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-4-answer-multiple-choice-items-with-autosave.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Table and number items of the open Individual test show only their title: the question set has no table or computed rule for them (only a rule name), `save_answer` refuses every non-choice value, nothing scores them, and Starting task items in the test are not rendered (FR-80, FR-52, FR-85, UX-DR38).

**Approach:** Give table and non-Starting-task number items an `interactive` spec in the question set (prompt, rows, given columns, asked column, `negative`, coded criteria), shipped as draft question set v2 by migration 0124; serve it as `table`/`column` on each item (Starting task items get their `column` from the pinned Starting task); extend `commands._valid`; add the pure `analysis.scoring.score_interactive(values, rule)`; render «Fyll inn kolonnen» as an accessible value table and number items with the reused `ColumnItem`, autosaving through 11.4's path.

## Boundaries & Constraints

**Always:**
- Content: `QuestionSetItem.interactive: InteractiveSpec | None` (optional so v1 still validates). Publish/load refuses a table item or a number item without `starting_task_item` that lacks it (stable code `interactive_missing`, in `_checked_first`), and refuses `interactive` on choice/long/Starting-task items. Spec: `prompt`, `hint?`, `caption`, `rows` (1..36 labels, table: «Uke 1»…; number: the given rows), `given` columns `{key,label,values}` (each `len(rows)` values; number: exactly one), `asked` label, `negative` (bool), `criteria` 1..8 `{code, weight, check}`, weights sum 100, unique codes; checks: `cell {row, value}` (row < answer length), `balance {added, missing}` (column key or `answer`), `flow {inflow, outflow, start}` (table only: the asked column is a stock). Interactive text never contains the word «øl» (validator) and uses «enheter».
- `analysis/scoring.py`: `InteractiveRule` (labels, given columns, criteria) and `score_interactive(values, rule) -> InteractiveScore(answered, credit, criteria=(CriterionScore(code, weight, met, explanation),…))`, pure. `flow` checks each Uke against the Student's own previous value (or `start`), so one early slip fails once, not cascading as a wrong level; any criterion needing an empty cell is not met ("Uke 4 er ikke besvart."). Credit = met weights / 100. No criterion looks at the curve's shape (no oscillation rule).
- `tests/scoring.py` `score_answer(item, value, starting_task)`: choice → `score_choice`, Starting task item → `score_sum`, table/number → `score_interactive` only. Pure; Epic 12's caller.
- Save: table value = list of `len(rows)` entries, each `null` or a strict int; number value = strict int or `null` (cleared); |v| ≤ 1 000 000; a negative only when `negative` (Starting task items: always allowed). Anything else → 422 `invalid_answer`. Items with no spec (v1 attempts) → 422.
- Api item out adds `table: {prompt, hint, caption, rows, columns:[{label, values}], asked_label, negative} | null` and `column: {prompt, hint, caption, rows:[{label, value}], asked_label, negative, starting_task} | null`. Never criteria, expected values or score.
- Frontend: generalise `autosave.ts` values to JSON (`string | number | (number|null)[] | null`), choice unchanged. `TableItem` in `frontend/src/modules/tests/` (graph-ready: table component takes values + onChange, 11.14 adds a graph over it): `<table>` with caption, `th scope="col"` headers, `th scope="row"` Uke labels (sticky left, `bg-paper`), given cells, one outlined `inputmode="numeric"` cell per Uke named «<asked>, <Uke>», «Ikke besvart» (`ink-muted`) beside the label of an empty row; inside `ScrollRegion`. Number items use `components/column-item.tsx` unchanged. Each valid change (empty clears the cell) autosaves; an invalid text is never sent, and on leaving the cell it shows `aria-invalid` + «Skriv et helt tall.» (`role="alert"`, described-by). A stored answer from another device resets the cells. Intro line on table and non-Starting-task number items: hard, also for well-educated adults (copy in `nb.ts`, [ASSUMPTION]). No right/wrong state anywhere.

**Never:** No scoring in the browser or api response; no graph (11.14); no long answers (11.6); no change to migration 0121's literal or the demo Class; no real question text (placeholders begin «Utkast:»); no new table.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Table save | `[12, null, 9, …]` len = rows | 200 stored | — |
| Wrong length / float / bool / string | `[1.5]`, `[true]`, `"12"` | nothing stored | 422 `invalid_answer` |
| Negative not allowed | `-3` where `negative=false` | nothing stored | 422 `invalid_answer` |
| Number cleared | `null` | stored `null` | — |
| Out of range | `1_000_001` | nothing stored | 422 |
| v1 item without spec | any value | nothing stored | 422 |
| Score: all right / one criterion off / empty / partial | values | credit 1 / 1 − w / 0 not answered / only met criteria | explanation per criterion |
| Cell typed «1,5» then left | — | error shown, no PUT | — |

</intent-contract>

## Code Map

- `backend/app/analysis/scoring.py` -- add `InteractiveRule`, check models, `CriterionScore`, `InteractiveScore`, `score_interactive` (pydantic for rule shape like `analysis.patterns`).
- `backend/app/modules/content/schemas.py` (~169 `QuestionSetItem`) -- `InteractiveSpec` (presentation + criteria, `.rule()` builds `InteractiveRule`), validators; export.
- `backend/app/modules/content/service.py` (~165 `_checked_first`) -- `interactive_missing` check.
- `backend/app/modules/content/files/question_set.json` -- v2: `interactive` for `tabell-nytt-monster`, `tabell-annen-bransje` (other business, e.g. bakery, `flow`), `tall-annen-bransje`, `erstatning-tabell`; `"interactive": null` on others (the file is the normalised dump; JSONB equality in `stored_version_of`).
- `backend/migrations/versions/0124_question_set_interactive.py` -- insert question_set v2 literal, id `01a1f9a0-0000-7000-8000-000000000124` (SHIPPED prefix kept by `tests/question_set` cleanup); downgrade deletes it.
- `backend/app/modules/tests/commands.py` (`_valid` ~192) -- table/number validation using the item spec and `starting_task_item`.
- `backend/app/modules/tests/attempt.py` (`_items`) -- `table`/`column` out; Starting task item from `content.starting_task(content.pinned_version(pins))` (pins via `sessions.individual_test_session_of`).
- `backend/app/modules/tests/schemas.py` (~205) -- `TableOut`, `TableColumnOut`, `ColumnOut`, `ColumnRowOut`.
- `backend/app/modules/tests/scoring.py` (new) -- `score_answer`.
- Tests: `backend/tests/analysis/test_scoring.py` (golden cases), `backend/tests/individual_test/test_answer.py` (table/number saves, item out keys), `test_open.py` (keys), `backend/tests/question_set/test_question_set.py` (v2 shipped = migration literal, v1 = 0121 literal, load «unchanged (v2)», `interactive_missing`), `backend/tests/test_migrations.py` if it lists heads.
- Frontend: `src/modules/tests/autosave.ts` (+test), new `table-item.tsx`, new `number-item.tsx` (or one `interactive-item.tsx`), shared hook `use-autosave.ts` extracted from `choice-item.tsx`, new `interactive.ts` (+test: cell parse via `games/starting-task.parseWholeNumber`, `negative` rule, texts↔values), `individual-test-page.tsx`, `copy/nb.ts`, `npm run api:generate`.
- Reuse: `components/column-item.tsx`, `components/scroll-region.tsx`, `lib/number-format.formatNumber`.
- e2e: `frontend/e2e/individual-test.spec.ts` -- stand-in test with table + number + Starting task items: keyboard-only table answer at 320/360/1440 and 200% text, axe, sticky label column, no page horizontal scroll, invalid cell error with no PUT; live: answer one table cell and reload shows it.

## Tasks & Acceptance

**Execution:**
- Backend scoring + golden tests; content schema, check, JSON v2, migration 0124; commands `_valid`; attempt/schemas out; `tests/scoring.py`; update existing tests.
- `npm run api:generate`; autosave generalisation; hook extraction; interactive helpers + Vitest; table and number items; copy; page.
- e2e as mapped.

**Acceptance Criteria:**
- Given an open attempt with a «Fyll inn kolonnen» item, when it opens, then a `<table>` with `th` scopes shows one outlined numeric cell per Uke, empty rows with «Ikke besvart», no graph.
- Given a cell typed «1,5» (or «-3» where negatives are not allowed), when the Student leaves it, then «Skriv et helt tall.» shows with the error border and nothing is sent.
- Given a valid cell or number change, when made, then it is saved through `save_answer` with a rising revision and «Lagret HH:MM» shows; a reload shows the values.
- Given the Starting task items in the set, when shown in the test, then they render with `ColumnItem` from the pinned Starting task, with no result line, and `score_answer` scores them with `score_sum`.
- Given stored table/number values, when scored, then only `score_interactive` gives the credit, per criterion with explanations; golden cases cover all right, each single criterion failing, empty and partly filled.
- Given an Interactive item, then its intro says these items are hard, from `nb.ts`, and no content text says «øl».
- Given 320/360/1440 px and 200% text, then the table item is answered by keyboard alone, axe passes, the table scrolls in its own region with a sticky label column and the page has no horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four per the runbook, since the change adds a content model, a migration and a write-path validator). Generated `openapi.json`/`schema.ts`, the shipped `question_set.json` (equal to migration 0124's literal, which was in the diff) and this spec were left out of the review diff.
- verdicts: 40 findings — high 0, medium 4, low 22, false 14, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: table/number items on a version-1 attempt fall back to their title, with a generic 422 — no attempt exists outside development (the app is not deployed); a line of its own adds copy and a state for data that cannot occur in the pilot.
  - `[low]` `[reject]` Blind: the «øl» check misses inflections and the title — `\bøl\b` matches «ØL-spillet» and «øl»; inflections in draft content are caught by the founder's content review (issue #16); the title is the Lecturer's label.
  - `[low]` `[reject]` Blind: a rule can be unsatisfiable (a cell contradicting the flow, a negative cell where `negative` is false) — a model-answer validator is a new solver for content the founder writes and reviews; the shipped rules are tested right (`test_a_stored_answer_is_scored_by_the_pure_rules_only`).
  - `[low]` `[patch]` Blind: `open_` reads the session again and, when it is gone, served the latest Starting task — now returns None (the 403) when the session is no longer the Student's; the extra read stays (one row) and the Starting task read is one cached-size row.
  - `[false]` `[reject]` Blind: `score_answer` can raise `KeyError` on a term naming a missing row — `StartingTaskItem._terms_name_rows` refuses such content at publish and read.
  - `[low]` `[patch]` Blind: test gaps — the pinned Starting task is now tested (`test_a_starting_task_item_shows_the_starting_task_its_session_pinned`); the replacement item path and `useFieldTexts`' reset are exercised by the shipped-content tests and the refusal e2e («a refused change brings it back»).
  - `[medium]` `[patch]` Blind/Edge: the stored answer lagged the cell — typing «1,5» stored 1 while the cell showed «1,5», and «Ikke besvart» followed the text, not the stored value. Now a text that is no whole number stores no value for that Uke (null, sent), the text itself is never sent, and «Ikke besvart» follows the stored values; e2e asserts the saves `[8,1,…]` then `[8,null,…]`.
  - `[low]` `[patch]` Blind: `inputMode="numeric"` has no minus on iOS — the value table gives the full keyboard when the item takes negative values; the Starting task's `ColumnItem` is Epic 6's and unchanged (its own residual, N-C4).
  - `[low]` `[reject]` Blind: migration 0124's downgrade leaves pins dangling; `max+1` may duplicate a loaded body — a downgrade is a development tool, as 0121's is; the body cannot be loaded before the migration that ships it.
  - `[low]` `[reject]` Blind: tests use content indices and a version constant — the pattern of 11.1's tests; real content (issue #16) replaces these tests' fixtures anyway.
  - `[false]` `[reject]` Blind: the reviewed diff lacks the generated client and the shipped file — left out on purpose; regenerated with `npm run api:generate` and kept equal to the migration literal by `test_the_latest_version_is_the_shipped_draft_file_and_the_migrations_literal`.
  - `[false]` `[reject]` Blind: explanations carry the expected values (an answer key) — `CriterionScore` reaches no schema or route; `test_table_and_number_items_carry_their_table_and_never_a_rule` asserts no criterion in what the Student reads; the intro is the AC's per-item line.
  - `[medium]` `[patch]` Edge: prefix stored while the cell shows invalid text — same fix as the Blind row.
  - `[low]` `[patch]` Edge: an edited stored value left behind when the text turns invalid and the tab closes — same fix (the Uke is saved empty at once).
  - `[low]` `[patch]` Edge: «Ikke besvart» disagreed with the stored value — same fix.
  - `[low]` `[reject]` Edge: v1 fallback silent — same as the Blind row.
  - `[low]` `[patch]` Edge: `open_` with None — same fix as the Blind row.
  - `[low]` `[reject]` Edge: migration downgrade — same as the Blind row.
  - `[low]` `[reject]` Edge: negative cell value with `negative: false` — same as the Blind unsatisfiable-rule row.
  - `[false]` `[reject]` Edge: a balance sum or flow past 1 000 000 — given values are at most 36 × 80 000 = 2 880 000 only in theory; the shipped rules stay small and a too-large answer is refused at save, the content review's concern (same root as unsatisfiable rules).
  - `[low]` `[patch]` Edge: duplicate column labels gave duplicate React keys — keys are now the column index.
  - `[false]` `[reject]` Edge: `score_answer` KeyError — same as the Blind row.
  - `[low]` `[patch]` Edge: a missing given value showed 0 — it now shows an empty cell (the schema already requires one value per row).
  - `[low]` `[reject]` Edge (claim): `column-item.tsx` changed though the spec says unchanged — one `id` on its caption, so a scroll region can name it; the Startoppgave's ids stay unique (`starting-task.spec.ts` passes). Recorded below.
  - `[medium]` `[patch]` Edge (claim): «nothing is sent» for an invalid cell while the prefix was — same fix as the Blind row.
  - `[low]` `[reject]` Edge (claim): «enheter» enforced only by a test — a word that must appear cannot be checked per text; the shipped items are checked.
  - `[low]` `[patch]` Verification: clearing a number answer never ran in a page test — the number e2e now empties the field and asserts `{value: null, revision: 3}` and «Lagret».
  - `[low]` `[patch]` Verification: the pinned Starting task was not told apart from the latest — new backend test publishes a changed Starting task after the lock; GET and POST keep the pinned column.
  - `[low]` `[patch]` Verification: `negative: true` unexercised — new test on `commands._valid` with a table and a number item that take negatives.
  - `[low]` `[patch]` Verification: repeated criterion codes and a balance on an unknown column untested — two cases added to `test_a_rule_that_does_not_add_up_is_refused`.
  - `[false]` `[reject]` Verification (other): `score_answer` has no caller — the story asks for the pure scorer; Epic 12 calls it.
  - `[false]` `[reject]` Verification (other): stand-ins carry hand-written JSON — the repo's pattern; the live test reads the real api and saves a cell through it.
  - `[false]` `[reject]` Intent 1: e2e fixtures differ from the backend's content — deliberate: three given columns force the region to scroll; the live test covers the real shape.
  - `[false]` `[reject]` Intent 2: 200 % text emulated by a root font size — the repo's pattern (`admin-users`, `cost-panel`); the number items are on the same page, so the page-reflow check at 200 % covers their scroll region too.
  - `[false]` `[reject]` Intent 3: keyboard tests start with `focus()` — Tab, Shift+Tab and typing carry the rest, as in 11.4.
  - `[medium]` `[patch]` Intent 4: invalid-cell semantics diverge from «the invalid value is not saved» — same fix as the Blind row.
  - `[false]` `[reject]` Intent 5: scoring is a callable with no consumer — what the AC asks.
  - `[false]` `[reject]` Intent 6: content shape invented by the diff — the AC leaves it open; recorded as a founder decision.
  - `[false]` `[reject]` Intent 7–8: the reuse clause and 11.14 readiness — met (`ValueTable` is presentational); readiness is not testable here.
  - `[false]` `[reject]` Intent 9: one live test links api and page — the repo's pattern.

## Design Notes

- Why v2 by migration: v1 is migration 0121's literal and is pinned by locked sessions; the spec is new content, so it is a new version, shipped and stored the same way (the shipped file and the migration literal stay equal, as for v1). Attempts pinned to v1 keep title-only table/number items that refuse saves.
- `flow` uses the Student's own previous value: consistency («the stock agrees with its flows») is scored separately from the level (`cell` criteria), so one slip costs one criterion, never all.
- Example rule (table, bakery stock): `K1 cell row 2 = 14` (40), `K2 flow inn/ut start 10` (60). Example (number, shortfall): `K1 balance added=answer missing=mangler` (100). Placeholder numbers only; real items are issue #16.

## Verification

**Commands:**
- `uv run pytest tests/analysis tests/individual_test tests/question_set tests/content -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Student answers «Fyll inn kolonnen» items in a value table and number items in a column, by keyboard alone, with Story 11.4's autosave. The question set gets version 2 (migration 0124, shipped as `files/question_set.json`): every table item and every number item that is not a Starting task item carries `interactive` (prompt, rows, given columns, asked label, `negative`, coded criteria), all draft «Utkast:» placeholders; the load refuses an Interactive item without it (`interactive_missing`) and any «øl» in its text. The test's items carry `table` or `column` (a Starting task item's from the Class session's pinned Starting task), never a rule or a score. `save_answer` takes a table answer as one whole number or null per row and a number answer as a whole number or null, negative only where allowed (422 `invalid_answer` otherwise; a version-1 item takes nothing). `analysis.scoring.score_interactive(values, rule)` is pure: partial credit per coded criterion (`cell` quantities, `balance` units added equal units missing, `flow` the stock agrees with its flows, judged against the Student's own row above), with an explanation per criterion and no look at the curve's shape; `tests.scoring.score_answer` routes choice, Starting task (`score_sum`) and Interactive items to their pure rules for Epic 12. The page shows an introduction above each Interactive item; `ValueTable` is an HTML table with `th` scopes, one outlined numeric cell per Uke, «Ikke besvart» beside empty Uker, a sticky label column inside its own scroll region, and «Skriv et helt tall.» (`role="alert"`, error border) on leaving an invalid cell. Number items reuse `components/column-item.tsx`. The autosave hook moved to `use-autosave.tsx` and now carries any answer value.

**Files.**
- `backend/app/analysis/scoring.py`: `InteractiveRule`, `CellCheck`/`BalanceCheck`/`FlowCheck`, `Criterion`, `CriterionScore`, `InteractiveScore`, `score_interactive`.
- `backend/app/modules/content/{schemas,service,__main__}.py`, `README.md`, `files/question_set.json`: `GivenColumn`, `InteractiveSpec`, `QuestionSetItem.interactive`, `interactive_missing`, version 2.
- `backend/migrations/versions/0124_question_set_interactive.py`: stores version 2 (the next version of the kind).
- `backend/app/modules/tests/{commands,attempt,schemas}.py`, new `scoring.py`, `README.md`: `_valid` for table/number, `table`/`column` out, `score_answer`.
- Tests: new `backend/tests/individual_test/test_interactive.py`; `tests/analysis/test_scoring.py` (golden cases), `tests/question_set/test_question_set.py` (version 2), `test_open.py`, `test_answer.py`, `tests/content/test_content.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py`.
- Frontend: new `src/modules/tests/{interactive-item.tsx,interactive.ts,interactive.test.ts,use-autosave.tsx}`; `autosave.ts` (+test), `choice-item.tsx`, `individual-test-page.tsx`, `api.ts`, `copy/nb.ts`, `components/column-item.tsx` (caption id); generated `lib/api/{openapi.json,schema.ts}`.
- e2e: `frontend/e2e/individual-test.spec.ts` (table by keyboard at 320/360/1440 and 320 with 200 % text, axe, own scroll and sticky labels; number and Starting task items; stored answer and refusal; live table cell + reload).

**Review.** Four sonnet reviewers, 40 findings: high 0, medium 4, low 22, false 14. Patched one medium entry (four rows, one root cause: an invalid cell now stores no value for its Uke, so the stored answer never lags the cell, and «Ikke besvart» follows the stored values) and low entries: `open_` returns the 403 when the session is gone between reads, full keyboard for tables that take negatives, column keys by index, a missing given value shows empty, and tests for clearing a number, the pinned Starting task, `negative: true`, repeated criterion codes and an unknown balance column. Rejected 12 low and 14 false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** Patched: high 0, medium 1 (entry), low 9 entries.

**Verification.**
- Backend: full suite `--maxprocesses=8`: 3272 passed. `ruff check` and `ruff format --check` clean. Migration walk (head to baseline and back) passes with 0124. New tests over 1 s under parallel load: `test_interactive.py::test_a_value_that_is_not_whole_numbers_in_the_items_shape_stores_nothing` about 1.2 s (20 refused saves on one opened attempt).
- Frontend: `tsc` clean, Vitest 1069 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081), 113 passed: individual-test (with axe per width and at 200 % text), homes, student-home, starting-task, order-field, order-confirm, week-table, game-start, guided-week.
- Screenshots at 320 and 1440 px and 320 px with 200 % text, checked by eye: the caption stays over the region, the label column sticks while the cells scroll, the error line under the table, «Lagret 21:14» under it; no sideways page scroll.

**Decisions taken for the founder.**
- The table and rule of an Interactive item live in the question set (`interactive`), as version 2 by migration 0124; version 1 stays for sessions pinned to it, whose table/number items show their title only and take no answer.
- Coded criteria kinds: `cell` (a quantity), `balance` (units added equal units missing; one side the answer), `flow` (the stock agrees with its flows, each Uke against the Student's own Uke before). Explanations are Norwegian sentences for the assessment, never shown to the Student.
- Draft content: four placeholder Interactive items («Utkast:», a bakery and a workshop as the other businesses); real items are issue #16.
- Each valid keystroke is saved (one save in flight); a text that is no whole number stores no value for that Uke, and the error shows on leaving the cell.
- The introduction copy (draft, [ASSUMPTION]): «Oppgaver som dette er vanskelige, også for voksne med lang utdanning. Ta én uke om gangen.», above each table item and each number item of its own, not above Starting task items.
- Cell names read «Lager, Uke 3»; the row-label heading reads «Uke».
- `components/column-item.tsx` gets an id on its caption (its only change) so the number item's scroll region can be named by it.

**Personal data.** No new table. Answers stay in `test_answers` (noted by 11.3 for Story 15.2's registry).

**Residual risks.**
- `score_answer` and `score_interactive` have no production caller until Epic 12.
- The Starting task item's field (Epic 6's `ColumnItem`) keeps the numeric keypad, which has no minus on iOS (existing residual N-C4).
- A content author can write a rule whose full credit is unreachable (a cell that contradicts the flow); the content review (issue #16) catches it, no validator does.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
