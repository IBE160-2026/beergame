import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { inactivityProblem, shareProblem, valueErrorsOf, wholeNumber } from "./obligatory";

describe("wholeNumber", () => {
  it("reads digits only, spaces around allowed", () => {
    expect(wholeNumber("24")).toBe(24);
    expect(wholeNumber(" 48 ")).toBe(48);
    for (const text of ["", " ", "2,5", "2.5", "-20", "+20", "20t", "1e3"]) {
      expect(wholeNumber(text)).toBeNull();
    }
  });
});

describe("inactivityProblem", () => {
  it("refuses empty, decimal and under 20 hours", () => {
    const error = nb.sessions.edit.inactivityError;
    for (const text of ["", "19", "2,5", "24.5", "abc", "0"]) expect(inactivityProblem(text)).toBe(error);
    for (const text of ["20", "24", "168"]) expect(inactivityProblem(text)).toBeUndefined();
  });
});

describe("shareProblem", () => {
  it("takes a whole percent from 1 to 100", () => {
    const error = nb.sessions.choices.shareError;
    for (const text of ["", "0", "101", "80,5", "-1"]) expect(shareProblem(text)).toBe(error);
    for (const text of ["1", "80", "100"]) expect(shareProblem(text)).toBeUndefined();
  });
});

describe("valueErrorsOf", () => {
  it("puts the api's refusal under each field it names", () => {
    const refused = new ApiRequestError(422, "invalid_session_values", {
      required_share_percent: "out_of_range",
      inactivity_limit_hours: "below_minimum",
    });
    expect(valueErrorsOf(refused)).toEqual({
      share: nb.sessions.choices.shareError,
      inactivity: nb.sessions.edit.inactivityError,
    });
    expect(valueErrorsOf(new ApiRequestError(409, "session_locked", { obligatory: "locked" }))).toEqual({});
    expect(valueErrorsOf(null)).toEqual({});
  });
});
