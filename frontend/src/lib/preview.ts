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
