import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AssessmentPage } from "@/modules/assessment/assessment-page";

export const metadata: Metadata = { title: nb.assessment.student.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it like any other
  }
}

/** The Student's «KI-vurdering» of their Individual test (Story 12.2). */
export default async function AssessmentRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <AssessmentPage classSessionId={decoded(sessionId)} />;
}
