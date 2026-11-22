import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { GROUP } from "@/lib/number-format";

import { levelName, modelName, percentText, refusalText, usdText } from "./ai-models";

const copy = nb.admin.aiCost;
const NBSP = "\u00a0";

describe("«KI-kostnad» (Story 15.5)", () => {
  it("shows a stored share in percent by moving the decimal point", () => {
    expect(percentText("0.0125")).toBe(`1,25${NBSP}%`);
    expect(percentText("0.025")).toBe(`2,5${NBSP}%`);
    expect(percentText("0")).toBe(`0${NBSP}%`);
    expect(percentText("1")).toBe(`100${NBSP}%`);
    expect(percentText("0.5")).toBe(`50${NBSP}%`);
    expect(percentText("0.333333")).toBe(`33,3333${NBSP}%`);
  });

  it("shows a cost in USD with the shared formatter", () => {
    expect(usdText("0.0725")).toBe(`0,0725${NBSP}USD`);
    expect(usdText("1234.5")).toBe(`1${GROUP}234,5${NBSP}USD`);
  });

  it("names a level and a model", () => {
    expect(levelName({ name: "careful", label: "Grundig" })).toBe("Grundig");
    expect(levelName({ name: "careful", label: null })).toBe("careful");
    expect(modelName({ name: "mock", model_version: "mock-1" })).toBe("mock · mock-1");
  });

  it("explains a refusal by its code, else the general failure", () => {
    const frozen = new ApiRequestError(409, "model_config_frozen");
    expect(refusalText(frozen, copy.sessions.refused, copy.sessions.failed)).toBe(
      copy.sessions.refused.model_config_frozen,
    );
    const other = new ApiRequestError(500, "internal_error");
    expect(refusalText(other, copy.sessions.refused, copy.sessions.failed)).toBe(copy.sessions.failed);
    expect(refusalText(new Error("x"), copy.freeze.refused, copy.freeze.failed)).toBe(copy.freeze.failed);
  });
});
