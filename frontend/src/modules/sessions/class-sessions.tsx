"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { formatTime } from "@/modules/admin/audit";
import { classSessionPath } from "@/modules/identity/homes";

import { classSessionKey, classSessionsKey, createClassSession, useClassSessions } from "./api";

const copy = nb.sessions.list;

/**
 * «Klasseøkter» on the Klasse page (Story 5.1): the Class's sessions, newest first, each a Lenke to
 * its Klasseøkt with whether it has been saved. «Lag Klasseøkt» creates one filled in with the
 * Classic defaults and opens it; it is shown only to the Class's Faglærere while the Class is
 * active (an Assistant lecturer never sees it, FR-5).
 */
export function ClassSessions({ classId, canCreate }: { classId: string; canCreate: boolean }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const sessions = useClassSessions(classId);
  const action = useAction({
    mutationFn: () => createClassSession(classId),
    fallback: copy.createFailed,
    onSuccess: (created) => {
      queryClient.setQueryData(classSessionKey(created.id), created);
      void queryClient.invalidateQueries({ queryKey: classSessionsKey(classId), exact: true });
      router.push(classSessionPath(created.id));
    },
  });
  const items = sessions.data?.items;
  return (
    <section aria-labelledby="class-sessions-title" className="mt-10">
      <h2 id="class-sessions-title" className="text-headline text-ink">
        {copy.title}
      </h2>
      {sessions.isError ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
          <p className="text-body-phone text-ink lg:text-body">{nb.system.pageError}</p>
          <Button onClick={() => void sessions.refetch()}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {items && items.length === 0 ? (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.empty}</p>
      ) : null}
      {items && items.length > 0 ? (
        <ul className="mt-2 max-w-2xl">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col items-start border-b border-hairline pb-2 sm:flex-row sm:items-baseline sm:justify-between sm:gap-x-4 sm:py-1">
              <Link href={classSessionPath(item.id)} standalone>
                {copy.item(item.number, formatTime(item.created_at))}
              </Link>
              <span className="text-body-phone text-ink-secondary">{item.saved_at ? copy.saved : copy.unsaved}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {canCreate ? (
        <div className="mt-4 flex flex-col items-start gap-2">
          <Button
            unavailable={action.isPending || action.isSuccess}
            onClick={() => {
              if (!action.isPending && !action.isSuccess) action.mutate();
            }}
          >
            {action.isPending || action.isSuccess ? copy.creating : copy.create}
          </Button>
          <ActionError message={action.errorMessage} />
        </div>
      ) : null}
    </section>
  );
}
