"use client";

import { useId } from "react";

import { Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { useStaffAssessment } from "./api";
import { AssessmentView } from "./assessment-page";

const copy = nb.assessment.staff;

/**
 * «KI-vurdering» on a Student's Studentside (Story 12.5, FR-55, UX-DR66), for the owners and
 * Assistant lecturers of the Class: what the Student reads (the disclosure «KI-generert, kan ta
 * feil. Teller ikke. Ingen karakter.», scores, feedback, the notes, the unchecked notice), how many
 * pieces of feedback the Student flagged and, under each, that they flagged it. Read only. It never
 * holds a choice only the Student sees (AD-12). The Class session's `session` event reads it again.
 */
export function StaffAssessmentBlock({ sessionId, userId }: { sessionId: string; userId: string }) {
  const titleId = useId();
  const found = useStaffAssessment(sessionId, userId);
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") return null;
  return (
    <section aria-labelledby={titleId} className="mt-8 max-w-2xl border-t border-hairline pt-4" data-staff-assessment="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      {found.data ? (
        <AssessmentView assessment={found.data} viewer="staff" level={3} />
      ) : found.isError ? (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.loadFailed}</p>
      ) : (
        <div className="mt-2">
          <Skeleton heading={false} rows={3} />
        </div>
      )}
    </section>
  );
}
