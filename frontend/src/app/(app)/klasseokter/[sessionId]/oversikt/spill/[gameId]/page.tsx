import { InsightPage } from "@/modules/games/insight-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no game: the page refuses it as any other
  }
}

/** Spillinnsikt: one Class game week by week, for the staff of its Class (Story 7.7). */
export default async function SpillinnsiktPage({
  params,
}: {
  params: Promise<{ sessionId: string; gameId: string }>;
}) {
  const { sessionId, gameId } = await params;
  return <InsightPage sessionId={decoded(sessionId)} gameId={decoded(gameId)} />;
}
