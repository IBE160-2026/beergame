"use client";

import { useId } from "react";

import { nb } from "@/copy/nb";

import type { StaffAssessment } from "./api";
import { AssessmentView } from "./assessment-page";

const copy = nb.assessment.staff;

/**
 * «KI-vurdering» on a Student's Studentside (Story 12.5, FR-55, UX-DR66), for the owners and
 * Assistant lecturers of the Class: what the Student reads (the disclosure «KI-generert, kan ta
 * feil. Teller ikke. Ingen karakter.», scores, feedback, the notes, the unchecked notice), how many
 * pieces of feedback the Student flagged and, under each, that they flagged it. Read only. It never
 * holds a choice only the Student sees (AD-12). Story 13.2: the Studentside's record carries it, so
 * the Class session's `session` event reads it again with the record.
 */
export function StaffAssessmentBlock({ assessment }: { assessment: StaffAssessment }) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="mt-8 max-w-2xl border-t border-hairline pt-4"
      data-staff-assessment=""
      data-record="assessment"
    >
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      <AssessmentView assessment={assessment} viewer="staff" level={3} />
    </section>
  );
}
