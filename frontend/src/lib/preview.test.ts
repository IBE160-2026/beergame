import { describe, expect, it } from "vitest";

import golden from "@/modules/games/fixtures/preview-golden.json";
import projected from "@/modules/games/fixtures/projection-golden.json";

import { orderProjection, orderPreview } from "./preview";

/** Every Seat-Week of three golden-trace games (Classic delays, 3/3/3 and 1/1/1), with Netto lager
 * at nå + horizon as the engine's supply-line slots give it (Story 10.4, AD-3). */
describe("orderProjection against the engine's golden-trace games (Story 10.4, AD-10)", () => {
  it("covers three delay horizons and every Role", () => {
    expect(new Set(projected.map((item) => item.horizon))).toEqual(new Set([2, 4, 6]));
    expect(new Set(projected.map((item) => item.role)).size).toBe(4);
  });

  it.each(projected.map((item) => [`${item.trace} ${item.role} Uke ${item.state.week}`, item] as const))("%s", (_, item) => {
    const shown = orderProjection(item.state, item.order);
    expect(shown.value).toBe(item.projection);
    expect(shown.horizon).toBe(item.horizon);
    expect(shown.week).toBe(item.state.week + item.horizon);
    expect(shown.position).toBe(item.state.position);
  });

  it("counts no Order as 0, and the spine's example: 3 + 24 − 4 × 8 = −5", () => {
    const state = { week: 11, incoming_order: 8, preview: { order_arrival_week: 15, supply_line_base: 16, position_base: 3 } };
    expect(orderProjection(state, 24)).toEqual({ position: 3, order: 24, horizon: 4, incoming: 8, week: 15, value: -5 });
    expect(orderProjection(state, null).value).toBe(-29);
  });
});

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
