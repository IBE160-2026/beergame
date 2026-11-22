"use client";

import { useId } from "react";

import { nb } from "@/copy/nb";

import { completionRows, participationLines, requirementLine, type StudentRecord } from "./record";

const copy = nb.reports.completion;

/**
 * The block «Fullføring» on the Studentside (Story 13.2, FR-17, UX-DR54, DESIGN.md →
 * Fullføringsretting): one row per step (Klassespill, Debrief, Debrief-quiz, Replay, Individuell
 * test) with its status in text, «gjort» or «ikke gjort», never by a mark alone; the Klassespill
 * row carries the share lines, and the requirement line shows only for an obligatory Class session.
 * Every value is the api's, from `reports.service.completion_status`. Under it, «Til informasjon»:
 * the time on the Student's own Orders and whether they were constant, which never change the
 * status. Story 13.3 adds the correction form to each row.
 */
export function CompletionBlock({ record }: { record: StudentRecord }) {
  const titleId = useId();
  const infoId = useId();
  const completion = record.completion;
  const requirement = completion ? requirementLine(completion) : null;
  return (
    <section aria-labelledby={titleId} className="mt-8 max-w-2xl border-t border-hairline pt-4" data-completion="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      {completion ? (
        <>
          {requirement ? (
            <p className="mt-2 text-body-phone text-ink lg:text-body" data-requirement="">
              {requirement}
            </p>
          ) : null}
          <ul className="mt-3 border-t border-hairline">
            {completionRows(completion).map((row) => (
              <li
                key={row.step}
                className="border-b border-hairline py-2 sm:grid sm:grid-cols-[minmax(0,10rem)_minmax(0,1fr)] sm:gap-x-4"
                data-step={row.step}
                data-done={row.done ? "true" : "false"}
              >
                <p className="text-label text-ink">{row.name}</p>
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="text-body-phone text-ink lg:text-body" data-step-status="">
                    {row.status}
                  </p>
                  {row.lines.map((line) => (
                    <p
                      key={line}
                      className="text-body-phone text-ink-secondary tabular-nums lining-nums [overflow-wrap:anywhere] lg:text-body"
                    >
                      {line}
                    </p>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.unavailable}</p>
      )}
      <div className="mt-4" role="group" aria-labelledby={infoId} data-participation="">
        <h3 id={infoId} className="text-label text-ink">
          {copy.infoTitle}
        </h3>
        <p className="text-caption text-ink-secondary">{copy.infoNote}</p>
        {participationLines(record.participation).map((line) => (
          <p key={line} className="mt-1 text-body-phone text-ink tabular-nums lining-nums lg:text-body">
            {line}
          </p>
        ))}
      </div>
    </section>
  );
}
