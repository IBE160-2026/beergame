import { ClassPage } from "@/modules/classes/class-page";

function decoded(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment; // a malformed escape names no Class: the api refuses it as any other
  }
}

export default async function KlassePage({ params }: { params: Promise<{ classId: string }> }) {
  const { classId } = await params;
  return <ClassPage classId={decoded(classId)} />;
}
