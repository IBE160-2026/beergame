import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { SeatState } from "./api";

/**
 * The week table's model (Story 6.6, FR-23, UX-DR17, DESIGN.md → Graf over tabell): which Uker
 * are columns, which rows there are, and what each cell shows. Every number is a field of the
 * api's `seat_state`, written as it came (AD-1, AD-10): the model picks and formats, it never
 * works out a game quantity.
 */

/** Columns before nå on the phone, and after nå everywhere: the right edge is always nå + 4. */
export const PHONE_BEFORE = 7;
export const AHEAD = 4;

export type Column = {
  week: number;
  when: "past" | "now" | "future";
  /** Shown on the phone too (nå − 7 … nå + 4); the laptop layout shows every column from Uke 1. */
  phone: boolean;
};

/** Uke 1 … nå + 4. */
export function weekColumns(now: number): Column[] {
  return Array.from({ length: now + AHEAD }, (_, i) => {
    const week = i + 1;
    return {
      week,
      when: week < now ? "past" : week === now ? "now" : "future",
      phone: week >= now - PHONE_BEFORE,
    };
  });
}

export type RowKey =
  | "incomingOrder"
  | "incomingDelivery"
  | "unitsShipped"
  | "netInventory"
  | "supplyLine"
  | "position"
  | "order"
  | "cost";

export type Row = { key: RowKey; label: string; laptopOnly: boolean };

/** The rows under «Uke», top to bottom; Sendt and På vei only in the laptop layout (FR-73). */
export const ROWS: readonly Row[] = [
  { key: "incomingOrder", label: nb.terms.incomingOrder, laptopOnly: false },
  { key: "incomingDelivery", label: nb.terms.incomingDelivery, laptopOnly: false },
  { key: "unitsShipped", label: nb.terms.unitsShipped, laptopOnly: true },
  { key: "netInventory", label: nb.terms.netInventory, laptopOnly: false },
  { key: "supplyLine", label: nb.terms.supplyLine, laptopOnly: true },
  { key: "position", label: nb.terms.position, laptopOnly: false },
  { key: "order", label: nb.games.play.table.order, laptopOnly: false },
  { key: "cost", label: nb.games.play.table.cost, laptopOnly: false },
];

/** A Netto lager matrix step (DESIGN.md → Colour → Matrix steps): |v| 1–9, 10–19, 20–34, 35+. */
export type NetStep = "zero" | `pos-${1 | 2 | 3 | 4}` | `neg-${1 | 2 | 3 | 4}`;

export function netStep(value: number): NetStep {
  if (value === 0) return "zero";
  const size = Math.abs(value);
  const bin = size < 10 ? 1 : size < 20 ? 2 : size < 35 ? 3 : 4;
  return value > 0 ? `pos-${bin}` : `neg-${bin}`;
}

export type Cell =
  | { kind: "empty" }
  | { kind: "plain"; text: string }
  | { kind: "net"; text: string; step: NetStep }
  /** A known arrival right of nå: ordered, not guaranteed. */
  | { kind: "arrival"; text: string }
  /** Din ordre at nå before an Order is typed: an empty dashed cell. */
  | { kind: "order-empty" };

type Values = {
  incoming_order: number;
  incoming_delivery: number;
  shipped: number;
  net_inventory: number;
  supply_line: number;
  position: number;
};

function known(values: Values, key: Exclude<RowKey, "order" | "cost">): Cell {
  if (key === "netInventory") {
    return { kind: "net", text: formatNumber(values.net_inventory), step: netStep(values.net_inventory) };
  }
  const value = {
    incomingOrder: values.incoming_order,
    incomingDelivery: values.incoming_delivery,
    unitsShipped: values.shipped,
    supplyLine: values.supply_line,
    position: values.position,
  }[key];
  return { kind: "plain", text: formatNumber(value) };
}

/** What the cell of `row` in Uke `week` shows. */
export function cellFor(state: SeatState, row: RowKey, week: number): Cell {
  if (week < state.week) {
    const past = state.history[week - 1];
    if (!past) return { kind: "empty" };
    if (row === "order") return { kind: "plain", text: formatNumber(past.order) };
    if (row === "cost") return { kind: "plain", text: formatNumber(past.cost, { narrow: true }) };
    return known(past, row);
  }
  if (week === state.week) {
    if (row === "order") return { kind: "order-empty" };
    if (row === "cost") return { kind: "plain", text: formatNumber(state.week_cost, { narrow: true }) };
    return known(state, row);
  }
  if (row !== "incomingDelivery") return { kind: "empty" };
  // The engine gives at most one slot per arrival Uke; were there more, each is written, never summed.
  const arriving = state.supply_line_slots.filter((slot) => slot.arrival_week === week);
  if (arriving.length === 0) return { kind: "empty" };
  return { kind: "arrival", text: arriving.map((slot) => formatNumber(slot.quantity)).join(" + ") };
}
