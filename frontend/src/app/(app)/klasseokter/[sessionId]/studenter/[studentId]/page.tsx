import { StudentPageView } from "@/modules/reports/student-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Student: the page refuses it as any other
  }
}

/** The Studentside: one Student of a Class session, for the Lecturers of its Class (Story 8.9).
 * The segment is `[studentId]`, as its `debrief` page's (Story 9.10): Next.js allows one slug name
 * per dynamic path. */
export default async function StudentsidePage({
  params,
}: {
  params: Promise<{ sessionId: string; studentId: string }>;
}) {
  const { sessionId, studentId } = await params;
  return <StudentPageView sessionId={decoded(sessionId)} userId={decoded(studentId)} />;
}
