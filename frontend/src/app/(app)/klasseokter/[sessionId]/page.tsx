import { ClassSessionPage } from "@/modules/sessions/class-session-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the api refuses it as any other
  }
}

export default async function KlasseoktPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <ClassSessionPage sessionId={decoded(sessionId)} />;
}
