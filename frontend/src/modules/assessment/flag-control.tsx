"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ActionError } from "@/components/action-error";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { myAssessmentKey, setFeedbackFlag } from "./api";

const copy = nb.assessment.flag;

/** A text button: weight 600, underlined, no icon, the 44 px tap target (UX-DR76). */
const TEXT_BUTTON =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center text-label text-ink underline underline-offset-2 hover:decoration-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink";

/**
 * «Marker som feil» under a piece of the Student's written feedback (Story 12.5, FR-55, UX-DR39,
 * UX-DR78): one press stores the flag at once, with no dialog. It is a toggle with `aria-pressed`
 * and no icon; flagged, the line «Markert. Faglærer ser det.» stands before it and its words are
 * «Angre», which takes the flag back. The same button keeps focus. A failed request says «Det ble
 * ikke lagret. Prøv igjen.» beside it, and the button stays active (UX-DR59). The api's answer is
 * the view as it now stands, which replaces the page's copy; a 409 (the view changed meanwhile)
 * reads the view again. `describedBy` names the item heading, so each toggle says which feedback it
 * marks.
 */
export function FlagControl({
  classSessionId,
  itemId,
  flagged,
  describedBy,
}: {
  classSessionId: string;
  itemId: string;
  flagged: boolean;
  describedBy?: string;
}) {
  const queryClient = useQueryClient();
  const toggle = useMutation({
    mutationFn: (next: boolean) => setFeedbackFlag(classSessionId, itemId, next),
    onSuccess: (view) => queryClient.setQueryData(myAssessmentKey(classSessionId), view),
    onError: (error) => {
      if (error instanceof ApiRequestError && error.status === 409) {
        void queryClient.invalidateQueries({ queryKey: myAssessmentKey(classSessionId) });
      }
    },
  });
  return (
    <div data-flag={flagged ? "marked" : ""} className="mt-1 flex flex-wrap items-center gap-x-3">
      <p aria-live="polite" className="text-body-phone text-ink lg:text-body">
        {flagged ? <span data-flag-marked="">{copy.marked}</span> : null}
      </p>
      <button
        type="button"
        aria-pressed={flagged}
        aria-describedby={describedBy}
        className={TEXT_BUTTON}
        onClick={() => {
          if (!toggle.isPending) toggle.mutate(!flagged);
        }}
      >
        {flagged ? copy.undo : copy.mark}
      </button>
      <ActionError message={toggle.isError ? copy.failed : undefined} />
    </div>
  );
}
