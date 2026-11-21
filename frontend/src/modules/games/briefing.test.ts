import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameRules } from "./api";
import { EXAMPLE, capacityLines, delayLines, exampleCostLine, exampleRows, guidedLine, isCapped, ratesLine } from "./briefing";

const CLASSIC: GameRules = {
  order_delay: 2,
  shipping_delay: 2,
  production_delay: 2,
  guided_weeks: 4,
  holding_cost: "0.50",
  backorder_cost: "1.00",
  capacity: [],
};

describe("briefing", () => {
  it("states the delays of the Student's own Role", () => {
    expect(delayLines("wholesaler", CLASSIC)).toEqual([
      "Ordren din kommer fram til Distributøren to uker etter at du la den inn.",
      "Det som sendes til deg, er to uker på vei før det kommer fram.",
      nb.games.briefing.delays.earliest,
      nb.games.briefing.delays.onTheWay,
    ]);
    expect(delayLines("distributor", CLASSIC)[0]).toBe("Ordren din kommer fram til Fabrikken to uker etter at du la den inn.");
    expect(delayLines("retailer", { ...CLASSIC, order_delay: 1, shipping_delay: 3 }).slice(0, 2)).toEqual([
      "Ordren din kommer fram til Grossisten én uke etter at du la den inn.",
      "Det som sendes til deg, er tre uker på vei før det kommer fram.",
    ]);
    expect(delayLines("factory", { ...CLASSIC, order_delay: 3, production_delay: 1 })[0]).toBe(
      "Ordren din går til produksjon tre uker etter at du la den inn. Produksjonen tar én uke.",
    );
  });

  it("names the Veiledede uker, or that there are none", () => {
    expect(guidedLine(CLASSIC)).toContain("De første fire ukene er veiledede uker.");
    expect(guidedLine({ guided_weeks: 1 })).toMatch(/^Den første uka er en veiledet uke\. /);
    expect(guidedLine({ guided_weeks: 0 })).toBe(nb.games.briefing.guided.none);
  });

  it("writes the game's own rates in Norwegian", () => {
    expect(ratesLine({ holding_cost: "0.75", backorder_cost: "2" })).toBe(
      "Hver enhet på lager koster 0,75 kr per uke. Hver enhet i restordre koster 2,00 kr per uke.",
    );
    expect(exampleCostLine({ backorder_cost: "2" })).toBe(
      "Denne uka: 13 enheter i restordre, hver til 2,00 kr. Lager 0 gir ingen lagerkostnad.",
    );
  });

  it("keeps the worked Uke true to the Week rule and the spine's Uke 11", () => {
    const row = EXAMPLE.rows;
    expect(EXAMPLE.onHand).toBe(EXAMPLE.inventoryBefore + row.incomingDelivery);
    expect(EXAMPLE.owed).toBe(row.incomingOrder + EXAMPLE.backlogBefore);
    expect(EXAMPLE.shipped).toBe(Math.min(EXAMPLE.onHand, EXAMPLE.owed));
    expect(row.unitsShipped).toBe(EXAMPLE.shipped);
    expect(row.inventory).toBe(EXAMPLE.onHand - EXAMPLE.shipped);
    expect(row.backlog).toBe(EXAMPLE.owed - EXAMPLE.shipped);
    expect([EXAMPLE.inventoryAfter, EXAMPLE.backlogAfter]).toEqual([row.inventory, row.backlog]);
    expect(row.netInventory).toBe(row.inventory - row.backlog);
    // EXPERIENCE.md's Uke 11, the Startoppgave's column: Posisjon 0 − 13 + 16 = 3.
    expect([row.incomingOrder, row.incomingDelivery, row.inventory, row.backlog, row.supplyLine]).toEqual([8, 4, 0, 13, 16]);
  });

  it("writes the worked Uke's own numbers into its lines", () => {
    expect(exampleRows().map((r) => [r.term, r.value, r.meaning])).toEqual([
      ["Ordre inn", "8", "Det Detaljisten bestilte. Med 9 i restordre fra før må Grossisten sende 17."],
      ["Levering", "4", "Enheter som kom fram denne uka. Med 0 på lager fra før har Grossisten 4."],
      ["Sendt", "4", "Grossisten sender alt den har, opp til det den skal sende."],
      ["Lager", "0", "Det som er igjen etter sendingen: 4 − 4."],
      ["Restordre", "13", "Det Grossisten ikke kunne sende: 17 − 4. Det sendes så snart enhetene finnes."],
      [
        "Netto lager",
        "−13",
        "Lager minus restordre: 0 − 13. Under null betyr restordre. Spillets tabell viser denne raden.",
      ],
      ["På vei", "16", "Enheter Grossisten har bestilt og ennå ikke fått."],
    ]);
  });
});

describe("the capacity (Story 6.22)", () => {
  const capped = (capacity: GameRules["capacity"]): GameRules => ({ ...CLASSIC, capacity });
  const BOTH = nb.games.briefing.capacity.both;
  const MINE = nb.games.briefing.capacity.mine;

  it("says nothing when no Role is capped, or the api gave no capacity", () => {
    expect(capacityLines("wholesaler", CLASSIC)).toEqual([]);
    const { capacity: _, ...older } = CLASSIC;
    expect(capacityLines("wholesaler", older as GameRules)).toEqual([]);
    expect(isCapped("wholesaler", older as GameRules)).toBe(false);
  });

  it("names a capped Role, that stock and backlog can stand together, and the capped Student's table", () => {
    const rules = capped([{ role: "wholesaler", units: 6 }]);
    expect(capacityLines("wholesaler", rules)).toEqual(["Grossisten kan sende høyst 6 enheter per uke.", BOTH, MINE]);
    expect(capacityLines("retailer", rules)).toEqual(["Grossisten kan sende høyst 6 enheter per uke.", BOTH]);
    expect(isCapped("wholesaler", rules)).toBe(true);
    expect(isCapped("retailer", rules)).toBe(false);
  });

  it("lists mixed caps as the api orders them, and every Role alike in one line", () => {
    const mixed = capped([
      { role: "retailer", units: 5 },
      { role: "factory", units: 12 },
    ]);
    expect(capacityLines("distributor", mixed)).toEqual([
      "Detaljisten kan sende høyst 5 enheter per uke.",
      "Fabrikken kan sende høyst 12 enheter per uke.",
      BOTH,
    ]);
    const every = capped((["retailer", "wholesaler", "distributor", "factory"] as const).map((role) => ({ role, units: 6 })));
    expect(capacityLines("factory", every)).toEqual(["Hver rolle kan sende høyst 6 enheter per uke.", BOTH, MINE]);
    // Three Roles alike is not every Role.
    expect(capacityLines("factory", capped(every.capacity.slice(0, 3)))).toHaveLength(4);
  });

  it("says «1 enhet» for a cap of one", () => {
    expect(capacityLines("retailer", capped([{ role: "wholesaler", units: 1 }]))[0]).toBe("Grossisten kan sende høyst 1 enhet per uke.");
  });

  it("names no number of Weeks", () => {
    const text = capacityLines("wholesaler", capped([{ role: "wholesaler", units: 6 }])).join(" ");
    expect(text).not.toMatch(/\d+ uker/);
  });
});

