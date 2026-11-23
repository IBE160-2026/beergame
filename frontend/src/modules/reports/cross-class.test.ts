import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { GROUP } from "@/lib/number-format";

import type { CrossClass } from "./cross-class-api";
import {
  comparableText,
  compareRows,
  differsText,
  formatValue,
  measureName,
  nothingToCompare,
  optionName,
  sessionName,
  splitSessions,
} from "./cross-class";

const A = "01a1f8ee-34f2-70af-8800-f79281ed7a00";
const B = "01a1f8ee-34f2-70af-8800-f79281ed7a01";
const C = "01a1f8ee-34f2-70af-8800-f79281ed7a02";

const data: CrossClass = {
  sessions: [
    {
      class_session_id: A,
      class_name: "class-of-1993",
      session_number: 1,
      archived: true,
      written_at: "2026-01-02T09:00:00Z",
      compared: true,
      differs: ["ai_mode", "model"],
    },
    {
      class_session_id: B,
      class_name: "class-of-1994",
      session_number: 1,
      archived: false,
      written_at: "2026-11-20T09:00:00Z",
      compared: true,
      differs: [],
    },
    {
      class_session_id: C,
      class_name: "class-of-1994",
      session_number: 2,
      archived: false,
      written_at: null,
      compared: false,
      differs: [],
    },
  ],
  measures: [
    {
      key: "chain.median",
      unit: "kroner",
      values: [
        { class_session_id: A, value: "2740.00", withheld: false },
        { class_session_id: B, value: "1954.40", withheld: false },
      ],
      comparable: null,
    },
    {
      key: "core.median",
      unit: "points",
      values: [
        { class_session_id: A, value: null, withheld: true },
        { class_session_id: B, value: null, withheld: false },
      ],
      comparable: false,
    },
  ],
  filters: [],
};

describe("Tverrklasse-statistikk (Story 14.3)", () => {
  it("names a Class session by its Class and number", () => {
    expect(sessionName(data.sessions[1]!)).toBe("class-of-1994, Klasseøkt 1");
  });

  it("has nothing to compare with fewer than two Class sessions", () => {
    expect(nothingToCompare(data)).toBe(false);
    expect(
      nothingToCompare({
        sessions: data.sessions.slice(0, 1),
        measures: [],
        filters: [],
      }),
    ).toBe(true);
  });

  it("compares the sessions with an aggregate and lists the others", () => {
    const { ready, compared, waiting } = splitSessions(data);
    expect(ready.map((s) => s.class_session_id)).toEqual([A, B]);
    expect(compared.map((s) => s.class_session_id)).toEqual([A, B]);
    expect(waiting.map((s) => s.class_session_id)).toEqual([C]);
  });

  it("formats each unit with the shared formatter", () => {
    expect(formatValue("kroner", "2740.00")).toBe(`2${GROUP}740 kr`);
    expect(formatValue("ratio", "6.456")).toBe("6,46×");
    expect(formatValue("percent", "8.45")).toBe("8,5 %");
    expect(formatValue("points", "71")).toBe("71,0");
  });

  it("scales bars to the highest value and says withheld and missing figures in words", () => {
    const [chain, core] = data.measures;
    const rows = compareRows(chain!, data.sessions);
    expect(rows.map((r) => r.share)).toEqual([1, 1954.4 / 2740]);
    expect(rows[0]!.reads).toBe(`class-of-1993, Klasseøkt 1: 2${GROUP}740 kr. Ulikt oppsett: KI-modus, modell`);
    expect(rows[1]!.reads).toBe(`class-of-1994, Klasseøkt 1: 1${GROUP}954 kr`);
    expect(rows.map((r) => r.differs)).toEqual(["Ulikt oppsett: KI-modus, modell", null]);
    const words = compareRows(core!, data.sessions);
    expect(words.map((r) => [r.text, r.share])).toEqual([
      [nb.crossClass.withheld, null],
      [nb.crossClass.notMeasured, null],
    ]);
  });

  it("names every compared measure from the copy", () => {
    expect(measureName("chain.median")).toBe("Median kjedekost, kr");
    expect(measureName("amplification.factory.median")).toBe("Median Forsterkning, Fabrikk");
  });
});

describe("Filters and difference labels (Story 14.4)", () => {
  it("names the api's options from the copy, the data as it is", () => {
    expect(optionName("game_settings", { label: "classic", ordinal: 0 })).toBe("Klassisk");
    expect(optionName("game_settings", { label: null, ordinal: 2 })).toBe("Oppsett 2");
    expect(optionName("ai_mode", { label: "rule_based", ordinal: 0 })).toBe("Regelbaserte spillere");
    expect(optionName("model", { label: "DeepSeek flash", ordinal: 0 })).toBe("DeepSeek flash");
    expect(optionName("effort_level", { label: null, ordinal: 0 })).toBe(nb.crossClass.none);
  });

  it("says what a Class session differs in, in words", () => {
    expect(differsText([])).toBeNull();
    expect(differsText(["question_set", "item_weights", "scoring_guide"])).toBe(
      "Ulikt oppsett: spørsmålssett, vekter, vurderingsveiledning",
    );
  });

  it("says whether the scores compare, only for a score measure", () => {
    expect(comparableText({ comparable: null })).toBeNull();
    expect(comparableText({ comparable: true })).toBe(nb.crossClass.scoresComparable);
    expect(comparableText({ comparable: false })).toBe(nb.crossClass.scoresNotComparable);
  });
});
