import { describe, expect, it } from "vitest";

import { bandLayout, PIPE_UNIT, STOCK_UNIT, textWidth } from "@/components/charts/chain-band-layout";

import { bandEnds, bandLabels, bandSentence, type BandState } from "./chain-band";
import classic from "./fixtures/chain-band-classic.json";

/** The Kjedebånd's scale test (Story 6.9, UX-DR15): every Uke of the Classic fixture game for all
 * four Roles (`chain-band-classic.json`, held to the engine by
 * `backend/tests/games/test_play_fixture.py`), at 320 and 360 px less the 16 px chart gutters,
 * at 100 % and 200 % text. */
const STATES = classic as BandState[];
const SEAT_ROLES = ["factory", "distributor", "wholesaler", "retailer"] as const;
const WIDTHS = [288, 328];
const FONTS = [13, 26];

function layout(state: BandState, width: number, fontSize: number) {
  return bandLayout({
    width,
    fontSize,
    inventory: state.inventory,
    backlog: state.backlog,
    slots: state.supply_line_slots.map((slot) => slot.quantity),
    overdue: state.overdue,
    labels: bandLabels(state, bandEnds(state.role, SEAT_ROLES)),
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

function problems(state: BandState, width: number, fontSize: number): string[] {
  const band = layout(state, width, fontSize);
  const found: string[] = [];
  const inside = (r: Rect, what: string) => {
    if (r.left < -0.01 || r.right > width + 0.01 || r.top < -0.01 || r.bottom > band.height + 0.01) found.push(`${what} leaves the band`);
  };
  const boxes = band.labels.map((label) => ({ label, box: textBox(label, fontSize) }));
  boxes.forEach(({ label, box }, i) => {
    inside(box, label.text);
    for (const other of boxes.slice(i + 1)) if (overlaps(box, other.box)) found.push(`${label.text} overlaps ${other.label.text}`);
  });
  const marks = [...band.boxes, ...(band.overdueBox ? [band.overdueBox] : []), band.node];
  for (const mark of marks) {
    const r = { left: mark.x, right: mark.x + mark.width, top: mark.y, bottom: mark.y + mark.height };
    inside(r, "a mark");
    for (const { label, box } of boxes) if (overlaps(r, box)) found.push(`${label.text} covers a mark`);
  }
  // Every box on the pipe stays left of the node.
  for (const box of band.boxes) if (box.x + box.width > band.node.x) found.push("a box runs into the node");
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

  it("reads as one sentence", () => {
    const state = { ...at("wholesaler", 11), incoming_order: 8, incoming_delivery: 4, shipped: 4, inventory: 0, backlog: 13, supply_line: 16, overdue: 0 };
    expect(bandSentence(state)).toBe("Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16");
    expect(bandSentence({ ...state, overdue: 7, supply_line: 23 })).toBe("Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 23, av dem 7 uten kjent uke");
  });

  it("estimates a label's width from its letters", () => {
    expect(textWidth("Restordre 13", 13)).toBeGreaterThan(textWidth("Sendt 4", 13));
    expect(textWidth("Restordre 13", 26)).toBeCloseTo(2 * textWidth("Restordre 13", 13), -1);
  });
});
