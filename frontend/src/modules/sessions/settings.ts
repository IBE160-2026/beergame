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

export type DemandKind = GameSettings["demand"]["kind"];
/** The Demand patterns in the select's order (Story 5.4, FR-13). */
export const DEMAND_KINDS: readonly DemandKind[] = ["step", "fixed", "random", "step+noise"];

/** The Demand pattern's fields as typed (Story 5.4). Only the chosen kind's fields are sent; the
 * series of a fixed pattern is one text of whole numbers. */
export type DemandDraft = {
  kind: DemandKind;
  values: string;
  start: string;
  new_level: string;
  change_week: string;
  mean: string;
  spread: string;
  seed: string;
};

export type DemandFieldName = Exclude<keyof DemandDraft, "kind">;

type Role = GameSettings["roles"][number];

/** A shipping capacity as chosen (Story 5.15, cut list): off, or one Role or every Role capped at
 * `units` per Week, as typed. */
export type CapacityDraft = {
  on: boolean;
  scope: "all" | "one";
  role: Role;
  units: string;
  /** A stored map the switch cannot show (several Roles, not all alike, set through the api): sent
   * back as it was until the Lecturer changes the capacity, so another save never drops a cap. */
  kept?: Partial<Record<Role, number>>;
};

/** The fields as typed, Norwegian style («0,50»), with the Demand pattern and its seed, and the
 * capacity while `FEATURE_CAPACITY` is on (absent otherwise, so it is never sent). */
export type SettingsDraft = Record<SettingName, string> & { demand: DemandDraft; capacity?: CapacityDraft };

/** The Demand fields each kind shows, in order; `seed` only for the kinds that draw. */
export const DEMAND_FIELDS: Record<DemandKind, readonly DemandFieldName[]> = {
  fixed: ["values"],
  step: ["start", "new_level", "change_week"],
  random: ["mean", "spread", "seed"],
  "step+noise": ["start", "new_level", "change_week", "spread", "seed"],
};

function demandDraftOf(settings: GameSettings): DemandDraft {
  const d = settings.demand;
  const text = (value: number | undefined) => (value === undefined ? "" : String(value));
  return {
    kind: d.kind,
    values: d.kind === "fixed" ? d.values.join(" ") : "",
    start: text("start" in d ? d.start : undefined),
    new_level: text("new_level" in d ? d.new_level : undefined),
    change_week: text("change_week" in d ? d.change_week : undefined),
    mean: text("mean" in d ? d.mean : undefined),
    spread: text("spread" in d ? d.spread : undefined),
    seed: settings.demand_seed == null ? "" : String(settings.demand_seed),
  };
}

/** The capacity the api returned as a draft: every Role of the chain at one value is «Alle ledd»;
 * anything else opens as «Ett ledd» with the first capped Role, downstream first. Off by default,
 * on the Retailer. */
function capacityDraftOf(settings: GameSettings): CapacityDraft {
  const capacity = settings.capacity ?? {};
  const capped = settings.roles.filter((role) => capacity[role] !== undefined);
  if (capped.length === 0) return { on: false, scope: "all", role: settings.roles[0], units: "" };
  const values = new Set(capped.map((role) => capacity[role]));
  const all = capped.length === settings.roles.length && values.size === 1;
  const draft: CapacityDraft = { on: true, scope: all ? "all" : "one", role: capped[0], units: String(capacity[capped[0]]) };
  if (!all && capped.length > 1) draft.kept = { ...capacity };
  return draft;
}

/** The fields of the settings the api returned; the capacity only while `FEATURE_CAPACITY` is on. */
export function draftOf(settings: GameSettings, capacityEnabled = false): SettingsDraft {
  const draft = { demand: demandDraftOf(settings) } as SettingsDraft;
  if (capacityEnabled) draft.capacity = capacityDraftOf(settings);
  for (const field of EDITABLE) {
    const value = settings[field.name];
    draft[field.name] = field.kind === "cost" ? costText(String(value)) : String(value);
  }
  return draft;
}

/** Another pattern chosen: the level typed so far carries over between a step's start and a random
 * mean; every other field keeps what it held, and an empty one is for the Lecturer to fill. */
