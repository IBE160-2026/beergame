import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { demandText, hiddenLine, type ReplayTemplate, scenarioRows } from "./replay-scenario";

const copy = nb.sessions.replay;

/** The Classic default as the api derives it (Story 10.1). */
const CLASSIC: ReplayTemplate = {
  schema_version: 1,
  roles: ["retailer", "wholesaler", "distributor", "factory"],
  starting_inventory: 12,
  starting_backlog: 0,
  supply_line: 4,
  order_delay: 2,
  shipping_delay: 2,
  production_delay: 2,
  demand: { kind: "step", start: 4, new_level: 8, change_week: { minimum: 5, maximum: 12 }, spread: 2 },
  holding_cost: "0.50",
  backorder_cost: "1.00",
  weeks: { minimum: 30, maximum: 40 },
  guided_weeks: 0,
  max_order: 999,
  info_visibility: { upstream: false, downstream: false },
};

describe("the Replay scenario in words", () => {
  it("lists the Classic default with its ranges", () => {
    expect(scenarioRows(CLASSIC)).toEqual([
      { label: copy.demand, value: "4, deretter 8, ± 2 hver uke" },
      { label: copy.changeWeek, value: "Uke 5 til 12" },
      { label: copy.weeks, value: "30 til 40" },
      { label: copy.guidedWeeks, value: copy.none },
      { label: copy.rest, value: copy.restValue },
    ]);
    expect(hiddenLine(CLASSIC)).toBe(copy.hiddenBoth);
  });

  it("has no change Week for random demand or a fixed series", () => {
    const random = { ...CLASSIC, demand: { kind: "random" as const, mean: 5, spread: 3 } };
    expect(demandText(random)).toBe("Rundt 5, ± 3 hver uke");
    expect(scenarioRows(random).map((row) => row.label)).not.toContain(copy.changeWeek);
    expect(hiddenLine(random)).toBe(copy.hiddenWeeks);
    const fixed = { ...CLASSIC, demand: { kind: "fixed" as const, values: [4, 8], spread: 2 } };
    expect(demandText(fixed)).toBe(copy.spread(copy.fixedDemand, 2));
  });

  it("shows single values and no variation as they are", () => {
    const exact = {
      ...CLASSIC,
      weeks: 36,
      guided_weeks: 4,
      demand: { kind: "step" as const, start: 4, new_level: 8, change_week: 5, spread: 0 },
    };
    expect(scenarioRows(exact).map((row) => row.value)).toEqual([
      "4, deretter 8",
      "Uke 5",
      "36",
      "4",
      copy.restValue,
    ]);
    expect(hiddenLine(exact)).toBe(copy.hiddenNone);
    expect(scenarioRows({ ...exact, weeks: { minimum: 32, maximum: 32 } })[2].value).toBe("32");
    expect(scenarioRows({ ...exact, guided_weeks: { minimum: 0, maximum: 0 } })[3].value).toBe(copy.none);
  });
});
