import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { reportCopy } from "@/app/print/report/copy";
import { Report } from "@/app/print/report/report";
import { type CompletionSection, requirementLine, type ReportData, shareLines, stepStatus } from "@/app/print/report/sections";
import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";
import { stepItems } from "@/modules/games/home";

import { myReportKey, type ReportState, staffReportKey, staffReportsKey } from "./api";
import type { StudentRecord } from "./record";
import { RecordBlocks } from "./record-blocks";
import { downloadView, StaffReportDownload } from "./report-download";

/** The Student report (Story 13.7, FR-57, FR-58, UX-DR29): the download's states, the «Rapport»
 * step's words, and the print route's report (header, tables with scopes, lines in words). */
const state = (over: Partial<ReportState> = {}): ReportState => ({
  opens_at: "2026-12-10T22:59:00Z",
  open: true,
  status: "none",
  generated_at: null,
  ai: false,
  ai_available: false,
  deleted: false,
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

describe("the staff's download on the Studentside (Story 13.12)", () => {
  const staffCopy = nb.reports.download;
  const render = (seeded: ReportState) => {
    const client = new QueryClient();
    client.setQueryData(staffReportKey("s1", "u1"), seeded);
    return renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <StaffReportDownload sessionId="s1" userId="u1" />
      </QueryClientProvider>,
    );
  };

  it("is open at any time, links to the staff's file and says what the report is", () => {
    const html = render(state({ opens_at: null, status: "ready", generated_at: "2026-12-11T09:00:00Z" }));
    expect(html).toContain('href="/api/class-sessions/s1/students/u1/report/file"');
    expect(html).toContain(staffCopy.link);
    expect(html).toContain(staffCopy.again);
    expect(html).toContain(staffCopy.staff.note);
    expect(html).not.toContain(staffCopy.note);
    // No AI assessment to add: no Bryter.
    expect(html).not.toContain(staffCopy.ai.control);
  });

  it("offers the AI section off by default, with the staff's help line on the letter", () => {
    const html = render(state({ opens_at: null, ai_available: true }));
    expect(html).toContain(staffCopy.ai.control);
    expect(html).toContain('data-report-ai="off"');
    expect(html).toContain(staffCopy.staff.aiHelp);
    expect(html).not.toContain(staffCopy.ai.help);
    expect(html).toContain(staffCopy.make);
  });

  it("says the data is deleted and offers nothing once the deletion date has come", () => {
    expect(downloadView(state({ deleted: true }), false)).toEqual({ kind: "deleted" });
    const html = render(state({ opens_at: null, deleted: true, ai_available: false }));
    expect(html).toContain(staffCopy.staff.deleted);
    expect(html).not.toContain(staffCopy.make);
    expect(html).not.toContain(staffCopy.link);
  });

  it("is no download for a Student the reports leave out", () => {
    const record: StudentRecord = {
      class_session_id: "s1",
      class_id: "c1",
      class_name: "Logistikk 1",
      session_number: 1,
      user_id: "u1",
      name: "Sara Student",
      can_manage: false,
      can_correct: false,
      can_give_makeup: false,
      test_deadline: null,
      completion: null, // reports leave the Student out
      participation: null,
      game: null,
      makeup: null,
      debrief: { explanation: null, explanation_saved_at: null, finished_at: null, late: false, moments: 0 },
      quiz: [],
      replay: null,
      test: null,
      assessment: null,
    };
    const html = renderToStaticMarkup(
      <QueryClientProvider client={new QueryClient()}>
        <RecordBlocks record={record} />
      </QueryClientProvider>,
    );
    expect(html).toContain('data-record="report"');
    expect(html).toContain(nb.reports.record.report.notCounted);
    expect(html).not.toContain(staffCopy.make);
  });

  it("is read again on the requester's user event, apart from the Student's own", () => {
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(staffReportsKey);
    expect(staffReportKey("s1", "u1").slice(0, 2)).toEqual(["reports", "staff"]);
    expect(staffReportKey("s1", "u1", true)).not.toEqual(staffReportKey("s1", "u1"));
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
