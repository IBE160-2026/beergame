import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";
import { useId } from "react";

import { CHART_FONT, colour } from "./palette";
import { netDomain, netTicks } from "./scales";

/** One Uke of the Seat's Netto lager, as the api gave it. */
export type NetOverGamePoint = { week: number; net: number };

export type NetOverGameProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  fontSize: number;
  /** Every Uke of the game, oldest first. */
  points: readonly NetOverGamePoint[];
  /** The SVG `<title>`, the alternative text a PDF reader gets (AD-18). */
  title: string;
  /** Tick text from the number formatter («20», «0», «−40»). */
  formatTick: (value: number) => string;
  /** The Uke labels under the axis («Uke 1» … «Uke 36»). */
  weekLabel: (week: number) => string;
};

/** The Uker labelled under the axis besides the first and the last (`07-debrief.png`: 1, 12, 24,
 * 36). */
const WEEK_STEP = 12;

/**
 * «Ditt netto lager, hele spillet» (Story 9.3, Debrief step 1, `07-debrief.png`): one Seat's Netto
 * lager over every Uke of a finished game, as `net-graph` draws it (UX-DR16): a 2 px line, `lager`
 * with `lager-fill` above a true zero and `restordre` with `restordre-fill` below, `hairline`
 * gridlines on the net ticks (multiples of 20) and an `axis` zero line. Its x is its own (Uke 1 …
 * last Uke), not table columns: there is no week table under it. `aria-hidden`; «Vis som tabell»
 * is its alternative. Hand-made SVG like the rest of the module (see README).
 */
export function NetOverGame({ width, height, fontSize, points, title, formatTick, weekLabel }: NetOverGameProps) {
  const clip = useId().replace(/:/g, "");
  const domain = netDomain(points.map((p) => p.net));
  const plotTop = Math.round(fontSize * 0.8);
  const base = height - Math.round(fontSize * 1.9);
  const ticks = netTicks(domain, base - plotTop, fontSize);
  const tickWidth = Math.max(...ticks.map((t) => formatTick(t).length)) * fontSize * 0.55 + fontSize * 0.6;
  const left = Math.ceil(tickWidth);
  const right = width - Math.ceil(fontSize * 0.4);
  const y = scaleLinear().domain(domain).range([base, plotTop]);
  const first = points[0]?.week ?? 1;
  const last = points[points.length - 1]?.week ?? first;
  const x = last > first ? scaleLinear().domain([first, last]).range([left, right]) : () => (left + right) / 2;
  const zero = y(0);
  const netLine = line<NetOverGamePoint>()
    .x((p) => x(p.week))
    .y((p) => y(p.net))(points);
  const netArea = area<NetOverGamePoint>()
    .x((p) => x(p.week))
    .y0(zero)
    .y1((p) => y(p.net))(points);
  const labelled = weekLabels(points, x, fontSize);
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-chart="net-over-game"
      aria-hidden="true"
      fontFamily={CHART_FONT}
      fontSize={fontSize}
      overflow="hidden"
    >
      <title>{title}</title>
      <defs>
        <clipPath id={`${clip}-above`}>
          <rect x={0} y={0} width={width} height={Math.max(0, zero)} />
        </clipPath>
        <clipPath id={`${clip}-below`}>
          <rect x={0} y={zero} width={width} height={Math.max(0, height - zero)} />
        </clipPath>
      </defs>
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
      {netArea ? (
        <>
          <path d={netArea} fill={colour("lager-fill")} clipPath={`url(#${clip}-above)`} />
          <path d={netArea} fill={colour("restordre-fill")} clipPath={`url(#${clip}-below)`} />
        </>
      ) : null}
      {netLine ? (
        <g
          data-mark="net"
          data-weeks={points.map((p) => p.week).join(" ")}
          fill="none"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        >
          <path d={netLine} stroke={colour("lager")} clipPath={`url(#${clip}-above)`} />
          <path d={netLine} stroke={colour("restordre")} clipPath={`url(#${clip}-below)`} />
        </g>
      ) : null}
      {points.length === 1 ? (
        <circle cx={x(first)} cy={y(points[0]!.net)} r={3.5} fill={colour(points[0]!.net < 0 ? "restordre" : "lager")} />
      ) : null}
      {labelled.map((week, index) => (
        <text
          key={week}
          data-label="week"
          x={x(week)}
          y={height - fontSize * 0.45}
          textAnchor={labelled.length > 1 && index === 0 ? "start" : index === labelled.length - 1 && labelled.length > 1 ? "end" : "middle"}
          fill={colour("ink-muted")}
        >
          {weekLabel(week)}
        </text>
      ))}
    </svg>
  );
}

/**
 * The Uker labelled under the axis: the first and the last always, and every twelfth between
 * them that leaves room for a label on each side (labels never overlap at any text size).
 */
export function weekLabels(
  points: readonly NetOverGamePoint[],
  x: (week: number) => number,
  fontSize: number,
): number[] {
  if (points.length === 0) return [];
  const first = points[0]!.week;
  const last = points[points.length - 1]!.week;
  if (last === first) return [first];
  // «Uke 36» is at most 7 characters of about 0.55 em. The first label starts at its Uke and the
  // last ends at its Uke, so a centred one beside them needs one and a half labels and a gap.
  const room = fontSize * 0.55 * 7 * 1.5 + fontSize * 0.5;
  const chosen = [first];
  for (let week = Math.ceil((first + 1) / WEEK_STEP) * WEEK_STEP; week < last; week += WEEK_STEP) {
    if (x(week) - x(chosen[chosen.length - 1]!) >= room && x(last) - x(week) >= room) chosen.push(week);
  }
  if (x(last) - x(first) >= room) chosen.push(last);
  return chosen;
}
