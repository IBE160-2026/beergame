import type { ChainBillRow, ChainBillTotal } from "@/components/chain-bill";
import type { ChainCostRow } from "@/components/chain-cost-chart";
import type { CostAreaPoint } from "@/components/charts/cost-area";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import type { GameResult } from "./api";

/**
 * «Spillet er ferdig» in words and figures (Story 6.18, FR-28, AD-10): every number is a field of
 * the api's result, formatted here; the only arithmetic is display ratios (a split bar's share
 * of the widest row) and the chart's points as numbers. Rows stay in the api's order, Detaljist to
 * Fabrikk, never sorted by cost (UX-DR72).
 */
export type GameEndModel = {
  /** «2 266,00 kr». */
  total: string;
  rows: ChainBillRow[];
  chain: ChainBillTotal;
  points: CostAreaPoint[];
  weeks: ChainCostRow[];
  endLabels: { holding: string; backorder: string };
};

const copy = nb.games.play.chain;
const money = (value: string) => formatNumber(value, { decimals: 2 });

function amount(value: string): number {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

export function gameEnd(result: GameResult, ownRole: string): GameEndModel {
  const widest = Math.max(0, ...result.roles.map((row) => amount(row.total_cost)));
  const rows = result.roles.map((row) => {
    const name = roleName(row.role);
    const own = row.role === ownRole;
    return {
      role: row.role,
      label: own ? copy.own(name) : name,
      own,
      holding: money(row.holding_cost),
      backorder: money(row.backorder_cost),
      total: money(row.total_cost),
      bar: {
        holding: widest > 0 ? amount(row.holding_cost) / widest : 0,
        backorder: widest > 0 ? amount(row.backorder_cost) / widest : 0,
      },
    };
  });
  return {
    total: formatNumber(result.chain.total_cost, { kroner: true }),
    rows,
    chain: {
      holding: money(result.chain.holding_cost),
      backorder: money(result.chain.backorder_cost),
      total: money(result.chain.total_cost),
    },
    points: result.weeks.map((week) => ({
      week: week.week,
      holding: Number(week.holding_cost),
      backorder: Number(week.backorder_cost),
    })),
    weeks: result.weeks.map((week) => ({
      week: week.week,
      holding: money(week.holding_cost),
      backorder: money(week.backorder_cost),
      total: money(week.total_cost),
    })),
    endLabels: {
      holding: `${copy.holding} ${money(result.chain.holding_cost)}`,
      backorder: `${copy.backorder} ${money(result.chain.backorder_cost)}`,
    },
  };
}
