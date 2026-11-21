import { describe, expect, it } from "vitest";

import { bandLayout, PIPE_UNIT, STOCK_UNIT, textWidth } from "@/components/charts/chain-band-layout";

import { bandEnds, bandLabels, bandSentence, type BandState } from "./chain-band";
import capped from "./fixtures/chain-band-capped.json";
import classic from "./fixtures/chain-band-classic.json";

/** The Kjedebånd's scale test (Story 6.9, UX-DR15): every Uke of the Classic fixture game for all
 * four Roles (`chain-band-classic.json`, held to the engine by
 * `backend/tests/games/test_play_fixture.py`), at 320 and 360 px less the 16 px chart gutters,
 * at 100 % and 200 % text. */
const STATES = classic as BandState[];
const SEAT_ROLES = ["factory", "distributor", "wholesaler", "retailer"] as const;
const WIDTHS = [288, 328];
const FONTS = [13, 26];

/** Both Information visibility views on (Story 6.21): the neighbours' own inventory and backlog in
 * the same Uke of the fixture game, upstream first, as the api fills `neighbour_numbers`. */
function withViews(state: BandState): BandState {
  const index = SEAT_ROLES.indexOf(state.role as (typeof SEAT_ROLES)[number]);
  const neighbours = [SEAT_ROLES[index - 1], SEAT_ROLES[index + 1]].filter((role) => role !== undefined);
  return {
    ...state,
    neighbour_numbers: neighbours.flatMap((role) => {
      const other = STATES.find((s) => s.role === role && s.week === state.week)!;
      return [
        { role, week: state.week, quantity: "inventory" as const, value: other.inventory },
        { role, week: state.week, quantity: "backlog" as const, value: other.backlog },
      ];
    }),
  };
}

function layout(state: BandState, width: number, fontSize: number, typed?: number) {
  return bandLayout({
    width,
    fontSize,
    inventory: state.inventory,
    backlog: state.backlog,
    slots: state.supply_line_slots.map((slot) => slot.quantity),
    overdue: state.overdue,
    typed,
    labels: bandLabels(state, bandEnds(state.role, SEAT_ROLES, state.neighbour_numbers), typed),
  });
}

type Rect = { left: number; right: number; top: number; bottom: number };

/** A label's text box: Source Sans 3 reaches 1.03 em above the baseline and 0.41 em below. */
function textBox(label: { x: number; y: number; width: number }, fontSize: number): Rect {
  return { left: label.x, right: label.x + label.width, top: label.y - 1.03 * fontSize, bottom: label.y + 0.41 * fontSize };
}

function overlaps(a: Rect, b: Rect) {
  return Math.min(a.right, b.right) - Math.max(a.left, b.left) > 0.5 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 0.5;
}

function problems(state: BandState, width: number, fontSize: number, typed?: number): string[] {
  const band = layout(state, width, fontSize, typed);
  const found: string[] = [];
  const inside = (r: Rect, what: string) => {
    if (r.left < -0.01 || r.right > width + 0.01 || r.top < -0.01 || r.bottom > band.height + 0.01) found.push(`${what} leaves the band`);
  };
  const boxes = band.labels.map((label) => ({ label, box: textBox(label, fontSize) }));
  boxes.forEach(({ label, box }, i) => {
    inside(box, label.text);
    for (const other of boxes.slice(i + 1)) if (overlaps(box, other.box)) found.push(`${label.text} overlaps ${other.label.text}`);
  });
  const marks = [...band.boxes, ...(band.typedBox ? [band.typedBox] : []), ...(band.overdueBox ? [band.overdueBox] : []), band.node];
  for (const mark of marks) {
    const r = { left: mark.x, right: mark.x + mark.width, top: mark.y, bottom: mark.y + mark.height };
    inside(r, "a mark");
    for (const { label, box } of boxes) if (overlaps(r, box)) found.push(`${label.text} covers a mark`);
  }
  // Every box on the pipe stays left of the node.
  for (const box of [...band.boxes, ...(band.typedBox ? [band.typedBox] : [])]) if (box.x + box.width > band.node.x) found.push("a box runs into the node");
  return found;
}

