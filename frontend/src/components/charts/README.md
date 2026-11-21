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
| Kjedebånd (Story 6.9) | — (a flow diagram, not a Recharts type) | Hand-made SVG (`chain-band.tsx`), laid out by the pure `chain-band-layout.ts`; `variant="seat"` (the Seat's own link) and, from Story 9.5, `variant="chain"` (all four Roles from «Produksjon» to «Kundene», `chainLayout`) for the Debrief and Spillinnsikt |
| Ordrestolper (Story 9.5, reused by Spillinnsikt in 7.8) | — (built after the spike) | Hand-made SVG (`order-bars.tsx`): one row per Role, Fabrikk at the top, `order-history` bars and the own Role in `ink`, a `restordre` dot and «Uke n» at each first Order of 10 or more joined by a diagonal, the scrubber's dashed line; drawn in a `GraphOverTable` field by `components/order-bars-table.tsx`, whose Rolle × Uke rows (`flow-*` steps, `flowStep`) and Forsterkning column are its alternative |
| Etterspørselsbånd (Story 9.4) | — (built after the spike) | Hand-made SVG (`demand-band.tsx`): a `lager-fill` step band for Kundene, an `ink-secondary` line for Ordre inn and `ink` bars for Din ordre over the week columns of `GraphOverTable`; `aria-hidden`, the table Uke / Kundene / Ordre inn / Din ordre is its alternative |
| Matrisevegg (Story 7.2) | — (a matrix of cells, not a Recharts type) | Hand-made SVG (`matrix-wall.tsx`), sized by the pure `matrix-wall-layout.ts` |
| Kostnadsfordeling (Story 7.6) | — (ticks, a box and a median on one axis; built after the spike) | Hand-made SVG (`cost-distribution.tsx`), `aria-hidden` with a `<title>`; its numbers are the text summary under it and «Vis som tabell». The Trakt and the per-Role bars beside it are HTML bars, `aria-hidden`, with the counts and amounts as text |
| Lager og restordre (Story 7.8) | — (built after the spike) | Hand-made SVG (`stock-backlog.tsx`): a band per Role, Fabrikk at the top, stock up in `lager` and backlog down in `restordre` from each band's zero line, one scale for the game; drawn in a `GraphOverTable` field by `components/stock-backlog-table.tsx`, `aria-hidden`, with Spillinnsikt's «Vis som tabell» as its alternative. Spillinnsikt also reuses Story 9.5's Ordrestolper (`order-bars.tsx`, `components/order-bars-table.tsx`) with the customers' demand as a fifth row and no Forsterkning column until a Role gives one |
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

**Row links (Story 7.11).** A row may carry a link («Melding» on the Oversikt). It is the row's
last `gridcell`, an SVG `<a>` at the drawing's right edge in a column `wallSizes` reserves, and it
keeps the wall one Tab stop: Right from the last Uke reaches it, Left goes back, Up and Down move
link to link, and a row with no Uke yet is reached by its link only; Home and End stay on the
Uker. Enter or a plain click follows it through `onFollow` and never opens the row. A `tint` row
(the Varselbånd's game) is drawn on `restordre-fill` with its link `ink`; other links are `lager`.
«Vis som tabell» gives the same link its own column, the row's second Tab stop after its row header.

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

## Cell scales, class median graph and summary rows (Story 7.4)

`MatrixWall` takes a `scale`: `net` (default, the signed `net-*` steps and the minus line) or
`flow` for Ordre and Kost per uke (`flow-*`: under 5 no fill, 5–9, 10–19, 20–29, 30+; text `ink` on
none and steps 1–2, `paper` on 3–4). The legend follows the scale; the unfilled step's swatch is
outlined so it can be seen.

With a `summary` (built by the caller from the api's aggregates, AD-10: the chart computes no
median or mean) the wall draws the class median graph (`matrix-median.tsx`) inside its own SVG,
above the Uke header, so its marks stand over the same Uke columns and scroll sideways with the
cells in the one «Alle spill» region. The graph is `aria-hidden`: its numbers are in the summary
rows. The Uke header sticks once the graph has scrolled away (the vertical offset is
`max(0, scrollTop − graph height)`). The summary rows («Median, Fabrikk», «Kjedekost/uke, snitt»)
stand after the last group as grid rows with a row header and a named cell per Uke; they print a
number only where it fits with 1 px to spare and are not keyboard stops (the games' cells are).
`MatrixTable` takes the same rows as `footer`, in a `<tfoot>` that never sorts; the table is at
least as wide as its region.
