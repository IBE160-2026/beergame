/** A stand-in answer of Debrief step 3 (Story 9.5), shaped like `07-debrief.png`: 36 Uker, the
 * Orders of each Role swinging more and later up the chain, a Grossist viewer. Week states are made
 * up but consistent per Uke; Forsterkning 1,8× to 7,6× as drawn. */
const ORDERS = {
  factory: [4, 4, 4, 4, 5, 4, 5, 4, 6, 5, 6, 6, 4, 5, 17, 23, 28, 31, 28, 26, 23, 21, 17, 9, 5, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  distributor: [4, 4, 4, 4, 6, 4, 4, 6, 5, 3, 2, 8, 20, 22, 22, 22, 17, 19, 20, 19, 15, 10, 9, 5, 4, 0, 0, 0, 0, 0, 0, 0, 0, 1, 4, 7],
  wholesaler: [4, 4, 4, 4, 4, 4, 4, 4, 4, 8, 24, 16, 16, 13, 12, 15, 14, 15, 8, 9, 10, 12, 8, 6, 6, 3, 3, 1, 2, 2, 3, 6, 7, 9, 9, 6],
  retailer: [4, 4, 4, 4, 4, 6, 10, 11, 10, 8, 11, 10, 10, 8, 11, 12, 9, 6, 9, 9, 10, 8, 8, 9, 9, 7, 6, 5, 5, 6, 6, 7, 8, 7, 8, 6],
} as const;
const ROLES = ["factory", "distributor", "wholesaler", "retailer"] as const;
const AMPLIFICATION = { factory: "7.600", distributor: "6.000", wholesaler: "4.100", retailer: "1.800" } as const;

/** Netto lager of Role `r` (0 = Fabrikk) in Uke `w`: dips deeper and later up the chain. */
function net(r: number, w: number): number {
  const depth = 8 + (3 - r) * 9;
  const centre = 12 + (3 - r) * 2;
  return Math.round(12 - depth * Math.exp(-(((w - centre) / 5) ** 2)));
}

export function chainAnswer({ capacity = null as Partial<Record<(typeof ROLES)[number], number>> | null } = {}) {
  return {
    own_role: "wholesaler",
    last_week: 36,
    large_order: 10,
    roles: ROLES.map((role, r) => {
      const orders = ORDERS[role];
      const incoming = r < 3 ? ORDERS[ROLES[r + 1]!] : orders.map((_, i) => (i < 4 ? 4 : 8));
      return {
        role,
        amplification: AMPLIFICATION[role],
        first_large_order_week: orders.findIndex((o) => o >= 10) + 1,
        capacity: capacity?.[role] ?? null,
        weeks: orders.map((order, i) => {
          const n = net(r, i + 1);
          // A capped Role holds stock and backlog together in its worst Uker (Story 6.22).
          const both = capacity?.[role] !== undefined && n < 0;
          return {
            week: i + 1,
            order,
            incoming_order: incoming[i]!,
            inventory: both ? 2 : Math.max(0, n),
            backlog: Math.max(0, -n),
            supply_line: 8 + ((i + r) % 5) * (r + 2),
          };
        }),
      };
    }),
  };
}

export const CHAIN = chainAnswer();
