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
  /** A dashed line at this Uke: the shared screen's chosen Uke (Story 9.13). */
  marker?: number;
  /** The Netto lager values the y scale must hold, beyond this chart's own: the shared screen
   * gives every Role's, so the four charts share one scale. */
  scaleWith?: readonly number[];
  /** A second run on the same Uke axis, drawn as a thin `ink-muted` line under the main one
   * (Story 10.7: the Class game beside the Replay, `09-alle-sider.png`, «grå: Klassespill»). The
   * axis runs from the first to the last Uke of either run. */
  compare?: readonly NetOverGamePoint[];
  /** Direct labels at the right end of the lines (DESIGN.md: label lines directly): the main run's
   * and, with `compare`, the second run's (Story 10.7 follow-up). Room for them is taken from the
   * plot's right side. */
  lineLabels?: { main: string; compare?: string };
  /** The y axis' unit («enheter»), written above the tick labels. */
  yUnit?: string;
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
export function NetOverGame({
  width,
  height,
  fontSize,
  points,
  title,
  formatTick,
  weekLabel,
  marker,
  scaleWith,
  compare,
  lineLabels,
  yUnit,
}: NetOverGameProps) {
  const clip = useId().replace(/:/g, "");
  const others = compare ?? [];
  const domain = netDomain([...points.map((p) => p.net), ...others.map((p) => p.net), ...(scaleWith ?? [])]);
  const plotTop = Math.round(fontSize * (yUnit ? 2 : 0.8));
  const base = height - Math.round(fontSize * 1.9);
  const ticks = netTicks(domain, base - plotTop, fontSize);
  const tickWidth = Math.max(...ticks.map((t) => formatTick(t).length)) * fontSize * 0.55 + fontSize * 0.6;
  const left = Math.ceil(tickWidth);
  const labelTexts = lineLabels ? [lineLabels.main, ...(compare && lineLabels.compare ? [lineLabels.compare] : [])] : [];
  // A direct label is about 0.55 em a character, with half an em before it.
  const labelRoom = labelTexts.length ? Math.ceil(Math.max(...labelTexts.map((t) => t.length)) * fontSize * 0.55 + fontSize * 0.5) : 0;
  const right = width - Math.ceil(fontSize * 0.4) - labelRoom;
  const y = scaleLinear().domain(domain).range([base, plotTop]);
  const weeks = [...points, ...others].map((p) => p.week);
  const first = weeks.length ? Math.min(...weeks) : 1;
  const last = weeks.length ? Math.max(...weeks) : first;
  const x = last > first ? scaleLinear().domain([first, last]).range([left, right]) : () => (left + right) / 2;
  const zero = y(0);
  const netLine = line<NetOverGamePoint>()
    .x((p) => x(p.week))
    .y((p) => y(p.net))(points);
  const netArea = area<NetOverGamePoint>()
    .x((p) => x(p.week))
    .y0(zero)
    .y1((p) => y(p.net))(points);
  const compareLine = others.length > 1 ? line<NetOverGamePoint>().x((p) => x(p.week)).y((p) => y(p.net))(others) : null;
  const ends = lineEnds(points, others, lineLabels, y, fontSize, plotTop, base);
  const labelled = weeks.length
    ? weekLabels(
        [
          { week: first, net: 0 },
          { week: last, net: 0 },
        ],
        x,
        fontSize,
      )
    : [];
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
      {compareLine ? (
        <path
          data-mark="compare"
          data-weeks={others.map((p) => p.week).join(" ")}
          d={compareLine}
          fill="none"
          stroke={colour("ink-muted")}
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
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
      {marker !== undefined && marker >= first && marker <= last ? (
        <line
          data-mark="marker"
          x1={Math.round(x(marker)) + 0.5}
          x2={Math.round(x(marker)) + 0.5}
          y1={plotTop}
          y2={base}
          stroke={colour("ink-muted")}
          strokeWidth={1}
          strokeDasharray="3 3"
        />
      ) : null}
      {points.length === 1 ? (
        <circle cx={x(points[0]!.week)} cy={y(points[0]!.net)} r={3.5} fill={colour(points[0]!.net < 0 ? "restordre" : "lager")} />
      ) : null}
      {yUnit ? (
        <text data-label="unit" x={0} y={fontSize * 0.9} fill={colour("ink-muted")}>
          {yUnit}
        </text>
      ) : null}
      {ends.map((end) => (
        <text
          key={end.kind}
          data-label={`line-${end.kind}`}
          x={right + fontSize * 0.4}
          y={end.y}
          dy="0.35em"
          fill={colour(end.kind === "compare" ? "ink-muted" : "ink")}
        >
          {end.text}
        </text>
      ))}
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
 * Where the direct labels stand: at the height of each line's last Uke, pushed apart to at least
 * 1.2 em when the two lines end close together, and kept inside the plot.
 */
function lineEnds(
  points: readonly NetOverGamePoint[],
  others: readonly NetOverGamePoint[],
  labels: NetOverGameProps["lineLabels"],
  y: (net: number) => number,
  fontSize: number,
  top: number,
  bottom: number,
): { kind: "main" | "compare"; text: string; y: number }[] {
  if (!labels) return [];
  const clamp = (value: number) => Math.min(bottom - fontSize * 0.5, Math.max(top + fontSize * 0.5, value));
  const ends: { kind: "main" | "compare"; text: string; y: number }[] = [];
  const lastMain = points[points.length - 1];
  if (lastMain) ends.push({ kind: "main", text: labels.main, y: clamp(y(lastMain.net)) });
  const lastOther = others[others.length - 1];
  if (lastOther && labels.compare) ends.push({ kind: "compare", text: labels.compare, y: clamp(y(lastOther.net)) });
  if (ends.length === 2) {
    const [a, b] = ends as [(typeof ends)[number], (typeof ends)[number]];
    const gap = fontSize * 1.2;
    if (Math.abs(a.y - b.y) < gap) {
      const middle = (a.y + b.y) / 2;
      const [upper, lower] = a.y <= b.y ? [a, b] : [b, a];
      upper.y = middle - gap / 2;
      lower.y = middle + gap / 2;
      if (upper.y < top) {
        upper.y = top;
        lower.y = top + gap;
      }
      if (lower.y > bottom) {
        lower.y = bottom;
        upper.y = bottom - gap;
      }
    }
  }
  return ends;
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
