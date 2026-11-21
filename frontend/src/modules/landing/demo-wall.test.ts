import { describe, expect, it } from "vitest";

import { DEMO_WALL_GAMES, demoWallGroups } from "./demo-wall";

describe("the Landing's demo wall (Story 7.2, UX-DR70, UX-DR71)", () => {
  it("holds made-up games only: no finished game, so no Uke total, and no name", () => {
    expect(DEMO_WALL_GAMES.length).toBeGreaterThan(3);
    for (const game of DEMO_WALL_GAMES) {
      expect(["waiting", "running"]).toContain(game.status);
      expect(game.values.every(Number.isInteger)).toBe(true);
      expect(Object.keys(game).sort()).toEqual(["number", "status", "values"]);
    }
  });

  it("draws Venter before Pågår with «Spill n» rows and nothing but the game and its status", () => {
    const groups = demoWallGroups();
    expect(groups.map((group) => group.title)).toEqual(["Venter 2", "Pågår 6"]);
    const row = groups[0]!.rows[0]!;
    expect(row.label).toBe("Spill 2");
    expect(row.rowName).toBe("Spill 2, venter");
    expect(row.figure).toBeUndefined();
    expect(row.detail).toBeUndefined();
  });
});
