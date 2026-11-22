import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { netScale } from "@/components/charts/net-graph";
import { orderProjection } from "@/lib/preview";

import short from "./fixtures/play-replay-short.json";
import week11 from "./fixtures/play-week-11.json";
import { graphSeries, weekColumns } from "./week-table";
import { ProjectionSentence, projectionPoints } from "./week-table-view";

/** The Replay's projection on Graf over tabell (Story 10.4, UX-DR19): where its line and dot go
 * over the drawn columns, and its sentence. The envelopes are the engine's
 * (`backend/tests/games/test_play_fixture.py`). */

function size(week: number) {
  const columns = weekColumns(week).filter((column) => column.phone);
  return { columns, xs: columns.map((_, i) => 10 + 20 * i) };
}

const sentence = (projection: ReturnType<typeof orderProjection>) =>
  renderToStaticMarkup(<ProjectionSentence projection={projection} />).replace(/<[^>]+>/g, "");

describe("the projection (Story 10.4)", () => {
  it("reads the spine's sentence with the Seat's numbers", () => {
    const state = { week: 11, incoming_order: 8, preview: { order_arrival_week: 15, supply_line_base: 16, position_base: 3 } };
    expect(sentence(orderProjection(state, 24))).toBe(
      "Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.",
    );
    expect(sentence(orderProjection(state, null))).toBe(
      "Den stiplede linja viser netto lager om fire uker: 3 − 4 × 8 = −29 hvis du ikke bestiller og ordre inn holder seg. Ikke garantert.",
    );
  });

  it("ends its dot at nå + 4 with the Classic delays", () => {
    const state = week11.seat_state;
    const projection = orderProjection(state, 24);
    const found = projectionPoints(size(state.week), state.net_inventory, projection)!;
    expect(found.clipped).toBe(false);
    expect(found.points.map((p) => p.week)).toEqual([11, 15]);
    expect(found.points[0]!.value).toBe(state.net_inventory);
    expect(found.points[1]!.value).toBe(projection.value);
  });

  it("renders a Replay with shorter delays: two Uker, the dot at nå + 2", () => {
    const state = short.seat_state;
    const projection = orderProjection(state, 10);
    expect(projection.horizon).toBe(2);
    expect(sentence(projection)).toMatch(/^Den stiplede linja viser netto lager om to uker: .* − 2 × \d+ = −?\d+ hvis ordre inn holder seg\. Ikke garantert\.$/);
    const found = projectionPoints(size(state.week), state.net_inventory, projection)!;
    expect(found.points.map((p) => p.week)).toEqual([state.week, state.week + 2]);
    const at = size(state.week).columns.findIndex((column) => column.week === state.week + 2);
    expect(found.points[1]!.x).toBe(size(state.week).xs[at]);
  });

  it("stretches the Netto lager axis to the projection's end, so the line stays on its ticks", () => {
    const state = week11.seat_state;
    const projection = orderProjection(state, null);
    const found = projectionPoints(size(state.week), state.net_inventory, projection)!;
    const points = graphSeries(state as unknown as Parameters<typeof graphSeries>[0]).weeks.map((week, i) => ({ ...week, x: i }));
    const height = 120;
    const scale = netScale({ height, fontSize: 13, points, projection: found.points });
    expect(scale.domain[0]).toBeLessThanOrEqual(Math.min(projection.value, state.net_inventory));
    expect(scale.domain[1]).toBeGreaterThanOrEqual(Math.max(projection.value, state.net_inventory));
    const end = scale.y(projection.value);
    expect(end).toBeGreaterThanOrEqual(0);
    expect(end).toBeLessThanOrEqual(height);
  });

  it("keeps the axis at nå + 4 when the horizon runs past it: the same line, clipped, no dot", () => {
    const projection = { position: 10, order: 6, horizon: 6, incoming: 4, week: 17, value: -8 };
    const found = projectionPoints(size(11), -2, projection)!;
    expect(found.clipped).toBe(true);
    expect(found.points.map((p) => p.week)).toEqual([11, 15]);
    // Four of the six Uker along the straight line from −2 to −8.
    expect(found.points[1]!.value).toBeCloseTo(-2 + (4 / 6) * -6);
  });
});
