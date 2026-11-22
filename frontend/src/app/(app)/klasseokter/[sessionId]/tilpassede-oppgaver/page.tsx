import { AdaptedPreviewPage } from "@/modules/tests/adapted-preview-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it as any other
  }
}

/** «Tilpassede oppgaver»: the Adapted item templates filled for a sample Student (Story 11.9). */
export default async function TilpassedeOppgaverPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <AdaptedPreviewPage sessionId={decoded(sessionId)} />;
}
