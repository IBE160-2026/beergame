import { describe, expect, it } from "vitest";

import { ApiRequestError } from "@/lib/api/client";

import type { StaffAssistant } from "./api";
import { assistantStatus, personLabel, staffRefusal } from "./staff";

const assistant = (extra: Partial<StaffAssistant>): StaffAssistant => ({
  email: "a@x.no",
  status: "active",
  user_id: null,
  invitation_id: null,
  name: null,
  last_valid_day: null,
  ...extra,
});

describe("«Faglærere og assistenter» (Story 4.9)", () => {
  it("names each Assistent's status in text, with the last valid day", () => {
    const today = "2026-11-19";
    expect(assistantStatus(assistant({ status: "active" }), today)).toBe("Aktiv");
    expect(assistantStatus(assistant({ status: "invited", last_valid_day: "2026-12-03" }), today)).toBe(
      "Invitert, gyldig til og med 3. desember",
    );
    expect(assistantStatus(assistant({ status: "expired" }), today)).toBe("Invitasjonen er utløpt");
  });

  it("words the refusals beside the field and tells nothing about an account", () => {
    const refused = (reason: string) => new ApiRequestError(422, "invalid_request", { email: reason });
    expect(staffRefusal(refused("not_lecturer"))).toBe(
      "Adressen tilhører ingen Faglærer. Be Admin gi personen Faglærer-rollen.",
    );
    expect(staffRefusal(refused("already_staff"))).toBe("Personen er allerede med i Klassen.");
    expect(staffRefusal(refused("missing_domain"))).toBe("Domene mangler");
    expect(staffRefusal(new ApiRequestError(422, "last_owner"))).toBeUndefined();
    expect(staffRefusal(new Error("network"))).toBeUndefined();
  });

  it("labels a person by name and address, or by address alone", () => {
    expect(personLabel({ name: "Kari", email: "k@x.no" })).toBe("Kari (k@x.no)");
    expect(personLabel({ name: null, email: "k@x.no" })).toBe("k@x.no");
  });
});
