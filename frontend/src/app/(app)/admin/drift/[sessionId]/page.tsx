import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { OperationsPage } from "@/modules/ops/operations-page";

export const metadata: Metadata = { title: nb.admin.operations.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it as any other
  }
}

/** One Class session's «Drift» view (Story 15.8). */
export default async function AdminSessionOperationsPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <OperationsPage sessionId={decoded(sessionId)} />;
}
