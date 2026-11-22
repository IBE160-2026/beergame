import { StartGamesPage } from "@/modules/games/start-games-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it as any other
  }
}

/** «Start spill»: every Class game of the Class session that has not started (Story 8.10). */
export default async function StartSpillPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <StartGamesPage sessionId={decoded(sessionId)} />;
}
