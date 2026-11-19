"use client";

import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";

import { enrolledClassesKey, useEnrolledClasses } from "./api";

/**
 * Hjem's Classes (Story 4.5, EXPERIENCE.md → Hjem before the Start date): each Class the Student
 * is in, named «class-of-1994, IBE160», with «Du får Rolle og spill på startdatoen.» beneath. No
 * game card and no link until the Start date (Epic 6 fills Hjem). A User in no Class (none yet,
 * removed, or its only Class archived, Story 4.10) is told so (Issue #93).
 */
export function StudentHome() {
  const classes = useEnrolledClasses();
  const { phase, retry } = usePageState(classes, enrolledClassesKey);

  if (phase === "loading" || phase === "slow") {
    return (
      <div className="mt-8">
        <Skeleton heading rows={1} />
        <LoadingNote visible={phase === "slow"} />
      </div>
    );
  }
  if (phase === "failed") {
    return (
      <div className="mt-8 flex flex-col items-start gap-3">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button onClick={retry}>{nb.system.retry}</Button>
      </div>
    );
  }

  const items = classes.data?.items ?? [];
  if (items.length === 0) {
    return <p className="mt-8 max-w-md text-body-phone text-ink-secondary lg:text-body">{nb.homes.noClass}</p>;
  }
  return (
    <ul className="mt-8 flex max-w-md flex-col border-t border-hairline">
      {items.map((item) => (
        <li key={item.id} className="border-b border-hairline py-4">
          <h2 className="text-headline text-ink [overflow-wrap:anywhere]">
            {nb.classes.home.label(item.name, item.course_code)}
          </h2>
          <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{nb.homes.startDate}</p>
        </li>
      ))}
    </ul>
  );
}
