import { MessagePage } from "@/modules/messaging/message-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it as any other
  }
}

/** The Meldingsskjema: a Message from the staff to a Student, a Class game or the whole Class
 * session (Story 7.9). */
export default async function MeldingPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <MessagePage sessionId={decoded(sessionId)} />;
}
