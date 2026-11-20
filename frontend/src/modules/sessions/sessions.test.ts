import { describe, expect, it } from "vitest";

import type { GameSettings } from "./api";
import { chainText, costText, customerLines, demandText, settingRows, upstreamFirst } from "./sessions";

/** A settings object as the API sends it. The values are a test fixture, not a copy of the
 * Classic preset: the web app reads them, it never supplies them. */
const settings: GameSettings = {
  schema_version: 2,
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
  info_visibility: { upstream: false, downstream: false },
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
        "Prikkene er ordre på vei, 2 uker. Kundenes etterspørsel: 4, så 8 fra Uke 5. Studentene ser ikke kundene under spillet.",
    );
  });

  it("writes decimals with a comma", () => {
    expect(costText("12.25")).toBe("12,25");
    expect(costText("0.5")).toBe("0,50");
  });
});

describe("the Demand pattern in words (Story 5.4)", () => {
  const step = { kind: "step", start: 4, new_level: 8, change_week: 5 } as const;
  const noise = { kind: "step+noise", start: 4, new_level: 8, change_week: 5, spread: 2 } as const;
  const random = { kind: "random", mean: 8, spread: 2 } as const;
  const fixed = { kind: "fixed" as const, values: [4, 4, 8] };

  it("words every pattern in the settings list", () => {
    expect(demandText(step)).toBe("4, så 8 fra Uke 5");
    expect(demandText(noise)).toBe("4, så 8 fra Uke 5, ± 2 tilfeldig");
    expect(demandText(random)).toBe("Tilfeldig, 8 ± 2");
    expect(demandText(fixed)).toBe("Fast serie over 3 uker");
  });

  it("lists the seed under the pattern only when the pattern draws", () => {
    const rows = (demand: GameSettings["demand"]) => settingRows({ ...settings, demand }, 24).map((r) => r.label);
    expect(rows(step)).not.toContain("Frø");
    expect(settingRows({ ...settings, demand: random }, 24).find((r) => r.key === "demand_seed")?.value).toBe("42");
    expect(rows(noise)).toContain("Frø");
  });

  it("puts two short lines under «Kundene», as mockup 03", () => {
    expect(customerLines(step)).toEqual(["4, så 8", "fra Uke 5"]);
    expect(customerLines(noise)).toEqual(["4, så 8 ± 2", "fra Uke 5"]);
    expect(customerLines(random)).toEqual(["8 ± 2", "tilfeldig"]);
    expect(customerLines(fixed)).toEqual(["Fast serie", "3 uker"]);
  });
});

describe("Information visibility in words (Story 5.16)", () => {
  const value = (upstream: boolean, downstream: boolean, on = true) =>
    settingRows({ ...settings, info_visibility: { upstream, downstream } }, 24, false, on).find(
      (r) => r.key === "info_visibility",
    );

  it("lists the views only while the flag is on, before the Inactivity limit", () => {
    expect(value(true, false, false)).toBeUndefined();
    const keys = settingRows(settings, 24, false, true).map((r) => r.key);
    expect(keys.slice(-2)).toEqual(["info_visibility", "inactivity_limit_hours"]);
    expect(value(false, false)).toEqual({ key: "info_visibility", label: "Synlige naboer", value: "Av" });
  });

  it("names the views that are on", () => {
    expect(value(true, false)?.value).toBe("Leddet oppstrøms");
    expect(value(false, true)?.value).toBe("Leddet nedstrøms");
    expect(value(true, true)?.value).toBe("Begge naboene");
  });
});

describe("the shipping capacity in words (Story 5.15)", () => {
  const value = (capacity: GameSettings["capacity"], on = true) =>
    settingRows({ ...settings, capacity }, 24, on).find((r) => r.key === "capacity")?.value;

  it("lists the capacity only while the flag is on", () => {
    expect(value(undefined, false)).toBeUndefined();
    expect(value({ retailer: 6 }, false)).toBeUndefined();
    expect(value(undefined)).toBe("Ingen");
    expect(value({ retailer: 6 })).toBe("6 per uke for Detaljist");
    expect(value({ retailer: 6, wholesaler: 6, distributor: 6, factory: 6 })).toBe("6 per uke for alle ledd");
    // Fabrikk first, the one Seat order everywhere (Issue #115).
    expect(value({ retailer: 6, factory: 9 })).toBe("9 per uke for Fabrikk; 6 per uke for Detaljist");
  });

  it("names the capped Role in the chain's text while the flag is on", () => {
    const capped = { ...settings, capacity: { wholesaler: 6 } };
    expect(chainText(capped, true)).toBe(chainText(settings) + " Grossist kan sende høyst 6 per uke.");
    expect(chainText(capped)).toBe(chainText(settings));
  });
});
