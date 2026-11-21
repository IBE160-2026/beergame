import { SentMessagesPage } from "@/modules/messaging/sent-messages-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it as any other
  }
}

/** «Meldinger»: the Messages a Class session was sent, for its staff (Story 7.10). */
export default async function MeldingerPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <SentMessagesPage sessionId={decoded(sessionId)} />;
}
