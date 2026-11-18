import { describe, expect, it } from "vitest";

import { normaliseName, roleName, validateInvitation, validateName, validityLine } from "./invitation";

describe("validateName", () => {
  it("asks for a name when only spaces are typed", () => {
    expect(validateName("")).toBe("nameEmpty");
    expect(validateName("  \t ")).toBe("nameEmpty");
    expect(validateName("Ola\u0000")).toBe("nameEmpty");
  });

  it("takes a name up to 200 characters, counted as the API counts them", () => {
    expect(validateName("Sara Lund")).toBeUndefined();
    expect(validateName("ø".repeat(200))).toBeUndefined();
    expect(validateName("ø".repeat(201))).toBe("nameLong");
  });

  it("trims and collapses spaces as the API does", () => {
    expect(normaliseName("  Ny   Faglærer ")).toBe("Ny Faglærer");
  });
});

describe("validateInvitation", () => {
  it("checks the name and the password rule of «Nytt passord»", () => {
    expect(validateInvitation("", "")).toEqual({ name: "nameEmpty", password: "passwordEmpty" });
    expect(validateInvitation("Sara", "kort")).toEqual({ name: undefined, password: "passwordShort" });
    expect(validateInvitation("Sara", "langt-nok")).toEqual({ name: undefined, password: undefined });
  });
});

describe("validityLine", () => {
  it("states the real days left", () => {
    expect(validityLine(14)).toBe("Invitasjonen er gyldig i 14 dager.");
    expect(validityLine(1)).toBe("Invitasjonen er gyldig i én dag.");
  });
});

describe("roleName", () => {
  it("names the role in the page's words", () => {
    expect(roleName("lecturer")).toBe("Faglærer");
    expect(roleName("admin")).toBe("Admin");
  });
});
