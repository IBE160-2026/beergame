import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { Plenary } from "./plenary-api";
import { hasWeeks, plenaryGroups, plenaryOrders, plenaryTableRows } from "./plenary";

const ROLES = ["retailer", "wholesaler", "distributor", "factory"] as const;

function plenary(weeks = 3): Plenary {
  return {
    weeks,
    roles: ROLES.map((role, r) => ({
      role,
      games: [
        { number: 2, net: [r + 1, -(r + 1), 4].slice(0, weeks), orders: [4, 8, 12].slice(0, weeks) },
        { number: 5, net: [], orders: Array.from({ length: weeks }, () => null) },
      ],
    })),
  };
}

describe("«Alle spill i plenum»", () => {
  it("draws one group of the Role's games in the api's game-number order, keyed by number", () => {
    const [group] = plenaryGroups(plenary(), "factory");
    expect(group.title).toBe(nb.plenary.group(2));
    expect(group.rows.map((row) => [row.id, row.label, row.values])).toEqual([
      ["2", "Spill 2", [4, -4, 4]],
      ["5", "Spill 5", []],
    ]);
    // Nothing beside the cells: no figure, status, wait, link or tint.
    for (const row of group.rows) {
      expect(Object.keys(row).sort()).toEqual(["id", "label", "rowName", "values"]);
    }
  });

  it("gives the table the same rows with nothing to sort by", () => {
    const rows = plenaryTableRows(plenary(), "retailer");
    expect(rows.map((row) => [row.id, row.values, row.cells, row.keys])).toEqual([
      ["2", [1, -1, 4], {}, {}],
      ["5", [], {}, {}],
    ]);
  });

  it("hands 14.5's Orders charts every game with no game marked", () => {
    const orders = plenaryOrders(plenary());
    expect(orders.weeks).toBe(3);
    expect(orders.roles.map((role) => role.role)).toEqual([...ROLES]);
    expect(orders.roles[0].games).toEqual([
      { number: 2, own: false, orders: [4, 8, 12] },
      { number: 5, own: false, orders: [null, null, null] },
    ]);
  });

  it("has nothing to show before any game has an opened Uke", () => {
    expect(hasWeeks(plenary(0))).toBe(false);
    expect(hasWeeks(plenary())).toBe(true);
  });
});
