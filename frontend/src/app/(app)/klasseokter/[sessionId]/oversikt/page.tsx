import { OverviewPage } from "@/modules/games/overview-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it as any other
  }
}

/** The Oversikt of a Class session (Story 7.1). */
export default async function OversiktPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <OverviewPage sessionId={decoded(sessionId)} />;
}
