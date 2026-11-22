import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { SharedScreenPage } from "@/modules/debrief/shared-screen";

export const metadata: Metadata = { title: nb.debrief.shared.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Debrief session: the api refuses it like any other
  }
}

/** «Delt skjerm: hele kjeden» (Story 9.13): a joined Student's own session in display mode. */
export default async function SharedScreenRoute({ params }: { params: Promise<{ debriefId: string }> }) {
  const { debriefId } = await params;
  return <SharedScreenPage debriefId={decoded(debriefId)} />;
}
