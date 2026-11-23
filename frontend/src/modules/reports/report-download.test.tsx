import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { reportCopy } from "@/app/print/report/copy";
import { Report } from "@/app/print/report/report";
import { type CompletionSection, requirementLine, type ReportData, shareLines, stepStatus } from "@/app/print/report/sections";
import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";
import { stepItems } from "@/modules/games/home";

import { myReportKey, type ReportState } from "./api";
import { downloadView } from "./report-download";

/** The Student report (Story 13.7, FR-57, FR-58, UX-DR29): the download's states, the «Rapport»
 * step's words, and the print route's report (header, tables with scopes, lines in words). */
const state = (over: Partial<ReportState> = {}): ReportState => ({
  opens_at: "2026-12-10T22:59:00Z",
  open: true,
  status: "none",
  generated_at: null,
  ai: false,
  ai_available: false,
  ...over,
});

describe("downloadView", () => {
  it("says when it opens before the Testfrist, and offers the action after", () => {
    expect(downloadView(state({ open: false }), false)).toEqual({ kind: "closed", opensAt: "2026-12-10T22:59:00Z" });
    expect(downloadView(state(), false)).toEqual({ kind: "make" });
  });

  it("shows the pending line while the press runs and while the api says pending", () => {
    expect(downloadView(state(), true)).toEqual({ kind: "pending" });
    expect(downloadView(state({ status: "pending" }), false)).toEqual({ kind: "pending" });
  });

  it("offers the download once ready, and the retry once failed", () => {
    expect(downloadView(state({ status: "ready", generated_at: "2026-12-11T09:00:00Z" }), false)).toEqual({
      kind: "ready",
    });
    expect(downloadView(state({ status: "failed" }), false)).toEqual({ kind: "failed" });
  });

  it("is read again on the Student's user event", () => {
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(["reports", "mine"]);
    expect(myReportKey("s1").slice(0, 2)).toEqual(["reports", "mine"]);
    // Story 13.11: the report with the AI section is a state of its own under the same key.
    expect(myReportKey("s1", true).slice(0, 2)).toEqual(["reports", "mine"]);
    expect(myReportKey("s1", true)).not.toEqual(myReportKey("s1"));
  });
});

describe("the «Rapport» step", () => {
  it("is locked with what opens it, and open once the api says so", () => {
    const step = {
      held: false,
      quiz_changed: false,
      group_open: false,
      closed: false,
      after_makeup: false,
      corrected: false,
    };
    const [locked] = stepItems([{ step: "report", state: "locked", ...step }]);
    expect(locked.note).toBe("Rapport, åpnes når Testfristen er ute.");
    const [open] = stepItems([{ step: "report", state: "current", ...step }], "s1");
    expect(open.state).toBe("current");
    expect(open.note).toBe(nb.homes.student.reportOpen);
    expect(open.href).toBeUndefined();
  });
});

const data = (over: Partial<CompletionSection> = {}): ReportData => ({
  schema_version: 1,
  generated_at: "2026-12-11T09:05:00Z",
  student_name: "Sara Nilsen",
  class_name: "IBE160 høst",
  session_number: 2,
  dates: {
    start_at: "2026-11-24T09:00:00Z",
    play_deadline: "2026-12-01T22:59:00Z",
    debrief_deadline: "2026-12-04T22:59:00Z",
    test_deadline: null,
  },
  sections: [
    {
      kind: "completion",
      obligatory: true,
      requirement_met: false,
      required_share: 80,
      ordered_share: 70,
      playout_share: 20,
      share_game: null,
      steps: [
        { step: "class_game", done: false, corrected: false },
        { step: "debrief", done: true, corrected: true },
        { step: "quiz_passed", done: true, corrected: false },
        { step: "replay", done: false, corrected: false },
        { step: "test_submitted", done: false, corrected: false },
      ],
      ...over,
    },
  ],
});

describe("the print route's report", () => {
  it("writes each step's status and the shares in words, through the Norwegian formatter", () => {
    const section = data().sections[0] as CompletionSection;
    expect(section.steps.map(stepStatus)).toEqual([
      "ikke gjort",
      "gjort, rettet av faglærer",
      "gjort",
      "ikke gjort",
      "ikke gjort",
    ]);
    expect(shareLines(section)).toEqual([
      "Bestilte selv i 70 % av ukene. Kravet er 80 %.",
      "20 % av ukene ble spilt i utspillingen ved Spillfristen.",
    ]);
    expect(requirementLine(section)).toBe("Kravet er ikke oppfylt.");
    expect(requirementLine({ ...section, requirement_met: true })).toBe("Kravet er oppfylt.");
    const free = data({ obligatory: false, requirement_met: null }).sections[0] as CompletionSection;
    expect(requirementLine(free)).toBe("Klasseøkten er ikke obligatorisk.");
    expect(shareLines(free)).toEqual([]);
  });

  it("is headed «ØL-spillet», names the Student, the Class and the dates, and says it is no grade", () => {
    const html = renderToStaticMarkup(<Report data={data()} />);
    expect(html).toContain(">ØL-spillet<");
    expect(html).toContain("<h1");
    expect(html).toContain("Sara Nilsen");
    expect(html).toContain("IBE160 høst");
    expect(html).toMatch(/Klasseøkt<\/dt><dd>2<\/dd>/);
    expect(html).toContain(reportCopy.purpose);
    expect(html).toContain("11. desember 2026 kl. 10:05");
    expect(html).toContain(">Ikke satt<");
    // Every table has a caption and header cells with scopes.
    expect(html.match(/<table/g)).toHaveLength(2);
    expect(html.match(/<caption/g)).toHaveLength(2);
    expect(html.match(/<th scope="col"/g)).toHaveLength(4);
    expect(html.match(/<th scope="row"/g)).toHaveLength(9);
    expect(html).not.toContain("<script");
  });
});
