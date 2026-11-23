import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { ScoringAnswerPage } from "@/modules/assessment/scoring-pages";

export const metadata: Metadata = { title: nb.scoring.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no answer: the api refuses it like any other
  }
}

/** One answer of a Control test to score (Story 12.9). */
export default async function ScoringAnswerRoute({
  params,
}: {
  params: Promise<{ sessionId: string; answerId: string }>;
}) {
  const { sessionId, answerId } = await params;
  return <ScoringAnswerPage sessionId={decoded(sessionId)} answerId={decoded(answerId)} />;
}
