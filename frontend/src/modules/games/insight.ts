import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import type { GameInsight, InsightRole, InsightSeat, InsightWeek, SeatMark } from "./api";

const copy = nb.insight;

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
  marks: string;
};

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
