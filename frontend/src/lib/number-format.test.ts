import { describe, expect, it } from "vitest";

import { formatNumber, GROUP, MINUS, parseNumber } from "./number-format";

describe("formatNumber (UX-DR5)", () => {
  it("writes a space between thousands, a decimal comma and a true minus", () => {
    expect(formatNumber(1234567)).toBe(`1${GROUP}234${GROUP}567`);
    expect(formatNumber("2266.00")).toBe(`2${GROUP}266,00`);
    expect(formatNumber(-13)).toBe(`${MINUS}13`);
    expect(formatNumber("-1234.5")).toBe(`${MINUS}1${GROUP}234,5`);
    expect(formatNumber(999)).toBe("999");
    expect(formatNumber(0)).toBe("0");
  });

  it("pads or rounds to a fixed number of decimals", () => {
    expect(formatNumber("0.5", { decimals: 2 })).toBe("0,50");
    expect(formatNumber("1", { decimals: 2 })).toBe("1,00");
    expect(formatNumber("0.505", { decimals: 2 })).toBe("0,51");
    expect(formatNumber(12.5, { decimals: 0 })).toBe("13");
    expect(formatNumber("100.00", { decimals: 2 })).toBe("100,00");
  });

  it("writes kroner to two decimals with «kr» after a no-break space", () => {
    expect(formatNumber("68.0000", { kroner: true })).toBe("68,00 kr");
    expect(formatNumber("2266", { kroner: true })).toBe(`2${GROUP}266,00 kr`);
    expect(formatNumber("-3.505", { kroner: true })).toBe(`${MINUS}3,51 kr`);
    expect(formatNumber(0, { kroner: true })).toBe("0,00 kr");
  });

  it("drops the zero decimals in a narrow cell", () => {
    expect(formatNumber("6.0000", { narrow: true })).toBe("6");
    expect(formatNumber("6.5000", { narrow: true })).toBe("6,5");
    expect(formatNumber("0.2500", { narrow: true })).toBe("0,25");
    expect(formatNumber("-13.00", { narrow: true })).toBe(`${MINUS}13`);
    expect(formatNumber("1234.0", { narrow: true })).toBe(`1${GROUP}234`);
    expect(formatNumber("-0.00", { narrow: true })).toBe("0");
    expect(formatNumber(12, { narrow: true })).toBe("12");
  });

  it("writes no minus on zero and leaves text that is no number as it is", () => {
    expect(formatNumber("-0.00")).toBe("0,00");
    expect(formatNumber("abc")).toBe("abc");
    expect(formatNumber(Number.NaN)).toBe("NaN");
  });
});

describe("parseNumber", () => {
  it("reads a number typed the Norwegian way into the api's decimal string", () => {
    expect(parseNumber("12")).toBe("12");
    expect(parseNumber(" 0,50 ")).toBe("0.50");
    expect(parseNumber("1 000,5")).toBe("1000.5");
    expect(parseNumber(`1${GROUP}000`)).toBe("1000");
    expect(parseNumber(`${MINUS}2`)).toBe("-2");
    expect(parseNumber("-2")).toBe("-2");
    expect(parseNumber("0.75")).toBe("0.75");
    expect(parseNumber("007")).toBe("7");
  });

  it("gives null for anything that is no number, for the api to name", () => {
    for (const text of ["", "abc", "1,2,3", "12a", "--1", ","]) expect(parseNumber(text)).toBeNull();
  });

  it("round-trips through the formatter", () => {
    expect(parseNumber(formatNumber("-1234.50"))).toBe("-1234.50");
  });
});
