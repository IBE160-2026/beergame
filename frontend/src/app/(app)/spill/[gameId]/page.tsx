import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { PlayPage } from "@/modules/games/play-page";

export const metadata: Metadata = { title: nb.product.name };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no game: the api refuses it like any other
  }
}

export default async function SpillPage({ params }: { params: Promise<{ gameId: string }> }) {
  const { gameId } = await params;
  return <PlayPage gameId={decoded(gameId)} />;
}
