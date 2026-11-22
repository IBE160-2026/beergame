import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameSettings } from "./api";
import {
  demandText,
  hiddenLine,
  ownHiddenLine,
  ownRows,
  replayDraftOfSettings,
  replayDraftOfTemplate,
  type ReplayTemplate,
  replayTemplateBody,
  replayWarningText,
  scenarioRows,
} from "./replay-scenario";

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

/** The Classic Game settings as the api sends them. */
const SETTINGS = {
  schema_version: 2,
  roles: ["retailer", "wholesaler", "distributor", "factory"],
  starting_inventory: 12,
  starting_backlog: 0,
  supply_line: 4,
  order_delay: 2,
  shipping_delay: 2,
  production_delay: 2,
  demand: { kind: "step", start: 4, new_level: 8, change_week: 5 },
  demand_seed: 77,
  holding_cost: "0.50",
  backorder_cost: "1.00",
  weeks: 36,
  guided_weeks: 4,
  max_order: 999,
  info_visibility: { upstream: false, downstream: false },
} as unknown as GameSettings;

describe("an own Replay scenario (Story 10.2)", () => {
  it("opens on the Class game's settings and sends them as fixed values, with no seed", () => {
    const draft = replayDraftOfSettings(SETTINGS);
    expect(draft.weeksTo).toBe("");
    expect(replayTemplateBody(draft)).toEqual({
      starting_inventory: 12,
      starting_backlog: 0,
      supply_line: 4,
      order_delay: 2,
      shipping_delay: 2,
      production_delay: 2,
      holding_cost: "0.50",
      backorder_cost: "1.00",
      weeks: 36,
      guided_weeks: 4,
      max_order: 999,
      demand: { kind: "step", start: 4, new_level: 8, change_week: 5, spread: 0 },
    });
  });

  it("sends a range when a different highest value is typed, and keeps what is not a number", () => {
    const draft = replayDraftOfSettings(SETTINGS);
    const ranged = { ...draft, weeks: "30", weeksTo: "40", changeWeekTo: "12" };
    const body = replayTemplateBody(ranged);
    expect(body.weeks).toEqual({ minimum: 30, maximum: 40 });
    expect((body.demand as { change_week: unknown }).change_week).toEqual({ minimum: 5, maximum: 12 });
    expect(replayTemplateBody({ ...draft, weeksTo: "36" }).weeks).toBe(36);
    expect(replayTemplateBody({ ...draft, weeks: "abc", weeksTo: "40" }).weeks).toEqual({ minimum: "abc", maximum: 40 });
  });

  it("maps the step with variation, random and fixed patterns to the template's kinds", () => {
    const draft = replayDraftOfSettings(SETTINGS);
    const noisy = { ...draft, demand: { ...draft.demand, kind: "step+noise" as const, spread: "3" } };
    expect(replayTemplateBody(noisy).demand).toEqual({ kind: "step", start: 4, new_level: 8, change_week: 5, spread: 3 });
    const random = { ...draft, demand: { ...draft.demand, kind: "random" as const, mean: "6", spread: "2" } };
    expect(replayTemplateBody(random).demand).toEqual({ kind: "random", mean: 6, spread: 2 });
    const fixed = { ...draft, demand: { ...draft.demand, kind: "fixed" as const, values: "4 8" } };
    expect(replayTemplateBody(fixed).demand).toEqual({ kind: "fixed", values: [4, 8], spread: 0 });
  });

  it("opens a stored own template with its ranges and sends it back unchanged", () => {
    const own: ReplayTemplate = {
      ...CLASSIC,
      demand: { kind: "step", start: 4, new_level: 12, change_week: { minimum: 6, maximum: 10 }, spread: 3 },
    };
    const draft = replayDraftOfTemplate(own);
    expect([draft.weeks, draft.weeksTo, draft.demand.kind, draft.changeWeekTo]).toEqual(["30", "40", "step+noise", "10"]);
    const { roles: _roles, info_visibility: _views, schema_version: _version, ...fields } = own;
    expect(replayTemplateBody(draft)).toEqual(fields);
  });

  it("lists every setting of an own scenario, and says what every Student shares", () => {
    const exact: ReplayTemplate = { ...CLASSIC, weeks: 36, demand: { ...CLASSIC.demand, change_week: 5, spread: 0 } as ReplayTemplate["demand"] };
    const rows = ownRows(exact);
    expect(rows.map((row) => row.key)).toContain("order_delay");
    expect(rows.find((row) => row.key === "holding_cost")?.value).toBe("0,50");
    expect(rows.at(-1)).toEqual({ key: "demand.change_week", label: copy.changeWeek, value: "Uke 5" });
    expect(ownHiddenLine(exact)).toBe(copy.hiddenOwnNone);
    expect(ownHiddenLine({ ...exact, demand: { ...exact.demand, spread: 2 } as ReplayTemplate["demand"] })).toBe(copy.hiddenOwnNoise);
    expect(ownHiddenLine(CLASSIC)).toBe(copy.hiddenBoth);
    expect(ownHiddenLine({ ...CLASSIC, weeks: 36 })).toBe(copy.hiddenChange);
  });

  it("words each warning with the change, the Class game's value and why", () => {
    const text = replayWarningText({ code: "replay_delay_shorter", field: "order_delay", values: { replay: "1", class_game: "2" } });
    expect(text).toBe(`${copy.warnings.delay(nb.sessions.settings.orderDelay, "1", "2")} ${copy.warnings.easier}`);
    expect(replayWarningText({ code: "replay_demand_no_change", field: "demand", values: {} })).toContain(copy.warnings.noChange);
    expect(replayWarningText({ code: "replay_guided_weeks", field: "guided_weeks", values: { replay: "4", class_game: "4" } })).toContain("opptil 4");
    expect(replayWarningText({ code: "x", field: "y", values: {} })).toBe(`${copy.warnings.other} ${copy.warnings.easier}`);
  });
});
