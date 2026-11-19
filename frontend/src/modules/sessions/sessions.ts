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

/** The Demand pattern in words: the step pattern as «4, så 8 fra Uke 5». */
export function demandText(demand: GameSettings["demand"]): string {
  if (demand.kind === "step") return copy.values.step(demand.start, demand.new_level, demand.change_week);
  return copy.values.otherDemand;
}

export type SettingRow = { key: string; label: string; value: string };

/** The settings list of the Klasseøkt, in the mockup's order, from the values the API returned. Each
 * row's `key` is the setting's api name (or `demand`, `inactivity_limit_hours`). */
export function settingRows(settings: GameSettings, inactivityLimitHours: number): SettingRow[] {
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
    { key: "guided_weeks", label: s.guidedWeeks, value: v.guidedWeeks(settings.guided_weeks) },
    { key: "max_order", label: s.maxOrder, value: formatNumber(settings.max_order) },
    { key: "inactivity_limit_hours", label: s.inactivityLimit, value: v.inactivityLimit(inactivityLimitHours) },
  ];
}

/** «Kjeden ved start» as text: the same values the diagram draws. */
export function chainText(settings: GameSettings): string {
  return copy.chain.text({
    roles: copy.chain.list(upstreamFirst(settings).map(roleName)),
    inventory: settings.starting_inventory,
    slot: settings.supply_line,
    shipping: settings.shipping_delay,
    production: settings.production_delay,
    order: settings.order_delay,
  });
}
