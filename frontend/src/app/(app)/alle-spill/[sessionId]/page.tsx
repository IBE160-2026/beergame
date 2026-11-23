import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AllGamesPage } from "@/modules/reports/all-games-page";

export const metadata: Metadata = { title: nb.allGames.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it like any other
  }
}

/** «Alle spill side om side» (Story 14.5): every Class game of the Student's Class session. */
export default async function AllGamesRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <AllGamesPage sessionId={decoded(sessionId)} />;
}
