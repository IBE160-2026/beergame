import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { PlenaryPage } from "@/modules/reports/plenary-page";

export const metadata: Metadata = { title: nb.plenary.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it like any other
  }
}

/** «Alle spill i plenum» (Story 14.6): the Oversikt's Class games for the projector. */
export default async function PlenaryRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <PlenaryPage sessionId={decoded(sessionId)} />;
}