export function withKind(demand: DemandDraft, kind: DemandKind): DemandDraft {
  return {
    ...demand,
    kind,
    start: demand.start || demand.mean,
    mean: demand.mean || demand.start,
  };
}

/** A whole number as a number; anything else as typed, so the api names what is wrong. */
function whole(typed: string): number | string {
  const parsed = parseNumber(typed);
  return parsed !== null && /^-?\d+$/.test(parsed) ? Number(parsed) : typed;
}

/** The body's `demand` for the chosen kind. A fixed series is whole numbers separated by spaces,
 * semicolons or a comma before a space; «4,5» stays one value, so the api refuses the decimal
 * rather than reading two Weeks. */
export function demandBody(demand: DemandDraft): Record<string, unknown> {
  if (demand.kind === "fixed") {
    const values = demand.values.split(/[\s;]+|,(?=\s|$)/).filter(Boolean).map(whole);
    return { kind: "fixed", values };
  }
  const body: Record<string, unknown> = { kind: demand.kind };
  for (const name of DEMAND_FIELDS[demand.kind]) if (name !== "seed") body[name] = whole(demand[name]);
  return body;
}

/** The body's `capacity` (Story 5.15): null when off, else the units for the chosen Role or for every
 * Role of the chain, as `roles` names them. */
export function capacityBody(capacity: CapacityDraft, roles: readonly Role[]): Record<string, unknown> | null {
  if (!capacity.on) return null;
  if (capacity.kept) return { ...capacity.kept };
  const units = whole(capacity.units);
  const capped = capacity.scope === "all" ? roles : [capacity.role];
  return Object.fromEntries(capped.map((role) => [role, units]));
}

/** The body's `game_settings`: whole numbers as numbers, costs as decimal strings, and anything
 * that does not read as a number as it was typed, so the api names what is wrong. The Demand
 * pattern goes as `demand`; its seed only for a pattern that draws, so the server's seed stays. */
export function settingsBody(draft: SettingsDraft, roles: readonly Role[] = ALL_ROLES): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const field of EDITABLE) {
    const typed = draft[field.name];
    body[field.name] = field.kind === "whole" ? whole(typed) : (parseNumber(typed) ?? typed);
  }
  body.demand = demandBody(draft.demand);
  if (DEMAND_FIELDS[draft.demand.kind].includes("seed")) body.demand_seed = whole(draft.demand.seed);
  if (draft.capacity) body.capacity = capacityBody(draft.capacity, roles);
  return body;
}

/** The Classic chain, downstream first, for a body built without the session's own chain. */
const ALL_ROLES: readonly Role[] = ["retailer", "wholesaler", "distributor", "factory"];

/** The api's problem on the capacity (Story 5.15): `capacity` itself, else the first Role's. */
export function capacityProblem(problems: Readonly<Record<string, SettingProblem>>): SettingProblem | undefined {
  if (problems.capacity) return problems.capacity;
  const key = Object.keys(problems).find((name) => name.startsWith("capacity."));
  return key === undefined ? undefined : problems[key];
}

/** The api's key of a problem under a Demand field («demand.start», «demand_seed»). */
export function demandProblemKey(name: DemandFieldName): string {
  return name === "seed" ? "demand_seed" : `demand.${name}`;
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
      if (ranged) return e.demandChangeOutside(min, max);
      break;
    case "fixed_series_length":
      if (max !== null) return e.fixedLength(max);
      break;
    case "demand_seed_required":
      return e.seedRequired;
    case "not_editable":
      return e.notEditable;
    case "feature_disabled":
      return copy.edit.capacity.disabled;
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
    case "capacity_below_peak_demand":
      return w.capacity(n("capacity"), n("peak_demand"));
    default:
      return w.other;
  }
}

/** The warnings in words, by the setting they stand under. A capacity warning («capacity.retailer»)
 * stands under `capacity`, once per wording, so four Roles capped alike warn once. */
export function warningsBySetting(warnings: readonly SettingWarning[]): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const warning of warnings) {
    const key = warning.field.startsWith("capacity.") ? "capacity" : warning.field;
    const text = warningText(warning);
    const list = (result[key] ??= []);
    if (!list.includes(text)) list.push(text);
  }
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
