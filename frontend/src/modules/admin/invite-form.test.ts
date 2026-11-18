import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { inviteEmailError, sentLine } from "./invite-form";

const copy = nb.admin.users.invite;

describe("inviteEmailError", () => {
  it("names an empty field in the Admin's words and keeps the reasons of «Logg inn»", () => {
    expect(inviteEmailError("   ")).toBe(copy.errors.emailEmpty);
    expect(inviteEmailError("kari")).toBe(nb.auth.login.errors.emailNoAt);
    expect(inviteEmailError("a@@b.no")).toBe(nb.auth.login.errors.emailTwoAt);
    expect(inviteEmailError("kari@b")).toBe(nb.auth.login.errors.emailNoDomain);
    expect(inviteEmailError("a b@c.no")).toBe(nb.auth.login.errors.emailSpace);
  });

  it("takes an address the server takes", () => {
    expect(inviteEmailError("  Ny.Faglaerer@Example.com ")).toBeUndefined();
  });
});

describe("sentLine", () => {
  const sent = { id: "x", email: "ny@example.com", expires_at: "2026-12-02T12:00:00Z" };

  it("states the address, the role and the real number of days", () => {
    expect(sentLine({ ...sent, role: "lecturer", valid_days: 14 })).toBe(
      "Invitasjonen er sendt til ny@example.com som Faglærer. Den er gyldig i 14 dager.",
    );
    expect(sentLine({ ...sent, role: "admin", valid_days: 1 })).toBe(
      "Invitasjonen er sendt til ny@example.com som Admin. Den er gyldig i én dag.",
    );
  });
});
