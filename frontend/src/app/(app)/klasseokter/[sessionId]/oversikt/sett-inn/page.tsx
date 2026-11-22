import { FillSeatsPage } from "@/modules/games/fill-seats-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it as any other
  }
}

/** «Sett inn KI-spillere»: every Seat the Class session's games wait for (Story 8.12). */
export default async function SettInnPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <FillSeatsPage sessionId={decoded(sessionId)} />;
}
