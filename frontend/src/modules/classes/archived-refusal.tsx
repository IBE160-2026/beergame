"use client";

import { useMutationState } from "@tanstack/react-query";
import { useState } from "react";

import { nb } from "@/copy/nb";
import { errorCode } from "@/lib/api/mutation";

/**
 * Whether an action on this page was refused with `class_archived` since the page opened (Story
 * 4.10). The form that held the refusal closes as the page turns read-only, so the page itself
 * says why (Issue #93). Refused mutations stay in the query client's cache after their form is
 * gone.
 */
export function useArchivedRefusal(): boolean {
  const [since] = useState(() => Date.now());
  const refused = useMutationState({
    filters: {
      status: "error",
      predicate: (m) => errorCode(m.state.error) === "class_archived" && m.state.submittedAt >= since,
    },
    select: (m) => m.state.submittedAt,
  });
  return refused.length > 0;
}

/** «Klassen er arkivert og kan ikke endres.», announced as it appears. */
export function ArchivedRefusal() {
  return (
    <p role="alert" className="mt-4 max-w-2xl text-body-phone text-ink lg:text-body">
      {nb.classes.archive.refused}
    </p>
  );
}
