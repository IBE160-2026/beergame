import { StaffPage } from "@/modules/classes/staff-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class: the api refuses it as any other
  }
}

/** «Faglærere og assistenter» of a Class (Story 4.9). */
export default async function FaglaererePage({ params }: { params: Promise<{ classId: string }> }) {
  const { classId } = await params;
  return <StaffPage classId={decoded(classId)} />;
}
