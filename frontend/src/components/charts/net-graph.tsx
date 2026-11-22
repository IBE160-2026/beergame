import { scaleLinear } from "d3-scale";
import { area, line } from "d3-shape";
import { useId } from "react";

import { CHART_FONT, colour } from "./palette";
import { netDomain, netTicks, spreadLabels } from "./scales";

/** One Uke of the Netto lager field, at the centre `x` of its table column. */
export type NetPoint = { week: number; x: number; net: number; position: number };

export type NetGraphProps = {
  /** Fixed size in px, from the caller (AD-18: never a responsive container). */
  width: number;
  height: number;
  /** Label size in px (the `caption` size at the current text zoom). */
  fontSize: number;
  /** Uke 1 or the first drawn Uke … nå, in order; both lines stop at the last one (nå). */
  points: readonly NetPoint[];
  /** The now-line's x: the right edge of the nå column. */
  nowX: number;
  /** The SVG `<title>`, the only alternative text a PDF reader gets (AD-18). */
  title: string;
  /** Direct labels at nå: «Restordre 13» and «Posisjon 3». */
  netLabel: string;
  positionLabel: string;
  /** «Nå», by the now-line. */
  nowLabel: string;
  /**
   * The projection from nå (Replay only, Epic 10): a dashed line ending in a hollow dot. The
   * Klassespill never passes it, so nothing of it is drawn (UX-DR19).
   */
  projection?: readonly { week: number; x: number; value: number }[];
  /** The projection runs past the drawn columns (a horizon beyond nå + 4, Story 10.4): its last
   * point is where the axis ends, so it gets no dot. */
  projectionClipped?: boolean;
  /**
   * Hjem's Spillkort (Story 6.17, DESIGN.md → Spillkort): Netto lager at mini scale, as drawn in
   * `04-student-hjem.png`: the line, its fills, the dot at nå and «Nå» only. No Posisjon and no
   * direct labels, so it adds no mark of its own; `netLabel` and `positionLabel` are unused.
   */
  mini?: boolean;
};

/** The y-scale and ticks the field and its sticky axis share. */
export function netScale(props: Pick<NetGraphProps, "height" | "fontSize" | "points" | "projection" | "mini">) {
  const { height, fontSize, points, projection, mini = false } = props;
  const values = [
    ...points.flatMap((p) => (mini ? [p.net] : [p.net, p.position])),
    ...(projection ?? []).map((p) => p.value),
  ];
  const domain = netDomain(values);
  // Room above for «Nå» and half a label below, so the outermost labels stay inside.
  const top = Math.round(fontSize * 1.7);
  const bottom = height - Math.round(fontSize * LABEL_HALF);
  const y = scaleLinear().domain(domain).range([bottom, top]);
  return { y, ticks: netTicks(domain, bottom - top, fontSize), domain };
}

const MARKER = 4;
/** Half a label's box below its centre line (Source Sans 3: descent and the `dy` shift), so a
 * label centred on the lowest tick stays inside the field. */
const LABEL_HALF = 0.85;

/**
 * Netto lager with the Posisjon line (UX-DR16, DESIGN.md `net-graph`): one 2 px line, blue with
 * `lager-fill` above a true zero and red with `restordre-fill` below; Posisjon thinner in
 * `ink-secondary` with a square at every Uke and no fill. The two differ in stroke, fill, marker
 * and label, never by colour alone. Hand-made SVG: Recharts renders nothing on the server (see
 * README). The marks carry `data-mark`/`data-week` for the alignment checks.
 */
