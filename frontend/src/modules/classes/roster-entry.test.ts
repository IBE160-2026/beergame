import { describe, expect, it } from "vitest";

import { ApiRequestError } from "@/lib/api/client";

import { emailReason, entryRefusal, firstRefused, nameError } from "./roster-entry";

describe("single addresses and manual registration (Story 4.8)", () => {
  it("words an address refusal as the upload does, plus a duplicate and a registered address", () => {
    expect(emailReason("missing_domain")).toBe("Domene mangler");
    expect(emailReason("on_roster")).toBe("Står allerede på Klasselista");
    expect(emailReason("already_registered")).toBe("Adressen er allerede registrert i Klassen.");
    expect(emailReason("string_too_long")).toBe("Adressen er for lang.");
    expect(emailReason("something_else")).toBeUndefined();
  });

  it("reads the refused fields of an api answer, and nothing from any other failure", () => {
    const refused = new ApiRequestError(422, "invalid_request", { email: "two_at", name: "name_empty" });
    expect(entryRefusal(refused)).toEqual({ email: "To @", name: "Skriv navnet til studenten." });
    expect(entryRefusal(new ApiRequestError(422, "invalid_request", { body: "x" }))).toEqual({});
    expect(entryRefusal(new ApiRequestError(403, "forbidden"))).toEqual({});
    expect(entryRefusal(new Error("x"))).toEqual({});
  });

  it("checks the name as the api does before sending", () => {
    expect(nameError("  ")).toBe("Skriv navnet til studenten.");
    expect(nameError("n".repeat(201))).toBe("Navnet kan ha høyst 200 tegn.");
    expect(nameError("  Kari  Nordmann ")).toBeUndefined();
  });

  it("puts focus on the first refused field in form order", () => {
    expect(firstRefused({ name: "x", email: "y" })).toBe("email");
    expect(firstRefused({ name: "x" })).toBe("name");
    expect(firstRefused({})).toBeUndefined();
  });
});
