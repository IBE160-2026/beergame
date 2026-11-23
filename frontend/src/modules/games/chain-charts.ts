import type { OrderBarsRole } from "@/components/order-bars-table";
import type { StockBacklogRole } from "@/components/stock-backlog-table";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import type { InsightRole, InsightWeek } from "./api";

/**
 * The chain charts' rows (Story 7.8, reused by the Student report in Story 13.8): pure, with no
 * hook, so the server-rendered print route can import them as well as Spillinnsikt. Every number
 * is the api's, only ordered and formatted (AD-10).
 */

const copy = nb.insight;

/** What the chain charts read of a game: Spillinnsikt's insight, or the Student report's game
 * section (Story 13.8), which carries the same per-Role Weeks and demand. */
type ChartWeek = Pick<InsightWeek, "week" | "inventory" | "backlog"> & { order?: number | null };
type ChartRole = Pick<InsightRole, "role"> & { weeks: readonly ChartWeek[]; first_large_order_week?: number | null };
export type ChartGame = { roles: readonly ChartRole[]; demand: readonly { week: number; demand: number }[] };

/** The Roles upstream first (Fabrikk at the top, UX-DR73): the api's chain order reversed. */
function rolesUpstreamFirst(insight: Pick<ChartGame, "roles">): ChartRole[] {
  return [...insight.roles].reverse();
}

/** The customers' row's key in the Ordrestolper. */
export const CUSTOMERS = "customers";

/**
 * The Ordrestolper's rows (Story 7.8): the four Roles, Fabrikk first, each with its placed Orders
 * (the open Week's Order not yet placed is left out) and the api's first Week of an Order of 10 or
 * more, then the customers' demand as «Kundene», on the same scale. No Forsterkning: Story 9.5
 * brings it to Spillinnsikt.
 */
export function orderRoles(insight: ChartGame): OrderBarsRole[] {
  return [
    ...rolesUpstreamFirst(insight).map((role) => ({
      key: role.role,
      name: roleName(role.role),
      orders: role.weeks.flatMap((week) => (week.order == null ? [] : [{ week: week.week, order: week.order }])),
      firstLargeWeek: role.first_large_order_week ?? null,
    })),
    {
      key: CUSTOMERS,
      name: copy.charts.orders.customers,
      orders: insight.demand.map((week) => ({ week: week.week, order: week.demand })),
      firstLargeWeek: null,
    },
  ];
}

/** «Lager og restordre»'s rows: the four Roles, Fabrikk first, with the stored values. */
export function stockRoles(insight: Pick<ChartGame, "roles">): StockBacklogRole[] {
  return rolesUpstreamFirst(insight).map((role) => ({
    key: role.role,
    name: roleName(role.role),
    weeks: role.weeks.map((week) => ({ week: week.week, inventory: week.inventory, backlog: week.backlog })),
  }));
}

/** One row of a chart's «Vis som tabell»: its label and one printed cell per Uke (empty for none). */
export type ChartTableRow = { key: string; label: string; cells: string[] };

/** Every opened Week, Week 1 first: the columns of both charts and their tables. */
export function chartWeeks(insight: Pick<ChartGame, "roles">): number[] {
  return [...new Set(insight.roles.flatMap((role) => role.weeks.map((week) => week.week)))].sort((a, b) => a - b);
}

/** The Ordre chart's «Vis som tabell»: the same rows as the Ordrestolper, every number formatted. */
export function orderTableRows(insight: ChartGame): ChartTableRow[] {
  const weeks = chartWeeks(insight);
  return orderRoles(insight).map((role) => {
    const by = new Map(role.orders.map((o) => [o.week, o.order]));
    return {
      key: role.key,
      label: role.name,
      cells: weeks.map((week) => {
        const order = by.get(week);
        return order === undefined ? "" : formatNumber(order);
      }),
    };
  });
}

/** «Lager og restordre»'s «Vis som tabell»: two rows per Role, «Fabrikk, lager» then «…, restordre». */
export function stockTableRows(insight: Pick<ChartGame, "roles">): ChartTableRow[] {
  const weeks = chartWeeks(insight);
  return stockRoles(insight).flatMap((role) => {
    const by = new Map(role.weeks.map((w) => [w.week, w]));
    const cells = (pick: (w: { inventory: number; backlog: number }) => number) =>
      weeks.map((week) => {
        const found = by.get(week);
        return found === undefined ? "" : formatNumber(pick(found));
      });
    return [
      { key: `${role.key}:stock`, label: copy.charts.stock.stockRow(role.name), cells: cells((w) => w.inventory) },
      { key: `${role.key}:backlog`, label: copy.charts.stock.backlogRow(role.name), cells: cells((w) => w.backlog) },
    ];
  });
}
