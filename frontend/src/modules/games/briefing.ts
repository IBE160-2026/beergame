import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { costText } from "@/modules/sessions/sessions";

import type { GameRules, MyGame } from "./api";

const copy = nb.games.briefing;

type Role = MyGame["role"];

/** The Role each Role orders from (the chain downstream first: Detaljist, Grossist, Distributør,
 * Fabrikk); Fabrikk orders from its own production. */
const SUPPLIER: Record<Exclude<Role, "factory">, keyof typeof copy.delays.supplier> = {
  retailer: "wholesaler",
  wholesaler: "distributor",
  distributor: "factory",
};

/** The delay lines for the Student's own Role, from the game's own settings (FR-84): never a
 * sum the web app worked out. */
export function delayLines(role: Role, rules: GameRules): string[] {
  const weeks = copy.delays.weeks;
  const first =
    role === "factory"
      ? [copy.delays.production(weeks(rules.order_delay), weeks(rules.production_delay))]
      : [
          copy.delays.order(weeks(rules.order_delay), copy.delays.supplier[SUPPLIER[role]]),
          copy.delays.shipping(weeks(rules.shipping_delay)),
        ];
  const earliest = role === "factory" ? copy.delays.earliestFactory : copy.delays.earliest;
  return [...first, earliest, copy.delays.onTheWay];
}

/** The Veiledede uker line: how many, or that there are none. */
export function guidedLine(rules: Pick<GameRules, "guided_weeks">): string {
  return rules.guided_weeks > 0 ? copy.guided.some(rules.guided_weeks) : copy.guided.none;
}

/** The two cost rates as the screen writes them («0,50», «1,00»). */
export function ratesLine(rules: Pick<GameRules, "holding_cost" | "backorder_cost">): string {
  return copy.goal.rates(costText(rules.holding_cost), costText(rules.backorder_cost));
}

/**
 * The worked Uke (Demodata, UX-DR70): the spine's Uke 11 of a Grossist (EXPERIENCE.md, mockup
 * `09`), the same column the Startoppgave shows. Invented and fixed; each number is written here
 * once, and the lines take theirs from it. They obey the engine's Week rule (rules v1): on hand =
 * Lager before + Levering; to ship = Ordre inn + Restordre before; Sendt = the smaller;
 * `briefing.test.ts` holds them to it.
 */
export const EXAMPLE = {
  inventoryBefore: 0,
  backlogBefore: 9,
  onHand: 4,
  owed: 17,
  shipped: 4,
  inventoryAfter: 0,
  backlogAfter: 13,
  rows: {
    incomingOrder: 8,
    incomingDelivery: 4,
    unitsShipped: 4,
    inventory: 0,
    backlog: 13,
    netInventory: -13,
    supplyLine: 16,
  },
} as const;

export type ExampleRow = keyof typeof EXAMPLE.rows;

/** The worked Uke's rows, top to bottom: the term, the number and what it means. */
export function exampleRows(): { key: ExampleRow; term: string; value: string; meaning: string }[] {
  return (Object.keys(EXAMPLE.rows) as ExampleRow[]).map((key) => ({
    key,
    term: nb.terms[key],
    value: formatNumber(EXAMPLE.rows[key]),
    meaning: copy.example.rows[key](EXAMPLE),
  }));
}

/** The worked Uke's cost line: its Restordre at the game's own rate, with no product worked out. */
export function exampleCostLine(rules: Pick<GameRules, "backorder_cost">): string {
  return copy.example.cost(EXAMPLE.rows.backlog, EXAMPLE.rows.inventory, costText(rules.backorder_cost));
}
