import { describe, expect, it } from "vitest";

import { GROUP } from "@/lib/number-format";

import type { GameSettings } from "./api";
import {
  calibratedText,
  demandBody,
  demandProblemKey,
  draftOf,
  problemsOf,
  problemText,
  settingsBody,
  warningsBySetting,
  withKind,
} from "./settings";

/** Settings as the API sends them; a test fixture, not a copy of the Classic preset. */
const settings: GameSettings = {
  schema_version: 1,
  roles: ["retailer", "wholesaler", "distributor", "factory"],
  starting_inventory: 12,
  starting_backlog: 0,
  supply_line: 4,
  order_delay: 2,
  shipping_delay: 2,
  production_delay: 2,
  demand: { kind: "step", start: 4, new_level: 8, change_week: 5 },
  demand_seed: 42,
  holding_cost: "0.5",
  backorder_cost: "1.00",
  weeks: 36,
  guided_weeks: 4,
  max_order: 1999,
};

describe("the settings block (Story 5.3)", () => {
  it("fills the fields from the api, costs with two decimals and a comma", () => {
    const draft = draftOf(settings);
    expect(draft.holding_cost).toBe("0,50");
    expect(draft.backorder_cost).toBe("1,00");
    expect(draft.max_order).toBe("1999");
    expect(Object.keys(draft)).toHaveLength(12);
  });

  it("sends whole numbers as numbers, costs as decimal strings, other text as typed", () => {
    const body = settingsBody({
      ...draftOf(settings),
      weeks: " 40 ",
      max_order: "1 000",
      holding_cost: "0,75",
      order_delay: "2,5",
      backorder_cost: "mye",
      starting_backlog: "",
    });
    expect(body.weeks).toBe(40);
    expect(body.max_order).toBe(1000);
    expect(body.holding_cost).toBe("0.75");
    expect(body.order_delay).toBe("2,5");
    expect(body.backorder_cost).toBe("mye");
    expect(body.starting_backlog).toBe("");
  });

  it("words each error with the range the api sent", () => {
    const range = (code: string, minimum: string | null, maximum: string | null, places: number | null = null) =>
      problemText({ code, minimum, maximum, decimal_places: places });
    expect(range("out_of_range", "1", "3")).toBe("Må være fra 1 til 3.");
    expect(range("out_of_range", "1", "9999")).toBe(`Må være fra 1 til 9${GROUP}999.`);
    expect(range("not_a_number", "1", "100")).toBe("Skriv et helt tall fra 1 til 100.");
    expect(range("not_a_number", "0.00", "100.00", 2)).toBe("Skriv et beløp fra 0,00 til 100,00, med komma.");
    expect(range("too_many_decimal_places", "0.00", "100.00", 2)).toBe("Bruk høyst 2 desimaler, fra 0,00 til 100,00.");
    expect(range("guided_weeks_not_before_demand_change", "0", "4")).toContain("Velg fra 0 til 4.");
    expect(range("guided_weeks_leave_no_weeks_to_play", "0", "3")).toContain("Velg fra 0 til 3.");
    expect(range("starting_inventory_and_backlog", null, null)).toContain("både lager og restordre");
    expect(range("something_new", null, null)).toBe("Verdien er ikke tillatt.");
    expect(range("demand_change_week_outside_game", "1", "4")).toContain("fra 1 til 4");
    expect(range("fixed_series_length", "36", "36")).toBe("Skriv ett helt tall per uke, 36 tall i alt.");
    expect(range("demand_seed_required", null, null)).toBe("Skriv et frø, et helt tall.");
    expect(range("out_of_range", "0", "999999999")).toBe(`Må være fra 0 til 999${GROUP}999${GROUP}999.`);
    expect(range("not_editable", null, null)).toBe("Denne innstillingen kan ikke endres her.");
  });

  it("reads problems from the envelope's fields and skips what is not one", () => {
    const problem = {
      code: "out_of_range",
      minimum: "1",
      maximum: "3",
      decimal_places: null,
    };
    expect(problemsOf({ order_delay: problem, game_settings: "locked" })).toEqual({ order_delay: problem });
  });

  it("words each warning under its setting, starting with «Advarsel»", () => {
    const by = warningsBySetting([
      {
        code: "supply_line_differs_from_demand",
        field: "supply_line",
        values: { supply_line: "5", starting_demand: "4" },
      },
      {
        code: "backorder_not_above_holding",
        field: "backorder_cost",
        values: { backorder_cost: "0.5", holding_cost: "0.50" },
      },
      {
        code: "max_order_may_bind",
        field: "max_order",
        values: { max_order: "50", peak_demand: "8", threshold: "80" },
      },
      {
        code: "too_few_weeks_for_demand_change",
        field: "weeks",
        values: { arrival_week: "21", weeks: "20" },
      },
      {
        code: "capacity_below_peak_demand",
        field: "capacity.retailer",
        values: {},
      },
    ]);
    for (const lines of Object.values(by)) for (const line of lines) expect(line.startsWith("Advarsel:")).toBe(true);
    expect(by.backorder_cost[0]).toContain("Restordrekost (0,50) er ikke høyere enn Lagerkost (0,50)");
    expect(by.weeks[0]).toContain("Uke 21, etter siste uke (20)");
    expect(by.max_order[0]).toContain("under 80");
    expect(by.supply_line[0]).toContain("(4)");
  });

  it("names the calibrated settings from the api's values", () => {
    expect(calibratedText(settings)).toContain("Startlager 12, 4 i hvert ledd, forsinkelser 2, 2 og 2 uker");
    expect(calibratedText(settings)).toContain("Lagerkost 0,50, Restordrekost 1,00 og 36 uker");
  });
});

