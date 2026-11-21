import { textWidth } from "./chain-band-layout";
import { CHART_FONT, colour } from "./palette";

/** One Role's row of the Ordrestolper, top to bottom (Fabrikk first, UX-DR73). */
export type OrderBarsRow = {
  /** Each drawn column's Order, aligned with `xs`; null for a column with no Uke of this Role. */
  orders: readonly (number | null)[];
  /** The viewer's own Role: `ink` bars instead of `order-history`. */
  own: boolean;
  /** The column of the Role's first Order of 10 or more and its label («Uke 6»); null with none. */
  firstLarge: { index: number; text: string } | null;
};

export type OrderBarsProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  fontSize: number;
  /** Each column's centre, in px. */
  xs: readonly number[];
  columnWidth: number;
  rows: readonly OrderBarsRow[];
  /** The column of the Uke the Ukeskrubber stands at: a dashed `ink` line across the rows. */
  chosen: number | null;
  /** The SVG `<title>` (AD-18). */
  title: string;
};

/** Source Sans 3's box above and below the baseline, in em. */
const ASCENT = 1.03;
const DESCENT = 0.41;

/** Each row's band: the room for the «Uke n» label at the top, then the bars to the baseline. */
export function orderRows(height: number, fontSize: number, count: number) {
  const rowHeight = height / Math.max(1, count);
  const labelRoom = Math.ceil((ASCENT + DESCENT) * fontSize) + 2;
  return Array.from({ length: count }, (_, i) => {
    const top = i * rowHeight;
    const baseline = Math.round(top + rowHeight - 2);
    return { top, baseline, barMax: Math.max(1, baseline - top - labelRoom), centre: top + rowHeight / 2 };
  });
}

/**
 * Ordrestolper (Story 9.5 for the Debrief, reused by Spillinnsikt in Story 7.8; UX-DR33,
 * DESIGN.md `order-bars`): one row per Role, Fabrikk at the top, a bar per Uke in `order-history`
 * and the viewer's own Role in `ink`, all rows on one scale so the swings can be compared. In each
 * row a `restordre` dot with «Uke n» marks the first Order of 10 or more; a thin `restordre`
 * diagonal joins the dots from the customers' end up. A dashed `ink` line stands at the Uke the
 * Ukeskrubber has chosen. Drawn in a Graf over tabell field, so its columns are the Rolle × Uke
 * table's; `aria-hidden`, the table and Forsterkning as text are its alternative.
 */
export function OrderBars({ width, height, fontSize, xs, columnWidth, rows, chosen, title }: OrderBarsProps) {
  const bands = orderRows(height, fontSize, rows.length);
  const highest = Math.max(1, ...rows.flatMap((row) => row.orders.map((order) => order ?? 0)));
  const barWidth = Math.max(2, Math.round(columnWidth * 0.7));
  const dots = rows.flatMap((row, i) => {
    if (!row.firstLarge) return [];
    const band = bands[i]!;
    const order = row.orders[row.firstLarge.index] ?? 0;
    const x = xs[row.firstLarge.index];
    if (x === undefined) return [];
    return [{ x, y: band.baseline - (order / highest) * band.barMax, text: row.firstLarge.text }];
  });
  // The diagonal runs from the customers' end (the bottom row) upstream.
  const diagonal = [...dots].reverse();
  const halo = { stroke: colour("paper"), strokeWidth: 3, paintOrder: "stroke" as const };
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="order-bars" fontFamily={CHART_FONT} fontSize={fontSize}>
      <title>{title}</title>
      {rows.map((row, i) => {
        const band = bands[i]!;
        return (
          <g key={i} data-row={i} data-own={row.own ? "" : undefined}>
            <line x1={0} x2={width} y1={band.baseline + 0.5} y2={band.baseline + 0.5} stroke={colour("axis")} strokeWidth={1} />
            {row.orders.map((order, column) => {
              const x = xs[column];
              if (order === null || order <= 0 || x === undefined) return null;
              const h = Math.max(1, (order / highest) * band.barMax);
              return (
                <rect
                  key={column}
                  data-mark="order"
                  x={round(x - barWidth / 2)}
                  y={round(band.baseline - h)}
                  width={barWidth}
                  height={round(h)}
                  fill={colour(row.own ? "ink" : "order-history")}
                />
              );
            })}
          </g>
        );
      })}
      {chosen !== null && xs[chosen] !== undefined ? (
        <line
          data-mark="chosen"
          x1={round(xs[chosen]!)}
          x2={round(xs[chosen]!)}
          y1={0}
          y2={height}
          stroke={colour("ink")}
          strokeWidth={1}
          strokeDasharray="3 2"
        />
      ) : null}
      {diagonal.length > 1 ? (
        <polyline
          data-mark="diagonal"
          points={diagonal.map((dot) => `${round(dot.x)},${round(dot.y)}`).join(" ")}
          fill="none"
          stroke={colour("restordre")}
          strokeWidth={1}
        />
      ) : null}
      {dots.map((dot, i) => {
        const w = textWidth(dot.text, fontSize, 600);
        // Left of the dot when there is room, else right of it; never past the field.
        const left = dot.x - 4 - w >= 0;
        return (
          // Two Roles may share their first large Uke: the row keeps each key apart.
          <g key={i} data-mark="first-large">
            <circle cx={round(dot.x)} cy={round(dot.y)} r={2.5} fill={colour("restordre")} />
            <text
              x={round(left ? dot.x - 4 : Math.min(dot.x + 4, width - w))}
              y={round(dot.y - 3)}
              textAnchor={left ? "end" : "start"}
              fontWeight={600}
              fill={colour("restordre")}
              {...halo}
            >
              {dot.text}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** The Role names in the sticky label column, each at its row's centre (`ink`; the own Role in
 * weight 600 with «(deg)»). */
export function OrderBarsLabels({
  width,
  height,
  fontSize,
  labels,
  title,
}: {
  width: number;
  height: number;
  fontSize: number;
  labels: readonly { text: string; own: boolean }[];
  title: string;
}) {
  const bands = orderRows(height, fontSize, labels.length);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="axis" fontFamily={CHART_FONT} fontSize={fontSize}>
      <title>{title}</title>
      {labels.map((label, i) => (
        <text key={label.text} x={0} y={round(bands[i]!.baseline - fontSize * DESCENT)} fontWeight={label.own ? 600 : 400} fill={colour("ink")}>
          {label.text}
        </text>
      ))}
    </svg>
  );
}

/**
 * The `flow-*` step of a Rolle × Uke cell (DESIGN.md → Matrix steps): 0 for no fill, else 1 to 4
 * by the Order's share of the game's largest Order, in five equal parts (the smallest part takes
 * no fill). A drawing choice, like an axis tick: the number itself is the api's and is printed.
 */
export function flowStep(order: number, largest: number): 0 | 1 | 2 | 3 | 4 {
  if (order <= 0 || largest <= 0) return 0;
  const part = Math.min(5, Math.ceil((order / largest) * 5));
  return Math.max(0, part - 1) as 0 | 1 | 2 | 3 | 4;
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}
