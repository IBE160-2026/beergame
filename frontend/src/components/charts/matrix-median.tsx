import { textWidth } from "./chain-band-layout";
import { colour } from "./palette";

/** One Uke of the class median graph: the median and the middle half of the games, as the api
 * sent them (AD-10); null where no game has a value. */
export type WallGraphPoint = { median: number; low: number; high: number } | null;

/** A cell of a summary row: the printed text and the cell's name as read; null for no value. */
export type WallSummaryCell = { text: string; name: string } | null;

/** «Median, Fabrikk» or «Kjedekost/uke, snitt» under the wall, one cell per Uke. */
export type WallSummaryRow = { key: string; label: string; cells: readonly WallSummaryCell[] };

/** The class median over the wall and its rows under it (Story 7.4, UX-DR40, UX-DR41). */
export type WallSummary = {
  /** Per Uke from Uke 1; empty draws no graph. */
  graph: readonly WallGraphPoint[];
  /** The y axis's tick labels («−20», «0»): the one number formatter. */
  tick: (value: number) => string;
  rows: readonly WallSummaryRow[];
};

/** The graph's height for the caption size: room for the band and three tick labels. */
export function graphHeight(summary: WallSummary | undefined, fontSize: number): number {
  return summary && summary.graph.some((point) => point !== null) ? Math.round(fontSize * 7) : 0;
}

export type GraphScale = { y: (value: number) => number; ticks: number[] };

/**
 * The graph's vertical scale over its points and zero, from `top` to `bottom` (px): the ticks are
 * the lowest value, zero and the highest, rounded outwards to a step of 5 and dropped when they
 * would stand closer than a line of text to zero.
 */
export function graphScale(points: readonly WallGraphPoint[], top: number, bottom: number, fontSize: number): GraphScale {
  const values = points.flatMap((point) => (point ? [point.low, point.median, point.high] : []));
  const step = (value: number) => (value === 0 ? 0 : Math.sign(value) * Math.ceil(Math.abs(value) / 5) * 5);
  const min = step(Math.min(0, ...values));
  const max = step(Math.max(0, ...values));
  const span = max - min || 1;
  const y = (value: number) => bottom - ((value - min) / span) * (bottom - top);
  const ticks = [max, 0, min].filter(
    (tick, i, all) => all.indexOf(tick) === i && (tick === 0 || Math.abs(y(tick) - y(0)) >= fontSize),
  );
  return { y, ticks };
}

/** Runs of consecutive Uker that have a point, as the line and band break where none has. */
function runs(points: readonly WallGraphPoint[]): { week: number; point: NonNullable<WallGraphPoint> }[][] {
  const found: { week: number; point: NonNullable<WallGraphPoint> }[][] = [];
  let run: { week: number; point: NonNullable<WallGraphPoint> }[] = [];
  points.forEach((point, i) => {
    if (point) run.push({ week: i + 1, point });
    else if (run.length > 0) {
      found.push(run);
      run = [];
    }
  });
  if (run.length > 0) found.push(run);
  return found;
}

/**
 * The class median graph over the Matrisevegg (Story 7.4, UX-DR40): the median as a 1.5 px `ink`
 * line with the middle half of the games as a `hairline` band behind it and zero as an `axis`
 * line, each Uke's mark over its own column. Drawn inside the wall's SVG so it scrolls sideways
 * with the cells; its numbers are printed in the median row under the wall, so the drawing itself
 * is hidden from assistive technology. The tick labels stand in the sticky game column.
 */
export function MedianGraph({
  summary,
  height,
  labelWidth,
  cellWidth,
  fontSize,
  clipPlot,
  stuckX,
}: {
  summary: WallSummary;
  height: number;
  labelWidth: number;
  cellWidth: number;
  fontSize: number;
  clipPlot: string;
  stuckX: { transform: string };
}) {
  const top = Math.round(fontSize * 0.6);
  const bottom = height - Math.round(fontSize * 0.6);
  const scale = graphScale(summary.graph, top, bottom, fontSize);
  const x = (week: number) => labelWidth + (week - 1) * cellWidth + cellWidth / 2;
  const columns = summary.graph.length;
  const right = labelWidth + columns * cellWidth;
  const gap = Math.round(fontSize * 0.75);
  // A run of one Uke (the first Uke of a class, or one between Uker without a value) is a short
  // band half a cell wide with a dot for its median, so its middle half still shows.
  const half = cellWidth / 4;
  const parts = runs(summary.graph);
  const band = parts.map((run) => {
    const edges = run.length === 1 ? [x(run[0]!.week) - half, x(run[0]!.week) + half] : run.map(({ week }) => x(week));
    const marks = run.length === 1 ? [run[0]!, run[0]!] : run;
    const upper = marks.map(({ point }, i) => `${edges[i]},${scale.y(point.high)}`);
    const lower = marks.map(({ point }, i) => `${edges[i]},${scale.y(point.low)}`).reverse();
    return [...upper, ...lower].join(" ");
  });
  return (
    <g aria-hidden="true" data-median-graph="">
      <g clipPath={`url(#${clipPlot})`}>
        {band.map((points, i) => (
          <polygon key={`band-${i}`} points={points} fill={colour("hairline")} data-band="" />
        ))}
        <line x1={labelWidth} x2={right} y1={scale.y(0)} y2={scale.y(0)} stroke={colour("axis")} strokeWidth={1} />
        {parts.map((run, i) =>
          run.length > 1 ? (
            <polyline
              key={`line-${i}`}
              points={run.map(({ week, point }) => `${x(week)},${scale.y(point.median)}`).join(" ")}
              fill="none"
              stroke={colour("ink")}
              strokeWidth={1.5}
              data-median=""
            />
          ) : (
            <circle
              key={`line-${i}`}
              cx={x(run[0]!.week)}
              cy={scale.y(run[0]!.point.median)}
              r={2}
              fill={colour("ink")}
              data-median=""
            />
          ),
        )}
      </g>
      <g style={stuckX}>
        <rect x={0} y={0} width={labelWidth} height={height} fill={colour("paper")} />
        {scale.ticks.map((tick) => (
          <text
            key={tick}
            x={labelWidth - gap}
            y={scale.y(tick) + fontSize * 0.35}
            textAnchor="end"
            fill={colour("ink-secondary")}
            className="tabular-nums"
            data-tick=""
          >
            {summary.tick(tick)}
          </text>
        ))}
      </g>
    </g>
  );
}

/** Whether `text` fits a cell `width` wide with 1 px to spare on each side. */
export function fitsCell(text: string, width: number, fontSize: number): boolean {
  return textWidth(text, fontSize) + 2 <= width;
}
