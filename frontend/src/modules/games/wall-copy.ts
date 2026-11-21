import type { MatrixWallCopy } from "@/components/charts/matrix-wall";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

const copy = nb.wall;

export type WallRole = Parameters<typeof roleName>[0];

/** The Matrisevegg's copy for a Role's Netto lager (Story 7.2). The Landing passes no Role, so
 * none is named beside its one-Seat figure. Holds no api or query code: the public Landing uses it. */
export function wallCopy(role: WallRole | null, withFigures: boolean): MatrixWallCopy {
  const measure = nb.terms.netInventory;
  return {
    region: copy.region,
    title: role ? copy.title(roleName(role)) : copy.demoTitle,
    gameHeader: copy.gameHeader,
    figureHeader: withFigures ? copy.figureHeader : undefined,
    week: copy.week,
    cell: (row, week, value) => copy.cell(row.label, week, measure, value),
    bins: copy.bins,
    minusNote: copy.minusNote,
    legend: copy.legend,
  };
}

/** A cell's number: the one Norwegian number formatter, with its true minus. */
export const formatCell = (value: number) => formatNumber(value);
