import { scaleLinear } from "d3-scale";

import { CHART_FONT, colour } from "./palette";

/** One Uke's cost at the centre `x` of its table column, as the api gave it, in kroner. */
export type CostBar = { week: number; x: number; holding: number; backorder: number };

export type CostBarsProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  fontSize: number;
  bars: readonly CostBar[];
  /** Bar width in px (a share of the narrowest column). */
  barWidth: number;
  /** The axis top in kroner (`costAxisTop`): no bar is ever cut. */
  top: number;
  /** The now-line's x; `future-tint` lies right of it. */
  nowX: number;
  title: string;
};

/** The gap between the two parts of a stacked bar (DESIGN.md: «1.5 px apart»). */
const GAP = 1.5;

/** The y-scale the field and its sticky «40 kr» tick share: 0 at the baseline, `top` above. */
export function costScale(height: number, fontSize: number, top: number) {
  return scaleLinear()
    .domain([0, top])
    .range([height - 1, Math.round(fontSize * 0.8)]);
}

/**
 * Kost per uke (UX-DR16, DESIGN.md `cost-field`): stacked bars, holding cost (`lager`) at the
 * bottom and backlog cost (`restordre`) on top, 1.5 px apart, over an `axis` baseline, with a
 * `hairline` at the axis top. Hand-made SVG (see README). Each bar carries `data-mark`/`data-week`.
 */
export function CostBars({ width, height, fontSize, bars, barWidth, top, nowX, title }: CostBarsProps) {
  const y = costScale(height, fontSize, top);
  const base = y(0);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="cost" fontFamily={CHART_FONT} overflow="hidden">
      <title>{title}</title>
      <rect x={nowX} y={0} width={Math.max(0, width - nowX)} height={height} fill={colour("future-tint")} />
      <line x1={0} x2={width} y1={y(top)} y2={y(top)} stroke={colour("hairline")} strokeWidth={1} />
      {bars.map((bar) => {
        const holdingTop = y(bar.holding);
        const gap = bar.holding > 0 && bar.backorder > 0 ? GAP : 0;
        // The gap comes out of the backlog part, so the bar's top stays at its value.
        const backorderBase = holdingTop - gap;
        const backorderTop = y(bar.holding + bar.backorder);
        return (
          <g key={bar.week} data-mark="cost" data-week={bar.week} data-x={Math.round(bar.x * 100) / 100}>
            {bar.holding > 0 ? (
              <rect x={bar.x - barWidth / 2} y={holdingTop} width={barWidth} height={base - holdingTop} fill={colour("lager")} />
            ) : null}
            {bar.backorder > 0 ? (
              <rect
                x={bar.x - barWidth / 2}
                y={backorderTop}
                width={barWidth}
                height={Math.max(0, backorderBase - backorderTop)}
                fill={colour("restordre")}
              />
            ) : null}
          </g>
        );
      })}
      <line x1={0} x2={width} y1={base + 0.5} y2={base + 0.5} stroke={colour("axis")} strokeWidth={1} />
    </svg>
  );
}
