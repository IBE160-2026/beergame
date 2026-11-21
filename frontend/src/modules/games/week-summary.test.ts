import { describe, expect, it } from "vitest";

import type { PlayEnvelope } from "./api";
import week1 from "./fixtures/play-week-1.json";
import week11 from "./fixtures/play-week-11.json";
import { weekSummary } from "./week-summary";

const envelope = week11 as unknown as PlayEnvelope;
const state = envelope.seat_state;
const free = { guided: false, order: null, viewed: false };

describe("weekSummary", () => {
  it("reads the Uke just run from the api's numbers (`06-spilldynamikk.png` D)", () => {
    const summary = weekSummary(state, free)!;
    expect(summary.title).toBe("Uke 10 er ferdig regnet");
    expect(summary.rows).toEqual([
      { label: "Levering", value: "4" },
      { label: "Ordre inn", value: "10" },
      { label: "Sendt", value: "4" },
      { label: "Restordre", value: "14 blir 20" },
    ]);
    expect(summary.cost).toBe("Denne uka: 20 restordre × 1,00 = 20,00 kr");
    expect(summary.spoken).toBe(
      "Uke 10 er ferdig regnet. Levering 4. Ordre inn 10. Sendt 4. Restordre 14 blir 20. Denne uka: 20 restordre × 1,00 = 20,00 kr.",
    );
  });

  it("shows Lager when there is stock, both when both change, and Lager alone when both are zero", () => {
    const last = state.history.at(-1)!;
    const stock = {
      ...state,
      inventory: 6,
      backlog: 0,
      history: [...state.history.slice(0, -1), { ...last, inventory: 2, backlog: 0 }],
      cost_lines: [
        { kind: "holding" as const, units: 6, rate: "0.50", amount: "3.00" },
        { kind: "backorder" as const, units: 0, rate: "1.00", amount: "0.00" },
      ],
      week_cost: "3.00",
    };
    const summary = weekSummary(stock, free)!;
    expect(summary.rows.slice(3)).toEqual([{ label: "Lager", value: "2 blir 6" }]);
    expect(summary.cost).toBe("Denne uka: 6 lager × 0,50 = 3,00 kr");
    const turned = { ...stock, history: [...state.history.slice(0, -1), { ...last, inventory: 3, backlog: 0 }], inventory: 0, backlog: 5 };
    expect(weekSummary(turned, free)!.rows.slice(3)).toEqual([
      { label: "Lager", value: "3 blir 0" },
      { label: "Restordre", value: "0 blir 5" },
    ]);
    const zero = {
      ...stock,
      inventory: 0,
      history: [...state.history.slice(0, -1), { ...last, inventory: 0, backlog: 0 }],
      cost_lines: stock.cost_lines.map((line) => ({ ...line, units: 0, amount: "0.00" })),
      week_cost: "0.00",
    };
    expect(weekSummary(zero, free)!.rows.slice(3)).toEqual([{ label: "Lager", value: "0 blir 0" }]);
    expect(weekSummary(zero, free)!.cost).toBe("Denne uka: 0,00 kr");
  });

  it("is gone in Uke 1 and once the own Order is placed, and stays all through a Veiledet uke", () => {
    const first = (week1 as unknown as PlayEnvelope).seat_state;
    expect(weekSummary(first, free)).toBeNull();
    expect(weekSummary(state, { ...free, order: 24 })).toBeNull();
    expect(weekSummary(state, { guided: true, order: 4, viewed: true })).not.toBeNull();
  });
});
