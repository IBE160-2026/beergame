import { scaleLinear } from "d3-scale";

import { CHART_FONT, colour } from "./palette";

/** One Uke of the reveal at the centre `x` of its table column, as the api gave it. */
export type DemandBandPoint = { week: number; x: number; demand: number; incoming: number; order: number };

export type DemandBandProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  fontSize: number;
  points: readonly DemandBandPoint[];
  /** The narrowest week column, in px: each Uke's band step is one column wide. */
  columnWidth: number;
  /** The axis top in units (`demandAxis`): no mark is ever cut. */
  top: number;
  /** «Kundenes etterspørsel: 8», on the band at its right end. */
  demandLabel: string;
  /** «Din ordre, 24 i Uke 11», at that Uke's bar; null with no Order. */
  largest: { week: number; text: string } | null;
  /** The SVG `<title>` (AD-18). */
  title: string;
};

/** The axis steps tried, smallest first: the band shows at most four steps (`07-debrief.png`:
 * 0, 8, 16, 24). */
const STEPS = [4, 8, 10, 20, 40, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000];

/** The axis of the band: its top and its ticks, from the highest value shown. */
export function demandAxis(highest: number): { top: number; ticks: number[] } {
  const step = STEPS.find((s) => highest / s <= 4) ?? Math.ceil(highest / 4);
  const count = Math.max(1, Math.ceil(highest / step));
  return { top: count * step, ticks: Array.from({ length: count + 1 }, (_, i) => i * step) };
}

/** The y-scale the band and its sticky tick labels share: 0 at the baseline, `top` below the
 * room the labels need. */
export function demandScale(height: number, fontSize: number, top: number) {
  return scaleLinear()
    .domain([0, top])
    .range([height - 1, Math.round(fontSize * 1.4)]);
}

/** Text width from an upper bound per character, so a label is never placed past the edge. */
function textWidth(text: string, fontSize: number): number {
  return text.length * fontSize * 0.58;
}

/**
 * Etterspørselsbånd (Story 9.4, Debrief step 2, UX-DR32, DESIGN.md `demand-band`): the customers'
 * demand as a `lager-fill` band, one column wide per Uke, with «Kundenes etterspørsel: N» on it in
 * `ink` weight 600; the Orders that reached the Seat as a thin `ink-secondary` line («Ordre inn:
 * det eneste du så»); the Seat's own Orders as `ink` bars, with «Din ordre, 24 i Uke 11» at the
 * largest. `hairline` gridlines on the ticks over an `axis` baseline. Not interactive and
 * `aria-hidden`: the table Uke / Kundene / Ordre inn / Din ordre under it is its alternative. Each
 * mark carries `data-mark`/`data-week`. Hand-made SVG (see README).
 */
export function DemandBand({ width, height, fontSize, points, columnWidth, top, demandLabel, largest, title }: DemandBandProps) {
  const y = demandScale(height, fontSize, top);
  const base = y(0);
  const half = columnWidth / 2;
  const barWidth = Math.max(3, Math.round(columnWidth * 0.45));
  const ticks = demandAxis(top).ticks.filter((tick) => tick <= top);
  // The band as one stepped outline: each Uke's level across its whole column.
  const band = points.length
    ? `M${points[0]!.x - half},${base} ` +
      points.map((p) => `L${p.x - half},${y(p.demand)} L${p.x + half},${y(p.demand)}`).join(" ") +
      ` L${points[points.length - 1]!.x + half},${base} Z`
    : "";
  const edge = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x - half},${y(p.demand)} L${p.x + half},${y(p.demand)}`).join(" ");
  const incoming = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${y(p.incoming)}`).join(" ");
  const last = points[points.length - 1];
  const peak = largest ? points.find((p) => p.week === largest.week) : undefined;
  // Text on the band keeps a `paper` halo, so it reads over a bar or the line.
  const halo = { stroke: colour("paper"), strokeWidth: 3, paintOrder: "stroke" as const, strokeLinejoin: "round" as const };
  let peakLabel = null;
  if (largest && peak) {
    const wide = textWidth(largest.text, fontSize);
    const right = peak.x + barWidth / 2 + fontSize * 0.25;
    const fitsRight = right + wide <= width;
    peakLabel = (
      <text
        data-label="largest"
        x={fitsRight ? right : Math.max(wide, peak.x - barWidth / 2 - fontSize * 0.25)}
        y={Math.max(fontSize, y(peak.order) + fontSize * 0.35)}
        textAnchor={fitsRight ? "start" : "end"}
        fill={colour("ink")}
        fontWeight={600}
        {...halo}
      >
        {largest.text}
      </text>
    );
  }
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-chart="demand-band"
      aria-hidden="true"
      fontFamily={CHART_FONT}
      fontSize={fontSize}
      overflow="hidden"
    >
      <title>{title}</title>
      {ticks.map((tick) => (
        <line key={tick} x1={0} x2={width} y1={y(tick)} y2={y(tick)} stroke={colour(tick === 0 ? "axis" : "hairline")} strokeWidth={1} />
      ))}
      <path data-mark="demand" d={band} fill={colour("lager-fill")} />
      <path d={edge} fill="none" stroke={colour("lager")} strokeWidth={1} />
      {points.map((p) =>
        p.order > 0 ? (
          <rect
            key={p.week}
            data-mark="order"
            data-week={p.week}
            data-x={Math.round(p.x * 100) / 100}
            x={p.x - barWidth / 2}
            y={y(p.order)}
            width={barWidth}
            height={base - y(p.order)}
            fill={colour("ink")}
          />
        ) : null,
      )}
      <path data-mark="incoming" d={incoming} fill="none" stroke={colour("ink-secondary")} strokeWidth={1.5} strokeLinejoin="round" />
      {last ? (
        <text
          data-label="demand"
          x={width - fontSize * 0.25}
          y={y(last.demand) - fontSize * 0.35}
          textAnchor="end"
          fill={colour("ink")}
          fontWeight={600}
          {...halo}
        >
          {demandLabel}
        </text>
      ) : null}
      {peakLabel}
    </svg>
  );
}
