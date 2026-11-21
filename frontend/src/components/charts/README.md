# Chart module (AD-18)

`frontend/src/components/charts` is the only code that imports a chart library (a Vitest test in
`charts.test.tsx` fails on any other import of `d3-*`, `recharts` and the like). Every chart takes
a fixed width and height from its caller, never a responsive container, and every chart SVG has a
`<title>`, the only alternative text WeasyPrint reads. Colours are SVG presentation attributes
from `src/theme/tokens.json` (`palette.ts`), so one SVG draws the same in the browser, in a server
render and in WeasyPrint.

`../graph-over-table.tsx` (Graf over tabell) lays the charts over the week table on the same
columns; reuse it rather than placing a chart over a table by hand.

## Spike outcome (Story 6.7)

AD-18 asks the first chart story to check each chart type twice: its Week marks within 1 px of
their table columns at 320, 360 and 1440 px (Playwright, `e2e/graph-over-table.spec.ts`), and the
chart correct in WeasyPrint's `pdf/ua-1` PDF (CI e2e job, `backend/app/platform/chart_print_check.py`
against the server-rendered `/print/graf-over-tabell`). A chart type that fails either is rebuilt
as hand-made SVG here.

| Chart type | Recharts 3.11.0 | Outcome |
|---|---|---|
| Line with area (Netto lager, Posisjon) | `renderToStaticMarkup(<LineChart width={300} height={100}>…)` gives `<div class="recharts-wrapper" …></div>` with no `<svg>`: nothing to print | Hand-made SVG (`net-graph.tsx`, d3-scale, d3-shape); passes both checks |
| Stacked bars (Kost per uke) | `<BarChart width={300} height={60}>` renders the same empty wrapper on the server | Hand-made SVG (`cost-bars.tsx`); passes both checks |
| Axis labels in the sticky column | — (not a Recharts type) | Hand-made SVG (`axis-labels.tsx`) |
| Kjedebånd (Story 6.9) | — (a flow diagram, not a Recharts type) | Hand-made SVG (`chain-band.tsx`), laid out by the pure `chain-band-layout.ts`; one-Seat variant only, the four-Role variant comes with Story 9.5 |
| Matrisevegg (Story 7.2) | — (a matrix of cells, not a Recharts type) | Hand-made SVG (`matrix-wall.tsx`), sized by the pure `matrix-wall-layout.ts` |
| Stacked area (Totalkostnad over tid, Story 6.16) | — (built after the spike; Recharts is not a dependency) | Hand-made SVG (`cost-area.tsx`), `aria-hidden` with a `<title>`; its x is its own (Uke 1 … nå), not table columns, and its table alternative is «Vis som tabell» or the «Sum, kr» row |

## Kjedebånd scale and labels

`bandLayout` sets one factor for the pipe and the stock bars (DESIGN.md's 1.4 and 0.82 px per unit
as maxima) from the band width alone, so a worst Uke of 80 units on the pipe plus the overdue box
fits and a game keeps one scale at a given width; a Uke that needs more is drawn smaller still.
Labels are placed from an upper-bound width estimate (`textWidth`); one with no room wraps under
the band on its own side. `modules/games/chain-band.test.ts` lays out every Uke of a Classic game
for all four Roles at 320 and 360 px (and 200 % text), and `e2e/chain-band.spec.ts` holds the
estimate to the rendered font.

Recharts is therefore not a dependency. Recharts 3 builds its chart in client effects, so a
server-rendered print page holds an empty box, which fails the PDF check before alignment can be
measured. Kjedebånd (Story 6.9) and the Matrisevegg were hand-made SVG by AD-18 already.

## Alignment

