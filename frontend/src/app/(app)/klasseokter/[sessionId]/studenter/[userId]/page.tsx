import { StudentPageView } from "@/modules/reports/student-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Student: the page refuses it as any other
  }
}

/** The Studentside: one Student of a Class session, for the Lecturers of its Class (Story 8.9). */
export default async function StudentsidePage({
  params,
}: {
  params: Promise<{ sessionId: string; userId: string }>;
}) {
  const { sessionId, userId } = await params;
  return <StudentPageView sessionId={decoded(sessionId)} userId={decoded(userId)} />;
}
