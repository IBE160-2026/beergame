import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { COUNTS, hasActivity } from "./invitation-summary";

const copy = nb.classes.invitations;

describe("«Invitasjoner» (Story 4.6)", () => {
  it("shows the four counts in the order the Invitations travel", () => {
    expect(COUNTS.map(([key, label]) => [key, label])).toEqual([
      ["sent", "Sendt"],
      ["bounced", "Kom ikke fram"],
      ["accepted", "Akseptert"],
      ["expired", "Utløpt"],
    ]);
  });

  it("names a bounce's class in text, never by colour alone", () => {
    expect(copy.bounceStatus("hard")).toBe("Kom ikke fram, permanent feil");
    expect(copy.bounceStatus("soft")).toBe("Kom ikke fram, midlertidig feil");
  });

  it("shows the section only once something has happened to the Invitations", () => {
    const none = { sent: 0, bounced: 0, accepted: 0, expired: 0, bounces: [] };
    expect(hasActivity(none)).toBe(false);
    expect(hasActivity({ ...none, sent: 1 })).toBe(true);
    expect(hasActivity({ ...none, expired: 2 })).toBe(true);
  });
});
