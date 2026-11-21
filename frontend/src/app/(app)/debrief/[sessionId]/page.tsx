import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { DebriefPage } from "@/modules/debrief/debrief-page";

export const metadata: Metadata = { title: nb.debriefEntry.locked };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it like any other
  }
}

export default async function DebriefRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <DebriefPage classSessionId={decoded(sessionId)} />;
}
