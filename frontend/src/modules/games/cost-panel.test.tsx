import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { formatNumber, MINUS } from "@/lib/number-format";
import demo from "@/modules/landing/demo-seat.json";

import type { SeatState } from "./api";
import { columnLines, costPanel } from "./cost-panel";
import { CostPanel } from "./cost-panel-view";
import week1 from "./fixtures/play-week-1.json";
import week3 from "./fixtures/play-week-3.json";
import week11 from "./fixtures/play-week-11.json";
import week14 from "./fixtures/play-week-14.json";
import week30 from "./fixtures/play-week-30.json";
import { ALL_ROWS, cellFor } from "./week-table";

const state11 = week11.seat_state as SeatState;
const state1 = week1.seat_state as SeatState;
const copy = nb.games.play.costPanel;
/** «40,00 kr» as the number formatter writes it (a no-break space before «kr»). */
const kr = (value: string) => formatNumber(value, { kroner: true });

describe("costPanel (Story 6.16)", () => {
  it("reads the running split, its shares and the Uke's sum from the api", () => {
    const model = costPanel(state11);
    expect(model.holding).toEqual({ label: "Lagerkostnad", amount: kr("40"), share: 40 / 82 });
    expect(model.backorder).toEqual({ label: "Restordrekostnad", amount: kr("42"), share: 42 / 82 });
    expect(model.total).toBe(kr("82"));
    expect(model.weekCost).toBe(`Denne uka: 20 restordre × 1,00 = ${kr("20")}`);
    expect(model.points.map((p) => p.week)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    expect(model.points.at(-1)).toEqual({ week: 11, holding: 40, backorder: 42 });
    expect(model.rows.at(-1)).toEqual({ week: 11, holding: "40,00", backorder: "42,00", total: "82,00" });
    expect(model.rows[0]).toEqual({ week: 1, holding: "6,00", backorder: "0,00", total: "6,00" });
  });

  it("has one Uke in Uke 1, and no bar while nothing is charged", () => {
    const model = costPanel(state1);
    expect(model.points).toEqual([{ week: 1, holding: 6, backorder: 0 }]);
    const nothing = { ...state1, total_cost: "0.00", total_holding_cost: "0.00", total_backorder_cost: "0.00" };
    expect(costPanel(nothing).holding.share).toBe(0);
    expect(costPanel(nothing).backorder.share).toBe(0);
  });
});

describe("columnLines (Alle rader)", () => {
  it("writes out the api's terms for column nå", () => {
    expect(columnLines(state11)).toEqual([
      { label: "Netto lager i kolonne 11", sum: `${MINUS}14 + 4 ${MINUS} 10 = ${MINUS}20` },
      { label: "Posisjon i kolonne 11", sum: `${MINUS}20 + 16 = ${MINUS}4` },
    ]);
  });

  it("leaves out the Netto lager line in Uke 1, where no column stands to the left", () => {
    expect(columnLines(state1)).toEqual([{ label: "Posisjon i kolonne 1", sum: "12 + 12 = 24" }]);
  });

  it("never shows a sum the api's numbers do not make (every fixture Uke)", () => {
    for (const fixture of [week3, week11, week14, week30, demo]) {
      const state = fixture.seat_state as SeatState;
      const before = state.history.at(-1)!;
      expect(before.net_inventory + state.incoming_delivery - state.incoming_order).toBe(state.net_inventory);
      expect(state.net_inventory + state.supply_line).toBe(state.position);
    }
  });
});

describe("the all-rows table", () => {
  it("adds Lager, Restordre and «Sum, kr» in the drawn order", () => {
    expect(ALL_ROWS.map((row) => row.label)).toEqual([
      "Ordre inn",
      "Levering",
      "Sendt",
      "Lager",
      "Restordre",
      "Netto lager",
      "På vei",
      "Posisjon",
      "Din ordre",
      "Kost per uke",
      "Sum, kr",
    ]);
    expect(ALL_ROWS.every((row) => !row.laptopOnly)).toBe(true);
    expect(cellFor(state11, "totalCost", 10)).toEqual({ kind: "plain", text: "62" });
    expect(cellFor(state11, "totalCost", 11)).toEqual({ kind: "plain", text: "82" });
    expect(cellFor(state11, "backlog", 11)).toEqual({ kind: "plain", text: "20" });
    expect(cellFor(state11, "inventory", 12)).toEqual({ kind: "empty" });
  });
});

describe("CostPanel rendered on the server", () => {
  it("shows the panel with a hidden chart and the «Vis som tabell» toggle", () => {
    const html = renderToStaticMarkup(<CostPanel state={state11} table="toggle" />);
    expect(html).toContain(copy.title);
    expect(html).toContain(kr("40"));
    expect(html).toContain(kr("82"));
    expect(html).toMatch(/<svg[^>]*data-chart="cost-area"[^>]*aria-hidden="true"/);
    expect(html).toContain(`<title>${copy.chartSvg}</title>`);
    expect(html).toContain(copy.showTable);
    expect(html).toContain(`Denne uka: 20 restordre × 1,00 = ${kr("20")}`);
    // Never another Seat, the chain or an Order to place.
    expect(html).not.toMatch(/Kjede|bestill|anbefal/i);
  });

  it("points to the «Sum, kr» row instead of a toggle inside Alle rader, and labels Demodata", () => {
    const html = renderToStaticMarkup(<CostPanel state={state11} table="sumRow" demoData="Demodata" />);
    expect(html).not.toContain(copy.showTable);
    expect(html).toContain(nb.games.play.allRows.sumRowNote);
    expect(html).toContain("Demodata");
  });
});
