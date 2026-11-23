"use client";

import { useId } from "react";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { studentPagePath } from "@/modules/identity/homes";

import { useAssessmentList } from "./api";
import { rowFlagsText } from "./assessment";

const copy = nb.assessment.list;

/**
 * «Studentenes KI-vurderinger» in the Klasseøkt's «KI-vurdering» block (Story 12.5, FR-55): each
 * Student of the Class by name, a Lenke to their Studentside, with the state of their AI
 * assessment and how many pieces of feedback they flagged, in words (never by colour). For the
 * Class's owners and Assistant lecturers; anyone else gets nothing here. The Class session's
 * `session` event reads it again.
 */
export function AssessmentList({ sessionId }: { sessionId: string }) {
  const titleId = useId();
  const found = useAssessmentList(sessionId);
  // Nothing until the api answers: a User who may not read it (the Admin of a Control test) never
  // sees the heading flash.
  if (found.isPending) return null;
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") return null;
  const students = found.data?.students;
  return (
    <section aria-labelledby={titleId} className="mt-6" data-assessment-list="">
      <h3 id={titleId} className="text-step-title font-semibold text-ink">
        {copy.title}
      </h3>
      {students ? (
        students.length === 0 ? (
          <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.empty}</p>
        ) : (
          <ul className="mt-1 flex flex-col">
            {students.map((row) => (
              <li
                key={row.user_id}
                data-assessment-row={row.user_id}
                className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-hairline py-1 last:border-b-0"
              >
                <Link href={studentPagePath(sessionId, row.user_id)} standalone className="[overflow-wrap:anywhere]">
                  {row.name}
                </Link>
                <p className="text-body-phone text-ink lg:text-body">
                  <span data-row-state="">{copy.states[row.state]}</span>
                  <span className="text-ink-secondary"> · </span>
                  <span data-row-flags="" className={row.flags > 0 ? "font-semibold" : "text-ink-secondary"}>
                    {rowFlagsText(row.flags)}
                  </span>
                </p>
              </li>
            ))}
          </ul>
        )
      ) : (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.loadFailed}</p>
      )}
    </section>
  );
}
