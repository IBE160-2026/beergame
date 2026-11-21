import { type BandInput, bandLayout, type Box } from "./chain-band-layout";
import { CHART_FONT, colour } from "./palette";

export type ChainBandProps = BandInput & {
  /** The SVG `<title>` (AD-18). */
  title: string;
  /**
   * Which band: the Seat's own link during play. The four-Role chain of the Debrief and
   * Spillinnsikt (Story 9.5) is a second variant of this component; only `seat` is built.
   */
  variant?: "seat";
};

const ARROW = 5;

/**
 * Kjedebånd (Story 6.9, UX-DR14, UX-DR15, DESIGN.md `chain-band`): the Seat's own link as a flow,
 * upstream at the left. Orders run left along the top, goods run right below; the node holds the
 * stock as a blue bar above the baseline and the backlog as a red bar below; the known arrivals
 * are boxes on the pipe at true scale, the overdue units a dashed box with a break. Hand-made SVG
 * at a fixed width from the caller; the caller hides it from screen readers and gives the band's
 * one sentence instead. Not interactive.
 */
export function ChainBand({ title, variant = "seat", ...input }: ChainBandProps) {
  const band = bandLayout(input);
  const { width, height, node, orderY, goodsY } = band;
  const ink = colour("ink");
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-chart="band"
      data-variant={variant}
      data-scale={round(band.scale)}
      fontFamily={CHART_FONT}
      fontSize={band.fontSize}
      overflow="hidden"
    >
      <title>{title}</title>
      {/* The order line, right to left: in from downstream to the node, out from it to upstream. */}
      <Arrow x1={width} x2={node.x + node.width + 1} y={orderY} colour={ink} />
      <Arrow x1={node.x - 1} x2={0} y={orderY} colour={ink} />
      {/* The goods line, left to right: the pipe into the node, then out downstream. */}
      <Arrow x1={0} x2={node.x - 1} y={goodsY} colour={ink} />
      <Arrow x1={node.x + node.width} x2={width} y={goodsY} colour={ink} />
      <rect
        data-mark="node"
        x={node.x}
        y={node.y}
        width={node.width}
        height={node.height}
        fill={colour("paper")}
        stroke={colour("axis")}
        strokeWidth={1}
      />
      <line x1={node.x} x2={node.x + node.width} y1={goodsY} y2={goodsY} stroke={colour("axis")} strokeWidth={1} />
      {band.stockBar ? <Rect box={band.stockBar} fill={colour("lager")} mark="stock" /> : null}
      {band.backlogBar ? <Rect box={band.backlogBar} fill={colour("restordre")} mark="backlog" /> : null}
      {band.boxes.map((box, i) => (
        <rect
          key={i}
          data-mark="arrival"
          x={box.x}
          y={box.y}
          width={box.width}
          height={box.height}
          fill={colour("paper")}
          stroke={colour("lager")}
          strokeWidth={1}
        />
      ))}
      {band.typedBox ? (
        // The just-typed Order: a 1.5 px `ink` border (DESIGN.md → Kjedebånd).
        <rect
          data-mark="typed"
          x={band.typedBox.x}
          y={band.typedBox.y}
          width={band.typedBox.width}
          height={band.typedBox.height}
          fill={colour("paper")}
          stroke={ink}
          strokeWidth={1.5}
        />
      ) : null}
      {band.overdueBox ? <Overdue box={band.overdueBox} /> : null}
      {band.labels.map((label) => (
        <text
          key={`${label.key}-${label.text}`}
          data-label={label.key}
          data-est={label.width}
          data-wrapped={label.wrapped ? "" : undefined}
          // Flush right keeps 1 px in from the edge: a glyph's box runs a little past its advance.
          x={round(label.alignEnd ? Math.min(label.x + label.width, width - 1) : label.x)}
          y={round(label.y)}
          textAnchor={label.alignEnd ? "end" : undefined}
          fontWeight={label.weight}
          fill={colour(label.muted ? "ink-muted" : "ink")}
        >
          {label.text}
        </text>
      ))}
    </svg>
  );
}

/** A 1.1 px `ink` line from `x1` to `x2` with its head at `x2`. */
function Arrow({ x1, x2, y, colour: stroke }: { x1: number; x2: number; y: number; colour: string }) {
  const dir = x2 > x1 ? 1 : -1;
  return (
    <g data-mark="arrow">
      <line x1={x1} x2={x2 - dir * (ARROW - 1)} y1={y} y2={y} stroke={stroke} strokeWidth={1.1} />
      <path d={`M${x2} ${y} L${x2 - dir * ARROW} ${y - 3} L${x2 - dir * ARROW} ${y + 3} Z`} fill={stroke} />
    </g>
  );
}

function Rect({ box, fill, mark }: { box: Box; fill: string; mark: string }) {
  return <rect data-mark={mark} x={round(box.x)} y={round(box.y)} width={round(box.width)} height={round(box.height)} fill={fill} />;
}

/** Units overdue with no known date: a dashed box of fixed width, broken by two slashes. */
function Overdue({ box }: { box: Box }) {
  const mid = box.x + box.width / 2;
  // The slashes stand 1 px past the box, clear of the number written above it.
  const slash = (dx: number) => `M${mid + dx - 2} ${box.y + box.height + 1} L${mid + dx + 2} ${box.y - 1}`;
  return (
    <g data-mark="overdue">
      <rect
        x={box.x}
        y={box.y}
        width={box.width}
        height={box.height}
        fill={colour("paper")}
        stroke={colour("lager")}
        strokeWidth={1}
        strokeDasharray="3 2"
      />
      <path d={`${slash(-2)} ${slash(2)}`} stroke={colour("paper")} strokeWidth={3} />
      <path d={`${slash(-2)} ${slash(2)}`} stroke={colour("ink")} strokeWidth={1} />
    </g>
  );
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}
