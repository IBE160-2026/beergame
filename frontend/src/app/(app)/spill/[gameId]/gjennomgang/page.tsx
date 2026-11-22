import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { WalkthroughPage } from "@/modules/replay/walkthrough-page";

export const metadata: Metadata = { title: nb.replay.walkthrough.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no game: the api refuses it like any other
  }
}

export default async function GjennomgangPage({ params }: { params: Promise<{ gameId: string }> }) {
  const { gameId } = await params;
  return <WalkthroughPage gameId={decoded(gameId)} />;
}