export function NetGraph(props: NetGraphProps) {
  const { width, height, fontSize, points, nowX, title, netLabel, positionLabel, nowLabel, projection, projectionClipped = false, mini = false } =
    props;
  const clip = useId().replace(/:/g, "");
  const { y, ticks } = netScale(props);
  const zero = y(0);
  const now = points[points.length - 1];

  const netLine = line<NetPoint>()
    .x((p) => p.x)
    .y((p) => y(p.net))(points);
  const netArea = area<NetPoint>()
    .x((p) => p.x)
    .y0(zero)
    .y1((p) => y(p.net))(points);
  const positionLine = mini
    ? null
    : line<NetPoint>()
        .x((p) => p.x)
        .y((p) => y(p.position))(points);

  // Direct labels start right of the now-line; one too long for the room left ends at the edge.
  const labelAt = (text: string) => {
    const x = nowX + fontSize * 0.4;
    return x + text.length * fontSize * 0.55 > width - 2
      ? { x: width - 2, textAnchor: "end" as const }
      : { x, textAnchor: "start" as const };
  };
  const labelTop = fontSize * 2.3;
  const labelBottom = height - fontSize * LABEL_HALF;
  const spread = now ? spreadLabels([y(now.net), y(now.position)], fontSize * 1.5, labelTop, labelBottom) : [0, 0];
  // Story 10.6 (10.4 visual check): the projection runs right of nå through where the labels
  // stand, so each label moves to the nearest height clear of its line and dot.
  const ahead = projection && projection.length > 0 && now && !mini;
  const [netY, positionY] = ahead
    ? clearOfProjection(
        spread,
        [labelSpan(labelAt(netLabel), netLabel, fontSize), labelSpan(labelAt(positionLabel), positionLabel, fontSize)],
        (x0, x1) => projectionBand(projection, y, x0, x1, projectionClipped),
        // Half a label's ink: from the ascenders 0.4 em above its centre to the descenders 0.55 em
        // below (`dy` 0.35 em), plus a pixel.
        { half: fontSize * 0.55 + 1, gap: fontSize * 1.5, top: labelTop, bottom: labelBottom },
      )
    : spread;
  // A halo in the tint they stand on keeps the labels legible where a gridline (drawn on right of
  // nå in a Replay) or, with no clear height left, the projection still crosses them.
  const halo = ahead
    ? { stroke: colour("future-tint"), strokeWidth: 4, paintOrder: "stroke" as const, strokeLinejoin: "round" as const }
    : {};

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-chart="net"
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
      {/* `future-tint` right of the now-line: known arrivals, never the past (DESIGN.md). */}
      <rect x={nowX} y={0} width={Math.max(0, width - nowX)} height={height} fill={colour("future-tint")} />
      {/* Gridlines and the zero line stop at nå, so no rule runs through the direct labels right of
          it (mockup 05); a projection (Replay) is drawn there, so they then run on. */}
      {ticks.map((tick) => (
        <line
          key={tick}
          x1={0}
          x2={projection && projection.length > 0 ? width : Math.min(width, nowX)}
          y1={y(tick)}
          y2={y(tick)}
          stroke={colour(tick === 0 ? "axis" : "hairline")}
          strokeWidth={1}
        />
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
          data-x={points.map((p) => round(p.x)).join(" ")}
          fill="none"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        >
          <path d={netLine} stroke={colour("lager")} clipPath={`url(#${clip}-above)`} />
          <path d={netLine} stroke={colour("restordre")} clipPath={`url(#${clip}-below)`} />
        </g>
      ) : null}
      {positionLine ? (
        <path d={positionLine} fill="none" stroke={colour("ink-secondary")} strokeWidth={1.5} strokeLinejoin="round" />
      ) : null}
      {(mini ? [] : points).map((p) => (
        <rect
          key={p.week}
          data-mark="position"
          data-week={p.week}
          x={p.x - MARKER / 2}
          y={y(p.position) - MARKER / 2}
          width={MARKER}
          height={MARKER}
          fill={colour("ink-secondary")}
        />
      ))}
      {projection && projection.length > 0 ? <Projection points={projection} y={y} clipped={projectionClipped} /> : null}
      {now ? (
        <>
          <circle
            data-mark="now"
            data-week={now.week}
            cx={now.x}
            cy={y(now.net)}
            r={3.5}
            fill={colour(now.net < 0 ? "restordre" : now.net > 0 ? "lager" : "ink")}
          />
          {mini ? null : (
            <>
              <text {...labelAt(netLabel)} {...halo} y={netY} dy="0.35em" fill={colour("ink")} data-label="net">
                {netLabel}
              </text>
              <text
                {...labelAt(positionLabel)}
                {...halo}
                y={positionY}
                dy="0.35em"
                fill={colour("ink-secondary")}
                data-label="position"
              >
                {positionLabel}
              </text>
            </>
          )}
        </>
      ) : null}
      <text x={nowX + fontSize * 0.3} y={fontSize * 1.15} fontWeight={600} fill={colour("ink")} data-label="now">
        {nowLabel}
      </text>
    </svg>
  );
}

/** The projection (UX-DR19): a 2 px dashed `projection` line and a hollow dot at its end, told
 * apart from Netto lager (solid, filled) and Posisjon (solid, squares) by dash and marker. */
function Projection({
  points,
  y,
  clipped,
}: {
  points: readonly { week: number; x: number; value: number }[];
  y: (v: number) => number;
  clipped: boolean;
}) {
  const d = line<{ x: number; value: number }>()
    .x((p) => p.x)
    .y((p) => y(p.value))(points);
  const end = points[points.length - 1]!;
  return (
    <g data-mark="projection" data-weeks={points.map((p) => p.week).join(" ")} data-x={points.map((p) => round(p.x)).join(" ")}>
      <path d={d ?? undefined} fill="none" stroke={colour("projection")} strokeWidth={2} strokeDasharray="5 4" />
      {clipped ? null : (
        <circle
          data-projection-end=""
          cx={end.x}
          cy={y(end.value)}
          r={3.5}
          fill={colour("paper")}
          stroke={colour("projection")}
          strokeWidth={1.5}
        />
      )}
    </g>
  );
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}

