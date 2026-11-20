import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { GameSettings } from "./api";

const copy = nb.sessions;

type Role = GameSettings["roles"][number];

const ROLE_NAMES: Record<Role, string> = {
  retailer: nb.terms.retailer,
  wholesaler: nb.terms.wholesaler,
  distributor: nb.terms.distributor,
  factory: nb.terms.factory,
};

/** The Role's name in the UI («Detaljist»). */
export function roleName(role: Role): string {
  return ROLE_NAMES[role];
}

/** The chain as «Kjeden ved start» draws it: upstream on the left, so the API's order (downstream
 * first) reversed. */
export function upstreamFirst(settings: Pick<GameSettings, "roles">): Role[] {
  return [...settings.roles].reverse();
}

/** A cost rate from the API («0.5») as the screen shows it: two decimals and a comma («0,50»). */
export function costText(value: string): string {
  return formatNumber(value, { decimals: 2 });
}

/** The Demand pattern in words: the step pattern as «4, så 8 fra Uke 5» (Story 5.4 words the rest). */
export function demandText(demand: GameSettings["demand"]): string {
  const v = copy.values;
  switch (demand.kind) {
    case "step":
      return v.step(demand.start, demand.new_level, demand.change_week);
    case "step+noise":
      return v.stepNoise(demand.start, demand.new_level, demand.change_week, demand.spread);
    case "random":
      return v.random(demand.mean, demand.spread);
    case "fixed":
      return v.fixed(demand.values.length);
  }
}

/** The demand in two short lines under «Kundene» in «Kjeden ved start» (mockup 03, Issue #98). */
export function customerLines(demand: GameSettings["demand"]): readonly [string, string] {
  const c = copy.chain.customerLines;
  switch (demand.kind) {
    case "step":
      return c.step(demand.start, demand.new_level, demand.change_week);
    case "step+noise":
      return c.stepNoise(demand.start, demand.new_level, demand.change_week, demand.spread);
    case "random":
      return c.random(demand.mean, demand.spread);
    case "fixed":
      return c.fixed(demand.values.length);
  }
}

export type SettingRow = { key: string; label: string; value: string };

/** The capped Roles with their capacity, Fabrikk first as the chain is drawn: the one Seat order
 * everywhere (Story 5.15, GitHub issue 115). */
export function cappedRoles(settings: GameSettings): [Role, number][] {
  const capacity = settings.capacity ?? {};
  return upstreamFirst(settings).flatMap((role) => {
    const units = capacity[role];
    return units === undefined ? [] : [[role, units] as [Role, number]];
  });
}

/** The capacity in words for the settings list: «Ingen», «6 per uke for alle ledd» or «6 per uke for
 * Detaljist». */
export function capacityText(settings: GameSettings): string {
  const v = copy.values;
  const capped = cappedRoles(settings);
  if (capped.length === 0) return v.capacityNone;
  const values = new Set(capped.map(([, units]) => units));
  if (capped.length === settings.roles.length && values.size === 1) return v.capacityAll(capped[0][1]);
  return capped.map(([role, units]) => v.capacityRoles(formatNumber(units), roleName(role))).join("; ");
}

/** Information visibility in words for the settings list (Story 5.16): «Av», one view, or both. */
export function infoVisibilityText(settings: GameSettings): string {
  const v = copy.values;
  const { upstream: up, downstream: down } = settings.info_visibility;
  if (up && down) return v.infoVisibilityBoth;
  if (up) return v.infoVisibilityUpstream;
  if (down) return v.infoVisibilityDownstream;
  return v.infoVisibilityNone;
}

/** The settings list of the Klasseøkt, in the mockup's order, from the values the API returned. Each
 * row's `key` is the setting's api name (or `demand`, `inactivity_limit_hours`). The capacity row
 * shows only while `FEATURE_CAPACITY` is on (Story 5.15), the Information visibility row only while
 * `FEATURE_INFO_VISIBILITY` is on (Story 5.16). */
export function settingRows(
  settings: GameSettings,
  inactivityLimitHours: number,
  capacityEnabled = false,
  infoVisibilityEnabled = false,
): SettingRow[] {
  const s = copy.settings;
  const v = copy.values;
  return [
    { key: "starting_inventory", label: s.startingInventory, value: formatNumber(settings.starting_inventory) },
    { key: "starting_backlog", label: s.startingBacklog, value: formatNumber(settings.starting_backlog) },
    { key: "supply_line", label: s.supplyLine, value: v.units(settings.supply_line) },
    { key: "order_delay", label: s.orderDelay, value: v.weeks(settings.order_delay) },
    { key: "shipping_delay", label: s.shippingDelay, value: v.weeks(settings.shipping_delay) },
    { key: "production_delay", label: s.productionDelay, value: v.weeks(settings.production_delay) },
    { key: "holding_cost", label: s.holdingCost, value: v.cost(costText(settings.holding_cost)) },
    { key: "backorder_cost", label: s.backorderCost, value: v.cost(costText(settings.backorder_cost)) },
    { key: "weeks", label: s.weeks, value: formatNumber(settings.weeks) },
    { key: "demand", label: s.demand, value: demandText(settings.demand) },
    // The seed of a pattern that draws: the same seed gives the same series (Story 5.4).
    ...(settings.demand.kind === "random" || settings.demand.kind === "step+noise"
      ? [{ key: "demand_seed", label: s.seed, value: String(settings.demand_seed ?? "") }]
      : []),
    { key: "guided_weeks", label: s.guidedWeeks, value: v.guidedWeeks(settings.guided_weeks) },
    { key: "max_order", label: s.maxOrder, value: formatNumber(settings.max_order) },
    ...(capacityEnabled ? [{ key: "capacity", label: s.capacity, value: capacityText(settings) }] : []),
    ...(infoVisibilityEnabled
      ? [{ key: "info_visibility", label: s.infoVisibility, value: infoVisibilityText(settings) }]
      : []),
    { key: "inactivity_limit_hours", label: s.inactivityLimit, value: v.inactivityLimit(inactivityLimitHours) },
  ];
}

/** «Kjeden ved start» as text: the same values the diagram draws, and a sentence per capped Role
 * while `FEATURE_CAPACITY` is on (Story 5.15). */
export function chainText(settings: GameSettings, capacityEnabled = false): string {
  const capped = capacityEnabled
    ? upstreamFirst(settings)
        .filter((role) => settings.capacity?.[role] !== undefined)
        .map((role) => " " + copy.chain.cappedText(roleName(role), settings.capacity?.[role] ?? 0))
        .join("")
    : "";
  return chainSentences(settings) + capped;
}

function chainSentences(settings: GameSettings): string {
  return copy.chain.text({
    roles: copy.chain.list(upstreamFirst(settings).map(roleName)),
    inventory: settings.starting_inventory,
    slot: settings.supply_line,
    shipping: settings.shipping_delay,
    production: settings.production_delay,
    order: settings.order_delay,
    demand: demandText(settings.demand),
  });
}
