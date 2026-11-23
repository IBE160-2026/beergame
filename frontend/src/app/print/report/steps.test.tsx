import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { reportCopy } from "./copy";
import { answerBlocks, debriefLine, type DebriefSection, points, type ReplayData, scenarioRows, type TestData, type TestItem, testLine } from "./parts";
import { Report } from "./report";
import type { ReportData } from "./sections";
import { scoreLine } from "./test-section";

const walk = nb.replay.walkthrough;

function report(section: ReportData["sections"][number]): string {
  const data: ReportData = {
    schema_version: 1,
    generated_at: "2026-12-11T09:05:00Z",
    student_name: "Sara Nilsen",
    class_name: "IBE160 høst",
    session_number: 2,
    dates: { start_at: null, play_deadline: null, debrief_deadline: null, test_deadline: null },
    sections: [section],
  };
  return renderToStaticMarkup(<Report data={data} />);
}

const text = (value: string, ai = false) => ({ text: value, ai_generated: ai });

function debrief(over: Partial<DebriefSection> = {}): DebriefSection {
  return {
    kind: "debrief",
    explanation: "Fabrikken svingte mest,\nfordi ordrene kom sent.",
    explanation_saved_at: "2026-11-20T17:00:00Z",
    finished_at: "2026-11-21T17:00:00Z",
    late: false,
    moments: [
      {
        week: 9,
        heading: text("Uke 9: du bestilte 20 da 16 allerede var på vei."),
        reckoning: text("Posisjon 0 − 13 + 16 = 3."),
        later: text("De neste fire ukene kostet setet ditt 54,00 kr."),
        patterns: [text("Stor ordre mens mye allerede er på vei.")],
      },
    ],
    narration: text("Øyeblikkene henger sammen.", true),
    reflection: [{ prompt: "Hva viste tallene?", text: "Fabrikken svingte mest." }],
    quiz_attempts: 2,
    quiz_passed: true,
    ...over,
  };
}

function weeks(...nets: number[]) {
  return nets.map((net, i) => ({ week: i + 1, net_inventory: net, order: 4, total_cost: `${i + 1}.00` }));
}

function replay(over: Partial<ReplayData> = {}): ReplayData {
  return {
    state: "finished",
    role: "wholesaler",
    scenario: {
      weeks: 3,
      guided_weeks: 0,
      starting_inventory: 12,
      starting_backlog: 0,
      order_delay: 2,
      shipping_delay: 2,
      production_delay: 1,
      holding_cost: "0.50",
      backorder_cost: "1.00",
    },
    replay: { weeks: weeks(4, -2, 1), total_cost: "3.00" },
    class_game: { weeks: weeks(0, 5), total_cost: "2.00" },
    class_game_number: 17,
    mostly_ai: false,
    ...over,
  };
}

const TABLE = {
  prompt: "Fyll inn lageret ved slutten av hver uke.",
  hint: null,
  caption: "Bakeriets lager per uke, i enheter",
  rows: ["Uke 1", "Uke 2", "Uke 3"],
  columns: [{ label: "Inn", values: [20, 20, 25] }],
  asked_label: "Lager",
  negative: false,
  axis: null,
};

function item(over: Partial<TestItem>): TestItem {
  return { number: 1, type: "choice", title: text("Hvorfor svinger ordrene?"), options: ["a", "b"], table: null, column: null, answer: null, weight: 10, points: null, ...over };
}

function test(over: Partial<TestData> = {}): TestData {
  return {
    state: "submitted",
    submitted_at: "2026-11-25T20:40:00Z",
    items: [
      item({ number: 1, answer: "b", points: "10.00" }),
      item({ number: 2, type: "table", title: text("Tabell"), table: TABLE, answer: [18, null, 30], weight: 15, points: "7.50" }),
      item({
        number: 3,
        type: "number",
        title: text("Tall"),
        column: { prompt: "Hvor mange enheter mangler?", hint: null, caption: "Mangler per uke", rows: [{ label: "Uke 1", value: 3 }], asked_label: "Legg til", negative: false, starting_task: false },
        answer: 16,
        weight: 5,
        points: "0.00",
      }),
      item({ number: 4, type: "long", title: text("Forklar forsinkelsen."), answer: "Et langsvar.\nTo linjer.", weight: 30 }),
      item({ number: 5, type: "adapted", title: text("Uke 9 i spillet ditt: hvorfor?", true), weight: 20 }),
    ],
    points: "17.50",
    points_of: 30,
    ...over,
  };
}

