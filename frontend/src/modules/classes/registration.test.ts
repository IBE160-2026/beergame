import { describe, expect, it } from "vitest";

import type { Registration } from "./api";
import { barShares, filterRegistrations, reminderReach, statusLabel } from "./registration";

const item = (email: string, status: Registration["status"], extra: Partial<Registration> = {}): Registration => ({
  id: email,
  email,
  status,
  last_valid_day: null,
  bounce_class: null,
  remindable: status !== "registered" && status !== "registered_manually",
  ...extra,
});

describe("statusLabel", () => {
  it("names every status in text, with the last valid day and the bounce class", () => {
    const today = "2026-11-19";
    expect(statusLabel(item("a", "invited", { last_valid_day: "2026-12-03" }), today)).toBe(
      "Invitert, gyldig til og med 3. desember",
    );
    expect(statusLabel(item("a", "invited", { last_valid_day: "2027-01-02" }), today)).toBe(
      "Invitert, gyldig til og med 2. januar 2027",
    );
    expect(statusLabel(item("a", "bounced", { bounce_class: "hard" }), today)).toBe("Kom ikke fram, permanent feil");
    expect(statusLabel(item("a", "bounced", { bounce_class: "soft" }), today)).toBe("Kom ikke fram, midlertidig feil");
    expect(statusLabel(item("a", "registered"), today)).toBe("Registrert");
    expect(statusLabel(item("a", "registered_manually"), today)).toBe("Registrert manuelt");
    expect(statusLabel(item("a", "renewal_requested"), today)).toBe("Ba om ny Invitasjon");
    expect(statusLabel(item("a", "unregistered"), today)).toBe("Uregistrert, Invitasjonen er utløpt");
    expect(statusLabel(item("a", "not_invited"), today)).toBe("Ikke invitert ennå");
  });
});

describe("filterRegistrations", () => {
  const items = [item("ola@x.no", "invited"), item("kari@y.no", "registered"), item("per@x.no", "unregistered")];
  it("filters by status and searches the address, trimmed and ignoring case", () => {
    expect(filterRegistrations(items, null, "").map((i) => i.email)).toEqual(["ola@x.no", "kari@y.no", "per@x.no"]);
    expect(filterRegistrations(items, "registered", "").map((i) => i.email)).toEqual(["kari@y.no"]);
    expect(filterRegistrations(items, null, "  X.NO ").map((i) => i.email)).toEqual(["ola@x.no", "per@x.no"]);
    expect(filterRegistrations(items, "invited", "per")).toEqual([]);
  });
});

describe("barShares and reminderReach", () => {
  it("splits the Roster into shares that add up to one, and none when it is empty", () => {
    expect(barShares({ registered: 238, registered_manually: 2, unregistered: 10 })).toEqual({
      registered: 238 / 250,
      manual: 2 / 250,
      unregistered: 10 / 250,
    });
    expect(barShares({ registered: 0, registered_manually: 0, unregistered: 0 })).toEqual({
      registered: 0,
      manual: 0,
      unregistered: 0,
    });
  });

  it("counts who a reminder reaches and the hard bounces it leaves out", () => {
    const items = [
      item("a", "invited"),
      item("b", "bounced", { bounce_class: "hard", remindable: false }),
      item("c", "registered"),
      item("d", "unregistered"),
    ];
    expect(reminderReach(items)).toEqual({ reach: 2, leftOut: 1 });
  });
});
