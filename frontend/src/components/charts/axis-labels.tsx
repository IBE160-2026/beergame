import { CHART_FONT, colour } from "./palette";

export type AxisLabelsProps = {
  width: number;
  height: number;
  fontSize: number;
  /** The SVG `<title>` (AD-18: every chart SVG has one). */
  title: string;
  /** Each label at its y in px, right-aligned against the field. */
  ticks: readonly { y: number; text: string }[];
};

/**
 * A field's y-axis labels («20», «0», «−20»; «40 kr»), drawn in the sticky row-label column so they
 * stay in view while the graph scrolls with the table (UX-DR18). `ink-muted`, as axis ticks are.
 */
export function AxisLabels({ width, height, fontSize, title, ticks }: AxisLabelsProps) {
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="axis" fontFamily={CHART_FONT} fontSize={fontSize}>
      <title>{title}</title>
      {ticks.map((tick) => (
        <text key={tick.text} x={width - fontSize * 0.4} y={tick.y} dy="0.35em" textAnchor="end" fill={colour("ink-muted")}>
          {tick.text}
        </text>
      ))}
    </svg>
  );
}
