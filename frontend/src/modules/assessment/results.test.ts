import { describe, expect, it } from "vitest";

import { aiCell, compressionText, humanCell, offsetText, percentText, scorerHeading, statusLines } from "./results";
import type { ControlResults } from "./scoring-api";

function page(overrides: Partial<ControlResults> = {}): ControlResults {
  return {
    test: { id: "t", name: "Kontrolltest høst", test_deadline: "2026-12-12T22:59:00Z", open: true },
    scoring_guide: { version: 1, edited: false },
    ai_config: { name: "mock-b", model_version: "mock-1" },
    scorers: [{ name: "Kari Sensor" }],
    rows: [],
    missing: 0,
    ai_missing: 0,
    open_attempts: 0,
    complete: true,
    checked: true,
    withheld: false,
    measures: null,
    ...overrides,
  };
}

describe("Control test results (Story 12.10)", () => {
  it("formats the measures with the shared number formatter, in words when there is none", () => {
    expect(percentText(0.5)).toBe("50 %");
    expect(percentText(0.3333)).toBe("33,3 %");
    expect(percentText(1)).toBe("100 %");
    expect(percentText(null)).toBe("Ikke beregnet");
    expect(offsetText(0.75)).toBe("+0,75 trinn");
    expect(offsetText(-0.6667)).toBe("−0,67 trinn");
    expect(offsetText(0)).toBe("0 trinn");
    expect(compressionText(0.4472)).toBe("0,45");
    expect(compressionText(null)).toBe("Ikke beregnet");
  });

  it("writes every cell in text: a step, «Ikke vurdert», «Mangler» or «Skjult»", () => {
    expect(humanCell(3)).toBe("3");
    expect(humanCell(0)).toBe("0");
    expect(humanCell(null)).toBe("Ikke vurdert");
    expect(aiCell(2, false)).toBe("2");
    expect(aiCell(null, false)).toBe("Mangler");
    expect(aiCell(2, true)).toBe("Skjult");
    expect(scorerHeading("Kari Sensor", 0)).toBe("Kari Sensor");
    expect(scorerHeading(" ", 1)).toBe("Sensor 2");
  });

  it("says checked, or preliminary with what is missing in words", () => {
    expect(statusLines(page())).toEqual(["Sensorveiledningen er kontrollert med denne modellkonfigurasjonen."]);
    expect(
      statusLines(page({ checked: false, complete: false, missing: 8, open_attempts: 1, ai_missing: 2 })),
    ).toEqual([
      "Foreløpige tall. Sensorveiledningen er ikke kontrollert ennå.",
      "8 vurderinger mangler.",
      "1 test er ikke levert ennå.",
      "KI-vurderingen mangler for 2 svar.",
    ]);
    expect(statusLines(page({ checked: false, scorers: [], missing: 1 }))).toEqual([
      "Foreløpige tall. Sensorveiledningen er ikke kontrollert ennå.",
      "Ingen sensorer er utnevnt.",
      "1 vurdering mangler.",
    ]);
    // A pair another Control test checked first: this one is still preliminary while scores are missing.
    expect(statusLines(page({ complete: false, checked: true, missing: 2 }))).toEqual([
      "Foreløpige tall for denne Kontrolltesten. Sensorveiledningen er alt kontrollert med denne modellkonfigurasjonen av en annen Kontrolltest.",
      "2 vurderinger mangler.",
    ]);
    expect(statusLines(page({ test: { ...page().test, open: false } }))[0]).toMatch(/^Resultatene kommer etter testfristen /);
  });
});
