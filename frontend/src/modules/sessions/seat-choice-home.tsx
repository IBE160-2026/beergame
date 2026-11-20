"use client";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { StudentHome } from "@/modules/classes/student-home";
import { seatChoicePath } from "@/modules/identity/homes";

import { useEnrolledSessions } from "./api";
import { homeLine } from "./seat-choice";

const copy = nb.sessions.seatChoice;

/**
 * Under a Class on Hjem (Story 5.17): while a Class session of it lets the Students choose,
 * «Du velger spill og sete selv før startdatoen.» and the Lenke «Velg spill og sete»; once the
 * lock drew the Student a Seat, «Du fikk et sete ved trekning: Grossist i Spill 17.». Otherwise,
 * or when the sessions fail to load, the Start-date line of Story 4.5; nothing while they load. Epic 6 rebuilds Hjem on
 * the same api fields.
 */
export function SeatChoiceStatus({ classId }: { classId: string }) {
  const sessions = useEnrolledSessions();
  const lines = (sessions.data?.items ?? [])
    .filter((session) => session.class_id === classId)
    .map((session) => ({ session, line: homeLine(session) }))
    .filter((entry) => entry.line !== null);
  // Nothing while the sessions load, so the Start-date line never flashes before the Lenke.
  if (sessions.isPending) return <p className="mt-1 min-h-6" aria-hidden="true" />;
  if (lines.length === 0) {
    return <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{nb.homes.startDate}</p>;
  }
  return (
    <div className="mt-1 flex flex-col items-start">
      {lines.map(({ session, line }) =>
        line?.kind === "open" ? (
          <div key={session.id} className="flex flex-col items-start">
            <p className="text-body-phone text-ink-secondary lg:text-body">{copy.openLine}</p>
            <Link href={seatChoicePath(session.id)} standalone>
              {copy.open}
            </Link>
          </div>
        ) : line ? (
          <p key={session.id} className="text-body-phone text-ink lg:text-body">
            {line.text}
          </p>
        ) : null,
      )}
    </div>
  );
}

/** Hjem's Classes (Story 4.5) with each Class's Student choice line (Story 5.17). */
export function StudentHomeWithSeatChoice() {
  return <StudentHome status={(classId) => <SeatChoiceStatus classId={classId} />} />;
}
