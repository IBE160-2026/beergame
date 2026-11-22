import { describe, expect, it } from "vitest";

import { cellText, isInteractive, numberValue, parseCell, sameValue, tableValues, withCell } from "./interactive";

const TABLE = { prompt: "", hint: null, caption: "", rows: ["Uke 1", "Uke 2"], columns: [], asked_label: "Lager", negative: false };
const COLUMN = { prompt: "", hint: null, caption: "", rows: [], asked_label: "Legg til", negative: false, starting_task: false };

describe("Interactive items (Story 11.5)", () => {
  it("reads a cell as a whole number, nothing or text that is never sent", () => {
    expect(parseCell("14", false)).toEqual({ kind: "value", value: 14 });
    expect(parseCell(" 7 ", false)).toEqual({ kind: "value", value: 7 });
    expect(parseCell("", false)).toEqual({ kind: "empty" });
    expect(parseCell("  ", true)).toEqual({ kind: "empty" });
    for (const text of ["1,5", "1.5", "abc", "12a", "1 000 000 1"]) {
      expect(parseCell(text, true)).toEqual({ kind: "invalid" });
    }
    // A leading minus only where the item takes negative quantities.
    expect(parseCell("-3", false)).toEqual({ kind: "invalid" });
    expect(parseCell("−3", true)).toEqual({ kind: "value", value: -3 });
    expect(parseCell("-0", false)).toEqual({ kind: "value", value: 0 });
  });

  it("holds one value or null per row, whatever was stored", () => {
    expect(tableValues([8, null, 9], 3)).toEqual([8, null, 9]);
    expect(tableValues(null, 2)).toEqual([null, null]);
    expect(tableValues("a", 2)).toEqual([null, null]);
    expect(tableValues([8], 3)).toEqual([8, null, null]);
    expect(withCell([8, null, 9], 1, 4)).toEqual([8, 4, 9]);
    expect(withCell([8, 4, 9], 0, null)).toEqual([null, 4, 9]);
    expect(numberValue(16)).toBe(16);
    expect(numberValue([16])).toBeNull();
    expect(cellText(-3)).toBe("-3");
    expect(cellText(null)).toBe("");
    expect(sameValue([8, null], [8, null])).toBe(true);
    expect(sameValue([8, null], [8, 0])).toBe(false);
  });

  it("introduces a table item and a number item of its own, not a Starting task item", () => {
    expect(isInteractive({ type: "table", table: TABLE, column: null })).toBe(true);
    expect(isInteractive({ type: "table", table: null, column: null })).toBe(false);
    expect(isInteractive({ type: "number", table: null, column: COLUMN })).toBe(true);
    expect(isInteractive({ type: "number", table: null, column: { ...COLUMN, starting_task: true } })).toBe(false);
    expect(isInteractive({ type: "choice", table: null, column: null })).toBe(false);
  });
});
