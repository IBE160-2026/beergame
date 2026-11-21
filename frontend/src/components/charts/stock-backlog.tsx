import { CHART_FONT, colour } from "./palette";

/** One Role's band of «Lager og restordre», top to bottom (Fabrikk first, UX-DR73). */
export type StockBacklogRow = {
  /** Each drawn column's stored inventory, aligned with `xs`; null for a column with no Uke. */
  stock: readonly (number | null)[];
  /** Each drawn column's stored backlog, aligned with `xs`. */
  backlog: readonly (number | null)[];
};

export type StockBacklogProps = {
  /** Fixed size in px, from the caller (AD-18). */
  width: number;
  height: number;
  /** Each column's centre, in px. */
  xs: readonly number[];
  columnWidth: number;
  rows: readonly StockBacklogRow[];
  /** The SVG `<title>` (AD-18). */
  title: string;
};

/** The room left free at the top and bottom of each band, in px, so two bands never touch. */
const GAP = 3;

/**
 * Each band's zero line and the px per unit, one scale for the whole game: the band is split at
 * the game's largest stock against its largest backlog, stock above the line and backlog below.
 * With neither the line sits at the band's foot. A drawing choice, like an axis: the numbers
 * themselves are the api's.
 */
export function stockBands(height: number, rows: readonly StockBacklogRow[]) {
  const band = height / Math.max(1, rows.length);
  const most = (pick: (row: StockBacklogRow) => readonly (number | null)[]) =>
    Math.max(0, ...rows.flatMap((row) => pick(row).map((value) => value ?? 0)));
  const stock = most((row) => row.stock);
  const backlog = most((row) => row.backlog);
  const room = Math.max(1, band - 2 * GAP);
  const total = stock + backlog;
  const unit = total > 0 ? room / total : 0;
  return rows.map((_, i) => {
    const top = i * band + GAP;
    return { zero: Math.round(top + (total > 0 ? stock * unit : room)), unit, centre: i * band + band / 2 };
  });
}

/**
 * «Lager og restordre» (Story 7.8, Spillinnsikt, FR-62): one band per Role in the order given
 * (Fabrikk first), a bar per Uke for the stored inventory up from the zero line in `lager` and
 * for the stored backlog down from it in `restordre`, every band on one scale so the swings of
 * the Roles can be compared. The four-Role Kjedebånd's convention (stock up, backlog down). Drawn
 * in a Graf over tabell field, so its columns are the Uke header's; `aria-hidden` there, its
 * «Vis som tabell» is the alternative.
 */
export function StockBacklog({ width, height, xs, columnWidth, rows, title }: StockBacklogProps) {
  const bands = stockBands(height, rows);
  const barWidth = Math.max(2, Math.round(columnWidth * 0.7));
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="stock-backlog">
      <title>{title}</title>
      {rows.map((row, i) => {
        const band = bands[i]!;
        const bar = (value: number | null, column: number, kind: "stock" | "backlog") => {
          const x = xs[column];
          if (value === null || value <= 0 || x === undefined) return null;
          const h = Math.max(1, value * band.unit);
          return (
            <rect
              key={`${kind}${column}`}
              data-mark={kind}
              x={round(x - barWidth / 2)}
              y={round(kind === "stock" ? band.zero - h : band.zero + 1)}
              width={barWidth}
              height={round(h)}
              fill={colour(kind === "stock" ? "lager" : "restordre")}
            />
          );
        };
        return (
          <g key={i} data-row={i}>
            {row.stock.map((value, column) => bar(value, column, "stock"))}
            {row.backlog.map((value, column) => bar(value, column, "backlog"))}
            <line x1={0} x2={width} y1={band.zero + 0.5} y2={band.zero + 0.5} stroke={colour("axis")} strokeWidth={1} />
          </g>
        );
      })}
    </svg>
  );
}

/** The Role names in the sticky label column, each at its band's middle (`ink`). */
export function StockBacklogLabels({
  width,
  height,
  fontSize,
  labels,
  rows,
  title,
}: {
  width: number;
  height: number;
  fontSize: number;
  labels: readonly string[];
  rows: readonly StockBacklogRow[];
  title: string;
}) {
  const bands = stockBands(height, rows);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="axis" fontFamily={CHART_FONT} fontSize={fontSize}>
      <title>{title}</title>
      {labels.map((label, i) => (
        <text key={label} x={0} y={round(bands[i]!.centre)} dominantBaseline="central" fill={colour("ink")}>
          {label}
        </text>
      ))}
    </svg>
  );
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}
