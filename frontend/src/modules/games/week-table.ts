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
  | { kind: "order-empty" }
  /** Din ordre at nå with an Order already placed (a Veiledet uke): the number, in nå's weight. */
  | { kind: "order-placed"; text: string }
  /** Din ordre at nå with a valid typed Order not yet confirmed (Story 6.11): the same block. */
  | { kind: "order-typed"; text: string }
  /** The typed Order in Levering at its arrival Uke, after any known arrival there. */
  | { kind: "arrival-typed"; text: string; known: string | null };

/** A valid typed Order and the Uke it arrives in (`lib/preview.ts`). */
export type TypedOrder = { order: number; arrivalWeek: number };

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

/** One Uke of the graph: Netto lager, Posisjon and the cost split, as the api gave them. */
export type GraphWeek = { week: number; net: number; position: number; holding: number; backorder: number };

export type GraphSeries = {
  /** Uke 1 … nå, oldest first; the graph draws the ones in its columns. */
  weeks: GraphWeek[];
  /** The Game settings' rates from this Uke's cost lines, formatted («1,00», «0,50»). */
  rates: { holding: string; backorder: string };
  /** The costliest Uke so far (nå included), and before nå, in kroner, for the axis top. */
  highest: number;
  highestBefore: number;
};

function amountOf(state: SeatState, kind: "holding" | "backorder"): string {
  return state.cost_lines.find((line) => line.kind === kind)?.amount ?? "0";
}

function rateOf(state: SeatState, kind: "holding" | "backorder"): string {
  const rate = state.cost_lines.find((line) => line.kind === kind)?.rate;
  return rate === undefined ? "" : formatNumber(rate, { decimals: 2 });
}

/**
 * The graph's series (Story 6.7): every value is a `seat_state` field as returned (history rows,
 * then nå's `net_inventory`, `position` and `cost_lines` amounts). Decimal strings become numbers
 * only to be drawn; nothing is worked out (AD-10).
 */
export function graphSeries(state: SeatState): GraphSeries {
  const weeks: GraphWeek[] = state.history.map((row) => ({
    week: row.week,
    net: row.net_inventory,
    position: row.position,
    holding: Number(row.holding_cost),
    backorder: Number(row.backorder_cost),
  }));
  weeks.push({
    week: state.week,
    net: state.net_inventory,
    position: state.position,
    holding: Number(amountOf(state, "holding")),
    backorder: Number(amountOf(state, "backorder")),
  });
  const costOf = (row: SeatState["history"][number]) => Number(row.cost);
  const before = Math.max(0, ...state.history.map(costOf));
  return {
    weeks,
    rates: { holding: rateOf(state, "holding"), backorder: rateOf(state, "backorder") },
    highest: Math.max(before, Number(state.week_cost)),
    highestBefore: before,
  };
}

/** What the cell of `row` in Uke `week` shows. `nowOrder` is an Order already placed at nå (a
 * Veiledet uke's fixed Order, as the Landing shows it); without it nå's Din ordre is empty, or
 * holds `typed`, the valid typed Order, which also stands in Levering at its arrival Uke. */
export function cellFor(state: SeatState, row: RowKey, week: number, nowOrder?: number, typed?: TypedOrder): Cell {
  const preview = nowOrder === undefined ? typed : undefined;
  if (week < state.week) {
    const past = state.history[week - 1];
    if (!past) return { kind: "empty" };
    if (row === "order") return { kind: "plain", text: formatNumber(past.order) };
    if (row === "cost") return { kind: "plain", text: formatNumber(past.cost, { narrow: true }) };
    return known(past, row);
  }
  if (week === state.week) {
    if (row === "order") {
      if (nowOrder !== undefined) return { kind: "order-placed", text: formatNumber(nowOrder) };
      return preview ? { kind: "order-typed", text: formatNumber(preview.order) } : { kind: "order-empty" };
    }
    if (row === "cost") return { kind: "plain", text: formatNumber(state.week_cost, { narrow: true }) };
    return known(state, row);
  }
  if (row !== "incomingDelivery") return { kind: "empty" };
  // The engine gives at most one slot per arrival Uke; were there more, each is written, never summed.
  const arriving = state.supply_line_slots.filter((slot) => slot.arrival_week === week);
  const due = arriving.length === 0 ? null : arriving.map((slot) => formatNumber(slot.quantity)).join(" + ");
  if (preview && preview.arrivalWeek === week) return { kind: "arrival-typed", text: formatNumber(preview.order), known: due };
  return due === null ? { kind: "empty" } : { kind: "arrival", text: due };
}
