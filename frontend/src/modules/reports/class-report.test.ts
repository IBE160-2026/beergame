import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";
import { GROUP } from "@/lib/number-format";

import type { ClassReport } from "./class-report-api";
import {
  aiSeatsLine,
  amplificationRows,
  costRoleRows,
  costSummary,
  coveredLine,
  fabrikkFirst,
  guardLine,
  llmRows,
  patternBars,
  ratingBars,
  ratingLine,
  sharedHighest,
  statusLine,
  switchLines,
} from "./class-report";
import { classReportKey } from "./class-report-api";

const spread = (median: string, low: string, high: string, values: string[]) => ({
  values,
  median,
  lower_quartile: low,
  upper_quartile: high,
});

const ROLES = ["retailer", "wholesaler", "distributor", "factory"] as const;

const report: ClassReport = {
  class_session_id: "01a1f8ee-34f2-70af-8800-f79281ed7a00",
  class_id: "01a1f8ee-34f2-70af-8800-f79281ed7a01",
  class_name: "class-of-2026",
  session_number: 2,
  games: 60,
  finished: 41,
  facts_games: 38,
  funnel: [{ stage: "registered", count: 60 }],
  cost: {
    chain: spread("1954.00", "1500.00", "2600.00", ["1500.00", "1954.00", "2600.00"]),
    holding_cost: "949.40",
    backorder_cost: "1063.10",
    roles: ROLES.map((role, i) => ({
      role,
      distribution: spread(`${(i + 1) * 100}.00`, `${(i + 1) * 80}.00`, `${(i + 1) * 120}.00`, [`${(i + 1) * 130}.00`]),
      holding_cost: "210.00",
      backorder_cost: "202.50",
      total_cost: "412.50",
    })),
    games: [{ number: 1, chain_cost: "1954.00" }],
  },
  amplification: ROLES.map((role, i) => ({
    role,
    games: i === 0 ? 0 : 38,
    distribution: i === 0 ? null : spread("2.40", "1.95", "3.10", ["2.40"]),
  })),
  patterns: [
    { pattern: "large-order-full-supply-line", name: "Stor ordre mens mye allerede er på vei", occurrences: 212, games: 30 },
    { pattern: "surge-after-shortage", name: "Ordre langt over innkommende ordre etter mangel", occurrences: 106, games: 22 },
  ],
  ai: {
    seats: 240,
    ai_seats: 14,
    whole_game: 9,
    ai_percent: "5.8",
    games: [
      { number: 1, ordered: 140, llm: 35, llm_percent: "25.0", fallback: 2 },
      { number: 2, ordered: 0, llm: 0, llm_percent: null, fallback: 0 },
    ],
    switches: [{ number: 4, role: "wholesaler", week: 12, mark: "guard_switch" }],
    llm_seats: 30,
    guard_switched: 2,
    guard_percent: "6.7",
  },
  ratings: [
    {
      ai_mode: "llm",
      count: 23,
      median: "4",
      values: [1, 2, 3, 4, 5].map((rating) => ({ rating, count: rating === 4 ? 10 : 2 })),
    },
  ],
};

describe("the Klasserapport's text (Story 14.1)", () => {
  it("reads none, some and all finished games with the real counts (FR-64)", () => {
    expect(statusLine({ games: 60, finished: 0 })).toBe("Ingen spill er ferdige ennå.");
    expect(statusLine({ games: 60, finished: 41 })).toBe(
      "Oppdateres etter hvert som studentene blir ferdige. 41 av 60 spill er med.",
    );
    expect(statusLine({ games: 60, finished: 60 })).toBe("Alle 60 spill er med.");
    expect(statusLine({ games: 0, finished: 0 })).toBe(nb.classReport.noGames);
    expect(coveredLine(report)).toBe("Fra 38 av 41 ferdige spill. Resten kommer når analysen er klar.");
    expect(coveredLine({ finished: 41, facts_games: 41 })).toBeNull();
    expect(coveredLine({ finished: 41, facts_games: 0 })).toBeNull();
  });

  it("puts Fabrikk at the top in Role lists and Detaljist first in per-Role tables (UX-DR73)", () => {
    expect(fabrikkFirst(report.cost!.roles).map((r) => r.role)).toEqual(["factory", "distributor", "wholesaler", "retailer"]);
    expect(costRoleRows(report.cost!).map((r) => r.name)).toEqual(["Detaljist", "Grossist", "Distributør", "Fabrikk"]);
    expect(costRoleRows(report.cost!)[0]).toMatchObject({ median: "100", middle: "80–120", holding: "210", backorder: "203" });
    expect(amplificationRows(report.amplification).map((r) => [r.name, r.median, r.middle])).toEqual([
      ["Detaljist", null, null],
      ["Grossist", "2,40", "1,95–3,10"],
      ["Distributør", "2,40", "1,95–3,10"],
      ["Fabrikk", "2,40", "1,95–3,10"],
    ]);
  });

  it("formats the api's numbers and computes none of its own (AD-10)", () => {
    expect(costSummary(report.cost!.chain)).toBe(`Median 1${GROUP}954. Midterste halvdel 1${GROUP}500–2${GROUP}600.`);
    expect(sharedHighest(report.cost!.roles.map((r) => r.distribution))).toBe(520);
    expect(aiSeatsLine(report.ai)).toBe("KI-spillere spilte 14 av 240 seter (5,8 %): 9 hele spillet, 5 en del av det.");
    expect(guardLine(report.ai)).toBe("Spillvakten byttet 2 av 30 seter med LLM-spiller (6,7 %).");
    expect(guardLine({ ...report.ai, llm_seats: 0, guard_percent: null })).toBe("Ingen seter hadde LLM-spiller.");
    expect(switchLines(report.ai)).toEqual(["Spill 4, Grossist, fra Uke 12: Byttet til regelbasert KI (spillvakt)"]);
    expect(llmRows(report.ai)).toEqual([
      { game: "Spill 1", ordered: "140", llm: "35", share: "25,0 %", fallback: "2" },
      { game: "Spill 2", ordered: "0", llm: "0", share: "–", fallback: "0" },
    ]);
  });

  it("titles the patterns «Mønstre» and reads each bar in text", () => {
    expect(nb.classReport.patterns.title).toBe("Mønstre");
    const bars = patternBars(report.patterns);
    expect(bars.map((b) => [b.count, b.share])).toEqual([
      ["212", 1],
      ["106", 0.5],
    ]);
    expect(bars[0]!.reads).toBe("Stor ordre mens mye allerede er på vei: 212 ganger i 30 spill");
  });

  it("shows the ratings per AI mode as counts and a median only (FR-70)", () => {
    const mode = report.ratings[0]!;
    expect(ratingLine(mode)).toBe("LLM-spillere: 23 svar, median 4.");
    expect(ratingBars(mode).map((b) => b.share)).toEqual([0.2, 0.2, 0.2, 1, 0.2]);
  });

  it("refetches on its Class session's topic (AD-8)", () => {
    const keys = topicKeys({ topic: "session", id: report.class_session_id, version: null });
    expect(keys).toContainEqual(classReportKey(report.class_session_id));
  });
});
