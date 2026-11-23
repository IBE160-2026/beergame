import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { ControlTestScorersPage } from "@/modules/admin/control-test-scorers-page";

export const metadata: Metadata = { title: nb.scoring.scorers.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Control test: the api answers not found
  }
}

/** Admin-område → «Kontrolltest» → «Sensorer» of one Control test (Story 12.9). */
export default async function ControlTestScorersRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <ControlTestScorersPage sessionId={decoded(sessionId)} />;
}
