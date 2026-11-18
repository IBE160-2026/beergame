/**
 * The synthetic Seat the Landing shows (Story 3.13, UX-DR70): one Seat, the Grossist, in the
 * Veiledede uker 1–4, where every order is fixed at 4. The numbers are invented, not taken from a
 * game, and every surface that shows them labels them «Demodata». Story 6.8 draws its graph over
 * this same fixture.
 *
 * Content rules (EXPERIENCE.md → Landing, Hidden information): one Seat only, no week beyond the
 * current one, and an Ordre inn that never rises. `demo-seat.test.ts` holds the fixture to them.
 */

export type DemoWeek = {
  week: number;
  incomingOrder: number;
  incomingDelivery: number;
  netInventory: number;
  supplyLine: number;
  order: number;
};

export type DemoSeat = {
  role: "wholesaler";
  currentWeek: number;
  weeks: readonly DemoWeek[];
};

export const DEMO_SEAT: DemoSeat = {
  role: "wholesaler",
  currentWeek: 4,
  weeks: [1, 2, 3, 4].map((week) => ({
    week,
    incomingOrder: 4,
    incomingDelivery: 4,
    netInventory: 12,
    supplyLine: 12,
    order: 4,
  })),
};

/** The table's rows, top to bottom: the `nb.terms` key of the label and the value of a week. */
export const DEMO_ROWS = [
  ["incomingOrder", (w: DemoWeek) => w.incomingOrder],
  ["incomingDelivery", (w: DemoWeek) => w.incomingDelivery],
  ["netInventory", (w: DemoWeek) => w.netInventory],
  ["supplyLine", (w: DemoWeek) => w.supplyLine],
  ["order", (w: DemoWeek) => w.order],
] as const;
