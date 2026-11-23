---
title: 'Story 13.10: The Student report documents the Debrief, the Replay and the Individual test'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '14d719847556a8475126b1d9611ef48e167416a9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-8-student-report-shows-the-game-with-its-charts.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Student report (Stories 13.7, 13.8) holds the header, «Fullføring» and the game; it does not document the Explanation, the key moments, the quiz attempts, the Replay or the Individual test (FR-58, FR-47).

**Approach:** Three more sections through the registry on both sides. `report_data.SECTIONS` gains `debrief`, `replay`, `test`, each read through its owning module's new report read (`debrief.service.report_debrief`, `replay.walkthrough.report`, `tests.service.report_test`); the print route renders each, with the Replay chart and the Interactive item images at a fixed width followed by their tables. The Interaktiv oppgave's read-only rendering moves to `frontend/src/components/`. AI text carries the prefix and a machine-readable mark in the tagged PDF.

## Boundaries & Constraints

**Always:**
- Every section is present whatever the Student did; a step not done says so in words and the report is still built (`done: false` / null part). Order: completion, game, debrief, replay, test.
- Debrief: the Explanation as written (and when it was saved); the summary's key moments (Uke, heading, reckoning, later, patterns) and the step-4 narration line, each as `{text, ai_generated}`; reflection answers on `evidence` and `structure` questions with their prompts, **never** `feelings` answers; the number of quiz attempts (as the summary counts them: up to the pass) and whether the quiz is passed. Nothing of another Student.
- Reflection step: one line in `nb.debrief.reflection` (draft, for review) saying the Lecturers and Assistant lecturers of the Class read the answers and that the answers on feelings are not in the Student report.
- Replay: state `finished` / `closed` (end_reason) / `open`; the scenario as the Replay's own settings (Rolle, Uker, Veiledede uker, starting inventory and backlog, the three delays, the two costs); its Totalkostnad; its Netto lager per Uke with Ordre and Kostnad så langt, beside the Class game's run (as the walkthrough compares: the recorded compared game, else `student_game`; left out when the Class game was mostly AI, said in words); «Ikke like for like.» with the walkthrough's reasons whenever both runs show. Chart: `NetOverGame` at a fixed width with its `<title>`, the table after it.
- Test: every frozen item in order with its question (an Adapted item's wording; AI wording prefixed), the Student's saved answer or «Ikke besvart», and for choice, table, number and drawn items the stored computed score (`test_answers.score`, credit × the frozen weight, «Poeng: 7,5 av 10»); a line with the sum of those. Long answers and Adapted items get no score. No AI score, feedback or Indicative letter.
- Interactive items with a value table (table, drawn): the Student's values as the drawn item's points-and-line graph (fixed width, `<title>`) over the value table (Uker as columns, given rows and the Student's row, `th` scopes). A number item: its column as a table with the Student's answer.
- AI text in the PDF: «KI-generert, kan ta feil: «…»» from `ai_generated` only, on an element with `data-ai-generated="true"`; the render maps that to a `/UserProperties` attribute (`ai_generated` = true) on the element's PDF structure element. PDF/UA-1 stays compliant.
- Reading order = visual order; each chart followed by its table; every table has `th` with scope; numbers through `formatNumber`.

**Never:** no AI assessment, AI score, AI feedback or Indicative letter (13.11 / Epic 12); no merge of Epic 12; no other Student's name, Explanation or answer; no second chart implementation; no client-side code in the print route; no new table or migration; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Every step | Debrief finished, quiz passed, Replay finished, test submitted | three sections filled | — |
| No Orders | Student seated, never played; nothing else | debrief/replay/test sections present, each «ikke gjort» | report built |
| No test | game, Debrief, Replay; no attempt | test section `test: null`, «Testen ble ikke levert.» | — |
| Explanation only | Debrief started, not finished | Explanation shown, summary line «Debriefen ble ikke fullført.» | — |
| Feelings answers | summary holds feelings + evidence + structure | only evidence and structure in the snapshot | — |
| Replay closed | Replay ended at the Test deadline | scenario + line that it was closed unfinished, no chart | — |
| Mostly-AI Class game | compared facts `sm_excluded` | Replay alone, line saying why | — |
| AI text | narration or Adapted wording `ai_generated` | prefixed, `data-ai-generated`, `/UserProperties` in PDF | — |
| Open test | attempt still `open` (staff download before deadline) | items with saved answers, line «Testen er ikke levert ennå.», no scores | — |

</intent-contract>

## Code Map

- `backend/app/modules/reports/report_data.py` -- `SECTIONS`, `AnySection` union, models after `GameSectionOut`; add `_debrief_section`, `_replay_section`, `_test_section`.
- `backend/app/modules/debrief/service.py` -- `_stored` (:521) Explanation, `_summary_row` (:1150), `_summary` (:1169, moments + reflection + attempts), `_questions` (:966, kinds), `_attempts` (:1314), `_narration` (:725, takes a `DebriefRow`: widen to ids), `rules.debrief_game`. Add `report_debrief(user_id, class_session_id)`.
- `backend/app/modules/replay/walkthrough.py` -- `_run` (:323), `_role_total`, `_recorded`, `shown`/`mostly_ai` via compared `fact_set(...).facts.seat.sm_excluded`; `repo.replay_game`. Add `report(user_id, class_session_id)`.
- `backend/app/modules/tests/attempt.py` -- `_items` (:131) builds `IndividualItemOut`s; `commands.attempt_of`; `test_answers.score` JSON `{answered, credit, criteria}` (commands.py :458); frozen items carry `weight`. Add `report_test` (exported from `tests.service`).
- `backend/app/modules/reports/render.py` -- `_convert` (:58) WeasyPrint `pdf/ua-1`; new `reports/pdf_marks.py` wraps `weasyprint.pdf.tags._build_box_tree` (v70) to add `/A <</O /UserProperties /P [<</N (ai_generated) /V true>>]>>` on `p`/`span` elements with `data-ai-generated="true"`, and `MarkInfo /UserProperties true`.
- `frontend/src/app/print/report/{sections.tsx,copy.ts}` -- registry; new `debrief-section.tsx`, `replay-section.tsx`, `test-section.tsx`, pure `parts.ts`.
- `frontend/src/modules/tests/{interactive.ts,submitted-items.tsx,drawn-item.tsx,interactive-item.tsx}` -- pure helpers and `AnsweredTable` move to `frontend/src/components/interactive.ts` / `interactive-answer.tsx`; `components/charts/point-graph.tsx` splits out the static `PointMarks`.
- `frontend/src/components/charts/net-over-game.tsx` -- Replay chart (as `modules/replay/walkthrough-chart.tsx` uses it); `modules/replay/walkthrough.ts` `unlikeReasons`, `walkthroughRows` reused for words.
- `frontend/src/copy/nb.ts` -- `debrief.reflection` gets `report`; `modules/debrief/reflection-step.tsx` shows it.
- Tests: `backend/tests/reports/test_report_game.py` (`built`, `short_game`, `play_weeks`, `confirmed`); `tests/debrief/test_explanation.py::finished`, `tests/replay/test_walkthrough.py`, `tests/individual_test/test_submit.py`; e2e `frontend/e2e/student-report.spec.ts` (fixture), `support/live-game.ts` `orderByApi`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/debrief/service.py` -- `report_debrief` (no principal: the report job runs after the policy) -- FR-58, FR-47.
- `backend/app/modules/replay/walkthrough.py` -- `report` -- FR-58, UX-DR70.
- `backend/app/modules/tests/attempt.py`, `service.py` -- `report_test` -- FR-58, C-2.
- `backend/app/modules/reports/report_data.py` -- three sections and models.
- `backend/app/modules/reports/pdf_marks.py`, `render.py` -- the PDF mark.
- Backend tests: `tests/reports/test_report_steps.py` (no Orders; Explanation only without a test; feelings left out with stubbed reads; every step through the stubbed reads), plus report-read asserts in the existing long Debrief, walkthrough and submit tests; `tests/reports/test_pdf_marks.py` (skipped without WeasyPrint).
- `npm run api:generate`.
- Frontend: components move + `PointMarks`; print sections + copy; Vitest for the pure parts and the renders; nb.ts line.
- `frontend/e2e/student-report.spec.ts` -- fixture: 12 own Orders then playout; real Debrief through the api (Explanation, step 4, reflection answers, finish), one quiz attempt then the dev pass, a Replay played to its end by the api, the test opened, answered and submitted; sample PDF for veraPDF.

**Acceptance Criteria:**
- Given the e2e sample PDF, when `scripts/verapdf` runs, then it is PDF/UA-1 compliant with every section present.
- Given a Student with every step, when the report is built, then the Debrief holds the Explanation, the moments and the attempts but no feelings answer, the Replay the scenario, Totalkostnad and runs with «Ikke like for like.», the test every item with answers and stored scores and no AI data.
- Given a Student with no Orders, or without a test, when the report is built, then the missing sections are present and say not done.
- Given AI text in the snapshot, when the print route renders, then it reads «KI-generert, kan ta feil: «…»» with `data-ai-generated="true"`.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: four on Sonnet (blind, edge case, verification gap, intent alignment), as the lane brief directs for a change that touches the report pipeline and three modules' reads.
- verdicts: 32 findings — high 0, medium 3, low 21, false 6, maybe-false 2
- findings:
  - `[low]` `[reject]` Blind: `report` returns None for a Replay with no game, no Student Seat or no settings. Not reachable: `replay.start` makes the Game, its Seats and settings in one transaction with the `replays` row.
  - `[medium]` `[patch]` Blind: a closed or open Replay's played Uker are in the snapshot but not shown. The section now draws the Uker it had (cost, chart, table, the Replay alone) whenever it has any; Vitest covers closed and unplayed.
  - `[low]` `[reject]` Blind: no words when a finished Replay's Class game cannot be read. Only a Class game without a facts set; a Replay needs a finished Debrief, which builds it.
  - `[low]` `[patch]` Blind: `pdf_marks.wrap` dropped the mark on an element with its own `A`. Now kept as an array beside the property; unit test updated.
  - `[maybe-false]` `[reject]` Blind: anonymous boxes inside a marked `p` might carry the property twice. Would only be low; the sample is PDF/UA-1 compliant with the mark (veraPDF).
  - `[low]` `[patch]` Blind: `MarkInfo /UserProperties` was written even with no AI text, so the e2e check proved little. The finisher now writes it only when a property was added (flag on the PDF object); unit tests cover both; the e2e still finds it on the sample with the AI line.
  - `[low]` `[reject]` Blind: `install()` untested. The e2e renders through it and finds the property; a WeasyPrint without the function fails the render.
  - `[low]` `[reject]` Blind: the feelings check in the test uses the question id. The pinned questions' `feelings` id is the only feelings question; the code filters by kind.
  - `[low]` `[reject]` Blind: `report_debrief` reads attempts twice. Same rows, read-only job; the new quiz test shows they agree with the summary.
  - `[false]` `[reject]` Blind: points contradict FR-54. FR-58 and the story require the scores in the report; FR-54 governs the test page.
  - `[low]` `[reject]` Blind: `options` unused. The API carries option ids only; the report writes «Alternativ B» as the test page does.
  - `[low]` `[patch]` Blind: `report_data.py` imported `tests.schemas` (the import-rule test failed too). Now through `tests.service`.
  - `[false]` `[reject]` Blind: non-personal Debrief blames the Student. Every mode has the Explanation, summary and quiz per Student; the steps are fixed (FR-17).
  - `[low]` `[patch]` Blind/Edge: the e2e Replay loop swallowed failures. It now expects 409 past the last Uke, more than 20 Uker, and `status: finished`.
  - `[low]` `[reject]` Blind: the reflection line overlaps the privacy hint. The story requires the line; draft copy for review.
  - `[false]` `[reject]` Blind: corner `th scope="row"` in the header. The test page's drawn item does the same; veraPDF compliant.
  - `[low]` `[patch]` Blind: moments keyed by Uke. Now by index.
  - `[low]` `[reject]` Edge: attempt, answers and scores read in separate statements. A handed-in attempt never changes; an open one at the deadline is the next row.
  - `[low]` `[reject]` Edge: a report at the Testfrist before the sweep shows «ikke levert». True at that moment; the PDF is regenerated on request.
  - `[maybe-false]` `[reject]` Edge: an unreadable facts set aborts the report. Would only be low: the render fails with the retry line (Story 13.7), as for any read error.
  - `[low]` `[reject]` Edge: any section error fails the whole job. Same as above, by the pipeline's design.
  - `[low]` `[reject]` Edge: reflection answers without a finished Debrief are left out. The story asks for the summary; the section says the Debrief was not finished.
  - `[false]` `[reject]` Edge: a Replay with no Seat prints «Du spilte ikke Replay». Not reachable (see the Blind row).
  - `[low]` `[reject]` Edge: no reason when the Class game comparison is missing. As the Blind row.
  - `[low]` `[reject]` Edge: a table item without its table and an array answer prints «Ikke besvart». Only version-1 attempts, which refused such answers.
  - `[low]` `[patch]` Edge: a boolean credit would raise. `_points` refuses bools.
  - `[false]` `[reject]` Edge (claim): `test_pdf_marks.py` does not skip without WeasyPrint. It needs only pydyf, a dependency of WeasyPrint; it runs everywhere.
  - `[low]` `[patch]` Edge (claim): closed Replay Uker not shown. Same as the Blind row.
  - `[medium]` `[patch]` Verification gap: `report_debrief`'s quiz count, pass and `late` not tested on real rows. `test_quiz.py` now asserts 2 attempts, passed, and `late` as the summary.
  - `[medium]` `[patch]` Verification gap: the Replay read's open, closed, mostly-AI and pre-record paths untested. `test_close.py` asserts open (1 Uke), closed (1 Uke, no comparison) and finished with a mostly-AI Class game; `test_walkthrough.py` asserts the comparison before any record equals the recorded one.
  - `[low]` `[patch]` Verification gap: scenario and run mapping. The stub test uses distinct settings and asserts every scenario field and each Uke's Order and cost.
  - `[false]` `[reject]` Intent alignment: descriptive report; its divergences (stubbed every-step composition, PDF checked by the e2e and veraPDF) are the ones above, covered by the real-row reads, the e2e and the manual page reading.

## Design Notes

The three reads live in their owning modules and take ids only (like `completion_status`): `reports` never reads their tables. The report's section models copy only what it shows, so the snapshot has no ids, LLM call ids, criteria explanations or weights other than the item's own.

## Verification

**Commands:**
- `uv run pytest tests/reports -q` -- pass
- `npm run typecheck && npx vitest run src/app/print src/components src/modules/tests src/modules/debrief` -- pass
- `npx playwright test e2e/student-report.spec.ts` then `python scripts/verapdf frontend/test-results/student-report.pdf` -- compliant

## Auto Run Result

Status: done

**Summary.** The Student report now documents the Debrief, the Replay and the Individual test (FR-58, FR-47, FR-34, UX-DR70). `report_data.SECTIONS` gains `debrief`, `replay` and `test`, always present, each read through its owning module by ids (`debrief.service.report_debrief`, `replay.service.report_replay`, `tests.service.report_test`). Debrief: the Explanation as written, the summary's key moments and the step-4 line, the answers on evidence and structure (never feelings, said in a line), the quiz attempts up to the pass. Replay: the scenario as the Replay's own settings, Totalkostnad, Netto lager of both runs in `NetOverGame` at a fixed width with the walkthrough's table after it, «Ikke like for like.» with its reasons; a mostly-AI Class game left out; a closed Replay shows the Uker it had. Test: every item with its question, answer and the stored computed points (credit × weight), a total over the scored items; no AI data. Table and drawn items are drawn as the answer's points over the value table (`components/interactive-answer.tsx`, where the Interaktiv oppgave's rendering moved: `pointField`, `AnsweredTable`, `InteractiveAnswer`, `AnsweredColumn`; `PointMarks` split from `PointGraph`). AI text reads «KI-generert, kan ta feil: «…»» with `data-ai-generated`; the render adds `/UserProperties ai_generated` to its PDF structure element (`reports/pdf_marks.py`). The reflection step has the line `nb.debrief.reflection.report`.

**Implementation note.** Step 3 ran in the builder's own context, as the lane brief says.

**Files.**
- Backend: `debrief/service.py` (`report_debrief`, `_narration` by ids), `replay/walkthrough.py` (`report`, `_compared`), `replay/service.py` (exports), `tests/attempt.py` (`report_test`), `tests/service.py` (exports), `reports/report_data.py` (three sections), `reports/pdf_marks.py` (new), `reports/render.py` (install, finisher). Tests: `tests/reports/test_report_steps.py`, `test_report_test_section.py`, `test_pdf_marks.py` (new); asserts added in `debrief/test_explanation.py`, `debrief/test_quiz.py`, `replay/test_walkthrough.py`, `replay/test_close.py`; `reports/test_report_game.py`, `test_student_report.py` (section list).
- Frontend: `app/print/report/{debrief-section,replay-section,test-section}.tsx`, `parts.ts`, `steps.test.tsx` (new), `copy.ts`, `sections.tsx`; `components/interactive-answer.tsx`, `components/interactive-values.ts` (new), `components/charts/point-graph.tsx`; `modules/tests/{interactive.ts,drawn-item.tsx,submitted-items.tsx}`; `modules/replay/walkthrough.ts` (structural run type); `modules/debrief/reflection-step.tsx`, `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; `e2e/student-report.spec.ts` (fixture: own Orders, the real Debrief with the mock's AI line, a quiz attempt, a played Replay, a handed-in test; the PDF's AI property).

**Review.** Four layers, 32 findings: 0 high, 3 medium, 21 low, 6 false, 2 maybe-false. Patched: closed Replay's Uker shown, the PDF mark (kept beside an own attribute object; `MarkInfo` only when used), the import rule, the moment key, the e2e Replay loop, the bool credit, and tests for the Debrief quiz/late read, the Replay read's open/closed/mostly-AI/pre-record paths and the scenario mapping. Nothing deferred; the rest rejected with reasons above. Follow-up review: false (three medium patches, all tests or a render branch the tests now pin; no unverified risk named).

**Verification.**
- Full backend suite (8 processes): 3795 passed, 4 skipped. ruff check and format pass.
- Frontend: typecheck, Vitest 1230 passed, `check:copy`, `lint:colours`, `npm run build`.
- Playwright (4 workers, lane stack): `student-report`, `individual-test`, `drawn-item`, `debrief-reflection`, `replay-walkthrough`, `homes`, `order-field`: 111 passed; `student-report` again after the patches: passed.
- PDF/UA: veraPDF 1.30.4 `ua1` on the sample: compliant (before and after the patches). The sample was read page by page: the Debrief with three moments and the marked AI line, the evidence and structure answers and the feelings note; the Replay scenario, totals, «Ikke like for like.», the chart and 32-Uke table; every test item with answers and points, the table items as points over their tables.
- New tests over 1 s: `test_an_explanation_without_a_replay_or_a_test_is_documented_as_written` (about 3 s), `test_a_handed_in_test_holds_every_item_its_answers_and_the_stored_scores` (1.4 s). The long Debrief, walkthrough and close tests got asserts, not new tests.

**Decisions taken for the founder [ASSUMPTION].**
- Reflection answers on evidence and structure are in the report, on feelings never (PRD FR-58: «answers on feelings are left out»); the reflection step's line: «Faglærerne og assistentene i Klassen kan lese svarene dine. Svarene på spørsmålene om følelser kommer ikke med i Studentrapporten.»
- «Replay scenario» is the Replay's own drawn settings (Uker, Veiledede uker, start, delays, costs); the comparison follows the walkthrough (its recorded Class game, else `student_game`; mostly-AI left out).
- Points are credit × the item's frozen weight («Poeng: 7,5 av 15»), an unanswered scored item 0, long answers and Adapted items «Ingen poeng her», plus «Poeng regnet ut av koden: X av Y.» over the scored items only.
- A number item shows its column with the answer (no image: one number); table and drawn items get the image, in blocks of at most 10 Uker.
- The machine-readable AI mark is a PDF `/UserProperties` attribute, added by wrapping WeasyPrint 70's private `_build_box_tree` (pinned version; the render fails loudly if it disappears).
- Epic 12 was not merged: the story shows no AI score or Indicative letter.

**Personal data.** No new table.

**Residual risks.** `pdf_marks` depends on a private WeasyPrint function (pinned `weasyprint==70.0`); a WeasyPrint upgrade must keep the e2e's property check green. The e2e sample shows «1 forsøk, ikke bestått» beside a passed quiz step because the fixture passes the quiz through the dev route.
