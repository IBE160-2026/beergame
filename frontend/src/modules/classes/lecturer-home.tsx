"use client";

import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { useMe } from "@/modules/identity/api";
import { canCreateClass, classPath, NEW_CLASS_PATH } from "@/modules/identity/homes";
import { LecturerHomeSessions } from "@/modules/sessions/lecturer-home-sessions";

import { type ClassListItem, classesKey, useClasses } from "./api";
import { splitArchived } from "./classes";

const copy = nb.classes.home;

/**
 * The Lærerhjem's content (Story 4.1, UX-DR56). With no Class, one line and «Ny Klasse», the only
 * action. With Classes, «Klassene dine» lists each as a Lenke to the Class («name, course code»)
 * with its Roster count beside it (Story 4.4),
 * «Ny Klasse» stays under the list, and beside it stand «Venter» and «Neste frist», filled from
 * the Class sessions (Story 5.2, `LecturerHomeSessions`). An Assistant lecturer sees
 * the Classes they are attached to and no «Ny Klasse» (Story 4.9).
 */
export function LecturerHome() {
  const classes = useClasses();
  const creates = canCreateClass(useMe().data ?? { roles: [] });
  const { phase, retry } = usePageState(classes, classesKey);

  if (phase === "loading" || phase === "slow") {
    return (
      <div className="mt-8">
        <Skeleton heading rows={3} />
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
    return (
      <div className="mt-8 max-w-md">
        <p className="text-body-phone text-ink-secondary lg:text-body">{copy.empty}</p>
        {creates ? (
          <p className="mt-4">
            <Link href={NEW_CLASS_PATH} standalone>
              {copy.newClass}
            </Link>
          </p>
        ) : null}
      </div>
    );
  }

  const { active, archived } = splitArchived(items);
  return (
    <div className="mt-8 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,28rem)_minmax(0,20rem)] lg:gap-16">
      <div className="flex flex-col gap-10">
        <section aria-labelledby="classes-title">
          <h2 id="classes-title" className="text-headline text-ink">
            {copy.title}
          </h2>
          {active.length > 0 ? (
            <ClassList items={active} />
          ) : (
            <p className="mt-4 text-body-phone text-ink-secondary lg:text-body">{nb.classes.archive.noActive}</p>
          )}
          {creates ? (
            <p className="mt-4">
              <Link href={NEW_CLASS_PATH} standalone>
                {copy.newClass}
              </Link>
            </p>
          ) : null}
        </section>
        {/* Archived Classes under their own heading, each marked in text (Story 4.10, UX-DR56). */}
        {archived.length > 0 ? (
          <section aria-labelledby="archived-title">
            <h2 id="archived-title" className="text-headline text-ink">
              {nb.classes.archive.homeTitle}
            </h2>
            <ClassList items={archived} />
          </section>
        ) : null}
      </div>
      <LecturerHomeSessions />
    </div>
  );
}

/** Each Class as a Lenke with its Roster count beside it; an archived one says so in text. */
function ClassList({ items }: { items: ClassListItem[] }) {
  return (
    <ul className="mt-4 flex flex-col border-t border-hairline">
      {items.map((item) => (
        <li key={item.id} className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-hairline">
          <Link href={classPath(item.id)} standalone className="min-w-0 py-2 [overflow-wrap:anywhere]">
            {copy.label(item.name, item.course_code)}
          </Link>
          <span className="pb-2 text-body-phone tabular-nums text-ink-secondary sm:pb-0 lg:text-body">
            {item.archived
              ? `${nb.classes.archive.marker} · ${copy.rosterCount(item.roster_count)}`
              : copy.rosterCount(item.roster_count)}
          </span>
        </li>
      ))}
    </ul>
  );
}
