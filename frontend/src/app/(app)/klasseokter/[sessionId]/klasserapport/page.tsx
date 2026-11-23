import { ClassReportPage } from "@/modules/reports/class-report-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class session: the page refuses it as any other
  }
}

/** The Klasserapport: how the Class games went, for the Lecturers of the Class (Story 14.1). */
export default async function KlasserapportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <ClassReportPage sessionId={decoded(sessionId)} />;
}
