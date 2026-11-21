import { describe, expect, it } from "vitest";

import golden from "@/modules/games/fixtures/preview-golden.json";

import { orderPreview } from "./preview";

/** Every Seat-Week of two golden-trace games (Classic delays, and 3/3/3), held to the engine by
 * `backend/tests/games/test_play_fixture.py`. */
describe("orderPreview against the engine's golden-trace games (Story 6.11, AD-10)", () => {
  it("covers both games and every Role", () => {
    expect(new Set(golden.map((item) => item.trace)).size).toBe(2);
    expect(new Set(golden.map((item) => item.role)).size).toBe(4);
  });

  it.each(golden.map((item) => [`${item.trace} ${item.role} Uke ${item.week}`, item] as const))("%s", (_, item) => {
    const shown = orderPreview(item.preview, item.order);
    const next = item.next;
    // The Order joins På vei now; the next Uke's delivery leaves it.
    expect(shown.supplyLine).toBe(next.supply_line + next.incoming_delivery);
    // Posisjon with the Order, less what the next Uke's incoming order takes.
    expect(shown.position).toBe(next.position + next.incoming_order);
    // The Order stands on the pipe the next Uke, due in the Uke the preview names.
    expect(next.supply_line_slots).toContainEqual(expect.objectContaining({ stage: "ordered", quantity: item.order, arrival_week: shown.arrivalWeek }));
    expect(shown.supplyLineBase).toBe(item.preview.supply_line_base);
    expect(shown.order).toBe(item.order);
  });

  it("names a later Uke when the delays are longer, with no delay of its own", () => {
    const classic = golden.find((item) => item.trace.startsWith("classic") && item.week === 5)!;
    const slow = golden.find((item) => item.trace.startsWith("delays-3") && item.week === 5)!;
    expect(orderPreview(classic.preview, 1).arrivalWeek).toBe(9);
    expect(orderPreview(slow.preview, 1).arrivalWeek).toBe(11);
  });
});
