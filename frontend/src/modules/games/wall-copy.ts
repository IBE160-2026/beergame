import type { MatrixWallCopy } from "@/components/charts/matrix-wall";
import type { WallScale } from "@/components/charts/matrix-wall-layout";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

const copy = nb.wall;

export type WallRole = Parameters<typeof roleName>[0];

/** What the wall's cells show (Story 7.4, the Celler filter), as the api names it. */
export type WallCells = "net" | "order" | "cost";

/** The measure's name: «Netto lager», «Ordre», «Kost per uke». */
export function measureName(cells: WallCells): string {
  return cells === "net" ? nb.terms.netInventory : cells === "order" ? nb.terms.order : nb.terms.costPerWeek;
}

/** Netto lager in its signed steps; Ordre and Kost per uke in the flow steps (DESIGN.md). */
export function scaleOf(cells: WallCells): WallScale {
  return cells === "net" ? "net" : "flow";
}

/** The Matrisevegg's copy for a Role's cells (Stories 7.2, 7.4). The Landing passes no Role, so
 * none is named beside its one-Seat figure. Holds no api or query code: the public Landing uses it. */
export function wallCopy(role: WallRole | null, withFigures: boolean, cells: WallCells = "net"): MatrixWallCopy {
  const measure = measureName(cells);
  const net = cells === "net";
  return {
    region: copy.region,
    title: role ? copy.title(measure, roleName(role)) : copy.demoTitle,
    gameHeader: copy.gameHeader,
    figureHeader: withFigures ? copy.figureHeader : undefined,
    week: copy.week,
    cell: (row, week, value) => copy.cell(row.label, week, measure, value),
    bins: net ? copy.bins : copy.flowBins,
    minusNote: net ? copy.minusNote : undefined,
    legend: net ? copy.legend : copy.flowLegend(measure),
  };
}

/** A cell's number: the one Norwegian number formatter, with its true minus. */
export const formatCell = (value: number) => formatNumber(value);

/** A Kost per uke cell: kroner with up to two decimals, trailing zeros dropped («12,5»). */
export const formatCost = (value: number) => formatNumber(value, { decimals: 2, narrow: true });
