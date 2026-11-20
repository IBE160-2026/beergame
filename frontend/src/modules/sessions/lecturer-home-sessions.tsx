"use client";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { formatTime } from "@/modules/admin/audit";
import { classSessionPath } from "@/modules/identity/homes";

import { useLecturerOverview } from "./api";

const home = nb.classes.home;
const copy = nb.sessions;

/**
 * The Lærerhjem's «Venter» and «Neste frist» (Story 5.2, UX-DR56): per Class the Class sessions
 * that still lack a date or a confirmed allocation (Story 5.9), each a Lenke to its Klasseøkt, and the next date across the User's
 * Class sessions with its name and time in Europe/Oslo. Fetched when the Lærerhjem opens; with no
 * Class session, or while it loads or failed, the parts keep their empty lines.
 */
export function LecturerHomeSessions() {
  const overview = useLecturerOverview().data;
  const waiting = overview?.waiting ?? [];
  const next = overview?.next_date ?? null;
  return (
    <dl className="flex flex-col gap-4 self-start border-t border-hairline pt-4">
      <div>
        <dt className="text-label text-ink">{home.waiting}</dt>
        {waiting.length === 0 ? (
          <dd className="mt-1 text-body-phone text-ink-secondary lg:text-body">{home.nothingWaiting}</dd>
        ) : (
          <dd className="mt-1">
            <ul className="flex flex-col">
              {waiting.flatMap((klass) =>
                klass.sessions.map((session) => (
                  <li key={session.id}>
                    <Link href={classSessionPath(session.id)} standalone className="[overflow-wrap:anywhere]">
                      {copy.home.lacks(klass.class_name, session.number, session.lacks)}
                    </Link>
                  </li>
                )),
              )}
            </ul>
          </dd>
        )}
      </div>
      <div>
        <dt className="text-label text-ink">{home.deadline}</dt>
        {next ? (
          <dd className="mt-1 text-body-phone text-ink lg:text-body">
            <Link href={classSessionPath(next.session_id)} standalone className="[overflow-wrap:anywhere]">
              {copy.home.nextDate(copy.dates.names[NAME_OF[next.kind]], next.number, next.class_name)}
            </Link>
            <span className="block text-ink-secondary tabular-nums">{formatTime(next.at)}</span>
          </dd>
        ) : (
          <dd className="mt-1 text-body-phone text-ink-secondary lg:text-body">{home.noDeadline}</dd>
        )}
      </div>
    </dl>
  );
}

const NAME_OF = {
  start: "start_at",
  play: "play_deadline",
  debrief: "debrief_deadline",
  test: "test_deadline",
} as const;
