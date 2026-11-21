import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { DEBRIEF_PATH } from "@/modules/identity/homes";

import { type Debrief, debriefView, downstreamRole, explanationDraftField, hasText } from "./api";

const copy = nb.debriefEntry;

const DEBRIEF: Debrief = {
  id: "d1",
  class_session_id: "s1",
  game_id: "g1",
  game_number: 17,
  role: "wholesaler",
  step: 1,
};

describe("the Debrief page's state (Story 9.2)", () => {
  it("comes from the api's answer or refusal code alone", () => {
    expect(debriefView(DEBRIEF, null)).toBe("open");
    expect(debriefView(undefined, "debrief_not_open")).toBe("notOpen");
    expect(debriefView(undefined, "debrief_held")).toBe("held");
    expect(debriefView(undefined, "forbidden")).toBe("denied");
    expect(debriefView(undefined, "network_error")).toBe("other");
    expect(debriefView(undefined, null)).toBe("other");
  });

  it("is reached at the Class session's own path", () => {
    expect(DEBRIEF_PATH("a/b")).toBe("/debrief/a%2Fb");
  });

  it("words the title, step 1 and the locked states without a count of games", () => {
    expect(copy.title(17)).toBe("Debrief, Spill 17");
    expect(copy.firstStep).toBe("Skriv Forklaringen først");
    expect(copy.stepOf(1, 5)).toBe("Steg 1 av 5");
    for (const line of [copy.notOpen, copy.held, nb.games.play.end.held]) {
      expect(line).not.toMatch(/\d|!/);
    }
  });
});

describe("the Explanation (Story 9.3)", () => {
  const words = copy.explanation;

  it("may be sent only with more than white space", () => {
    expect(hasText("")).toBe(false);
    expect(hasText("  \n\t ")).toBe(false);
    expect(hasText(" Lageret svingte. ")).toBe(true);
  });

  it("keeps its draft per Class session", () => {
    expect(explanationDraftField("s1")).not.toBe(explanationDraftField("s2"));
  });

  it("uses the spine's words and says nothing of customers or demand before the reveal", () => {
    expect([words.netTitle, words.prompt, words.send, words.showTable, words.failed]).toEqual([
      "Ditt netto lager, hele spillet",
      "Hvorfor svingte lageret ditt?",
      "Send Forklaring",
      "Vis som tabell",
      "Det ble ikke lagret. Prøv igjen.",
    ]);
    const all = Object.values(words)
      .map((value) => (typeof value === "function" ? value(1) : value))
      .join(" ");
    expect(all).not.toMatch(/kunde|etterspørsel|!/i);
  });
});

describe("the reveal (Story 9.4)", () => {
  it("names the Role whose Orders reached the Seat, and none for the Detaljist", () => {
    expect(downstreamRole("factory")).toBe("distributor");
    expect(downstreamRole("distributor")).toBe("wholesaler");
    expect(downstreamRole("wholesaler")).toBe("retailer");
    expect(downstreamRole("retailer")).toBeNull();
  });

  it("words the band and table as the spine does, and names the exercise only after the reveal", () => {
    const reveal = nb.debrief.reveal;
    expect(reveal.incomingKey).toBe("Ordre inn: det eneste du så");
    expect(reveal.largestOrder("24", 11)).toBe("Din ordre, 24 i Uke 11");
    expect(reveal.demandLabel("8")).toBe("Kundenes etterspørsel: 8");
    expect(Object.values(reveal.rows)).toEqual(["Kundene", "Ordre inn", "Din ordre"]);
    expect(reveal.named).toBe("Øvelsen heter Beer Game.");
    expect(JSON.stringify(nb.debriefEntry)).not.toMatch(/beer|bullwhip/i);
  });
});
