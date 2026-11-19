import { nb } from "@/copy/nb";

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

/** A decimal string from the API with a decimal comma («0.50» → «0,50»). The value is shown as the
 * API sent it; Story 5.3 brings the shared number formatter. */
export function decimalComma(value: string): string {
  return value.replace(".", ",");
}

/** The Demand pattern in words: the step pattern as «4, så 8 fra Uke 5». */
export function demandText(demand: GameSettings["demand"]): string {
  if (demand.kind === "step") return copy.values.step(demand.start, demand.new_level, demand.change_week);
  return copy.values.otherDemand;
}

/** The settings list of the Klasseøkt, in the mockup's order, from the values the API returned. */
export function settingRows(settings: GameSettings, inactivityLimitHours: number): { label: string; value: string }[] {
  const s = copy.settings;
  const v = copy.values;
  return [
    { label: s.startingInventory, value: String(settings.starting_inventory) },
    { label: s.supplyLine, value: v.units(settings.supply_line) },
    { label: s.orderDelay, value: v.weeks(settings.order_delay) },
    { label: s.shippingDelay, value: v.weeks(settings.shipping_delay) },
    { label: s.productionDelay, value: v.weeks(settings.production_delay) },
    { label: s.holdingCost, value: v.cost(decimalComma(settings.holding_cost)) },
    { label: s.backorderCost, value: v.cost(decimalComma(settings.backorder_cost)) },
    { label: s.weeks, value: String(settings.weeks) },
    { label: s.demand, value: demandText(settings.demand) },
    { label: s.guidedWeeks, value: v.guidedWeeks(settings.guided_weeks) },
    { label: s.inactivityLimit, value: v.inactivityLimit(inactivityLimitHours) },
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
