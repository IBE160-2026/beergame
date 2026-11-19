import { describe, expect, it } from "vitest";

import { invitationLead, normaliseName, roleName, validateInvitation, validateName, validityLine } from "./invitation";

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

  it("adds the Start-date line for a Student Invitation", () => {
    expect(validityLine(14, true)).toBe("Invitasjonen er gyldig i 14 dager. Du får Rolle og spill på startdatoen.");
  });
});

describe("roleName", () => {
  it("names the role in the page's words", () => {
    expect(roleName("lecturer")).toBe("Faglærer");
    expect(roleName("admin")).toBe("Admin");
  });
});

describe("invitationLead", () => {
  const student = { kind: "student" as const, class_name: "class-of-1994", course_code: "IBE160", invited_by: "Bård" };

  it("names the Class and its Lecturer for a Student Invitation", () => {
    expect(invitationLead(student, false)).toBe("Faglærer Bård har lagt deg til i class-of-1994, IBE160.");
    expect(invitationLead({ ...student, invited_by: null, course_code: null }, false)).toBe(
      "Du er lagt til i class-of-1994.",
    );
    expect(invitationLead(student, true)).toBe(
      "Adressen har allerede en konto. Logg inn, så blir du med i class-of-1994, IBE160.",
    );
  });

  it("names the role for a role Invitation", () => {
    expect(invitationLead({ kind: "role", role: "admin" }, true)).toBe(
      "Adressen har allerede en konto. Logg inn, så får kontoen rollen Admin.",
    );
  });
});
