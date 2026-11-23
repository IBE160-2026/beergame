import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { topicKeys } from "@/lib/api/topics";

import { assessmentListKey, type MyAssessment, staffAssessmentKey } from "./api";
import { flagCount, flagCountText, rowFlagsText, stateLine } from "./assessment";
import { AssessmentView } from "./assessment-page";
import { FlagControl } from "./flag-control";

const flag = nb.assessment.flag;
const staff = nb.assessment.staff;

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

const FEEDBACK = { ai_generated: true, text: "Du skriver «x».", parts: [{ kind: "text" as const, text: "Du skriver «x»." }] };

const item = (id: string, flagged: boolean, feedback: typeof FEEDBACK | null = FEEDBACK) => ({
  id,
  number: 1,
  type: "long" as const,
  title: "Spørsmål",
  wording: null,
  weight: 10,
  points: 5,
  computed: null,
  ai: { assessed: true, step: 2, top: 4, label: "Middels", feedback, feedback_dropped: false, flagged },
});

const view = (items: ReturnType<typeof item>[]): MyAssessment => ({
  state: "ready",
  items,
  unassessed: [],
  total: 5,
  total_max: 10,
  checked: false,
});

describe("«Marker som feil» (Story 12.5)", () => {
  it("is a text toggle with aria-pressed, no icon, the spine's words before and after", () => {
    const off = html(<FlagControl classSessionId="s1" itemId="i1" flagged={false} />);
    expect(off).toContain('aria-pressed="false"');
    expect(off).toContain(flag.mark);
    expect(off).not.toContain(flag.marked);
    expect(off).not.toMatch(/<svg|<img/u);
    const on = html(<FlagControl classSessionId="s1" itemId="i1" flagged />);
    expect(on).toContain('aria-pressed="true"');
    expect(on).toContain(flag.marked);
    expect(on).toContain(`>${flag.undo}</button>`);
    expect(flag.marked).toBe("Markert. Faglærer ser det.");
    expect(flag.failed).toBe("Det ble ikke lagret. Prøv igjen.");
  });

  it("stands under the Student's feedback only, and the staff read the flag in words", () => {
    const assessment = view([item("a", true), item("b", false), item("c", true, null)]);
    const own = html(<AssessmentView assessment={assessment} viewer="student" classSessionId="s1" />);
    expect(own.match(/aria-pressed/gu)).toHaveLength(2); // none where there is no feedback
    expect(own).not.toContain(staff.flagged);
    const theirs = html(<AssessmentView assessment={assessment} viewer="staff" level={3} />);
    expect(theirs).not.toContain("aria-pressed");
    expect(theirs.split(staff.flagged)).toHaveLength(2); // one flagged piece with feedback
    expect(theirs).toContain(nb.assessment.student.disclosure);
    expect(theirs).toContain("<h3");
    expect(theirs).toContain("<h4");
  });

  it("counts the flagged pieces and says the staff's lines", () => {
    expect(flagCount(view([item("a", true), item("b", true), item("c", false)]))).toBe(2);
    expect(flagCountText(view([item("a", false)]))).toBeNull();
    expect(flagCountText(view([item("a", true)]))).toBe("Studenten har markert 1 tilbakemelding som feil.");
    expect(flagCountText(view([item("a", true), item("b", true)]))).toBe(
      "Studenten har markert 2 tilbakemeldinger som feil.",
    );
    expect(rowFlagsText(0)).toBe("Ingen markert som feil");
    expect(rowFlagsText(1200)).toBe(`${formatNumber(1200)} markert som feil`);
    expect(stateLine({ state: "no_test", unassessed: [] }, "staff")).toBe(staff.noTest);
    expect(stateLine({ state: "switched_off", unassessed: [] }, "staff")).toBe(staff.switchedOff);
  });

  it("is read again on the Class session's event", () => {
    const keys = topicKeys({ topic: "session", id: "s1", version: null });
    const prefixes = (key: readonly unknown[]) =>
      keys.some((prefix) => (prefix as unknown[]).every((part, index) => key[index] === part));
    expect(prefixes(staffAssessmentKey("s1", "u1"))).toBe(true);
    expect(prefixes(assessmentListKey("s1"))).toBe(true);
  });
});
