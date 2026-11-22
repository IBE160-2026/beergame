import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { labelSpan, NetGraph, netScale, projectionBand } from "@/components/charts/net-graph";
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
    // The sum's spaces are non-breaking (Story 10.6), so it reads as one unit.
    expect(sentence(orderProjection(state, 24))).toBe(
      "Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.",
    );
    expect(sentence(orderProjection(state, null))).toBe(
      "Den stiplede linja viser netto lager om fire uker: 3 − 4 × 8 = −29 hvis du ikke bestiller og ordre inn holder seg. Ikke garantert.",
    );
  });

  it("keeps the sum on one line: no breakable space inside it (Story 10.6, the 10.4 visual check)", () => {
    const state = { week: 11, incoming_order: 10, preview: { order_arrival_week: 15, supply_line_base: 0, position_base: -4 } };
    const text = sentence(orderProjection(state, null));
    const sum = text.slice(text.indexOf(": ") + 2, text.indexOf(" hvis"));
    expect(sum).toBe("−4 − 4 × 10 = −44");
    expect(sum).not.toMatch(/ /);
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
    expect(sentence(projection)).toMatch(
      /^Den stiplede linja viser netto lager om to uker: .* − 2 × \d+ = −?\d+ hvis ordre inn holder seg\. Ikke garantert\.$/,
    );
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

  it.each([
    // The 10.4 visual check at 390 px: Netto lager −20 at nå, Posisjon −4, a flat projection.
    { name: "flat at Netto lager", net: -20, position: -4, value: -20, both: true },
    { name: "falling", net: -20, position: -4, value: -44, both: true },
    { name: "from stock to backlog", net: 12, position: 20, value: -5, both: true },
    // A line rising over the field's whole height leaves room clear of it for one label only: the
    // Netto lager label takes it, and the halo keeps Posisjon legible where the line crosses it.
    { name: "rising over the whole field", net: -8, position: 4, value: 30, both: false },
  ])("keeps the direct labels clear of the projection's line and dot: $name (Story 10.6)", ({ net, position, value, both }) => {
    const fontSize = 12;
    const width = 130;
    const height = 92;
    const history = [4, 5, 6, 7, 8, 9, 10, 11].map((week, i) => ({ week, x: 4 + 3.5 * i, net: net + 2 * (7 - i), position }));
    const now = history.at(-1)!;
    const projection = [
      { week: 11, x: now.x, value: net },
      { week: 15, x: now.x + 4 * 22, value },
    ];
    const props = {
      width,
      height,
      fontSize,
      points: history,
      nowX: now.x + 11,
      title: "t",
      netLabel: `Restordre ${Math.abs(net)}`,
      positionLabel: `Posisjon ${position}`,
      nowLabel: "Nå",
      projection,
    };
    const markup = renderToStaticMarkup(<NetGraph {...props} />);
    const { y } = netScale(props);
    const ys: number[] = [];
    for (const [label, text] of [
      ["net", props.netLabel],
      ["position", props.positionLabel],
    ] as const) {
      const tag = markup.match(new RegExp(`<text[^>]*data-label="${label}"[^>]*>`))![0];
      const at = Number(tag.match(/ y="([-\d.]+)"/)![1]);
      const anchor = tag.includes('text-anchor="end"') ? "end" : "start";
      const x = Number(tag.match(/ x="([-\d.]+)"/)![1]);
      const band = projectionBand(projection, y, ...labelSpan({ x, textAnchor: anchor }, text, fontSize), false);
      const half = fontSize * 0.6;
      if (band && (both || label === "net")) {
        expect(at + half <= band[0] || at - half >= band[1], `${label} at ${at} in ${band}`).toBe(true);
      }
      expect(at).toBeGreaterThanOrEqual(fontSize * 2.3); // under «Nå», inside the field
      expect(at).toBeLessThanOrEqual(height - fontSize * 0.85);
      expect(tag).toContain('paint-order="stroke"'); // the halo, for the gridlines right of nå
      ys.push(at);
    }
    expect(Math.abs(ys[0]! - ys[1]!)).toBeGreaterThanOrEqual(fontSize * 1.5 - 0.01); // never on each other
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
