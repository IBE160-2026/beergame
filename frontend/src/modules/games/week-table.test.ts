import { describe, expect, it } from "vitest";

import { MINUS } from "@/lib/number-format";

import fixture from "./fixtures/play-week-11.json";
import type { SeatState } from "./api";
import { cellFor, netStep, ROWS, weekColumns } from "./week-table";

// The engine's Grossist in Uke 11 of a Classic game (pinned by `backend/tests/games/test_play_fixture.py`).
const state = fixture.seat_state as SeatState;

describe("weekColumns", () => {
  it("runs from Uke 1 to nå + 4, the phone showing nå − 7 onwards", () => {
    const columns = weekColumns(11);
    expect(columns.map((c) => c.week)).toEqual(Array.from({ length: 15 }, (_, i) => i + 1));
    expect(columns.filter((c) => c.phone).map((c) => c.week)).toEqual([4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
    expect(columns.find((c) => c.when === "now")?.week).toBe(11);
    expect(columns.filter((c) => c.when === "future").map((c) => c.week)).toEqual([12, 13, 14, 15]);
  });

  it("starts at Uke 1 while nå is below 8", () => {
    expect(weekColumns(1).map((c) => [c.week, c.when, c.phone])).toEqual([
      [1, "now", true],
      [2, "future", true],
      [3, "future", true],
      [4, "future", true],
      [5, "future", true],
    ]);
    expect(weekColumns(7).every((c) => c.phone)).toBe(true);
  });
});

describe("netStep", () => {
  it("bins |v| into the four matrix steps by sign, zero apart", () => {
    expect([0, 1, 9, 10, 19, 20, 34, 35, 120].map(netStep)).toEqual([
      "zero",
      "pos-1",
      "pos-1",
      "pos-2",
      "pos-2",
      "pos-3",
      "pos-3",
      "pos-4",
      "pos-4",
    ]);
    expect([-1, -9, -10, -19, -20, -34, -35].map(netStep)).toEqual([
      "neg-1",
      "neg-1",
      "neg-2",
      "neg-2",
      "neg-3",
      "neg-3",
      "neg-4",
    ]);
  });
});

describe("cellFor", () => {
  it("writes the earlier Uker from the history as the api gave them", () => {
    expect(cellFor(state, "incomingOrder", 9)).toEqual({ kind: "plain", text: "12" });
    expect(cellFor(state, "netInventory", 9)).toEqual({ kind: "net", text: `${MINUS}8`, step: "neg-1" });
    expect(cellFor(state, "netInventory", 8)).toEqual({ kind: "net", text: "0", step: "zero" });
    expect(cellFor(state, "position", 10)).toEqual({ kind: "plain", text: `${MINUS}2` });
    expect(cellFor(state, "order", 10)).toEqual({ kind: "plain", text: "8" });
    expect(cellFor(state, "cost", 10)).toEqual({ kind: "plain", text: "14" });
    expect(cellFor(state, "unitsShipped", 4)).toEqual({ kind: "plain", text: "4" });
    expect(cellFor(state, "supplyLine", 4)).toEqual({ kind: "plain", text: "12" });
  });

  it("writes nå from the open Week, with an empty dashed Din ordre", () => {
    expect(cellFor(state, "incomingOrder", 11)).toEqual({ kind: "plain", text: "10" });
    expect(cellFor(state, "netInventory", 11)).toEqual({ kind: "net", text: `${MINUS}20`, step: "neg-3" });
    expect(cellFor(state, "position", 11)).toEqual({ kind: "plain", text: `${MINUS}4` });
    expect(cellFor(state, "supplyLine", 11)).toEqual({ kind: "plain", text: "16" });
    expect(cellFor(state, "order", 11)).toEqual({ kind: "order-empty" });
    expect(cellFor(state, "cost", 11)).toEqual({ kind: "plain", text: "20" });
  });

  it("right of nå shows only the known arrivals, each in its Uke", () => {
    expect([12, 13, 14, 15].map((w) => cellFor(state, "incomingDelivery", w))).toEqual([
      { kind: "arrival", text: "4" },
      { kind: "arrival", text: "4" },
      { kind: "arrival", text: "8" },
      { kind: "empty" },
    ]);
    for (const row of ROWS.filter((r) => r.key !== "incomingDelivery")) {
      expect(cellFor(state, row.key, 12)).toEqual({ kind: "empty" });
    }
  });

  it("has the phone's rows, with Sendt and På vei for the laptop only", () => {
    expect(ROWS.filter((r) => !r.laptopOnly).map((r) => r.label)).toEqual([
      "Ordre inn",
      "Levering",
      "Netto lager",
      "Posisjon",
      "Din ordre",
      "Kost, kr",
    ]);
    expect(ROWS.map((r) => r.label)).toEqual([
      "Ordre inn",
      "Levering",
      "Sendt",
      "Netto lager",
      "På vei",
      "Posisjon",
      "Din ordre",
      "Kost, kr",
    ]);
  });
});