/** Room around the projection's stroke and dot that a label's text box keeps clear of, in px. */
const LINE_CLEARANCE = 1;
const DOT_REACH = 3.5 + 1.5;

/** A direct label's horizontal extent, from where `labelAt` anchors it and the same width estimate. */
export function labelSpan(at: { x: number; textAnchor: "start" | "end" }, text: string, fontSize: number): [number, number] {
  const width = text.length * fontSize * 0.55;
  return at.textAnchor === "start" ? [at.x, at.x + width] : [at.x - width, at.x];
}

/**
 * The heights the projection (its dashed line, and its end dot unless `clipped`) covers between
 * `x0` and `x1`, as [upper, lower] in px with its stroke; null where it does not reach that span.
 */
export function projectionBand(
  points: readonly { x: number; value: number }[],
  y: (value: number) => number,
  x0: number,
  x1: number,
  clipped: boolean,
): [number, number] | null {
  let upper = Infinity;
  let lower = -Infinity;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]!;
    const b = points[i]!;
    const from = Math.max(x0, Math.min(a.x, b.x));
    const to = Math.min(x1, Math.max(a.x, b.x));
    if (from > to) continue;
    const at = (x: number) => (b.x === a.x ? y(a.value) : y(a.value) + ((x - a.x) / (b.x - a.x)) * (y(b.value) - y(a.value)));
    // The 2 px stroke reaches 1 px either side of the line.
    upper = Math.min(upper, at(from) - 1, at(to) - 1);
    lower = Math.max(lower, at(from) + 1, at(to) + 1);
  }
  const end = points[points.length - 1];
  if (!clipped && end && end.x + DOT_REACH >= x0 && end.x - DOT_REACH <= x1) {
    upper = Math.min(upper, y(end.value) - DOT_REACH);
    lower = Math.max(lower, y(end.value) + DOT_REACH);
  }
  return upper <= lower ? [upper, lower] : null;
}

/**
 * The direct labels' heights moved clear of the projection (Story 10.6): each label in turn (the
 * Netto lager label first, so it stays nearest its line's end) goes to the height nearest the one
 * it wants whose text box (± `half`) meets neither its projection band nor a label placed before
 * it (closer than `gap`), within [top, bottom]. A label with no such height keeps the one it
 * wants (its halo keeps it legible).
 */
export function clearOfProjection(
  wanted: readonly number[],
  spans: readonly [number, number][],
  band: (x0: number, x1: number) => [number, number] | null,
  bounds: { half: number; gap: number; top: number; bottom: number },
): number[] {
  // The Netto lager label first; when that leaves a label without a clear height, the other order
  // is tried, and the one with fewer labels left crossing the projection wins.
  const forward = wanted.map((_, index) => index);
  const first = placeInOrder(forward, wanted, spans, band, bounds);
  if (first.crossing === 0 || wanted.length < 2) return first.placed;
  const second = placeInOrder([...forward].reverse(), wanted, spans, band, bounds);
  return second.crossing < first.crossing ? second.placed : first.placed;
}

function placeInOrder(
  order: readonly number[],
  wanted: readonly number[],
  spans: readonly [number, number][],
  band: (x0: number, x1: number) => [number, number] | null,
  { half, gap, top, bottom }: { half: number; gap: number; top: number; bottom: number },
): { placed: number[]; crossing: number } {
  const placed: number[] = [...wanted];
  const done: number[] = [];
  let crossing = 0;
  for (const index of order) {
    const [x0, x1] = spans[index]!;
    const labels: [number, number][] = done.map((other) => [placed[other]! - gap, placed[other]! + gap]);
    const reach = band(x0, x1);
    const want = wanted[index]!;
    const nearest = (blocked: [number, number][]) => {
      const free = (value: number) => value >= top && value <= bottom && blocked.every(([lo, hi]) => value <= lo || value >= hi);
      const candidates = [Math.min(bottom, Math.max(top, want)), ...blocked.flatMap(([lo, hi]) => [lo, hi])];
      return candidates.filter(free).sort((a, b) => Math.abs(a - want) - Math.abs(b - want))[0];
    };
    const clear = reach ? nearest([...labels, [reach[0] - half - LINE_CLEARANCE, reach[1] + half + LINE_CLEARANCE]]) : undefined;
    if (clear !== undefined) placed[index] = clear;
    else {
      // No height clear of the projection: at least clear of the labels placed before it.
      if (reach) crossing += 1;
      placed[index] = nearest(labels) ?? want;
    }
    done.push(index);
  }
  return { placed, crossing };
}
