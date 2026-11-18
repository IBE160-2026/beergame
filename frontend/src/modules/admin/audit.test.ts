import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { actionLabel, actorText, changeLines, formatTime, rangeError, targetText } from "./audit";

const copy = nb.admin.audit;

describe("the audit row's words", () => {
  it("shows the time in Oslo, summer and winter", () => {
    expect(formatTime("2026-11-18T12:01:00Z")).toBe("18. nov. 2026 kl. 13:01");
    expect(formatTime("2026-07-01T22:30:00Z")).toBe("2. jul. 2026 kl. 00:30");
  });

  it("names a known action and shows the code of an unknown one", () => {
    expect(actionLabel("role.granted")).toBe("Rolle gitt");
    expect(actionLabel("takeover.by_person")).toBe("takeover.by_person");
    expect(actionLabel("toString")).toBe("toString");
  });

  it("says the system for a row with no actor and «Ukjent» for a name it lacks", () => {
    expect(actorText({ actor_id: null, actor_name: null })).toBe(copy.system);
    expect(actorText({ actor_id: "a", actor_name: "Kari" })).toBe("Kari");
    expect(actorText({ actor_id: "a", actor_name: null })).toBe(copy.unknown);
  });

  it("words the target by its key", () => {
    expect(targetText({ key: "invitation_id", id: "i", label: "kari@example.no" })).toBe(
      "Invitasjon til kari@example.no",
    );
    expect(targetText({ key: "user_id", id: "u", label: "Ola" })).toBe("Ola");
    expect(targetText({ key: "seat_id", id: "s", label: "Sete 2" })).toBe("Sete 2");
    expect(targetText({ key: "user_id", id: "u", label: null })).toBe(copy.unknown);
  });

  it("labels the change fields and words their values", () => {
    expect(
      changeLines({
        role: "lecturer",
        account: "existing",
        role_added: false,
        voided_invitation_ids: ["a", "b"],
        resent_invitation_id: "x",
        new_field: { a: 1 },
        count: 3,
      }),
    ).toEqual([
      { label: "Rolle", value: "Faglærer" },
      { label: "Konto", value: "Eksisterende konto" },
      { label: "Rollen lagt til", value: "Nei" },
      { label: "Lenker gjort ugyldige", value: "2" },
      { label: "new_field", value: '{"a":1}' },
      { label: "count", value: "3" },
    ]);
    expect(changeLines({})).toEqual([]);
  });

  it("puts the known fields in the order of nb.ts, whatever order the row holds", () => {
    expect(changeLines({ zeta: 1, new_name: "USN Bø", old_name: "USN" }).map((line) => line.label)).toEqual([
      "Gammelt navn",
      "Nytt navn",
      "zeta",
    ]);
  });

  it("refuses a range that ends before it starts", () => {
    expect(rangeError("2026-11-18", "2026-11-17")).toBe(copy.filters.rangeReversed);
    expect(rangeError("2026-11-18", "2026-11-18")).toBeUndefined();
    expect(rangeError("", "2026-11-17")).toBeUndefined();
  });
});
