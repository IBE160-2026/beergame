import { describe, expect, it } from "vitest";

import { renderToStaticMarkup } from "react-dom/server";

import { nb } from "@/copy/nb";
import { MINUS } from "@/lib/number-format";

import week1 from "./fixtures/play-week-1.json";
import fixture from "./fixtures/play-week-11.json";
import week14 from "./fixtures/play-week-14.json";
import week30 from "./fixtures/play-week-30.json";
import type { SeatState } from "./api";
import { cellFor, graphSeries, netStep, ROWS, weekColumns } from "./week-table";
import { WeekTable } from "./week-table-view";

// The engine's Grossist in Uke 11 of a Classic game (pinned by `backend/tests/games/test_play_fixture.py`).
const state = fixture.seat_state as SeatState;

describe("weekColumns", () => {
  it("runs from Uke 1 to nå + 4, the phone showing nå − 7 onwards", () => {
    const columns = weekColumns(11);
    expect(columns.map((c) => c.week)).toEqual(Array.from({ length: 15 }, (_, i) => i + 1));
    expect(columns.filter((c) => c.phone).map((c) => c.week)).toEqual([4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
    expect(columns.find((c) => c.when === "now")?.week).toBe(11);
    expect(columns.filter((c) => c.when === "future").map((c) => c.week)).toEqual([12, 13, 14, 15]);
  });

  it("starts at Uke 1 while nå is below 8", () => {
    expect(weekColumns(1).map((c) => [c.week, c.when, c.phone])).toEqual([
      [1, "now", true],
      [2, "future", true],
      [3, "future", true],
      [4, "future", true],
      [5, "future", true],
    ]);
    expect(weekColumns(7).every((c) => c.phone)).toBe(true);
  });
});

describe("netStep", () => {
  it("bins |v| into the four matrix steps by sign, zero apart", () => {
    expect([0, 1, 9, 10, 19, 20, 34, 35, 120].map(netStep)).toEqual([
      "zero",
      "pos-1",
      "pos-1",
      "pos-2",
      "pos-2",
      "pos-3",
      "pos-3",
      "pos-4",
      "pos-4",
    ]);
    expect([-1, -9, -10, -19, -20, -34, -35].map(netStep)).toEqual([
      "neg-1",
      "neg-1",
      "neg-2",
      "neg-2",
      "neg-3",
      "neg-3",
      "neg-4",
    ]);
  });
});

describe("cellFor", () => {
  it("writes the earlier Uker from the history as the api gave them", () => {
    expect(cellFor(state, "incomingOrder", 9)).toEqual({ kind: "plain", text: "12" });
    expect(cellFor(state, "netInventory", 9)).toEqual({ kind: "net", text: `${MINUS}8`, step: "neg-1" });
    expect(cellFor(state, "netInventory", 8)).toEqual({ kind: "net", text: "0", step: "zero" });
    expect(cellFor(state, "position", 10)).toEqual({ kind: "plain", text: `${MINUS}2` });
    expect(cellFor(state, "order", 10)).toEqual({ kind: "plain", text: "8" });
    expect(cellFor(state, "cost", 10)).toEqual({ kind: "plain", text: "14" });
    expect(cellFor(state, "unitsShipped", 4)).toEqual({ kind: "plain", text: "4" });
    expect(cellFor(state, "supplyLine", 4)).toEqual({ kind: "plain", text: "12" });
  });

  it("writes nå from the open Week, with an empty dashed Din ordre", () => {
    expect(cellFor(state, "incomingOrder", 11)).toEqual({ kind: "plain", text: "10" });
    expect(cellFor(state, "netInventory", 11)).toEqual({ kind: "net", text: `${MINUS}20`, step: "neg-3" });
    expect(cellFor(state, "position", 11)).toEqual({ kind: "plain", text: `${MINUS}4` });
    expect(cellFor(state, "supplyLine", 11)).toEqual({ kind: "plain", text: "16" });
    expect(cellFor(state, "order", 11)).toEqual({ kind: "order-empty" });
    expect(cellFor(state, "cost", 11)).toEqual({ kind: "plain", text: "20" });
  });

  it("right of nå shows only the known arrivals, each in its Uke", () => {
    expect([12, 13, 14, 15].map((w) => cellFor(state, "incomingDelivery", w))).toEqual([
      { kind: "arrival", text: "4" },
      { kind: "arrival", text: "4" },
      { kind: "arrival", text: "8" },
      { kind: "empty" },
    ]);
    for (const row of ROWS.filter((r) => r.key !== "incomingDelivery")) {
      expect(cellFor(state, row.key, 12)).toEqual({ kind: "empty" });
    }
  });

  it("has the phone's rows, with Sendt and På vei for the laptop only", () => {
    expect(ROWS.filter((r) => !r.laptopOnly).map((r) => r.label)).toEqual([
      "Ordre inn",
      "Levering",
      "Netto lager",
      "Posisjon",
      "Din ordre",
      "Kost, kr",
    ]);
    expect(ROWS.map((r) => r.label)).toEqual([
      "Ordre inn",
      "Levering",
      "Sendt",
      "Netto lager",
      "På vei",
      "Posisjon",
      "Din ordre",
      "Kost, kr",
    ]);
  });
});

describe("graphSeries (Story 6.7)", () => {
  it("takes every value from the history and nå's fields, as the api gave them", () => {
    const series = graphSeries(state);
    expect(series.weeks.map((w) => w.week)).toEqual(Array.from({ length: 11 }, (_, i) => i + 1));
    const now = series.weeks[10]!;
    expect(now).toEqual({ week: 11, net: state.net_inventory, position: state.position, holding: 0, backorder: 20 });
    const first = state.history[0]!;
    expect(series.weeks[0]).toEqual({
      week: 1,
      net: first.net_inventory,
      position: first.position,
      holding: Number(first.holding_cost),
      backorder: Number(first.backorder_cost),
    });
    expect(series.rates).toEqual({ holding: "0,50", backorder: "1,00" });
    expect(series.highest).toBe(20);
    expect(series.highestBefore).toBe(14);
  });

  it("finds the costliest Uke over the whole game so far, not only the window", () => {
    const late = graphSeries(week30.seat_state as SeatState);
    expect(late.highest).toBe(56);
    expect(late.weeks).toHaveLength(30);
  });
});

describe("WeekTable rendered on the server with a fixed layout (the print page)", () => {
  const html = renderToStaticMarkup(<WeekTable state={state} fixed={{ labelWidth: 96, columnWidth: 28, fontSize: 13 }} />);

  it("draws both fields over the phone and laptop columns, with titles, in aria-hidden rows", () => {
    expect(html.match(/<svg[^>]*data-chart="net"/g)).toHaveLength(2);
    expect(html.match(/<svg[^>]*data-chart="cost"/g)).toHaveLength(2);
    expect(html.match(/<tr aria-hidden="true" data-field=/g)).toHaveLength(4);
    expect(html).toContain(`<title>${nb.games.play.graph.netSvg}</title>`);
    // Phone: Uke 4 … 15, so nå (11) is the 8th column; its centre at 7.5 × 28 px.
    expect(html).toMatch(/data-mark="now" data-week="11" cx="210"/);
    expect(html).toContain("Restordre 20");
    expect(html).toContain(`Posisjon ${MINUS}4`);
    expect(html).toContain("40 kr");
    expect(html).toContain("restordre 1,00");
    expect(html).toContain("lager 0,50");
  });

  it("greys every Uke number but nå (Issue #124)", () => {
    expect(html).toMatch(/data-col="11" data-now=""[^>]*font-bold text-ink/);
    expect(html).toMatch(/data-col="10"[^>]*font-normal text-ink-muted/);
    expect(html).toMatch(/data-col="12"[^>]*font-normal text-ink-muted/);
  });

  it("says so in the Uke the Kost per uke axis grows, and only then", () => {
    const grows = renderToStaticMarkup(<WeekTable state={week14.seat_state as SeatState} />);
    expect(html).not.toContain("Aksen går nå til");
    expect(grows).toContain(nb.games.play.graph.axisGrown("80"));
  });
});

describe("WeekTable in Uke 1 (no history)", () => {
  it("draws one point per line, one bar and the 40 kr axis, all at nå", () => {
    const html = renderToStaticMarkup(
      <WeekTable state={week1.seat_state as SeatState} fixed={{ labelWidth: 96, columnWidth: 28, fontSize: 13 }} />,
    );
    // Uke 1 … 5 are phone columns too: one field row each, no laptop variant.
    expect(html.match(/<tr aria-hidden="true" data-field=/g)).toHaveLength(2);
    expect(html).toContain('data-weeks="1" data-x="14"');
    expect(html.match(/data-mark="position"/g)).toHaveLength(1);
    expect(html.match(/data-mark="cost"/g)).toHaveLength(1);
    expect(html).toContain(">40 kr</text>");
    expect(html).toContain("Lager 12");
  });
});
