import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { osloDateText } from "@/modules/sessions/dates";

import type { ManagedStudentPage } from "./api";
import { canExtend, checkDeadline, deadlineLines, refusalOnField, type StudentDeadlines } from "./deadline";
import { DeadlineBlock } from "./deadline-block";

/** The block «Frister» (Story 11.13, FR-18): its lines, the form's rule and its states. */
const copy = nb.reports.deadline;

const CLASS_TEST = "2026-12-18T09:00:00Z"; // fr. 18. des. kl. 10:00 in Oslo
const CLASS_DEBRIEF = "2026-12-11T09:00:00Z";

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

const deadlines = (over: Partial<StudentDeadlines> = {}): StudentDeadlines => ({
  class_debrief_deadline: CLASS_DEBRIEF,
  class_test_deadline: CLASS_TEST,
  debrief_deadline: CLASS_DEBRIEF,
  test_deadline: CLASS_TEST,
  extended: false,
  submitted: false,
  ...over,
});

const page = (over: Partial<StudentDeadlines> = {}): ManagedStudentPage => ({
  class_session_id: "s1",
  class_id: "c1",
  class_name: "Klasse",
  session_number: 1,
  user_id: "u-jonas",
  name: "Jonas",
  class_share: 80,
  adjustment: null,
  deadlines: deadlines(over),
  can_manage: true,
});

describe("Frister's words", () => {
  it("names the Student's dates in Oslo time and says whether they are extended", () => {
    expect(deadlineLines(deadlines())).toEqual([
      `Testfrist: ${osloDateText(CLASS_TEST)}.`,
      `Debrieffrist: ${osloDateText(CLASS_DEBRIEF)}.`,
      "Som klassen.",
    ]);
    expect(osloDateText(CLASS_TEST)).toMatch(/^fr\. 18\. des\. kl\.\s10:00$/);
    const own = "2026-12-21T09:00:00Z";
    expect(deadlineLines(deadlines({ test_deadline: own, debrief_deadline: null, extended: true }))).toEqual([
      `Testfrist: ${osloDateText(own)}.`,
      `Forlenget. Klassens testfrist: ${osloDateText(CLASS_TEST)}.`,
    ]);
    expect(deadlineLines(deadlines({ class_test_deadline: null, test_deadline: null }))).toEqual([copy.noTest]);
  });

  it("offers the extension only with a Test deadline and before the hand-in", () => {
    expect(canExtend(deadlines())).toBe(true);
    expect(canExtend(deadlines({ submitted: true }))).toBe(false);
    expect(canExtend(deadlines({ class_test_deadline: null }))).toBe(false);
  });

  it("takes only a date after the Class's Test deadline and after now", () => {
    const now = Date.parse("2026-12-01T09:00:00Z");
    expect(checkDeadline("2026-12-21T10:00", CLASS_TEST, now)).toEqual({ at: "2026-12-21T09:00:00.000Z" });
    expect(checkDeadline("", CLASS_TEST, now)).toEqual({ error: copy.errors.required });
    expect(checkDeadline("2026-12-18T10:00", CLASS_TEST, now)).toEqual({
      error: copy.errors.not_later(osloDateText(CLASS_TEST)),
    });
    expect(checkDeadline("2026-12-21T10:00", CLASS_TEST, Date.parse("2026-12-22T00:00:00Z"))).toEqual({
      error: copy.errors.passed,
    });
  });

  it("says the api's reasons on the field", () => {
    expect(refusalOnField("not_later", CLASS_TEST)).toBe(copy.errors.not_later(osloDateText(CLASS_TEST)));
    expect(refusalOnField("passed", CLASS_TEST)).toBe(copy.errors.passed);
    expect(refusalOnField("no_test_deadline", CLASS_TEST)).toBeUndefined();
  });
});

describe("The block «Frister»", () => {
  it("shows the dates with «Forleng testfrist», and the form in place when open", () => {
    const idle = html(<DeadlineBlock data={page()} open={false} onOpenChange={() => {}} />);
    expect(idle).toContain(copy.title);
    expect(idle).toContain(copy.change);
    expect(idle).not.toContain("data-deadline-form");
    const open = html(<DeadlineBlock data={page()} open onOpenChange={() => {}} />);
    expect(open).toContain("data-deadline-form");
    expect(open).toContain('type="datetime-local"');
    expect(open).toContain('value="2026-12-18T10:00"');
    expect(open).toContain(copy.scope("Jonas"));
    expect(open).toContain(copy.save);
  });

  it("has no button once the Student has handed in, only the line", () => {
    const done = html(<DeadlineBlock data={page({ submitted: true })} open onOpenChange={() => {}} />);
    expect(done).toContain(copy.submitted("Jonas"));
    expect(done).not.toContain(copy.change);
    expect(done).not.toContain("data-deadline-form");
  });
});
