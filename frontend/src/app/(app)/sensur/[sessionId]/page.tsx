import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { ScoringListPage } from "@/modules/assessment/scoring-pages";

export const metadata: Metadata = { title: nb.scoring.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Control test: the api refuses it like any other
  }
}

/** One Control test's answers to score (Story 12.9). */
export default async function ScoringListRoute({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <ScoringListPage sessionId={decoded(sessionId)} />;
}
