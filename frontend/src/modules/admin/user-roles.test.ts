import { describe, expect, it } from "vitest";

import { ApiRequestError } from "@/lib/api/client";

import type { ListedUser } from "./api";
import {
  changedLine,
  firstName,
  refusalLine,
  roleButtonLabel,
  rolesText,
  statusButtonLabel,
  statusChangedLine,
  statusRefusalLine,
} from "./user-roles";

const bard = (roles: ListedUser["roles"] = []): ListedUser => ({
  id: "u1",
  name: "  Bård Hansen ",
  email: "bard@example.com",
  roles,
  is_active: true,
});

describe("the User list's words", () => {
  it("addresses a User by the first word of the name", () => {
    expect(firstName("  Bård Hansen ")).toBe("Bård");
    expect(firstName("Kari")).toBe("Kari");
  });

  it("names the roles held, or none", () => {
    expect(rolesText(bard())).toBe("Ingen rolle");
    expect(rolesText(bard(["admin", "lecturer"]))).toBe("Faglærer, Admin");
  });

  it("labels each button with its effect and the User", () => {
    expect(roleButtonLabel(bard(), "lecturer")).toBe("Gi Bård rollen Faglærer");
    expect(roleButtonLabel(bard(["lecturer"]), "lecturer")).toBe("Fjern rollen Faglærer fra Bård");
    expect(roleButtonLabel(bard(["lecturer"]), "admin")).toBe("Gi Bård rollen Admin");
  });

  it("states the change", () => {
    expect(changedLine(bard(["lecturer"]), "lecturer", true)).toBe("Bård har nå rollen Faglærer.");
    expect(changedLine(bard(), "admin", false)).toBe("Bård har ikke lenger rollen Admin.");
  });

  it("words a blocked revoke with the real count, and the last Admin", () => {
    const blocked = (classes: unknown) => new ApiRequestError(409, "role_revoke_blocked", { classes });
    expect(refusalLine(blocked(2), bard())).toBe(
      "Bård eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.",
    );
    expect(refusalLine(blocked(1), bard())).toBe(
      "Bård eier 1 Klasse. Legg til en annen Faglærer eller arkiver Klassen først.",
    );
    expect(refusalLine(new ApiRequestError(409, "last_admin"), bard())).toBe(
      "Bård er den eneste aktive Admin. Gi en annen bruker rollen Admin først.",
    );
  });

  it("falls back to the general line", () => {
    const general = "Rollen ble ikke endret. Prøv igjen.";
    expect(refusalLine(new ApiRequestError(409, "role_revoke_blocked", { classes: "x" }), bard())).toBe(general);
    expect(refusalLine(new ApiRequestError(0, "network_error"), bard())).toBe(general);
    expect(refusalLine(new Error("boom"), bard())).toBe(general);
  });

  it("labels the status button with its consequence and the User (Story 3.10)", () => {
    expect(statusButtonLabel(bard())).toBe("Deaktiver Bård. Bård kan ikke logge inn, og dataene blir værende.");
    expect(statusButtonLabel({ ...bard(), is_active: false })).toBe("Aktiver Bård igjen");
  });

  it("states a status change from the answer", () => {
    expect(statusChangedLine({ ...bard(), is_active: false })).toBe("Bård er deaktivert.");
    expect(statusChangedLine(bard())).toBe("Bård er aktiv igjen.");
  });

  it("words a refused status change for oneself, the last Admin and the rest", () => {
    const lastAdmin = new ApiRequestError(409, "last_admin");
    expect(statusRefusalLine(lastAdmin, bard(), "u1")).toBe("Du kan ikke deaktivere deg selv.");
    expect(statusRefusalLine(lastAdmin, bard(), "u2")).toBe(
      "Bård er den eneste aktive Admin. Gi en annen bruker rollen Admin først.",
    );
    expect(statusRefusalLine(new ApiRequestError(404, "not_found"), bard(), "u2")).toBe(
      "Statusen ble ikke endret. Prøv igjen.",
    );
  });
});
