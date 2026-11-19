"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";

import { archiveClass, classesKey, classKey, classStaffKey, invitationSummaryKey, registrationsKey } from "./api";
import { useFormArea } from "./one-form";
import { LINK_BUTTON } from "./roster-entry-forms";

const copy = nb.classes.archive;
const PANEL = "flex w-full max-w-md flex-col items-start gap-4 rounded-sm border border-axis px-4 py-4";

/**
 * «Arkiver Klassen» on an active Class's page, for its Faglærere (Story 4.10, FR-6, UX-DR56): a
 * Lenke-styled button opens the panel in place (one form on the page at a time); the consequence
 * stands above the button before it is pressed. «Avbryt» returns focus to the opener. Once
 * archived, the page holds the archived Class and turns read-only; it moves focus to its notice.
 */
export function ArchiveClass({ classId }: { classId: string }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const opener = useRef<HTMLButtonElement>(null);
  const submit = useRef<HTMLButtonElement>(null);
  const [focus, setFocus] = useState<"opener" | "submit" | null>(null);
  useEffect(() => {
    if (!focus) return;
    (focus === "opener" ? opener : submit).current?.focus();
    setFocus(null);
  }, [focus]);
  const take = useFormArea("archive", () => setOpen(false));
  const action = useAction({
    mutationFn: () => archiveClass(classId),
    fallback: copy.failed,
    onSuccess: (archived) => {
      queryClient.setQueryData(classKey(classId), archived);
      for (const key of [classesKey, invitationSummaryKey(classId), registrationsKey(classId), classStaffKey(classId)]) {
        void queryClient.invalidateQueries({ queryKey: key, exact: true });
      }
    },
  });

  return (
    <section aria-labelledby="archive-title" className="mt-12 flex flex-col items-start gap-4 border-t border-hairline pt-6">
      <h2 id="archive-title" className="sr-only">
        {copy.title}
      </h2>
      <button
        ref={opener}
        type="button"
        className={LINK_BUTTON}
        aria-expanded={open}
        onClick={() => {
          action.reset();
          setOpen(true);
          setFocus("submit");
          take();
        }}
      >
        {copy.open}
      </button>
      {open ? (
        <div role="group" aria-labelledby="archive-panel-title" className={PANEL}>
          <h3 id="archive-panel-title" className="text-label text-ink">
            {copy.title}
          </h3>
          <p id="archive-consequence" className="text-body-phone text-ink">
            {copy.consequence}
          </p>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Button
              ref={submit}
              type="button"
              variant="primary"
              unavailable={action.isPending}
              aria-describedby="archive-consequence"
              onClick={() => {
                if (!action.isPending) action.mutate();
              }}
            >
              {action.isPending ? copy.saving : copy.submit}
            </Button>
            <button
              type="button"
              className={LINK_BUTTON}
              onClick={() => {
                if (action.isPending) return;
                setOpen(false);
                setFocus("opener");
              }}
            >
              {copy.cancel}
            </button>
          </div>
          <ActionError message={action.errorMessage} />
        </div>
      ) : null}
    </section>
  );
}
