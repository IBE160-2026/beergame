import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { BriefingPage } from "@/modules/games/briefing-page";

export const metadata: Metadata = { title: nb.games.briefing.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no game: the api refuses it like any other
  }
}

export default async function ReglerPage({ params }: { params: Promise<{ gameId: string }> }) {
  const { gameId } = await params;
  return <BriefingPage gameId={decoded(gameId)} />;
}
