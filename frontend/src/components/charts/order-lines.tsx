import { line } from "d3-shape";

import { CHART_FONT, colour } from "./palette";
import { niceTicks, scaleY } from "./scales";

/** One game's Orders, Uke 1 first; null for a Week with no Order. */
export type OrderLine = {
  key: string;
  /** The Student's own game: drawn thick, with a point at each Week (NFR-6: not colour alone). */
  own: boolean;
  orders: readonly (number | null)[];
};

export type OrderLinesProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  fontSize: number;
  /** The top of the y axis, shared by every Role so the charts read on one scale. */
  top: number;
  lines: readonly OrderLine[];
  /** The SVG `<title>`, the alternative text a PDF reader gets (AD-18). */
  title: string;
  /** Tick text from the number formatter. */
  formatTick: (value: number) => string;
  /** «Uke 1» at the left end and «Uke 36» at the right end. */
  firstLabel: string;
  lastLabel: string;
};

/** The step the Order axis grows by. */
const ORDER_STEP = 10;

/** The top of the Order axis: the highest Order rounded up to a multiple of 10, at least 10. */
export function orderAxisTop(highest: number): number {
  if (!Number.isFinite(highest) || highest <= ORDER_STEP) return ORDER_STEP;
  return Math.ceil(highest / ORDER_STEP) * ORDER_STEP;
}

/** The narrowest a Week may be before the chart is drawn wider than its box and scrolls. */
export const MIN_WEEK_WIDTH = 9;

/**
 * Ordrelinjer (Story 14.5, FR-86, UX-DR72): every Class game's Orders per Uke for one Role as a
 * line, all games in one thin `ink-muted` stroke so none stands out, and the Student's own game
 * on top in a thick `ink` stroke with a point at each Uke. There is no ranking and no colour per
 * game. Hand-made SVG like the rest of the module (see README); `aria-hidden`, its numbers are
 * «Vis som tabell», and the `<title>` stays for print. A Week with no Order breaks the line.
 */
export function OrderLines({ width, height, fontSize, top, lines, title, formatTick, firstLabel, lastLabel }: OrderLinesProps) {
  const weeks = Math.max(1, ...lines.map((l) => l.orders.length));
  const plotTop = Math.round(fontSize * 0.8);
  const base = height - Math.round(fontSize * 1.9);
  const ticks = niceTicks([0, top], base - plotTop, fontSize);
  const tickWidth = Math.max(...ticks.map((t) => formatTick(t).length)) * fontSize * 0.55 + fontSize * 0.6;
  const left = Math.ceil(tickWidth);
  const right = width - Math.ceil(fontSize * 0.4);
  const y = scaleY([0, top], plotTop, base);
  const x = (week: number) => (weeks > 1 ? left + ((week - 1) / (weeks - 1)) * (right - left) : (left + right) / 2);
  const path = line<number | null>()
    .defined((order) => order !== null)
    .x((_, index) => x(index + 1))
    .y((order) => y(order ?? 0));
  const others = lines.filter((l) => !l.own);
  const own = lines.filter((l) => l.own);
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-chart="order-lines"
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
      {others.map((l) => (
        <path
          key={l.key}
          d={path(l.orders as (number | null)[]) ?? ""}
          fill="none"
          stroke={colour("ink-muted")}
          strokeOpacity={0.55}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          data-mark="game-line"
          data-game={l.key}
        />
      ))}
      {own.map((l) => (
        <g key={l.key} data-mark="own-line" data-game={l.key}>
          {/* A `paper` halo under the own line keeps it apart from the lines it crosses. */}
          <path
            d={path(l.orders as (number | null)[]) ?? ""}
            fill="none"
            stroke={colour("paper")}
            strokeWidth={5}
            strokeLinejoin="round"
          />
          <path
            d={path(l.orders as (number | null)[]) ?? ""}
            fill="none"
            stroke={colour("ink")}
            strokeWidth={2.5}
            strokeLinejoin="round"
          />
          {l.orders.map((order, index) =>
            order === null ? null : (
              <circle
                key={index}
                cx={x(index + 1)}
                cy={y(order)}
                r={2.75}
                fill={colour("ink")}
                stroke={colour("paper")}
                strokeWidth={1}
                data-week={index + 1}
              />
            ),
          )}
        </g>
      ))}
      <text x={left} y={height - fontSize * 0.45} fill={colour("ink-muted")}>
        {firstLabel}
      </text>
      {weeks > 1 ? (
        <text x={right} y={height - fontSize * 0.45} textAnchor="end" fill={colour("ink-muted")}>
          {lastLabel}
        </text>
      ) : null}
    </svg>
  );
}
