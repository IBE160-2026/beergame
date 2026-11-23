import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { ControlTestResultsPage } from "@/modules/admin/control-test-results-page";

export const metadata: Metadata = { title: nb.scoring.results.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Control test: the api answers not found
  }
}

/** Admin-område → «Kontrolltest» → «Resultater» of one Control test (Story 12.10). */
export default async function ControlTestResultsRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <ControlTestResultsPage sessionId={decoded(sessionId)} />;
}
