import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";

import { CHART_FONT, colour } from "./palette";
import { totalAxisTop } from "./scales";

/** One Uke's running cost, as the api gave it, in kroner: holding and backlog so far. */
export type CostAreaPoint = {
  week: number;
  holding: number;
  backorder: number;
};

export type CostAreaProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  fontSize: number;
  /** Uke 1 … nå, oldest first. */
  points: readonly CostAreaPoint[];
  /** The SVG `<title>`, the alternative text a PDF reader gets (AD-18). */
  title: string;
  /** Tick text from the number formatter («50», «1 000»). */
  formatTick: (value: number) => string;
  /** «Uke 1» at the left end and «Uke 11» (bold) at the right end. */
  firstLabel: string;
  lastLabel: string;
  /** The final values, labelled directly at the right end (Story 6.18, `chain-cost-chart`):
   * «Lager 901,00» in the holding band and «Restordre 1 365,00» in the backlog band, kept at
   * least a line apart. Left out, no end labels are drawn (Story 6.16's panel). */
  endLabels?: { holding: string; backorder: string };
};

/** Width of a lone Uke (Uke 1): one point has no length, so it is drawn as a short block. */
const LONE = 6;

/**
 * «Totalkostnad over tid» (Story 6.16, UX-DR22, DESIGN.md `cost-panel`): the Seat's running cost
 * from Uke 1 to nå as a stacked area, holding cost (`lager-fill`, `lager` edge) below and backlog
 * cost (`restordre-fill`, `restordre` edge) above, on an `axis` baseline with a true zero and
 * `hairline` gridlines at half and top (`totalAxisTop`). Hand-made SVG like the rest of the module
 * (see README). It is `aria-hidden`: its numbers are a table elsewhere (the «Sum, kr» row, or
 * «Vis som tabell»), and the `<title>` stays for print.
 */
export function CostArea({
  width,
  height,
  fontSize,
  points,
  title,
  formatTick,
  firstLabel,
  lastLabel,
  endLabels,
}: CostAreaProps) {
  const highest = Math.max(0, ...points.map((p) => p.holding + p.backorder));
  const top = totalAxisTop(highest);
  const ticks = [0, top / 2, top];
  const tickWidth = Math.max(...ticks.map((t) => formatTick(t).length)) * fontSize * 0.55 + fontSize * 0.6;
  const left = Math.ceil(tickWidth);
  const right = width - 2;
  // Half a label above the top tick and a label line under the baseline, so every label stays inside.
  const plotTop = Math.round(fontSize * 0.8);
  const base = height - Math.round(fontSize * 1.9);
  const y = scaleLinear().domain([0, top]).range([base, plotTop]);
  const first = points[0]?.week ?? 1;
  const last = points[points.length - 1]?.week ?? first;
  const x =
    last > first
      ? scaleLinear().domain([first, last]).range([left, right])
      : (week: number) => (week === first ? left : left + LONE);
  // A lone Uke is drawn from its point to a short way right, so it is seen.
  const drawn = points.length === 1 ? [points[0]!, { ...points[0]!, week: first + 1 }] : points;
  const holding = area<CostAreaPoint>()
    .x((p) => x(p.week))
    .y0(base)
    .y1((p) => y(p.holding))(drawn);
  const backorder = area<CostAreaPoint>()
    .x((p) => x(p.week))
    .y0((p) => y(p.holding))
    .y1((p) => y(p.holding + p.backorder))(drawn);
  const holdingEdge = line<CostAreaPoint>()
    .x((p) => x(p.week))
    .y((p) => y(p.holding))(drawn);
  const totalEdge = line<CostAreaPoint>()
    .x((p) => x(p.week))
    .y((p) => y(p.holding + p.backorder))(drawn);
  const owes = points.some((p) => p.backorder > 0);
  const ends = endLabels ? endPlaces(points[points.length - 1], y, plotTop, base, fontSize) : null;
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-chart="cost-area"
      aria-hidden="true"
      fontFamily={CHART_FONT}
      fontSize={fontSize}
      overflow="hidden"
    >
      <title>{title}</title>
      {ticks.map((tick) => (
        <g key={tick}>
          <line
            x1={left}
            x2={right}
            y1={Math.round(y(tick)) + 0.5}
            y2={Math.round(y(tick)) + 0.5}
            stroke={colour(tick === 0 ? "axis" : "hairline")}
            strokeWidth={1}
          />
          <text x={left - fontSize * 0.5} y={y(tick)} dy="0.35em" textAnchor="end" fill={colour("ink-muted")}>
            {formatTick(tick)}
          </text>
        </g>
      ))}
      {holding ? <path d={holding} fill={colour("lager-fill")} data-mark="holding-area" /> : null}
      {backorder && owes ? <path d={backorder} fill={colour("restordre-fill")} data-mark="backorder-area" /> : null}
      {/* The backlog edge first: where no backlog is owed it runs on the holding edge, drawn over it. */}
      {totalEdge && owes ? (
        <path d={totalEdge} fill="none" stroke={colour("restordre")} strokeWidth={1.5} strokeLinejoin="round" />
      ) : null}
      {holdingEdge ? (
        <path d={holdingEdge} fill="none" stroke={colour("lager")} strokeWidth={1.5} strokeLinejoin="round" />
      ) : null}
      {endLabels && ends ? (
        // A `paper` halo under each label keeps it readable on its band (WCAG 1.4.3): the series
        // colour on the halo, not on the tint.
        <g
          textAnchor="end"
          fontWeight={600}
          stroke={colour("paper")}
          strokeWidth={4}
          strokeLinejoin="round"
          paintOrder="stroke"
          data-mark="end-labels"
        >
          <text x={right - fontSize * 0.3} y={ends.backorder} dy="0.35em" fill={colour("restordre")}>
            {endLabels.backorder}
          </text>
          <text x={right - fontSize * 0.3} y={ends.holding} dy="0.35em" fill={colour("lager")}>
            {endLabels.holding}
          </text>
        </g>
      ) : null}
      <text x={left} y={height - fontSize * 0.45} fill={colour("ink-muted")}>
        {firstLabel}
      </text>
      {last > first ? (
        <text x={right} y={height - fontSize * 0.45} textAnchor="end" fontWeight={700} fill={colour("ink")}>
          {lastLabel}
        </text>
      ) : null}
    </svg>
  );
}

/** Where the end labels stand: each in the middle of its band at the last Uke, then pushed apart
 * to at least a line between them and kept inside the plot (holding below, backlog above). */
export function endPlaces(
  last: CostAreaPoint | undefined,
  y: (value: number) => number,
  plotTop: number,
  base: number,
  fontSize: number,
): { holding: number; backorder: number } {
  const holdingTop = y(last?.holding ?? 0);
  const totalTop = y((last?.holding ?? 0) + (last?.backorder ?? 0));
  const gap = fontSize * 1.2;
  const half = fontSize * 0.6;
  let holding = Math.min(base - half, (base + holdingTop) / 2);
  let backorder = Math.max(plotTop + half, (holdingTop + totalTop) / 2);
  if (holding - backorder < gap) {
    const middle = (holding + backorder) / 2;
    holding = Math.min(base - half, middle + gap / 2);
    backorder = holding - gap;
    if (backorder < plotTop + half) {
      backorder = plotTop + half;
      holding = backorder + gap;
    }
  }
  return { holding, backorder };
}
