import { describe, expect, it } from "vitest";

import { firstOpen, parseWholeNumber, resultLine, type StartingTask, sumText } from "./starting-task";

const POSITION = [
  { sign: 1, value: 0 },
  { sign: -1, value: 13 },
  { sign: 1, value: 16 },
] as const;

describe("parseWholeNumber", () => {
  it("reads whole numbers with any minus sign", () => {
    expect(parseWholeNumber("13")).toBe(13);
    expect(parseWholeNumber(" 4 ")).toBe(4);
    expect(parseWholeNumber("−13")).toBe(-13);
    expect(parseWholeNumber("-13")).toBe(-13);
    expect(Object.is(parseWholeNumber("-0"), 0)).toBe(true);
    expect(parseWholeNumber("1000000")).toBe(1_000_000);
  });

  it("refuses letters, decimals and nothing", () => {
    for (const bad of ["", "  ", "x", "3x", "1,5", "1.5", "1 000", "+3", "--3", "12345678", "1000001", "-1000001"]) {
      expect(parseWholeNumber(bad), bad).toBeNull();
    }
  });
});

describe("the result line", () => {
  it("writes the api's terms out as the spine's sum", () => {
    expect(sumText([...POSITION])).toBe("0 − 13 + 16");
    expect(
      sumText([
        { sign: -1, value: 4 },
        { sign: 1, value: -3 },
      ]),
    ).toBe("−4 + (−3)");
    expect(
      sumText([
        { sign: -1, value: 0 },
        { sign: 1, value: 2 },
      ]),
    ).toBe("0 + 2");
  });

  it("says right or wrong in words", () => {
    const terms = [...POSITION];
    expect(resultLine({ answer: 5, correct: false, expected: 3, terms })).toBe(
      "Ikke riktig. Svaret er 3: 0 − 13 + 16.",
    );
    expect(resultLine({ answer: 3, correct: true, expected: 3, terms })).toBe("Riktig. Svaret er 3: 0 − 13 + 16.");
  });
});

describe("firstOpen", () => {
  const item = (answered: boolean) => ({
    id: "x",
    prompt: "p",
    hint: null,
    column: "Uke 11",
    rows: [],
    asked_label: "Posisjon",
    result: answered ? { answer: 3, correct: true, expected: 3, terms: [...POSITION] } : null,
  });
  const task = (...answered: boolean[]): StartingTask => ({
    version: 1,
    items: answered.map(item),
    played_before: null,
    done: false,
  });

  it("resumes at the first unanswered item", () => {
    expect(firstOpen(task(false, false))).toBe(0);
    expect(firstOpen(task(true, false, true))).toBe(1);
    expect(firstOpen(task(true, true))).toBe(-1);
  });
});
