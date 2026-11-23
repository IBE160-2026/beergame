---
title: 'Story 13.8: The Student report shows the game with its charts'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '8bfb1159ed2f375698106bb3df82ab8cf80c8de5'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-7-student-downloads-the-student-report-as-a-tagged-pdf.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Student report of Story 13.7 holds a header and the Completion section only; it does not document the game the Student played (FR-58, FR-34).

**Approach:** Add a `game` section through the report's section registry on both sides: `report_data.SECTIONS` builds it from `games.service.student_game`, `games.service.seat_state` and `games.service.game_insight` (as Spillinnsikt reads it); the print route's `sections.tsx` renders it with the existing chart components at a fixed width (Graf over tabell for the own Seat, the Ordrestolper and «Lager og restordre» for the chain), each chart followed by its table, and the marks of the one AD-15 mapping in text.

## Boundaries & Constraints

**Always:**
- Section model `GameSectionOut` (`kind: "game"`) after `completion`; `ReportSection` becomes a union discriminated by `kind`; `ReportDataOut.schema_version` stays 1 (snapshots live 5 minutes).
- The game is `games.service.student_game` (a finished Oppfølgingsspill wins); `played: false` (and nothing else) when the Student has none or it has no opened Week. With a game: `makeup`, `game_number`, `role`, `weeks_played` (opened Weeks), `weeks_total`, `finished` (status finished and no `end_reason`), `total_cost` (the Seat's running Total cost through its last Week), `seat` (the `SeatState` of the last opened Week), `last_order` (its Order, or null), `demand` and `roles` (chain order, each Week: `order`, `inventory`, `backlog`, `holder` ∈ student|ai|free, `marks` from `seat_mark`), `first_large_order_week`. No user id, name or free text of anyone; other Seats by Role only.
- Section heading «Klassespill» (with «Spill N»), or «Oppfølgingsspill» for a make-up; facts Rolle, Uker spilt «N av M», Totalkostnad (`formatNumber`, kr).
- Seat chart: `WeekTable` with `fixed` and a new `span {from, to}` (a finished game's Uker, all past: no nå, no Uker ahead, no «Nå» or direct labels, the last Uke's Order plain). Chain charts: `OrderBarsTable` (own Role «(deg)», Kundene as the last row) and `StockBacklogTable`, both taking `fixed`, a shared scale for the game (`largest`, `most`) and, for «Lager og restordre», its table rows under the bands (two rows per Role). Uker split into even blocks of at most 18 so each fits A4 (labelWidth 96, columnWidth 28, fontSize 13).
- «Hvem spilte» table: per Role (Fabrikk first) who held it by Uke ranges («Student, uke 1–4», «KI-spiller, uke 5–20», own Role «(deg)») and each marked Uke with the mark's words (`nb.insight.marks`).
- Every SVG keeps its `<title>`; PDF stays PDF/UA-1 (veraPDF), reading order = visual order.

**Never:** no new chart implementation; no client-side code or measuring in the print route; no other Student's name; no AI data; no Debrief/Replay/test sections (13.10); no change to the demo Class «class-of-1994»; no pipeline change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Class game played | finished Class game | `game` section, makeup false, 4 Roles, demand | — |
| Finished make-up | make-up finished by its last Week | section headed «Oppfølgingsspill», the make-up's Weeks | — |
| No game | Student never seated, or no opened Week | `played: false`, line «Du spilte ikke noe spill i denne Klasseøkten.» | report still built |
| Other Students | 2 Students in one game | other Seat `holder: student`, no name or id in the snapshot | — |
| Playout / Takeover | AI took the Seat | `holder: ai` from that Uke, mark words in «Hvem spilte» | — |
| Long game | 36 Uker | two blocks of 18 per chart, one scale | — |

</intent-contract>

## Code Map

- `backend/app/modules/reports/report_data.py` -- `SECTIONS` registry, `SectionContext`, `ReportSection` alias to turn into a discriminated union; add `_game_section`.
- `backend/app/modules/games/service.py` -- exports `student_game` (:523), `seat_state` (views :152, `session=`), `game_insight` (insight.py :182: per Role weeks with `occupant_kind`, `order`, `inventory`, `backlog`, `marks`; `demand`; `weeks_total`; `status`; `end_reason`).
- `backend/app/modules/games/schemas.py` -- `SeatState` (:233), `SeatMark` (:82), `OccupantKind` (:59).
- `frontend/src/app/print/report/{sections.tsx,copy.ts,report.tsx}` -- renderer registry, PDF copy; new `game-section.tsx` + `game.ts` (pure helpers: blocks, holder ranges).
- `frontend/src/modules/games/week-table-view.tsx` -- `WeekTable` (`fixed`, rows, `graphFields`): add `span`.
- `frontend/src/components/{order-bars-table.tsx,stock-backlog-table.tsx,graph-over-table.tsx}` -- add `fixed`, shared scale, stock body rows; `fixedCell`.
- `frontend/src/components/charts/{order-bars.tsx,stock-backlog.tsx}` -- optional `highest` / `most` overrides.
- `frontend/src/modules/games/insight.ts` -- reference for Role order (upstream first), `CUSTOMERS`, stock table rows; `nb.insight.charts`, `nb.insight.marks`.
- Tests: `backend/tests/reports/test_makeup_continue.py` (`short_game`, `play_weeks`, `given`, `start`), `test_student_report.py`; e2e `frontend/e2e/student-report.spec.ts`, `support/live-game.ts` (`liveClassGame`, `orderByApi`), dev `POST /api/dev/games/{id}/playout`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/reports/report_data.py` -- `GameSectionOut` and nested models, `_game_section`, union, registry entry.
- `backend/tests/reports/test_report_game.py` -- class-only Student, finished make-up Student, Student with no opened Week; no other Student's name or id in the dumped JSON.
- `npm run api:generate` -- schema types.
- Charts: `order-bars.tsx`, `stock-backlog.tsx`, `order-bars-table.tsx`, `stock-backlog-table.tsx`, `week-table-view.tsx` -- additive props; unit tests for `span` and fixed widths.
- `frontend/src/app/print/report/{game.ts,game-section.tsx,sections.tsx,copy.ts}` + `game.test.ts(x)` -- section rendering and helpers.
- `frontend/e2e/student-report.spec.ts` -- fixture: a played Class game (20 Uker, a few Orders by the api, then the dev playout through `games.commands`) before the report; sample PDF kept for veraPDF.

**Acceptance Criteria:**
- Given a Student with a finished Class game, when the report is built, then it holds the game section with Role, Uker spilt, Totalkostnad, the Seat's Graf over tabell and the two chain charts with their tables, AI Uker and marks in text, and no other Student's name.
- Given a Student whose finished make-up is their game, when the report is built, then the section is headed «Oppfølgingsspill».
- Given the e2e sample PDF, when `scripts/verapdf` runs, then it is PDF/UA-1 compliant and holds the game section.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: two (blind, edge case) on Sonnet, as the lane brief directs when the report pipeline is not changed; verification gap and intent alignment skipped.
- verdicts: 27 findings — high 0, medium 1, low 16, false 8, maybe-false 2
- findings:
  - `[medium]` `[patch]` Blind: `GameWeekOut` collided with `sessions.schemas.GameWeekOut`, renaming the Matrisevegg type in the generated schema. Report models renamed `ReportGameOut`, `ReportGameRoleOut`, `ReportGameWeekOut`, `ReportDemandWeekOut`; schema regenerated, no `app__modules__` names left.
  - `[low]` `[patch]` Blind: `game.seat as SeatState` cast. Removed (the generated type is the same).
  - `[low]` `[patch]` Blind: «Uker spilt» counts the open Week of a game closed without its Order. Now counts Weeks with a placed Order.
  - `[low]` `[reject]` Blind: `finished=False`, an `end_reason`, a Takeover mark and a free Seat lack backend tests. Vitest covers the words and the not-finished line; the e2e sample has the playout mark, read in the PDF.
  - `[low]` `[reject]` Blind: `_holder` maps an unknown kind to free. `OccupantKind` is a closed enum; None is a free Seat.
  - `[low]` `[reject]` Blind: `AxisCell` makes the axis cell a `th` for every fixed caller. Intended: the only other fixed caller is `/print/graf-over-tabell`, nothing selects `td[data-axis]`, and veraPDF needs it (7.5-1 failed without).
  - `[low]` `[reject]` Blind: the e2e does not assert the section inside the PDF. The PDF is compressed; the section is asserted at the api (`test_report_game.py`), in the render (`game.test.tsx`) and read in the sample.
  - `[low]` `[reject]` Blind: test hygiene (imported fixtures, `_class_of` order, privacy check scope). The house fixture pattern; ids and names are the personal data in question.
  - `[low]` `[patch]` Blind: copy. «Spill» beside «Spill 3» now prints the number; «uke» in runs and regions now «Uke». Role names stay capitalised (defined terms); marks carry no punctuation of their own.
  - `[false]` `[reject]` Blind: unused imports in `insight.ts`. `formatNumber`, `roleName` and `InsightRole` are still used; typecheck passes. The widened optional fields still accept Spillinnsikt's types.
  - `[low]` `[reject]` Blind: e2e doc comment and hard-coded playout. The dev playout route is documented (Story 8.14).
  - `[low]` `[patch]` Blind: `__all__` incomplete; `test_student_report.py` unpacks exactly two sections. `__all__` lists the models; the test asserts the first two kinds.
  - `[low]` `[reject]` Edge: chain data for an unfinished game (AD-3). The report opens after the effective Test deadline, when the Student no longer plays.
  - `[false]` `[reject]` Edge: the staff `insight` policy gate. That gate is for staff on Spillinnsikt; the report documents the Student's own game.
  - `[maybe-false]` `[reject]` Edge: the game advances between the two reads. Nothing advances after the Test deadline; would only be low.
  - `[low]` `[patch]` Edge: open Week counted in «Uker spilt». Same as the Blind row.
  - `[false]` `[reject]` Edge: `seat_state` raises after `student_game`. The own Role has opened Weeks, so the Game has started and the Seat exists.
  - `[false]` `[reject]` Edge: a Role with no Weeks prints a lone full stop. Every Role has every opened Week.
  - `[low]` `[reject]` Edge: an empty axis `th` in fixed mode. Every fixed field draws an axis.
  - `[low]` `[reject]` Edge: other fixed callers' selectors. Same as the Blind `AxisCell` row; none exist.
  - `[false]` `[reject]` Edge: an unmapped mark prints «undefined». `nb.insight.marks` is `Record<SeatMark, string>`; a new mark fails the typecheck.
  - `[low]` `[reject]` Edge: a game with no placed Order. The columns come from the customers' demand too.
  - `[maybe-false]` `[reject]` Edge: Seat and chain cover different Uker. Both read the same opened Weeks; would only be low.
  - `[false]` `[reject]` Edge (claim): no `played` flag. `game: null` is the section's "not played", rendered with its line.
  - `[low]` `[patch]` Edge (claim): no-game copy differs from the matrix. Now «Du spilte ikke noe spill i denne Klasseøkten.»
  - `[false]` `[reject]` Edge (claim): label width 136 instead of 96. 136 + 18 × 28 = 640 px still fits A4's 672 px; widened after the first sample wrapped «Distributør, restordre».
  - `[false]` `[reject]` Edge (claim): the empty-Weeks branch is untested. It shares the `game=None` return with the tested no-game case.

## Design Notes

Chunking keeps every number legible at 13 px on A4 portrait; the chain charts share one scale across blocks through the new override props, the Seat's Netto lager axis is per block (its ticks are printed). Chart words and mark words come from `nb.ts` (the components already read it), the section's own words from `copy.ts`.

## Verification

**Commands:**
- `uv run pytest tests/reports/test_report_game.py tests/reports/test_student_report.py -q` -- pass
- `npm run typecheck && npx vitest run src/app/print src/components src/modules/games` -- pass
- `npx playwright test e2e/student-report.spec.ts` then `python scripts/verapdf frontend/test-results/student-report.pdf` -- compliant

## Auto Run Result

Status: done

**Summary.** The Student report now documents the game (FR-58, FR-34, FR-17). `report_data.SECTIONS` gains `game`: `games.service.student_game` (a finished Oppfølgingsspill wins), `seat_state` in the last opened Week and `game_insight` (Spillinnsikt's read); other Seats by Role only, holders as student/ai/free, the AD-15 marks. The print route renders «Klassespill» or «Oppfølgingsspill» with Spill, Rolle, Uker spilt, Totalkostnad; the Seat as Graf over tabell (`WeekTable` with a new `span`: no nå, no Uker ahead); the Ordrestolper and «Lager og restordre» for all four Roles plus Kundene, each over its table, in even blocks of at most 18 Uker on one shared scale; and «Hvem spilte» with the marks in words.

**Implementation note.** Step 3 ran in the builder's own context, as the lane brief says.

**Files.**
- Backend: `reports/report_data.py` (section models, builder, union); tests `tests/reports/test_report_game.py` (new), `test_student_report.py`.
- Frontend: `app/print/report/{game.ts,game-section.tsx,game.test.tsx}` (new), `sections.tsx`, `copy.ts`; `modules/games/chain-charts.ts` (new: the pure chart rows moved out of `insight.ts`, which re-exports them, so the server-rendered print route can import them), `week-table-view.tsx` (`span`), `components/{order-bars-table,stock-backlog-table,graph-over-table}.tsx` (`fixed`, shared scale, stock table rows, print axis cell as `th scope="row"`), `components/charts/{order-bars,stock-backlog}.tsx` (scale override), `modules/reports/report-download.test.tsx`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/student-report.spec.ts` (fixture: a 20-Uke Class game, one Order, the dev playout through `games.commands`).

**Review.** Two layers, 27 findings: 0 high, 1 medium, 16 low, 8 false, 2 maybe-false. Patched: the schema name collision (medium), «Uker spilt», the cast, copy, `__all__` and the section-count assertion. Nothing deferred; the rest rejected with reasons in the triage log. Follow-up review: false (one medium patched, a rename the regenerated schema and typecheck confirm).

**Verification.**
- Full backend suite (8 processes): 3778 passed before the review patches; after them the reports and import tests (31) pass. ruff check and format pass.
- Frontend: typecheck, Vitest 1217 passed (print and reports tests, 40, after the patches), lint:colours, check:copy; build in the image.
- Playwright (4 workers, lane stack): `student-report`, `homes`, `graph-over-table`, `game-insight`, `debrief-chain`, `order-field`, `order-confirm`, `game-end`, `completion`, `student-home`: 90 passed; after the patches `student-report`, `graph-over-table`, `game-insight`, `debrief-chain`: 29 passed.
- PDF/UA: veraPDF 1.30.4 `ua1` on the sample: compliant. The first sample failed 7.5-1 (the graph rows' axis cells had no headers); in print the axis cell is now `th scope="row"`. The sample was read page by page: game section, two blocks per chart with the table under each, «Hvem spilte» with «Uke 2: KI spilte spillet ferdig.».
- New tests over 1 s: `test_a_finished_makeup_is_the_game_section_headed_oppfolgingsspill` (about 4 s), `test_a_played_class_game_is_documented_with_the_chain_by_role_only` (2.4 s): each plays a short game.

**Decisions taken for the founder [ASSUMPTION].**
- Long games split into even blocks of at most 18 Uker (A4 portrait, 13 px numbers, 136 px row labels); the chain charts share one scale; the Seat's Netto lager axis is per block.
- Section order: facts, «Din rolle uke for uke», «Hele kjeden» (Ordre, Lager og restordre), «Hvem spilte» (runs of Uker, marks in words; own Role «(deg)», others «Student»/«KI-spiller»).
- «Uker spilt» counts Weeks with a placed Order, «N av M»; an unfinished game gets one line saying so; no game: «Du spilte ikke noe spill i denne Klasseøkten.»
- Chart and mark words come from `nb.ts` (as on Spillinnsikt and the play screen); the section's own draft copy is in `app/print/report/copy.ts`.
- `game-section.tsx` is a client module only because the shared chart tables take functions; the print route still renders complete HTML on the server.

**Personal data.** No new table.

**Residual risks.** Story 13.10's sections must keep graph rows' axis cells as row headers for veraPDF; a game of 19–36 Uker gives two blocks per chart (about five pages).
