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
