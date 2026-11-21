import type { OrderBarsRole } from "@/components/order-bars-table";
import type { StockBacklogRole } from "@/components/stock-backlog-table";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import type { GameInsight, InsightRole, InsightSeat, InsightWeek, SeatMark } from "./api";
import { waitDuration } from "./seat-status";

const copy = nb.insight;
const MONTHS = nb.admin.users.invitations.months;

/** Every mark of the one AD-15 mapping in words; a mark the api adds later fails the typecheck. */
const MARKS: Record<SeatMark, string> = copy.marks;

/** The Seats upstream first, as the chain is drawn everywhere (UX-DR73): the api's chain order
 * (Detaljist first) reversed. */
export function seatsUpstreamFirst(insight: Pick<GameInsight, "seats">): InsightSeat[] {
  return [...insight.seats].reverse();
}

/** Who holds a Seat or held it in a Week: the Student's name, «KI-spiller», or «Ledig». */
export function holderText(holder: Pick<InsightSeat, "holder" | "name">): string {
  if (holder.holder === "ai") return copy.aiPlayer;
  if (holder.holder === "free") return copy.freeSeat;
  return holder.name ?? copy.unknownStudent;
}

/** A Seat's mark in words, with who put the AI player in when the api names them (Story 8.5):
 * «KI satt inn av Bård» for a Takeover by a person, else the mark's own words. */
export function markWords(mark: SeatMark, by: string | null | undefined): string {
  return by && (mark === "takeover_staff" || mark === "takeover_peer") ? copy.markedBy(by) : MARKS[mark];
}

/** Why an AI player holds the Seat now, in text (Stories 8.3 and 8.5, FR-34): «KI tok over etter
 * ventetiden», «KI satt inn av Bård»; null for a Student, a free Seat or an AI player with no
 * mark. */
export function seatMarkText(seat: Pick<InsightSeat, "holder" | "mark"> & { mark_by?: string | null }): string | null {
  return seat.holder === "ai" && seat.mark ? markWords(seat.mark, seat.mark_by) : null;
}

/** The words of a Student Seat's links, or the line that none exists yet; nothing for the others. */
export function linkTexts(seat: InsightSeat): { kind: string; text: string; href: string }[] | string | null {
  if (seat.holder !== "student") return null;
  if (seat.links.length === 0) return copy.noLinks;
  return seat.links.map((link) => ({ kind: link.kind, text: copy.links[link.kind] ?? copy.otherLink, href: link.href }));
}

/** A Week's marks in words, joined. */
export function markText(marks: readonly SeatMark[]): string {
  return marks.map((mark) => MARKS[mark]).join(". ");
}

/** One table row as printed: every number the api's own, only formatted (AD-10). */
export type WeekRow = {
  week: number;
  playedBy: string;
  incomingOrder: string;
  incomingDelivery: string;
  inventory: string;
  backlog: string;
  /** Empty while the Order has not been placed. */
  order: string;
  cost: string;
  /** When the Week opened for the Seat and when its Order came (Story 8.1, FR-35), in
   * Europe/Oslo; empty when not stored. */
  opened: string;
  ordered: string;
  /** The time between the two stored times; empty while the Seat has not ordered. */
  took: string;
  marks: string;
};

/** «18. nov. kl. 13:01» in Europe/Oslo, from a stored time. */
export function clockText(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date(iso));
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return copy.at(`${Number(part("day"))}. ${MONTHS[Number(part("month")) - 1]}`, `${part("hour")}:${part("minute")}`);
}

/** How long the Seat took from the Week's opening to its Order: the two stored times' difference. */
function tookText(week: Pick<InsightWeek, "opened_at" | "ordered_at">): string {
  if (!week.opened_at || !week.ordered_at) return "";
  return waitDuration(Math.max(0, Date.parse(week.ordered_at) - Date.parse(week.opened_at)));
}

export function weekRow(week: InsightWeek): WeekRow {
  return {
    week: week.week,
    playedBy: holderText(week),
    incomingOrder: formatNumber(week.incoming_order),
    incomingDelivery: formatNumber(week.incoming_delivery),
    inventory: formatNumber(week.inventory),
    backlog: formatNumber(week.backlog),
    order: week.order == null ? "" : formatNumber(week.order),
    cost: formatNumber(week.cost, { decimals: 2 }),
    opened: week.opened_at ? clockText(week.opened_at) : "",
    ordered: week.ordered_at ? clockText(week.ordered_at) : "",
    took: tookText(week),
    marks: markText(week.marks),
  };
}

/** The per-Role tables in chain order, Detaljist first, as the api gives them. */
export function roleTables(insight: Pick<GameInsight, "roles">): { role: InsightRole["role"]; name: string; rows: WeekRow[] }[] {
  return insight.roles.map((role) => ({ role: role.role, name: roleName(role.role), rows: role.weeks.map(weekRow) }));
}

/** Whether the game has an opened Week to show. */
export function hasWeeks(insight: Pick<GameInsight, "roles">): boolean {
  return insight.roles.some((role) => role.weeks.length > 0);
}

/** The Roles upstream first (Fabrikk at the top, UX-DR73): the api's chain order reversed. */
function rolesUpstreamFirst(insight: Pick<GameInsight, "roles">): InsightRole[] {
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
export function orderRoles(insight: Pick<GameInsight, "roles" | "demand">): OrderBarsRole[] {
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
export function stockRoles(insight: Pick<GameInsight, "roles">): StockBacklogRole[] {
  return rolesUpstreamFirst(insight).map((role) => ({
    key: role.role,
    name: roleName(role.role),
    weeks: role.weeks.map((week) => ({ week: week.week, inventory: week.inventory, backlog: week.backlog })),
  }));
}

/** One row of a chart's «Vis som tabell»: its label and one printed cell per Uke (empty for none). */
export type ChartTableRow = { key: string; label: string; cells: string[] };

/** Every opened Week, Week 1 first: the columns of both charts and their tables. */
export function chartWeeks(insight: Pick<GameInsight, "roles">): number[] {
  return [...new Set(insight.roles.flatMap((role) => role.weeks.map((week) => week.week)))].sort((a, b) => a - b);
}

/** The Ordre chart's «Vis som tabell»: the same rows as the Ordrestolper, every number formatted. */
export function orderTableRows(insight: Pick<GameInsight, "roles" | "demand">): ChartTableRow[] {
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
export function stockTableRows(insight: Pick<GameInsight, "roles">): ChartTableRow[] {
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
