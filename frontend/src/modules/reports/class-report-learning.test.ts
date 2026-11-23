import { describe, expect, it } from "vitest";

import { type ClassLearning, classLearningKey, classReportKey } from "./class-report-api";
import {
  aiLine,
  bandRows,
  learningStatus,
  questionBars,
  questionRows,
  scoreSummary,
  startingBars,
  startingRows,
} from "./class-report-learning";

type Question = ClassLearning["questions"][number];

const question = (over: Partial<Question>): Question => ({
  number: 1,
  id: "flervalg",
  title: "Flervalg om årsaker",
  type: "choice",
  weight: 5,
  excluded: false,
  scoring: "computed",
  students: 4,
  answered: 3,
  right: 2,
  partly: 0,
  wrong: 1,
  not_answered: 1,
  percent: "50.0",
  ...over,
});

const ai = (over: Partial<ClassLearning["ai"]>): ClassLearning["ai"] => ({
  state: "ready",
  ready: 2,
  submitted: 3,
  total: {
    values: ["41.5", "80.0"],
    median: "60.8",
    lower_quartile: "51.1",
    upper_quartile: "70.4",
  },
  core: {
    values: ["50.0", "100.0"],
    median: "75.0",
    lower_quartile: "62.5",
    upper_quartile: "87.5",
  },
  bands: [
    { low: 40, high: 50, total: 1, core: 0 },
    { low: 90, high: 100, total: 0, core: 1 },
  ],
  ...over,
});

describe("the learning part's text", () => {
  it("says how many handed in and how many still may", () => {
    expect(
      learningStatus({ students: 20, submitted: 14, still_to_submit: 3 }),
    ).toBe("14 av 20 studenter har levert testen. 3 kan fortsatt levere.");
    expect(
      learningStatus({ students: 1, submitted: 1, still_to_submit: 0 }),
    ).toBe("1 av 1 student har levert testen.");
    expect(
      learningStatus({ students: 0, submitted: 0, still_to_submit: 0 }),
    ).toBe("Klasseøkta har ingen studenter å vise resultater for.");
  });

  it("puts the Starting task beside the test item with the api's percents", () => {
    const item = {
      number: 1,
      title: "Sende",
      students: 3,
      start_correct: 2,
      start_percent: "66.7",
      test_right: 3,
      test_percent: "100.0",
    };
    const [start, test] = startingBars(item);
    expect([start!.count, start!.share, start!.reads]).toEqual([
      "66,7 %",
      0.667,
      "Startoppgaven, riktig: 2 av 3 (66,7 %)",
    ]);
    expect([test!.count, test!.share]).toEqual(["100,0 %", 1]);
    expect(startingRows([item])[0]).toEqual({
      key: "1",
      head: "1. Sende",
      cells: ["3", "2 (66,7 %)", "3", "100,0 %"],
    });
  });

  it("marks a question taken out and a long answer, and shows the mean of a computed one", () => {
    const rows = [
      question({}),
      question({
        id: "ut",
        number: null,
        excluded: true,
        scoring: "excluded",
        weight: null,
        students: 0,
        percent: null,
      }),
      question({
        id: "lang",
        number: 2,
        type: "long",
        scoring: "ai",
        answered: 3,
        percent: null,
      }),
    ];
    const bars = questionBars(rows);
    expect(bars.map((bar) => [bar.label, bar.count])).toEqual([
      ["1. Flervalg om årsaker", "50,0 %"],
      ["Flervalg om årsaker", "Tatt ut"],
      ["2. Flervalg om årsaker", "Vurderes av KI"],
    ]);
    expect(bars[0]!.reads).toBe(
      "1. Flervalg om årsaker: snitt 50,0 %, 3 av 4 svarte",
    );
    expect(questionRows(rows).map((row) => row.cells)).toEqual([
      ["4", "2", "0", "1", "1", "50,0 %"],
      ["Tatt ut", "–", "–", "–", "–", "–"],
      ["4", "–", "–", "–", "1", "Vurderes av KI"],
    ]);
  });

  it("states the AI part's state and formats its scores", () => {
    expect(aiLine(ai({ state: "switched_off" }))).toMatch(/slått av/);
    expect(aiLine(ai({ state: "not_ready" }))).toMatch(/ikke klare/);
    expect(aiLine(ai({}))).toBe("2 av 3 innleverte tester er vurdert.");
    expect(scoreSummary(ai({}).total!)).toBe(
      "Median 60,8. Midterste halvdel 51,1–70,4.",
    );
    expect(bandRows(ai({}))).toEqual([
      { key: "40", head: "40–50", cells: ["1", "0"] },
      { key: "90", head: "90–100", cells: ["0", "1"] },
    ]);
  });

  it("keeps its query under the report's key, so `session:<id>` refetches it with the report", () => {
    expect(classLearningKey("s1").slice(0, classReportKey("s1").length)).toEqual([...classReportKey("s1")]);
  });

  it("reads an item no Student reached as no answers, not as 0 %", () => {
    const [start] = startingBars({
      number: 3,
      title: "Posisjon",
      students: 0,
      start_correct: 0,
      start_percent: null,
      test_right: 0,
      test_percent: null,
    });
    expect([start!.count, start!.reads]).toEqual(["–", "Startoppgaven, riktig: Ingen har levert ennå."]);
  });
});
