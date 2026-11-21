import { describe, expect, it } from "vitest";

import type { GameResult } from "./api";
import result from "./fixtures/result-classic.json";
import { gameEnd } from "./result";

const classic = result as GameResult;
/** The formatter's narrow spaces as plain ones, so the expectations read as the screen does. */
const plain = (value: unknown): unknown => JSON.parse(JSON.stringify(value).replace(/[  ]/g, " "));

describe("gameEnd (Story 6.18)", () => {
  it("formats the chain total and keeps the Roles in the api's order, Detaljist to Fabrikk", () => {
    const model = gameEnd(classic, "wholesaler");
    expect(plain(model.total)).toBe("2 266,00 kr");
    expect(model.rows.map((row) => row.label)).toEqual(["Detaljist", "Grossist (deg)", "Distributør", "Fabrikk"]);
    expect(model.rows.map((row) => row.own)).toEqual([false, true, false, false]);
    expect(model.rows[1]).toMatchObject({ holding: "154,50", backorder: "399,00", total: "553,50" });
    expect(plain(model.chain)).toEqual({ holding: "901,00", backorder: "1 365,00", total: "2 266,00" });
  });

  it("never sorts by cost: a cheaper Role after a dearer one stays where it is", () => {
    const model = gameEnd(classic, "retailer");
    // Distributør (691,00) stands before Fabrikk (679,50), as in the chain.
    expect(model.rows.map((row) => row.role)).toEqual(["retailer", "wholesaler", "distributor", "factory"]);
  });

  it("sizes each split bar against the widest Role, holding then backlog", () => {
    const model = gameEnd(classic, "wholesaler");
    const widest = model.rows.find((row) => row.role === "distributor")!;
    expect(widest.bar.holding + widest.bar.backorder).toBeCloseTo(1);
    const retailer = model.rows[0]!;
    expect(retailer.bar.holding).toBeCloseTo(95 / 691);
    expect(retailer.bar.backorder).toBeCloseTo(247 / 691);
  });

  it("gives the chart and its table every Uke, and labels the final values", () => {
    const model = gameEnd(classic, "wholesaler");
    expect(model.points).toHaveLength(36);
    expect(model.points.at(-1)).toEqual({ week: 36, holding: 901, backorder: 1365 });
    expect(plain(model.weeks.at(-1))).toEqual({ week: 36, holding: "901,00", backorder: "1 365,00", total: "2 266,00" });
    expect(plain(model.endLabels)).toEqual({ holding: "Lager 901,00", backorder: "Restordre 1 365,00" });
  });

  it("draws no bar for a game that cost nothing", () => {
    const zero = "0.0000";
    const empty: GameResult = {
      roles: classic.roles.map((row) => ({ ...row, holding_cost: zero, backorder_cost: zero, total_cost: zero })),
      chain: { holding_cost: zero, backorder_cost: zero, total_cost: zero },
      weeks: [{ week: 1, holding_cost: zero, backorder_cost: zero, total_cost: zero }],
    };
    const model = gameEnd(empty, "factory");
    expect(plain(model.total)).toBe("0,00 kr");
    expect(model.rows.every((row) => row.bar.holding === 0 && row.bar.backorder === 0)).toBe(true);
  });
});
