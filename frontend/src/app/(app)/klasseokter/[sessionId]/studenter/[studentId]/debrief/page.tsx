import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { SummaryPage } from "@/modules/debrief/summary-page";

export const metadata: Metadata = { title: nb.debrief.staffSummary.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session or Student: the page refuses it
  }
}

export default async function StudentDebriefPage({
  params,
}: {
  params: Promise<{ sessionId: string; studentId: string }>;
}) {
  const { sessionId, studentId } = await params;
  return <SummaryPage classSessionId={decoded(sessionId)} studentId={decoded(studentId)} />;
}
