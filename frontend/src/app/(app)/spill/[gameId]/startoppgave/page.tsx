import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { StartingTaskPage } from "@/modules/games/starting-task-page";

export const metadata: Metadata = { title: nb.games.startingTask.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no game: the api refuses it like any other
  }
}

export default async function StartoppgavePage({ params }: { params: Promise<{ gameId: string }> }) {
  const { gameId } = await params;
  return <StartingTaskPage gameId={decoded(gameId)} />;
}