describe("the Demand pattern (Story 5.4)", () => {
  it("fills the pattern's fields and the seed from the api", () => {
    expect(draftOf(settings).demand).toEqual({
      kind: "step",
      values: "",
      start: "4",
      new_level: "8",
      change_week: "5",
      mean: "",
      spread: "",
      seed: "42",
    });
    const fixed = draftOf({ ...settings, demand: { kind: "fixed", values: [4, 4, 8] } }).demand;
    expect(fixed.values).toBe("4 4 8");
  });

  it("sends the chosen pattern's fields, and the seed only for a pattern that draws", () => {
    const draft = draftOf(settings);
    const step = settingsBody(draft);
    expect(step.demand).toEqual({ kind: "step", start: 4, new_level: 8, change_week: 5 });
    expect("demand_seed" in step).toBe(false);
    const random = settingsBody({ ...draft, demand: { ...withKind(draft.demand, "random"), spread: "2" } });
    // The step's start carries over as the mean; the seed drawn at creation is sent as it stands.
    expect(random.demand).toEqual({ kind: "random", mean: 4, spread: 2 });
    expect(random.demand_seed).toBe(42);
    const noise = settingsBody({ ...draft, demand: { ...withKind(draft.demand, "step+noise"), spread: "x", seed: "7" } });
    expect(noise.demand).toEqual({ kind: "step+noise", start: 4, new_level: 8, change_week: 5, spread: "x" });
    expect(noise.demand_seed).toBe(7);
  });

  it("reads a fixed series separated by spaces, commas or new lines, and sends other text as typed", () => {
    const base = withKind(draftOf(settings).demand, "fixed");
    expect(demandBody({ ...base, values: " 4, 4;8\n 12 " })).toEqual({ kind: "fixed", values: [4, 4, 8, 12] });
    expect(demandBody({ ...base, values: "4 fire" })).toEqual({ kind: "fixed", values: [4, "fire"] });
    // A decimal comma stays one value, for the api to refuse.
    expect(demandBody({ ...base, values: "4,5 4, 4," })).toEqual({ kind: "fixed", values: ["4,5", 4, 4] });
    expect(demandBody({ ...base, values: "" })).toEqual({ kind: "fixed", values: [] });
  });

  it("finds each field's error under the api's key", () => {
    expect(demandProblemKey("seed")).toBe("demand_seed");
    expect(demandProblemKey("spread")).toBe("demand.spread");
    expect(demandProblemKey("change_week")).toBe("demand.change_week");
  });
});