describe("the Kjedebånd's scale (UX-DR15)", () => {
  it("covers every Uke of the fixture game for all four Roles", () => {
    expect(STATES).toHaveLength(120);
    expect(new Set(STATES.map((s) => s.role))).toEqual(new Set(SEAT_ROLES));
    expect(Math.max(...STATES.map((s) => s.supply_line))).toBeGreaterThanOrEqual(80);
    expect(STATES.some((s) => s.overdue > 0)).toBe(true);
  });

  for (const width of WIDTHS) {
    for (const fontSize of FONTS) {
      it(`fits every Uke at ${width} px band width and ${fontSize} px text: nothing overflows, no labels overlap`, () => {
        const found = STATES.flatMap((state) => problems(state, width, fontSize).map((p) => `${state.role} Uke ${state.week}: ${p}`));
        expect(found).toEqual([]);
      });
    }
  }

  for (const width of WIDTHS) {
    for (const fontSize of FONTS) {
      it(`fits every Uke with both neighbour views on at ${width} px and ${fontSize} px text (Story 6.21)`, () => {
        const found = STATES.flatMap((state) => problems(withViews(state), width, fontSize).map((p) => `${state.role} Uke ${state.week}: ${p}`));
        expect(found).toEqual([]);
        // Every neighbour number is drawn, none is lost.
        const drawn = STATES.map((state) => layout(withViews(state), width, fontSize).labels.filter((l) => l.key.endsWith("Numbers")).length);
        expect(drawn.every((count, i) => count === withViews(STATES[i]!).neighbour_numbers.length)).toBe(true);
      });
    }
  }

  // A capped Seat (Story 6.22, FR-12): the fixture game's Orders with the Grossist shipping at most 6
  // a Week (`chain-band-capped.json`, held to the engine), so it holds stock and backlog at once.
  const CAPPED = capped as BandState[];

  it("covers a capped Seat holding stock and backlog at once (Story 6.22)", () => {
    expect(CAPPED).toHaveLength(120);
    expect(CAPPED.filter((s) => s.inventory > 0 && s.backlog > 0).length).toBeGreaterThanOrEqual(10);
  });

  for (const width of WIDTHS) {
    for (const fontSize of FONTS) {
      it(`fits every Uke of the capped game with both bars at ${width} px and ${fontSize} px text (Story 6.22)`, () => {
        const found = CAPPED.flatMap((state) => problems(state, width, fontSize).map((p) => `${state.role} Uke ${state.week}: ${p}`));
        expect(found).toEqual([]);
        for (const state of CAPPED.filter((s) => s.inventory > 0 && s.backlog > 0)) {
          const band = layout(state, width, fontSize);
          // Stock above the baseline, backlog below it, each with its label.
          expect(band.stockBar!.y + band.stockBar!.height).toBeCloseTo(band.goodsY);
          expect(band.backlogBar!.y).toBeCloseTo(band.goodsY);
          expect(band.labels.filter((l) => l.key === "stock").map((l) => l.text)).toEqual([`Lager ${state.inventory}`, `Restordre ${state.backlog}`]);
        }
      });
    }
  }

  it("reads both numbers of a capped Seat (Story 6.22, NFR-6)", () => {
    const state = CAPPED.find((s) => s.role === "wholesaler" && s.week === 9)!;
    expect(bandSentence(state)).toBe(
      `Ordre inn ${state.incoming_order}, Levering ${state.incoming_delivery}, Sendt ${state.shipped}, Lager ${state.inventory}, Restordre ${state.backlog}, På vei ${state.supply_line}`,
    );
  });

  it("fits every Uke with one view on, its block beside the other end's plain label (Story 6.21)", () => {
    const one = (state: BandState, side: number) => {
      const index = SEAT_ROLES.indexOf(state.role as (typeof SEAT_ROLES)[number]);
      const role = SEAT_ROLES[index + side];
      return { ...withViews(state), neighbour_numbers: withViews(state).neighbour_numbers.filter((n) => n.role === role) };
    };
    for (const side of [-1, 1]) {
      for (const width of WIDTHS) {
        for (const fontSize of FONTS) {
          const found = STATES.flatMap((state) => problems(one(state, side), width, fontSize).map((p) => `${state.role} Uke ${state.week} (${side}): ${p}`));
          expect(found).toEqual([]);
        }
      }
    }
    // The plain end label stays on the other side.
    const band = layout(one(STATES.find((s) => s.role === "wholesaler" && s.week === 11)!, -1), 328, 13);
    expect(band.labels.find((l) => l.key === "downstream")!.text).toBe("Detaljist");
    expect(band.labels.find((l) => l.key === "upstream")!.text).toBe("Distributør, Uke 11");
  });

  it("uses one factor for pipe and stock, the DESIGN.md units as maxima, from the band width", () => {
    const state = STATES.find((s) => s.role === "wholesaler" && s.week === 11)!;
    const wide = layout(state, 600, 13);
    expect(wide.scale).toBe(1);
    expect(wide.pipeUnit).toBe(PIPE_UNIT);
    expect(wide.stockUnit).toBe(STOCK_UNIT);
    const narrow = layout(state, 288, 13);
    expect(narrow.scale).toBeLessThan(1);
    expect(narrow.pipeUnit / PIPE_UNIT).toBeCloseTo(narrow.stockUnit / STOCK_UNIT);
    // At a given width the scale is the same in every ordinary Uke, so boxes compare across Uker.
    const scales = new Set(STATES.filter((s) => s.supply_line - s.overdue <= 60).map((s) => layout(s, 288, 13).scale));
    expect(scales.size).toBe(1);
    // Boxes at true scale: width = quantity × pipe unit, soonest next to the node.
    const [first, second] = narrow.boxes;
    expect(first!.width).toBeCloseTo(state.supply_line_slots[0]!.quantity * narrow.pipeUnit);
    expect(first!.x).toBeGreaterThan(second!.x);
  });

  it("holds the worst case of 80 units on the pipe plus overdue units at the width's own scale", () => {
    const base = STATES.find((s) => s.role === "wholesaler" && s.week === 11)!;
    const slots = [20, 20, 20, 20].map((quantity, i) => ({ stage: "in_transit" as const, quantity, arrival_week: 12 + i }));
    const worst = { ...base, supply_line: 120, supply_line_slots: slots, overdue: 40 };
    for (const width of WIDTHS) {
      expect(layout(worst, width, 13).scale).toBe(layout(base, width, 13).scale);
      for (const fontSize of FONTS) expect(problems(worst, width, fontSize)).toEqual([]);
    }
  });

  it("keeps the overdue number over its box at 200 % text", () => {
    const state = { ...STATES.find((s) => s.overdue >= 50)!, overdue: 56 };
    const number = layout(state, 288, 26).labels.find((l) => l.key === "overdue")!;
    expect(number.wrapped).toBe(false);
    expect(number.x).toBeGreaterThanOrEqual(0);
  });

  it("wraps a label with no room under the band, on its own side", () => {
    const state = STATES.find((s) => s.role === "wholesaler" && s.week === 11)!;
    const band = layout(state, 288, 13);
    const wrapped = band.labels.filter((l) => l.wrapped);
    expect(wrapped.length).toBeGreaterThan(0);
    const node = band.node.y + band.node.height;
    for (const l of wrapped) expect(l.y).toBeGreaterThan(node);
    const downstream = band.labels.find((l) => l.key === "downstream")!;
    expect(downstream.wrapped).toBe(true);
    expect(downstream.x + downstream.width).toBe(288);
    // With room, nothing wraps.
    expect(layout(state, 448, 13).labels.filter((l) => l.wrapped)).toEqual([]);
  });

  it("shrinks a Uke beyond the worst case further, never past the band", () => {
    const state = { ...STATES[0]!, supply_line: 300, supply_line_slots: [{ stage: "in_transit" as const, quantity: 150, arrival_week: 2 }, { stage: "ordered" as const, quantity: 150, arrival_week: 3 }], overdue: 0 };
    expect(problems(state, 288, 13)).toEqual([]);
    expect(layout(state, 288, 13).scale).toBeLessThan(layout(STATES[0]!, 288, 13).scale);
  });
});

