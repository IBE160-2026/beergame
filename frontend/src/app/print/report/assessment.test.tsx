import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { type AssessmentSection, AssessmentSectionView, itemPoints, itemScore } from "./assessment-section";
import { reportCopy } from "./copy";
import { ReportSection } from "./sections";

const student = nb.assessment.student;

const SECTION: AssessmentSection = {
  kind: "assessment",
  checked: false,
  total: 57.5,
  total_max: 100,
  letter: null,
  items: [
    {
      number: 1,
      type: "choice",
      title: { text: "Hva er Posisjon?", ai_generated: false },
      weight: 10,
      points: 10,
      computed: "right",
      ai: null,
    },
    {
      number: 2,
      type: "long",
      title: { text: "Forklar svingningene.", ai_generated: false },
      weight: 40,
      points: 30,
      computed: null,
      ai: {
        assessed: true,
        step: 3,
        top: 4,
        label: "Godt",
        feedback: { text: "Du nevner «forsinkelsen», men ikke lageret.", ai_generated: true },
        feedback_dropped: false,
      },
    },
    {
      number: 3,
      type: "adapted",
      title: { text: "Hvorfor bestilte du 20 i uke 8?", ai_generated: true },
      weight: 50,
      points: 17.5,
      computed: null,
      ai: { assessed: true, step: 1, top: 4, label: "Svakt", feedback: null, feedback_dropped: true },
    },
  ],
};

/** «KI-vurdering» in the Student report (Story 13.11, FR-55, FR-56, FR-34). */
describe("the AI assessment section", () => {
  it("says what it is first, and marks every AI text for machines", () => {
    const html = renderToStaticMarkup(<AssessmentSectionView section={SECTION} />);
    expect(html).toContain(reportCopy.assessment.title);
    expect(html.indexOf(student.disclosure)).toBeLessThan(html.indexOf("Oppgave 1"));
    expect(html).toContain(student.unchecked);
    // The AI's score lines, the feedback, an AI-worded question and the total are marked.
    expect(html).toContain('data-ai-generated="true" data-score="">KI-vurdering: 3 av 4 (Godt)');
    expect(html).toContain(`<span data-ai-generated="true">KI-generert, kan ta feil:`);
    expect(html).toMatch(/data-ai-generated="true" data-total="">Vektet sum: 57,5 av 100 poeng/);
    // A computed score is the code's: not marked.
    expect(html).toContain(`<p class="mt-2 text-body text-ink" data-score="">${student.computed.right}`);
    expect(html).toContain(student.feedbackDropped);
    expect(html).not.toContain("data-letter");
    expect(html).not.toMatch(/flagg|markert/i);
  });

  it("shows the letter with its label only when the api gave one", () => {
    const html = renderToStaticMarkup(<AssessmentSectionView section={{ ...SECTION, checked: true, letter: "C" }} />);
    expect(html).toContain(nb.assessment.letter.value("C"));
    expect(html).toContain(nb.assessment.letter.label);
    expect(html).not.toContain(student.unchecked);
  });

  it("is in the print route's registry", () => {
    expect(renderToStaticMarkup(<ReportSection section={SECTION} />)).toContain('data-section="assessment"');
  });

  it("words the points and the scores as the Student's own view does", () => {
    expect(itemPoints({ points: 17.5, weight: 50 })).toBe("17,5 av 50 poeng");
    expect(itemPoints({ points: null, weight: 50 })).toBe(student.notAssessed);
    expect(itemScore({ ai: null, computed: "partly" })).toBe(student.computed.partly);
    expect(itemScore({ ai: { ...SECTION.items[1]!.ai!, assessed: false, step: null }, computed: null })).toBe(student.notAssessed);
  });
});
