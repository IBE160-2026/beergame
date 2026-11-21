import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { DEBRIEF_PATH } from "@/modules/identity/homes";

import { type Chain, type Debrief, debriefView, downstreamRole, explanationDraftField, hasText } from "./api";
import { amplificationLine, chainBandInput, chainReading } from "./chain-step";

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

const week = (w: number, order: number, inventory: number, backlog: number, supply = 0, incoming = 4) => ({
  week: w,
  order,
  incoming_order: incoming,
  inventory,
  backlog,
  supply_line: supply,
});

const CHAIN: Chain = {
  own_role: "wholesaler",
  last_week: 2,
  large_order: 10,
  roles: [
    { role: "factory", amplification: "7.600", first_large_order_week: 2, capacity: null, weeks: [week(1, 4, 12, 0), week(2, 22, 0, 3, 50)] },
    { role: "distributor", amplification: "6.000", first_large_order_week: 2, capacity: null, weeks: [week(1, 4, 12, 0), week(2, 12, 0, 34, 52)] },
    { role: "wholesaler", amplification: "4.100", first_large_order_week: 2, capacity: 12, weeks: [week(1, 4, 12, 0), week(2, 12, 2, 19)] },
    { role: "retailer", amplification: null, first_large_order_week: null, capacity: null, weeks: [week(1, 4, 0, 0), week(2, 8, 12, 0, 13, 8)] },
  ],
};

describe("the whole chain at a Uke (Story 9.5)", () => {
  it("reads the chain Fabrikk first, both held numbers of a capped Seat, then the customers", () => {
    expect(chainReading(CHAIN, 2)).toBe(
      "Uke 2. Fabrikk: restordre 3, ordre 22. Distributør: restordre 34, ordre 12. Grossist: lager 2, restordre 19, ordre 12. Detaljist: lager 12, ordre 8. Kundene: ordre 8.",
    );
    expect(chainReading(CHAIN, 1)).toContain("Detaljist: lager 0, ordre 4.");
  });

  it("gives the band the api's numbers at the Uke, one bar scale for the game", () => {
    const input = chainBandInput(CHAIN, 2, 360, 13);
    expect(input.nodes.map((n) => [n.label, n.numbers, n.own])).toEqual([
      ["Fabrikk", ["Restordre 3"], false],
      ["Distributør", ["Restordre 34"], false],
      ["Grossist", ["Lager 2", "Restordre 19"], true],
      ["Detaljist", ["Lager 12"], false],
    ]);
    expect(input.orders).toEqual(["22", "12", "12", "8", "8"]);
    expect(input.supplyLines).toEqual(["50", "52", null, "13"]);
    expect(input.maxUnits).toBe(34);
    expect([input.upstream, input.downstream]).toEqual(["Produksjon", "Kundene"]);
  });

  it("states Forsterkning from the customers' end up, with a dash where demand never varied", () => {
    expect(amplificationLine(CHAIN)).toBe("Forsterkning fra kundene og oppover: Detaljist –, Grossist 4,1×, Distributør 6,0×, Fabrikk 7,6×.");
    expect(nb.debrief.chain.heading).toBe("Hele kjeden: svingningene vokser oppstrøms og kommer senere");
    expect(nb.debrief.chain.at(15)).toBe("Kjeden i Uke 15. Dra i skrubberen for å spole.");
  });
});