describe("the report's Debrief section (Story 13.10)", () => {
  it("holds the Explanation as written, the moments, the line, the answers and the attempts", () => {
    const html = report(debrief());
    expect(html).toContain(`>${reportCopy.debrief.title}</h2>`);
    expect(html).toContain("Fabrikken svingte mest,\nfordi ordrene kom sent.");
    expect(html).toContain("Uke 9: du bestilte 20 da 16 allerede var på vei.");
    expect(html).toContain(`${walk.reckoned}: Posisjon 0 − 13 + 16 = 3.`);
    expect(html).toContain("Hva viste tallene?");
    expect(html).toContain(reportCopy.debrief.reflectionNote);
    expect(html).toContain("Bestått etter 2 forsøk.");
    // Only AI text is marked, from the flag: the prefix for readers, the attribute for the PDF.
    expect(html).toContain('<span data-ai-generated="true">KI-generert, kan ta feil: «Øyeblikkene henger sammen.»</span>');
    expect(html.match(/data-ai-generated/g)).toHaveLength(1);
  });

  it("says what was not done", () => {
    const html = report(debrief({ explanation: null, explanation_saved_at: null, finished_at: null, moments: [], narration: null, reflection: [], quiz_attempts: 0, quiz_passed: false }));
    expect(html).toContain(reportCopy.debrief.noExplanation);
    expect(html).toContain(reportCopy.debrief.notFinished);
    expect(html).toContain("Quizen ble ikke tatt.");
    expect(html).not.toContain(reportCopy.debrief.moments);
  });

  it("words the finish and the attempts", () => {
    expect(debriefLine({ finished_at: null, late: false })).toBe(reportCopy.debrief.notFinished);
    expect(debriefLine({ finished_at: "2026-11-21T17:00:00Z", late: true })).toMatch(/etter Debrieffristen\.$/);
    expect(reportCopy.debrief.attempts(1, true)).toBe("Bestått på første forsøk.");
    expect(reportCopy.debrief.attempts(3, false)).toBe("3 forsøk, ikke bestått.");
  });
});

describe("the report's Replay section (Story 13.10)", () => {
  it("holds the scenario, both totals, «Ikke like for like.», the chart with its title and its table", () => {
    const html = report({ kind: "replay", replay: replay() });
    expect(html).toContain(`>${reportCopy.replay.scenario}</h3>`);
    expect(html).toContain("Ordre 2 uker, frakt 2 uker, produksjon 1 uker");
    expect(html).toContain("0,50 kr per enhet på lager, 1,00 kr per enhet i restordre, hver uke");
    expect(html).toContain("3,00 kr");
    expect(html).toContain(walk.classTotalLabel(17));
    expect(html).toContain(walk.unlike);
    expect(html).toContain(walk.unlikeWeeks(3, 2));
    const chart = html.indexOf('data-chart="net-over-game"');
    const table = html.indexOf("data-replay-table");
    expect(chart).toBeGreaterThan(0);
    expect(table).toBeGreaterThan(chart);
    expect(html).toMatch(/<svg[^>]*data-chart="net-over-game"[^>]*><title>/);
    // Every Uke of either run, the shorter one's missing Uke a dash.
    expect(html.match(/<th scope="row" class="py-1 text-left font-normal">\d<\/th>/g)).toHaveLength(3);
    expect(html).toContain(walk.noWeek);
  });

  it("leaves a mostly-AI Class game out, and draws a closed Replay's Uker alone", () => {
    const alone = report({ kind: "replay", replay: replay({ class_game: null, class_game_number: null, mostly_ai: true }) });
    expect(alone).toContain(walk.mostlyAi);
    expect(alone).not.toContain(walk.unlike);
    const closed = report({ kind: "replay", replay: replay({ state: "closed", class_game: null, class_game_number: null }) });
    expect(closed).toContain(reportCopy.replay.closed);
    // The Uker it had: the Replay alone, no comparison.
    expect(closed).toContain('data-chart="net-over-game"');
    expect(closed).not.toContain(walk.unlike);
    const unplayed = report({ kind: "replay", replay: replay({ state: "open", replay: { weeks: [], total_cost: "0" }, class_game: null, class_game_number: null }) });
    expect(unplayed).toContain(reportCopy.replay.open);
    expect(unplayed).not.toContain('data-chart="net-over-game"');
    expect(report({ kind: "replay", replay: null })).toContain(reportCopy.replay.none);
  });

  it("lists the scenario in words", () => {
    expect(scenarioRows(replay(), "Grossist")[1]).toEqual({ name: "Uker", value: "3 av 3" });
  });
});

