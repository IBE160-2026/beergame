import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import {
  cellText,
  graphDomain,
  isInteractive,
  numberValue,
  parseCell,
  pointValue,
  sameValue,
  startValue,
  stepValue,
  tableValues,
  withCell,
} from "./interactive";

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

describe("Drawn items (Story 11.14)", () => {
  const AXIS = { min: 0, max: 40 };

  it("is an Interactive item with its table", () => {
    expect(isInteractive({ type: "drawn", table: { ...TABLE, axis: AXIS }, column: null })).toBe(true);
    expect(isInteractive({ type: "drawn", table: null, column: null })).toBe(false);
  });

  it("shows the axis, widened to hold every answered value", () => {
    expect(graphDomain(AXIS, [null, 12, null])).toEqual([0, 40]);
    expect(graphDomain(AXIS, [60, null, -5])).toEqual([-5, 60]);
    expect(graphDomain(AXIS, [])).toEqual([0, 40]);
  });

  it("starts an unanswered point at the nearest answered Uke before it, else 0", () => {
    expect(startValue([null, 12, null, null], 3, [0, 40])).toBe(12);
    expect(startValue([null, 12], 0, [0, 40])).toBe(0);
    expect(startValue([null], 0, [5, 40])).toBe(5);
  });

  it("moves by 1 and 10 and to the ends, inside the range", () => {
    expect(stepValue("ArrowUp", 14, [0, 40])).toBe(15);
    expect(stepValue("ArrowDown", 14, [0, 40])).toBe(13);
    expect(stepValue("PageUp", 35, [0, 40])).toBe(40);
    expect(stepValue("PageDown", 4, [0, 40])).toBe(0);
    expect(stepValue("Home", 14, [0, 40])).toBe(0);
    expect(stepValue("End", 14, [0, 40])).toBe(40);
    // Right and Left as on any slider.
    expect(stepValue("ArrowRight", 14, [0, 40])).toBe(15);
    expect(stepValue("ArrowLeft", 14, [0, 40])).toBe(13);
    expect(stepValue("Tab", 14, [0, 40])).toBeNull();
  });

  it("reads a value as a slider says it: «Uke 3: 14 enheter», «1 enhet»", () => {
    const drawn = nb.tests.individual.drawn;
    expect(drawn.valueText("Uke 3", "14", 14)).toBe("Uke 3: 14 enheter");
    expect(drawn.valueText("Uke 1", "1", 1)).toBe("Uke 1: 1 enhet");
    expect(drawn.valueText("Uke 1", "0", 0)).toBe("Uke 1: 0 enheter");
  });

  it("reads a pointer's height as a whole number inside the axis", () => {
    // A plot from y 10 (the value 40) to y 110 (the value 0): 2.5 px per unit.
    expect(pointValue(110, 10, 110, [0, 40], AXIS)).toBe(0);
    expect(pointValue(10, 10, 110, [0, 40], AXIS)).toBe(40);
    expect(pointValue(60, 10, 110, [0, 40], AXIS)).toBe(20);
    expect(pointValue(61, 10, 110, [0, 40], AXIS)).toBe(20);
    expect(pointValue(-50, 10, 110, [0, 40], AXIS)).toBe(40);
    expect(pointValue(500, 10, 110, [0, 40], AXIS)).toBe(0);
    // A domain widened by a typed 60: a pointer still places inside the axis.
    expect(pointValue(10, 10, 110, [0, 60], AXIS)).toBe(40);
  });
});
