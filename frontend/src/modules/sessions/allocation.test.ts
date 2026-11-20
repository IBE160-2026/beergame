import { describe, expect, it } from "vitest";

import { gameLine, holderName, nextGame, ticks } from "./allocation";
import type { AllocationGame } from "./api";

const game: AllocationGame = {
  number: 17,
  seats: [
    { role: "factory", user_id: null, name: null },
    { role: "distributor", user_id: "c", name: null },
    { role: "wholesaler", user_id: "b", name: "Sara" },
    { role: "retailer", user_id: "a", name: "Ida" },
  ],
};

describe("the allocation preview (Story 5.8)", () => {
  it("reads a game's Seats from Detaljist to Fabrikk, naming empty and removed Seats", () => {
    expect(gameLine(game)).toBe(
      "Ida, Detaljist. Sara, Grossist. Ikke lenger i Klassen, Distributør. KI-spiller, Fabrikk.",
    );
    expect(holderName(game.seats[0])).toBe("KI-spiller");
  });

  it("ticks the first, selected and last game once each", () => {
    expect(ticks(60, 17)).toEqual([1, 17, 60]);
    expect(ticks(60, 1)).toEqual([1, 60]);
    expect(ticks(1, 1)).toEqual([1]);
    expect(ticks(0, 1)).toEqual([]);
    // Narrow columns: a number too close to the selected one gives way.
    expect(ticks(100, 99, 3)).toEqual([1, 99]);
    expect(ticks(100, 2, 3)).toEqual([2, 100]);
    expect(ticks(100, 50, 3)).toEqual([1, 50, 100]);
  });

  it("moves the selection with the arrow keys, Home and End, inside the games", () => {
    expect(nextGame("ArrowRight", 3, 5)).toBe(4);
    expect(nextGame("ArrowRight", 5, 5)).toBe(5);
    expect(nextGame("ArrowLeft", 1, 5)).toBe(1);
    expect(nextGame("Home", 4, 5)).toBe(1);
    expect(nextGame("End", 2, 5)).toBe(5);
    expect(nextGame("Enter", 2, 5)).toBeNull();
  });
});
