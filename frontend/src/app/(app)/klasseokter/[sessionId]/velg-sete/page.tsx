import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { SeatChoicePage } from "@/modules/sessions/seat-choice-page";

export const metadata: Metadata = { title: nb.sessions.seatChoice.title };

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api answers not found
  }
}

export default async function VelgSetePage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <SeatChoicePage sessionId={decoded(sessionId)} />;
}
