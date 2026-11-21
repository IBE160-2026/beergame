import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import demo from "./demo-seat.json";
import { DEMO_GUIDED_ORDER, DEMO_SEAT } from "./demo-seat";

// The Landing's content rules (Stories 3.13 and 6.8, UX-DR70, UX-DR71, EXPERIENCE.md → Landing).
describe("the Landing's Demodata Seat", () => {
  it("is the Grossist in Uke 4, with Uke 1–3 behind it and no Week beyond nå", () => {
    expect(DEMO_SEAT.week).toBe(4);
    expect(DEMO_SEAT.history.map((w) => w.week)).toEqual([1, 2, 3]);
    expect(Math.max(...DEMO_SEAT.supply_line_slots.map((s) => s.arrival_week))).toBeLessThanOrEqual(DEMO_SEAT.week + 4);
  });

  it("is the Seat the caption names", () => {
    expect(DEMO_SEAT.role).toBe("wholesaler");
    expect(nb.landing.seat.caption).toContain(`${nb.terms.wholesaler}, ${nb.terms.week} ${DEMO_SEAT.week}.`);
  });

  it("never shows a rising Ordre inn", () => {
    const orders = [...DEMO_SEAT.history.map((w) => w.incoming_order), DEMO_SEAT.incoming_order];
    orders.slice(1).forEach((value, i) => expect(value).toBeLessThanOrEqual(orders[i]));
  });

  it("orders the fixed 4 of a Veiledet uke and holds no stock below zero", () => {
    expect(DEMO_GUIDED_ORDER).toBe(4);
    expect(DEMO_SEAT.history.every((w) => w.order === DEMO_GUIDED_ORDER)).toBe(true);
    expect([...DEMO_SEAT.history.map((w) => w.net_inventory), DEMO_SEAT.net_inventory].every((v) => v >= 0)).toBe(true);
  });

  it("holds only the Seat's own state: no names and no other Seat", () => {
    expect(Object.keys(demo).sort()).toEqual(["guided_order", "seat_state"]);
    expect(DEMO_SEAT.neighbour_numbers).toEqual([]);
  });
});
