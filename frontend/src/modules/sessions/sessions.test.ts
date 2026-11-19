import { describe, expect, it } from "vitest";

import type { GameSettings } from "./api";
import { chainText, costText, demandText, settingRows, upstreamFirst } from "./sessions";

/** A settings object as the API sends it. The values are a test fixture, not a copy of the
 * Classic preset: the web app reads them, it never supplies them. */
const settings: GameSettings = {
  schema_version: 1,
  roles: ["retailer", "wholesaler", "distributor", "factory"],
  starting_inventory: 12,
  starting_backlog: 0,
  supply_line: 4,
  order_delay: 2,
  shipping_delay: 3,
  production_delay: 1,
  demand: { kind: "step", start: 4, new_level: 8, change_week: 5 },
  demand_seed: 42,
  holding_cost: "0.50",
  backorder_cost: "1.00",
  weeks: 36,
  guided_weeks: 4,
  max_order: 999,
};

describe("the Klasseøkt (Story 5.1)", () => {
  it("lists the settings in words from the values the API returned", () => {
    expect(settingRows(settings, 24).map((r) => `${r.label}: ${r.value}`)).toEqual([
      "Startlager: 12",
      "Startrestordre: 0",
      "I hvert ledd ved start: 4 enheter",
      "Ordreforsinkelse: 2 uker",
      "Fraktforsinkelse: 3 uker",
      "Produksjonsforsinkelse: 1 uke",
      "Lagerkost: 0,50 per enhet per uke",
      "Restordrekost: 1,00 per enhet per uke",
      "Antall uker: 36",
      "Etterspørsel: 4, så 8 fra Uke 5",
      "Veiledede uker: 1–4",
      "Største ordre: 999",
      "Inaktivitetsgrense: 24 t, så KI overtar",
    ]);
  });

  it("draws the chain upstream first and says the same in text", () => {
    expect(upstreamFirst(settings)).toEqual(["factory", "distributor", "wholesaler", "retailer"]);
    expect(chainText(settings)).toBe(
      "Fabrikk, Distributør, Grossist og Detaljist starter med Lager 12 hver. Hver boks på røret er 4 enheter. " +
        "Frakt mellom leddene tar 3 uker, og produksjon inn til Fabrikk tar 1 uke. " +
        "Prikkene er ordre på vei, 2 uker. Studentene ser ikke kundene under spillet.",
    );
  });

  it("writes decimals with a comma and names a pattern it does not word yet", () => {
    expect(costText("12.25")).toBe("12,25");
    expect(costText("0.5")).toBe("0,50");
    expect(demandText({ kind: "fixed", values: [4, 4] })).toBe("Eget mønster");
  });
});