In the browser `GraphOverTable` measures the centre of each `th[scope=col][data-col]` and passes
it to the chart as `x`, again whenever the table resizes (text zoom, a loaded font, the laptop
breakpoint). With `fixed` (print) every width is given in px. Marks carry `data-mark` and
`data-week` (a line's vertices `data-weeks` and `data-x`), which both checks read.

## Matrisevegg: a grid on the SVG (Story 7.2)

The founder decided on 2026-11-14 that the wall is never `aria-hidden` and is read cell by cell,
either as table roles on the SVG or as an HTML table under it. **The choice: ARIA roles on the
SVG.** The `<svg>` is `role="grid"` (a grid is a table to assistive technology, the interactive
kind) named by its `<title>`; a `row` of `columnheader`s («Uke n», the game column first), a
`row` per status group with one `rowheader` across the wall («Venter 4»), and per Class game a
`row` with a `rowheader` (game number, status, wait and kjedekost in words) and one `gridcell` per
Uke named «Spill 2, Uke 14: Netto lager −13.», also where the cell prints «−» or nothing.
`aria-rowindex` and `aria-colindex` number them. Grid rather than `table`: the wall is one Tab
stop that arrow keys move through, which is the grid pattern; in a `table` a screen reader in
browse mode keeps the arrow keys for itself. An HTML table under the SVG would hold every number
twice and leave the drawn cells unreachable; «Vis som tabell» (Story 7.3) is that second way.

One cell is in the Tab order (roving `tabindex`); arrows move cell by cell, Up and Down to the
nearest game row (its last Uke when it has fewer), Home and End to the row's ends
(`moveFocus`). Focus is held by Game id and Uke and put back after a re-render that moved the
row. The focused cell draws `focus-ring-inset` itself, as SVG children draw no outline.

**Sticky game column and Uke header.** CSS `position: sticky` does not act inside an SVG, and
splitting the wall into several SVGs would break the grid's rows. The wall's scroll region writes
its offsets to `--wall-x` and `--wall-y` on the SVG; the row headers translate by `--wall-x`, the
Uke header by `--wall-y` and the corner by both, and three clip paths (moved in the same scroll
handler) keep the cells under the header and the game column. In print or a server render the
offsets are 0.

**Cells.** `cellText`: the signed number when `textWidth` plus 1 px on each side fits the cell,
else «−» for below zero, else blank; text `ink` on zero and steps 1–2, `paper` on steps 3–4.
Cell text is 9 px (`matrix-cell-min`) at a 13 px caption and grows with text zoom; labels and
the header are the caption size. `netStep` lives here and the week table imports it.

## «Vis som tabell»: an HTML table beside the wall (Story 7.3)

`matrix-table.tsx` is the wall's second way to the same numbers (UX-DR42): an HTML `<table>`, not
SVG, so text is `table-cell` (13 px, 15 px from 1024 px), never shrinks and every cell prints its
signed number. The Visningsbryter (`view-toggle`) swaps it for the wall; only one of the two is in
the DOM, and each sits in a region named «Alle spill», so to the user it is the same region. The
table gets real CSS `position: sticky` (game column, header row, the corner both) with
`border-separate`, which keeps sticky cells' backgrounds and rules.

Cells get their game and Uke from `th scope="row"` and `th scope="col"`; the caption is the
wall's title. Sorting (`matrix-table-sort.ts`) uses numbers the caller gives per row and column
(`TableRow.keys`), never the printed text; a row with no number stays last in both directions and
ties keep the caller's order. The sorted header carries `aria-sort`. A column is sortable only when
the caller passes its first direction, so «Vis i plenum» (Epic 14) can leave the cost column out.

Keyboard: one row header is in the Tab order (roving `tabindex`), Up and Down move between games,
and the focused header draws `focus-ring-inset`. The caller may share the game with the wall
(`focusId`/`onFocusId` here, `position`/`onPosition` on `MatrixWall`), so switching views keeps the
same Class game as the view's Tab stop. A game with no Uke yet (not started, or its weeks failed
to load) has no wall cell to hold it, so the wall's Tab stop falls back to its first game with a
cell; the table keeps it. The Oversikt also keeps the table's sort across a switch. While focus is inside the table its rows keep their places
(`keepOrder`) and values update in place; they re-sort when focus leaves or a header is activated.
