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
/** The status word in Spillinnsikt's header: the api's `status`, except a Replay closed at the
 * Testfrist, which is `finished` without having finished (Story 10.6). */
export function statusText(insight: Pick<GameInsight, "status" | "end_reason">): string {
  return insight.end_reason === "test_deadline" ? copy.closedAtTestDeadline : copy.status[insight.status];
}

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

/** The words of a Student Seat's links, or the line that none exists yet; nothing for the others.
 * A Replay (Story 10.5) has no Explanation or Debrief of its own: no line while it has no link. */
export function linkTexts(
  seat: InsightSeat,
  replay = false,
): { kind: string; text: string; href: string }[] | string | null {
  if (seat.holder !== "student") return null;
  if (seat.links.length === 0) return replay ? null : copy.noLinks;
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

export {
  type ChartGame,
  type ChartTableRow,
  chartWeeks,
  CUSTOMERS,
  orderRoles,
  orderTableRows,
  stockRoles,
  stockTableRows,
} from "./chain-charts";
