import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { cleanName, nameError, nameReason, refusalForField } from "./institutions";

const copy = nb.admin.institutions;

describe("the Institution name rule", () => {
  it("trims and collapses whitespace as the api stores it", () => {
    expect(cleanName("  USN   Bø ")).toBe("USN Bø");
  });

  it.each([
    ["", "name_empty"],
    ["   ", "name_empty"],
    ["x".repeat(201), "name_too_long"],
    ["kontakt@usn.no", "name_invalid"],
    ["USN\u0007", "name_invalid"],
  ])("refuses %j with %s", (value, reason) => {
    expect(nameReason(value)).toBe(reason);
  });

  it("takes 200 characters and a plain name", () => {
    expect(nameReason("x".repeat(200))).toBeUndefined();
    expect(nameReason(" Universitetet i Sørøst-Norge ")).toBeUndefined();
    expect(nameError("USN")).toBeUndefined();
  });

  it("words each reason", () => {
    expect(nameError("")).toBe("Skriv navnet på Institusjonen.");
    expect(nameError("a@b")).toBe(copy.errors.name_invalid);
  });
});

describe("refusals beside the field", () => {
  it("puts a taken name and the api's name reasons under the field", () => {
    expect(refusalForField(new ApiRequestError(409, "institution_name_taken"))).toBe(
      "Det finnes allerede en Institusjon med dette navnet.",
    );
    expect(refusalForField(new ApiRequestError(422, "invalid_request", { name: "name_too_long" }))).toBe(
      copy.errors.name_too_long,
    );
  });

  it("leaves every other failure to the general line", () => {
    expect(refusalForField(new ApiRequestError(0, "network_error"))).toBeUndefined();
    expect(refusalForField(new ApiRequestError(422, "invalid_request", { name: "other" }))).toBeUndefined();
    expect(refusalForField(new ApiRequestError(404, "not_found"))).toBeUndefined();
    expect(refusalForField(new Error("x"))).toBeUndefined();
  });

  it("states the results", () => {
    expect(copy.create.created("USN")).toBe("USN er opprettet.");
    expect(copy.rename.renamed("USN", "USN Bø")).toBe("USN heter nå USN Bø.");
    expect(copy.rename.open("USN")).toBe("Gi USN nytt navn");
  });
});
