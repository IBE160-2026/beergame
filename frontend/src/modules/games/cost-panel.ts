import type { CostAreaPoint } from "@/components/charts/cost-area";
import { nb } from "@/copy/nb";
import { formatNumber, MINUS } from "@/lib/number-format";

import type { SeatState } from "./api";
import { weekCostLine } from "./week-summary";

/**
 * «Kostnad så langt» and the column lines of «Alle rader og kostnad» (Story 6.16, UX-DR21,
 * UX-DR22): what the panel shows, every number a field of the api's `seat_state` (AD-10). The
 * running sums are the api's; the model formats them and works out only display ratios (a bar's
 * share of the Totalkostnad), never a game quantity.
 */

export type CostPart = {
  label: string;
  /** «43,00 kr». */
  amount: string;
  /** The part's share of the Totalkostnad, 0 … 1, for its thin bar; 0 while nothing is charged. */
  share: number;
};

export type CostTableRow = {
  week: number;
  holding: string;
  backorder: string;
  total: string;
};

export type CostPanelModel = {
  holding: CostPart;
  backorder: CostPart;
  /** «68,00 kr». */
  total: string;
  /** Uke 1 … nå, the running holding and backlog cost, for «Totalkostnad over tid». */
  points: CostAreaPoint[];
  /** The same Uker as the table «Vis som tabell» opens: Uke / Lager / Restordre / «Sum, kr». */
  rows: CostTableRow[];
  /** «Denne uka: 13 restordre × 1,00 = 13,00 kr». */
  weekCost: string;
  week: number;
};

const copy = nb.games.play.costPanel;
const kroner = (value: string) => formatNumber(value, { kroner: true });
const money = (value: string) => formatNumber(value, { decimals: 2 });

function share(part: string, total: string): number {
  const whole = Number(total);
  if (!(whole > 0)) return 0;
  return Math.min(1, Math.max(0, Number(part) / whole));
}

export function costPanel(state: SeatState): CostPanelModel {
  const weeks = [
    ...state.history.map((row) => ({
      week: row.week,
      holding: row.total_holding_cost,
      backorder: row.total_backorder_cost,
      total: row.total_cost,
    })),
    {
      week: state.week,
      holding: state.total_holding_cost,
      backorder: state.total_backorder_cost,
      total: state.total_cost,
    },
  ];
  return {
    holding: {
      label: copy.holding,
      amount: kroner(state.total_holding_cost),
      share: share(state.total_holding_cost, state.total_cost),
    },
    backorder: {
      label: copy.backorder,
      amount: kroner(state.total_backorder_cost),
      share: share(state.total_backorder_cost, state.total_cost),
    },
    total: kroner(state.total_cost),
    points: weeks.map((w) => ({
      week: w.week,
      holding: Number(w.holding),
      backorder: Number(w.backorder),
    })),
    rows: weeks.map((w) => ({
      week: w.week,
      holding: money(w.holding),
      backorder: money(w.backorder),
      total: money(w.total),
    })),
    weekCost: weekCostLine(state),
    week: state.week,
  };
}

export type ColumnLine = { label: string; sum: string };

/** «+ 4» or «− 8»: a count added or taken away. */
function term(sign: 1 | -1, value: number): string {
  return `${sign < 0 ? MINUS : "+"} ${formatNumber(value)}`;
}

/**
 * The two column sums under the table in Alle rader (DESIGN.md → Alle rader og kostnad): «Netto
 * lager i kolonne 11  −9 + 4 − 8 = −13» (the Netto lager of the column to the left, plus Levering,
 * minus Ordre inn) and «Posisjon i kolonne 11  −13 + 16 = 3» (Netto lager plus På vei). Terms and
 * results are the api's fields, written out; `backend/tests/engine/test_view.py` holds the engine
 * to the first sum. In Uke 1 there is no column to the left, so only the Posisjon line.
 */
export function columnLines(state: SeatState): ColumnLine[] {
  const lines: ColumnLine[] = [];
  const before = state.history.at(-1);
  const n = (value: number) => formatNumber(value);
  if (before) {
    lines.push({
      label: nb.games.play.allRows.netLine(state.week),
      sum: `${n(before.net_inventory)} ${term(1, state.incoming_delivery)} ${term(-1, state.incoming_order)} = ${n(state.net_inventory)}`,
    });
  }
  lines.push({
    label: nb.games.play.allRows.positionLine(state.week),
    sum: `${n(state.net_inventory)} ${term(1, state.supply_line)} = ${n(state.position)}`,
  });
  return lines;
}
