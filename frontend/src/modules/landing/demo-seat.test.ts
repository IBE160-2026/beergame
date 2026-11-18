import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { DEMO_SEAT } from "./demo-seat";

// The Landing's content rules (Story 3.13, UX-DR70, UX-DR71, EXPERIENCE.md → Landing).
describe("the Landing's Demodata Seat", () => {
  it("shows the Veiledede uker 1–4 and no week beyond the current one", () => {
    expect(DEMO_SEAT.weeks.map((w) => w.week)).toEqual([1, 2, 3, 4]);
    expect(DEMO_SEAT.currentWeek).toBe(4);
    expect(Math.max(...DEMO_SEAT.weeks.map((w) => w.week))).toBe(DEMO_SEAT.currentWeek);
  });

  it("is the Seat the caption names", () => {
    expect(DEMO_SEAT.role).toBe("wholesaler");
    expect(nb.landing.seat.caption).toContain(`${nb.terms.wholesaler}, ${nb.terms.week} ${DEMO_SEAT.currentWeek}.`);
  });

  it("never shows a rising Ordre inn", () => {
    const orders = DEMO_SEAT.weeks.map((w) => w.incomingOrder);
    orders.slice(1).forEach((value, i) => expect(value).toBeLessThanOrEqual(orders[i]));
  });

  it("orders the fixed 4 of a Veiledet uke and holds no stock below zero", () => {
    expect(DEMO_SEAT.weeks.every((w) => w.order === 4)).toBe(true);
    expect(DEMO_SEAT.weeks.every((w) => w.netInventory >= 0)).toBe(true);
  });
});
