import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { formatNumber, parseNumber } from "@/lib/number-format";

import type { GameSettings } from "./api";
import { costText } from "./sessions";

const copy = nb.sessions;

export type SettingProblem = components["schemas"]["SettingProblem"];
export type SettingWarning = components["schemas"]["SettingWarning"];

/** The Game settings a Lecturer changes on the Klasseøkt (Story 5.3, FR-12), in the list's order.
 * `kind` says how the field is shown and sent; which values are allowed is the api's alone. */
export const EDITABLE = [
  {
    name: "starting_inventory",
    kind: "whole",
    label: copy.settings.startingInventory,
    hint: copy.edit.perRole,
  },
  {
    name: "starting_backlog",
    kind: "whole",
    label: copy.settings.startingBacklog,
    hint: copy.edit.perRole,
  },
  { name: "supply_line", kind: "whole", label: copy.settings.supplyLine },
  { name: "order_delay", kind: "whole", label: copy.settings.orderDelay },
  { name: "shipping_delay", kind: "whole", label: copy.settings.shippingDelay },
  {
    name: "production_delay",
    kind: "whole",
    label: copy.settings.productionDelay,
  },
  {
    name: "holding_cost",
    kind: "cost",
    label: copy.settings.holdingCost,
    hint: copy.edit.costHint,
  },
  {
    name: "backorder_cost",
    kind: "cost",
    label: copy.settings.backorderCost,
    hint: copy.edit.costHint,
  },
  { name: "weeks", kind: "whole", label: copy.settings.weeks },
  {
    name: "guided_weeks",
    kind: "whole",
    label: copy.settings.guidedWeeks,
    hint: copy.edit.guidedHint,
  },
  { name: "max_order", kind: "whole", label: copy.settings.maxOrder },
] as const;

export type SettingName = (typeof EDITABLE)[number]["name"];
/** The fields as typed, Norwegian style («0,50»). */
export type SettingsDraft = Record<SettingName, string>;

/** The fields of the settings the api returned. */
export function draftOf(settings: GameSettings): SettingsDraft {
  const draft = {} as SettingsDraft;
  for (const field of EDITABLE) {
    const value = settings[field.name];
    draft[field.name] = field.kind === "cost" ? costText(String(value)) : String(value);
  }
  return draft;
}

/** The body's `game_settings`: whole numbers as numbers, costs as decimal strings, and anything
 * that does not read as a number as it was typed, so the api names what is wrong. */
export function settingsBody(draft: SettingsDraft): Record<SettingName, number | string> {
  const body = {} as Record<SettingName, number | string>;
  for (const field of EDITABLE) {
    const typed = draft[field.name];
    const parsed = parseNumber(typed);
    if (field.kind === "whole") {
      body[field.name] = parsed !== null && /^-?\d+$/.test(parsed) ? Number(parsed) : typed;
    } else {
      body[field.name] = parsed ?? typed;
    }
  }
  return body;
}

function isProblem(value: unknown): value is SettingProblem {
  return typeof value === "object" && value !== null && typeof (value as { code?: unknown }).code === "string";
}

/** The api's problems by setting, from a check answer or the `fields` of `invalid_settings`. */
export function problemsOf(fields: Readonly<Record<string, unknown>>): Record<string, SettingProblem> {
  const result: Record<string, SettingProblem> = {};
  for (const [name, value] of Object.entries(fields)) if (isProblem(value)) result[name] = value;
  return result;
}

/** The reason under a setting, in words, with the allowed range the api sent. */
export function problemText(problem: SettingProblem): string {
  const e = copy.edit.errors;
  const places = problem.decimal_places ?? undefined;
  const bound = (value: string | null) => (value === null ? null : formatNumber(value, { decimals: places }));
  const min = bound(problem.minimum);
  const max = bound(problem.maximum);
  const ranged = min !== null && max !== null;
  switch (problem.code) {
    case "starting_inventory_and_backlog":
      return e.inventoryAndBacklog;
    case "demand_change_week_outside_game":
      return e.demandChangeOutside;
    case "not_editable":
      return e.notEditable;
    case "guided_weeks_not_before_demand_change":
      if (ranged) return e.guidedBeforeChange(min, max);
      break;
    case "guided_weeks_leave_no_weeks_to_play":
      if (ranged) return e.guidedLeaveWeeks(min, max);
      break;
    case "not_a_number":
      if (ranged) return places !== undefined ? e.amount(min, max) : e.wholeNumber(min, max);
      break;
    case "too_many_decimal_places":
      if (ranged && places !== undefined) return e.decimals(places, min, max);
      break;
  }
  return ranged ? e.outOfRange(min, max) : e.other;
}

/** A warning in words, with the numbers the api sent, under its setting. */
export function warningText(warning: SettingWarning): string {
  const w = copy.edit.warnings;
  const v = warning.values;
  const n = (key: string) => formatNumber(v[key] ?? "");
  switch (warning.code) {
    case "supply_line_differs_from_demand":
      return w.supplyLine(n("supply_line"), n("starting_demand"));
    case "backorder_not_above_holding":
      return w.backorder(costText(v.backorder_cost ?? ""), costText(v.holding_cost ?? ""));
    case "max_order_may_bind":
      return w.maxOrder(n("max_order"), n("threshold"), n("peak_demand"));
    case "too_few_weeks_for_demand_change":
      return w.weeks(n("arrival_week"), n("weeks"));
    default:
      return w.other;
  }
}

/** The warnings in words, by the setting they stand under. */
export function warningsBySetting(warnings: readonly SettingWarning[]): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const warning of warnings) (result[warning.field] ??= []).push(warningText(warning));
  return result;
}

/** The line naming what content and Play guard were calibrated for, from the api's Classic. */
export function calibratedText(classic: GameSettings): string {
  return copy.edit.calibrated({
    inventory: formatNumber(classic.starting_inventory),
    slot: formatNumber(classic.supply_line),
    order: formatNumber(classic.order_delay),
    shipping: formatNumber(classic.shipping_delay),
    production: formatNumber(classic.production_delay),
    holding: costText(classic.holding_cost),
    backorder: costText(classic.backorder_cost),
    weeks: formatNumber(classic.weeks),
  });
}