describe("the Kjedebånd's content", () => {
  const at = (role: string, week: number) => STATES.find((s) => s.role === role && s.week === week)!;

  it("has the neighbours at its ends: Produksjon left of the Fabrikk, Kundene right of the Detaljist (UX-DR73)", () => {
    expect(bandEnds("wholesaler", SEAT_ROLES)).toEqual({ upstream: "Distributør", downstream: "Detaljist" });
    expect(bandEnds("factory", SEAT_ROLES)).toEqual({ upstream: "Produksjon", downstream: "Distributør" });
    expect(bandEnds("retailer", SEAT_ROLES)).toEqual({ upstream: "Grossist", downstream: "Kundene" });
  });

  it("puts a neighbour's numbers at its end, labelled with Role and Uke (Story 6.21, UX-DR24)", () => {
    const state = withViews(at("wholesaler", 11));
    const distributor = at("distributor", 11);
    const retailer = at("retailer", 11);
    const ends = bandEnds(state.role, SEAT_ROLES, state.neighbour_numbers);
    expect(ends).toEqual({
      upstream: "Distributør, Uke 11",
      downstream: "Detaljist, Uke 11",
      upstreamNumbers: [`Lager ${distributor.inventory}`, `Restordre ${distributor.backlog}`],
      downstreamNumbers: [`Lager ${retailer.inventory}`, `Restordre ${retailer.backlog}`],
    });
    // One view: only that end changes; no numbers keep the plain ends of Story 6.9.
    const up = state.neighbour_numbers.filter((n) => n.role === "distributor");
    expect(bandEnds("wholesaler", SEAT_ROLES, up)).toEqual({ upstream: "Distributør, Uke 11", downstream: "Detaljist", upstreamNumbers: ends.upstreamNumbers });
    expect(bandEnds("wholesaler", SEAT_ROLES, [])).toEqual({ upstream: "Distributør", downstream: "Detaljist" });
    // The ends of the chain: Produksjon and Kundene stay; a Role that is no neighbour is never drawn.
    const factory = withViews(at("factory", 11));
    expect(bandEnds("factory", SEAT_ROLES, factory.neighbour_numbers)).toMatchObject({ upstream: "Produksjon", downstream: "Distributør, Uke 11" });
    expect(bandEnds("factory", SEAT_ROLES, state.neighbour_numbers)).toEqual({ upstream: "Produksjon", downstream: "Distributør, Uke 11", downstreamNumbers: ends.upstreamNumbers });
    expect(bandEnds("retailer", SEAT_ROLES, up)).toEqual({ upstream: "Grossist", downstream: "Kundene" });
    // Drawn at their own end: upstream numbers left of the node, downstream right of it, in reading order.
    const band = layout(state, 448, 13);
    const placed = (key: string) => band.labels.filter((l) => l.key === key);
    for (const l of placed("upstreamNumbers")) expect(l.x + l.width).toBeLessThanOrEqual(band.node.x);
    for (const l of placed("downstreamNumbers")) expect(l.x).toBeGreaterThanOrEqual(band.node.x + band.node.width);
    const lager = placed("downstreamNumbers").find((l) => l.text.startsWith("Lager"))!;
    const restordre = placed("downstreamNumbers").find((l) => l.text.startsWith("Restordre"))!;
    expect(lager.x).toBeLessThan(restordre.x);
  });

  it("reads the neighbours' numbers after the Seat's own (Story 6.21, NFR-6)", () => {
    const state = { ...at("wholesaler", 11), incoming_order: 8, incoming_delivery: 4, shipped: 4, inventory: 0, backlog: 13, supply_line: 16, overdue: 0 };
    const numbers = [
      { role: "distributor" as const, week: 11, quantity: "inventory" as const, value: 12 },
      { role: "distributor" as const, week: 11, quantity: "backlog" as const, value: 3 },
      { role: "retailer" as const, week: 11, quantity: "inventory" as const, value: 0 },
      { role: "retailer" as const, week: 11, quantity: "backlog" as const, value: 5 },
    ];
    expect(bandSentence(state, undefined, bandEnds("wholesaler", SEAT_ROLES, numbers))).toBe(
      "Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16. Distributør, Uke 11: Lager 12, Restordre 3. Detaljist, Uke 11: Lager 0, Restordre 5",
    );
    expect(bandSentence(state, undefined, bandEnds("wholesaler", SEAT_ROLES, numbers.slice(2)))).toBe(
      "Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16. Detaljist, Uke 11: Lager 0, Restordre 5",
    );
    expect(bandSentence(state, undefined, bandEnds("wholesaler", SEAT_ROLES, []))).toBe("Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16");
  });

  it("labels the flow from the api's numbers, Din ordre without a number", () => {
    const state = at("wholesaler", 11);
    const labels = bandLabels(state, bandEnds(state.role, SEAT_ROLES));
    expect(labels).toMatchObject({
      order: "Din ordre",
      incoming: `Ordre inn ${state.incoming_order}`,
      delivery: `Levering ${state.incoming_delivery}`,
      shipped: `Sendt ${state.shipped}`,
      supplyLine: `På vei ${state.supply_line}`,
    });
    expect(labels.stock).toEqual([`Restordre ${state.backlog}`]);
  });

  it("names stock or backlog, both when both are held, and «Lager 0» when neither", () => {
    const base = at("wholesaler", 1);
    const stock = (inventory: number, backlog: number) => bandLabels({ ...base, inventory, backlog }, { upstream: "", downstream: "" }).stock;
    expect(stock(12, 0)).toEqual(["Lager 12"]);
    expect(stock(0, 13)).toEqual(["Restordre 13"]);
    expect(stock(6, 4)).toEqual(["Lager 6", "Restordre 4"]);
    expect(stock(0, 0)).toEqual(["Lager 0"]);
    const both = layout({ ...base, inventory: 6, backlog: 4 }, 328, 13);
    expect(both.stockBar!.y + both.stockBar!.height).toBe(both.goodsY);
    expect(both.backlogBar!.y).toBe(both.goodsY);
    const none = layout({ ...base, inventory: 0, backlog: 0 }, 328, 13);
    expect([none.stockBar, none.backlogBar]).toEqual([null, null]);
  });

  it("draws overdue units as a fixed-width box farthest out, with their number above it", () => {
    const state = STATES.find((s) => s.overdue > 0 && s.overdue < 20)!;
    const band = layout(state, 328, 13);
    expect(band.overdueBox).not.toBeNull();
    expect(band.overdueBox!.width).toBe(layout({ ...state, overdue: state.overdue * 3 }, 328, 13).overdueBox!.width);
    expect(Math.min(...band.boxes.map((b) => b.x))).toBeGreaterThan(band.overdueBox!.x);
    const number = band.labels.find((l) => l.key === "overdue")!;
    expect(number.text).toBe(String(state.overdue));
    expect(number.wrapped).toBe(false);
    expect(number.y).toBeLessThan(band.overdueBox!.y);
    expect(layout({ ...state, overdue: 0 }, 328, 13).overdueBox).toBeNull();
  });

  it("fits every Uke with a typed Order of 24 at 288 px and 200 % text (Story 6.11)", () => {
    const found = STATES.flatMap((state) => problems(state, 288, 26, 24).map((p) => `${state.role} Uke ${state.week}: ${p}`));
    expect(found).toEqual([]);
  });

  it("draws a typed Order as the last box on the pipe and writes it beside På vei (Story 6.11)", () => {
    const state = STATES.find((s) => s.role === "wholesaler" && s.week === 11)!;
    const band = layout(state, 328, 13, 24);
    expect(band.boxes).toHaveLength(layout(state, 328, 13).boxes.length);
    expect(band.typedBox).not.toBeNull();
    expect(band.typedBox!.x).toBeLessThan(Math.min(...band.boxes.map((b) => b.x)));
    expect(band.typedBox!.width).toBeCloseTo(24 * band.pipeUnit);
    const text = (key: string) => band.labels.find((l) => l.key === key)!.text;
    expect(text("order")).toBe("Din ordre 24");
    expect(text("supplyLine")).toBe("På vei 16 + 24");
    // 0 is an Order with no box; nothing typed keeps «Din ordre» without a number.
    expect(layout(state, 328, 13, 0).typedBox).toBeNull();
    expect(layout(state, 328, 13).labels.find((l) => l.key === "order")!.text).toBe("Din ordre");
  });

  it("reads as one sentence", () => {
    const state = { ...at("wholesaler", 11), incoming_order: 8, incoming_delivery: 4, shipped: 4, inventory: 0, backlog: 13, supply_line: 16, overdue: 0 };
    expect(bandSentence(state)).toBe("Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16");
    expect(bandSentence({ ...state, overdue: 7, supply_line: 23 })).toBe("Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 23, av dem 7 uten kjent uke");
    // With a typed Order it ends «På vei 16 pluss 24» (Story 6.11).
    expect(bandSentence(state, 24)).toBe("Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16 pluss 24");
    expect(bandSentence({ ...state, overdue: 7, supply_line: 23 }, 24)).toMatch(/uten kjent uke, pluss 24$/);
  });

  it("estimates a label's width from its letters", () => {
    expect(textWidth("Restordre 13", 13)).toBeGreaterThan(textWidth("Sendt 4", 13));
    expect(textWidth("Restordre 13", 26)).toBeCloseTo(2 * textWidth("Restordre 13", 13), -1);
  });
});
