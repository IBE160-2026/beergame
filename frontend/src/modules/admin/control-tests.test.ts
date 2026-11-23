import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { controlTestFieldErrors, controlTestNameError } from "./control-tests";

const errors = nb.admin.controlTests.create.errors;

describe("the Control test's Class name", () => {
  it.each([
    ["", errors.name_empty],
    ["   ", errors.name_empty],
    ["x".repeat(201), errors.name_too_long],
    ["Test\u0007", errors.name_invalid],
    ["Kontrolltest høst", undefined],
    ["x".repeat(200), undefined],
  ])("%j reads %j", (value, expected) => {
    expect(controlTestNameError(value)).toBe(expected);
  });
});

describe("a refused «Opprett Kontrolltest»", () => {
  it("words each refused field beside it", () => {
    const refused = new ApiRequestError(422, "invalid_request", {
      name: "name_empty",
      scoring_guide_id: "unknown",
      model_config_id: "missing",
    });
    expect(controlTestFieldErrors(refused)).toEqual({
      name: errors.name_empty,
      scoring_guide_id: errors.unknown,
      model_config_id: errors.unknown,
    });
  });

  it("says what to do first when no Institution is the operator's own", () => {
    const refused = new ApiRequestError(409, "operator_institution_missing");
    expect(controlTestFieldErrors(refused)).toEqual({ general: errors.operator_institution_missing });
  });

  it("leaves every other failure to the form's general line", () => {
    expect(controlTestFieldErrors(new ApiRequestError(500, "internal_error"))).toEqual({});
    expect(controlTestFieldErrors(new Error("x"))).toEqual({});
  });
});
