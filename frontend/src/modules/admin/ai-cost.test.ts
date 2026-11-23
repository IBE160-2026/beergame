import { describe, expect, it } from "vitest";

import { costPercent, costText, gameName, parseLimit } from "./ai-cost";

/** The text with every kind of space as a plain one (the formatter writes no-break spaces). */
const plain = (text: string) => text.replace(/\s/g, " ");

describe("«KI-kostnad per Klasseøkt»", () => {
  it("writes dollars with two decimals and cents with four", () => {
    expect(plain(costText("1234.50000000"))).toBe("1 234,50 USD");
    expect(plain(costText("0.12345678"))).toBe("0,1235 USD");
    expect(plain(costText("0.00000000"))).toBe("0,0000 USD");
  });

  it("reads a typed limit as the api's decimal string", () => {
    expect(parseLimit("12,50")).toBe("12.50");
    expect(parseLimit(" 20 ")).toBe("20");
    expect(parseLimit("1 000")).toBe("1000");
    expect(parseLimit("-3")).toBeNull();
    expect(parseLimit("tolv")).toBeNull();
    expect(parseLimit("")).toBeNull();
    expect(parseLimit("1,123456789")).toBeNull();
    expect(parseLimit("12345678901")).toBeNull();
  });

  it("names each Game line", () => {
    expect(gameName({ game_id: "g", number: 2 })).toBe("Spill 2");
    expect(gameName({ game_id: "g", number: null })).toBe("Annet spill");
    expect(gameName({ game_id: null, number: null })).toBe("Uten spill");
  });

  it("draws a bar against the largest value", () => {
    expect(costPercent("0.5", 1)).toBe("50%");
    expect(costPercent("2", 1)).toBe("100%");
    expect(costPercent("0", 1)).toBe("0%");
    expect(costPercent("1", 0)).toBe("0%");
  });
});