describe("the report's Individual test section (Story 13.10)", () => {
  it("holds every item with its answer and the computed points, an Interaktiv oppgave as an image over its table", () => {
    const html = report({ kind: "test", test: test() });
    expect(html).toContain(`>${reportCopy.test.title}</h2>`);
    expect(html).toContain("Poeng regnet ut av koden: 17,5 av 30.");
    expect(html).toContain("Ditt svar: Alternativ B");
    expect(html).toContain("Poeng: 10 av 10");
    expect(html).toContain("Poeng: 7,5 av 15");
    expect(html).toContain("Poeng: 0 av 5");
    expect(html).toContain("Et langsvar.\nTo linjer.");
    expect(html.match(new RegExp(reportCopy.test.notScored, "g"))).toHaveLength(2);
    // The table item: the points' SVG with its title, then the table with the Student's row.
    const image = html.slice(html.indexOf("data-answer-image"));
    expect(image).toMatch(/<svg[^>]*data-chart="points"[^>]*><title>Graf: Bakeriets lager per uke, i enheter<\/title>/);
    expect(image.match(/data-mark="point"/g)).toHaveLength(2);
    expect(image).toContain('<th scope="col" data-col="1"');
    expect(image).toMatch(/data-answer-row=""><th scope="row"[^>]*>Lager<\/th>/);
    expect(html).toContain(reportCopy.test.empty);
    // The number item: its column with the answer in the asked row.
    expect(html).toMatch(/data-answer-column=""[\s\S]*Legg til<\/th><td[^>]*>16<\/td>/);
    // The Adapted item an AI worded: the prefix and the mark; nothing else marked.
    expect(html).toContain('<span data-ai-generated="true">KI-generert, kan ta feil: «Uke 9 i spillet ditt: hvorfor?»</span>');
    expect(html.match(/data-ai-generated/g)).toHaveLength(1);
    // Every SVG has its title.
    const svgs = html.match(/<svg[^>]*>/g) ?? [];
    expect(svgs.length).toBeGreaterThan(1);
    expect(html.match(/<svg[^>]*><title>/g)).toHaveLength(svgs.length);
  });

  it("says when the test was not handed in or never opened", () => {
    const open = report({ kind: "test", test: test({ state: "open", submitted_at: null, points: null, points_of: 0, items: [item({ answer: null })] }) });
    expect(open).toContain(reportCopy.test.open);
    expect(open).toContain(nb.tests.individual.interactive.notAnswered);
    expect(open).not.toContain("Poeng:");
    expect(report({ kind: "test", test: null })).toContain(reportCopy.test.none);
    expect(testLine({ state: "auto_submitted", submitted_at: "2026-11-25T22:59:00Z" })).toMatch(/^Levert automatisk/);
  });

  it("writes points the Norwegian way and splits long tables into even blocks", () => {
    expect(points("7.50")).toBe("7,5");
    expect(points("10.00")).toBe("10");
    expect(scoreLine({ points: null, weight: 10, type: "choice" })).toBeNull();
    expect(answerBlocks(6, 10)).toEqual([{ from: 1, to: 6 }]);
    expect(answerBlocks(12, 10)).toEqual([
      { from: 1, to: 6 },
      { from: 7, to: 12 },
    ]);
    expect(answerBlocks(0, 10)).toEqual([]);
  });
});
