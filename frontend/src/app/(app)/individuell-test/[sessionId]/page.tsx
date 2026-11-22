import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { IndividualTestPage } from "@/modules/tests/individual-test-page";

export const metadata: Metadata = { title: nb.tests.individual.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it like any other
  }
}

export default async function IndividualTestRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <IndividualTestPage classSessionId={decoded(sessionId)} />;
}
