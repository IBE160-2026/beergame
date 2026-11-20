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
  projection?: readonly { x: number; value: number }[];
};

/** The y-scale and ticks the field and its sticky axis share. */
export function netScale(props: Pick<NetGraphProps, "height" | "fontSize" | "points" | "projection">) {
  const { height, fontSize, points, projection } = props;
  const values = [...points.flatMap((p) => [p.net, p.position]), ...(projection ?? []).map((p) => p.value)];
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
  const { width, height, fontSize, points, nowX, title, netLabel, positionLabel, nowLabel, projection } = props;
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
  const positionLine = line<NetPoint>()
    .x((p) => p.x)
    .y((p) => y(p.position))(points);

  // Direct labels start right of the now-line; one too long for the room left ends at the edge.
  const labelAt = (text: string) => {
    const x = nowX + fontSize * 0.4;
    return x + text.length * fontSize * 0.55 > width - 2
      ? { x: width - 2, textAnchor: "end" as const }
      : { x, textAnchor: "start" as const };
  };
  const [netY, positionY] = now
    ? spreadLabels([y(now.net), y(now.position)], fontSize * 1.5, fontSize * 2.3, height - fontSize * LABEL_HALF)
    : [0, 0];

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
      {ticks.map((tick) => (
        <line
          key={tick}
          x1={0}
          x2={width}
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
      {points.map((p) => (
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
      {projection && projection.length > 0 ? <Projection points={projection} y={y} /> : null}
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
          <text {...labelAt(netLabel)} y={netY} dy="0.35em" fill={colour("ink")} data-label="net">
            {netLabel}
          </text>
          <text {...labelAt(positionLabel)} y={positionY} dy="0.35em" fill={colour("ink-secondary")} data-label="position">
            {positionLabel}
          </text>
        </>
      ) : null}
      <text x={nowX + fontSize * 0.3} y={fontSize * 1.15} fontWeight={600} fill={colour("ink")} data-label="now">
        {nowLabel}
      </text>
    </svg>
  );
}

function Projection({ points, y }: { points: readonly { x: number; value: number }[]; y: (v: number) => number }) {
  const d = line<{ x: number; value: number }>()
    .x((p) => p.x)
    .y((p) => y(p.value))(points);
  const end = points[points.length - 1]!;
  return (
    <g data-mark="projection">
      <path d={d ?? undefined} fill="none" stroke={colour("projection")} strokeWidth={2} strokeDasharray="5 4" />
      <circle cx={end.x} cy={y(end.value)} r={3.5} fill={colour("paper")} stroke={colour("projection")} strokeWidth={1.5} />
    </g>
  );
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}
