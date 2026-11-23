import { textWidth } from "./chain-band-layout";
import { CHART_FONT, colour } from "./palette";

export type CostDistributionProps = {
  /** Fixed size from the caller (AD-18); the height follows from the font size. */
  width: number;
  fontSize: number;
  /** Each finished game's chain cost in kroner, as the api sent it: one tick each. */
  values: readonly number[];
  /** The api's median and quartiles (AD-10): the box spans the quartiles. */
  median: number;
  lower: number;
  upper: number;
  /** «Median 1 954», over the median line. */
  medianLabel: string;
  /** The SVG `<title>` (AD-18). */
  title: string;
  /** Axis label text from the number formatter («1 000»). */
  formatTick: (value: number) => string;
  /** A value the axis must reach as well (Story 14.1): small multiples pass their highest value,
   * so every one shares one axis. */
  highest?: number;
  /** Story 14.3 (UX-DR51): «Fjoråret», the previous Class session's stored median chain cost, a
   * dashed mark with its label (`previousLabel`, «Fjoråret 2 740») under the axis. */
  previous?: number | null;
  previousLabel?: string;
};

const STEPS = [1, 2, 2.5, 5];

/**
 * The axis of the Kostnadsfordeling: from 0 to the lowest multiple of a 1–2–2,5–5 step that holds
 * every value, with the smallest step whose labels stand at least 1.6 label widths apart. Where no
 * step leaves that room (a box narrower than two labels), 0 and the lowest 1–2–2,5–5 top. A
 * display choice only (AD-10).
 */
export function distributionAxis(highest: number, width: number, labelWidth: (value: number) => number): number[] {
  const most = Number.isFinite(highest) && highest > 0 ? highest : 1;
  for (let decade = 1; decade <= most * 10; decade *= 10) {
    for (const each of STEPS) {
      const step = decade * each;
      const top = Math.ceil(most / step) * step;
      const intervals = top / step;
      if (width / intervals >= 1.6 * labelWidth(top)) {
        return Array.from({ length: intervals + 1 }, (_, i) => i * step);
      }
    }
  }
  for (let decade = 1; ; decade *= 10) {
    const top = STEPS.map((each) => decade * each).find((value) => value >= most);
    if (top !== undefined) return [0, top];
  }
}

/** Where a label of `w` centred on `x` stands, kept inside 0 … `width`. */
function clampedStart(x: number, w: number, width: number): number {
  return Math.min(Math.max(0, x - w / 2), Math.max(0, width - w));
}

/**
 * Kostnadsfordeling (`cost-distribution`, Story 7.6, DESIGN.md → Charts, `08-laerer-oversikt.png`):
 * «Klassens kostnad» as one `order-history` tick per finished game on a kroner axis from 0, a
 * `hairline` box for the middle half and an `ink` median line labelled «Median 1 954»; with a
 * stored aggregate of the previous Class session (Story 14.3), a dashed `ink-secondary` mark
 * labelled «Fjoråret 2 740» under the axis. Hand-made SVG (README). `aria-hidden`: the text summary
 * under it and its «Vis som tabell» carry the numbers; the `<title>` stays for print.
 */
export function CostDistribution({
  width,
  fontSize,
  values,
  median,
  lower,
  upper,
  medianLabel,
  title,
  formatTick,
  highest = 0,
  previous = null,
  previousLabel = "",
}: CostDistributionProps) {
  const pad = Math.ceil(fontSize * 0.5);
  const left = pad;
  const right = Math.max(left + 1, width - pad);
  const labelWidth = (value: number) => textWidth(formatTick(value), fontSize);
  const marked = previous != null && Number.isFinite(previous);
  const ticks = distributionAxis(Math.max(upper, highest, marked ? previous : 0, ...values), right - left, labelWidth);
  const top = ticks[ticks.length - 1]!;
  const x = (value: number) => left + (Math.max(0, Math.min(top, value)) / top) * (right - left);
  const labelLine = Math.ceil(fontSize * 1.3);
  const stripTop = labelLine + Math.ceil(fontSize * 0.4);
  const strip = Math.ceil(fontSize * 2);
  const axisY = stripTop + strip + Math.ceil(fontSize * 0.4);
  const previousY = axisY + Math.ceil(fontSize * 2.6);
  const height = marked ? previousY + Math.ceil(fontSize * 0.5) : axisY + Math.ceil(fontSize * 1.5);
  const medianX = x(median);
  const medianWidth = textWidth(medianLabel, fontSize, 600);
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fontFamily={CHART_FONT}
      fontSize={fontSize}
      aria-hidden="true"
      className="block"
      data-chart="cost-distribution"
    >
      <title>{title}</title>
      <rect
        x={x(lower)}
        y={stripTop}
        width={Math.max(1, x(upper) - x(lower))}
        height={strip}
        fill={colour("hairline")}
        stroke={colour("axis")}
        data-mark="box"
      />
      {values.map((value, i) => (
        <line
          key={i}
          x1={x(value)}
          x2={x(value)}
          y1={stripTop + 3}
          y2={stripTop + strip - 3}
          stroke={colour("order-history")}
          strokeWidth={1.5}
          data-mark="game"
        />
      ))}
      <line
        x1={medianX}
        x2={medianX}
        y1={stripTop - 2}
        y2={stripTop + strip + 2}
        stroke={colour("ink")}
        strokeWidth={2.5}
        data-mark="median"
      />
      <text
        x={clampedStart(medianX, medianWidth, width)}
        y={labelLine - Math.ceil(fontSize * 0.25)}
        fill={colour("ink")}
        fontWeight={600}
        className="tabular-nums"
        data-label="median"
      >
        {medianLabel}
      </text>
      {marked ? (
        <g data-mark="previous">
          <line
            x1={x(previous)}
            x2={x(previous)}
            y1={stripTop - 2}
            y2={previousY - Math.ceil(fontSize * 1.1)}
            stroke={colour("ink-secondary")}
            strokeWidth={1.5}
            strokeDasharray="4 3"
          />
          <text
            x={clampedStart(x(previous), textWidth(previousLabel, fontSize), width)}
            y={previousY}
            fill={colour("ink-secondary")}
            className="tabular-nums"
            data-label="previous"
          >
            {previousLabel}
          </text>
        </g>
      ) : null}
      <line x1={left} x2={right} y1={axisY} y2={axisY} stroke={colour("axis")} />
      {ticks.map((tick, i) => {
        const text = formatTick(tick);
        const w = textWidth(text, fontSize);
        return (
          <text
            key={tick}
            x={i === 0 ? left : i === ticks.length - 1 ? right - w : x(tick) - w / 2}
            y={axisY + Math.ceil(fontSize * 1.2)}
            fill={colour("ink-secondary")}
            className="tabular-nums"
            data-tick={tick}
          >
            {text}
          </text>
        );
      })}
    </svg>
  );
}
