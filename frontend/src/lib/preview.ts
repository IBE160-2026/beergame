import type { components } from "@/lib/api/schema";

/** The preview coefficients the api sends in `seat_state.preview` (AD-10). */
export type PreviewCoefficients = components["schemas"]["OrderPreview"];

/** Where a typed Order would land (Story 6.11, UX-DR14, UX-DR17). */
export type OrderPreview = {
  /** The typed Order. */
  order: number;
  /** The Uke the Order reaches the Seat's stock if the upstream Seat ships it in full. */
  arrivalWeek: number;
  /** På vei before the Order, as the Kjedebånd writes it («På vei 16 + 24»). */
  supplyLineBase: number;
  /** På vei and Posisjon with the Order. Shown nowhere yet: Posisjon takes the Order when the Uke
   * advances (EXPERIENCE.md → Graf over tabell). */
  supplyLine: number;
  position: number;
};

/**
 * The live Order preview (AD-10): the product's only client arithmetic. It reads only the
 * coefficients the engine put in `seat_state.preview` and the typed whole number, and knows no
 * delay or rule of its own. `preview.test.ts` holds it to the engine's golden-trace games.
 */
export function orderPreview(coefficients: PreviewCoefficients, order: number): OrderPreview {
  return {
    order,
    arrivalWeek: coefficients.order_arrival_week,
    supplyLineBase: coefficients.supply_line_base,
    supplyLine: coefficients.supply_line_base + order,
    position: coefficients.position_base + order,
  };
}

/** The fields of `seat_state` the projection reads (Story 10.4): the open Uke, its incoming order
 * and the preview coefficients. */
export type ProjectionFields = {
  week: number;
  incoming_order: number;
  preview: PreviewCoefficients;
};

/** Netto lager at nå + `horizon` if the incoming order holds (Story 10.4, UX-DR19): the numbers of
 * «3 + 24 − 4 × 8 = −5». */
export type Projection = {
  /** Posisjon before the Order (`position_base`). */
  position: number;
  /** The Order counted, or null when none is typed: it then counts as 0. */
  order: number | null;
  /** Uker until the Order arrives: the delay horizon, from the api's arrival Uke. */
  horizon: number;
  /** The incoming order assumed to hold for every Uke of the horizon. */
  incoming: number;
  /** The Uke the projection reaches: nå + `horizon`. */
  week: number;
  value: number;
};

/**
 * The Replay's projection of Netto lager (Story 10.4, AD-10, UX-DR19): Posisjon, plus the typed
 * Order, less the incoming order for each Uke until the Order arrives. Display arithmetic on the
 * fields the api sent: the horizon is the Order's lead time, the Uke of `order_arrival_week` less
 * nå, so the client holds no delay of its own. `preview.test.ts` holds it to the engine's golden
 * values.
 */
export function orderProjection(state: ProjectionFields, order: number | null): Projection {
  const horizon = state.preview.order_arrival_week - state.week;
  const position = state.preview.position_base;
  return {
    position,
    order,
    horizon,
    incoming: state.incoming_order,
    week: state.preview.order_arrival_week,
    value: position + (order ?? 0) - horizon * state.incoming_order,
  };
}
