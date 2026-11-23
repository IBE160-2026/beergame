import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AiCostSessionPage } from "@/modules/admin/ai-cost-session-page";

export const metadata: Metadata = { title: nb.admin.aiCost.costs.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it as any other
  }
}

/** One Class session's AI cost and its limit (Story 15.6). */
export default async function AdminAiCostSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <AiCostSessionPage sessionId={decoded(sessionId)} />;
}
