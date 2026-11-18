"use client";

import { type QueryKey, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { isSessionExpired } from "@/lib/api/client";

/** «Laster …» shows only once a page has loaded this long (EXPERIENCE.md → Skjelett). */
export const LOADING_TEXT_AFTER_MS = 1_000;

/** [ASSUMPTION] EXPERIENCE.md → Skjelett: after this long a page that still loads shows the
 * page-error state. */
export const PAGE_ERROR_AFTER_MS = 10_000;

/** `loading`: Skjelett, no text. `slow`: Skjelett and «Laster …». `failed`: the page-error line.
 * `ready`: the page. */
export type PagePhase = "loading" | "slow" | "failed" | "ready";

export type Waited = "short" | "long" | "too-long";

/** The phase of a page from its data request and how long it has waited. */
export function pagePhase({ pending, failed, waited }: { pending: boolean; failed: boolean; waited: Waited }): PagePhase {
  if (failed) return "failed";
  if (!pending) return "ready";
  if (waited === "too-long") return "failed";
  return waited === "long" ? "slow" : "loading";
}

/** The part of a TanStack query a page reads. */
export type PageQuery = {
  isPending: boolean;
  isError: boolean;
  isFetching: boolean;
  error: unknown;
  refetch: () => unknown;
};

/**
 * The loading and page-error state of a page that reads `query` under `queryKey` (UX-DR58,
 * UX-DR59). The clock starts when the page starts waiting, and again at each «Prøv igjen», which
 * drops a request still hanging and asks again, in place, so typed text stays.
 */
export function usePageState(query: PageQuery, queryKey: QueryKey): { phase: PagePhase; retry: () => void } {
  const queryClient = useQueryClient();
  // A session that has ended is not a page error: the app is on its way to «Logg inn».
  const expired = isSessionExpired(query.error);
  // A retry after an error keeps the error status while it fetches: show it as loading.
  const pending = query.isPending || expired || (query.isError && query.isFetching);
  const failed = query.isError && !query.isFetching && !expired;
  const [attempt, setAttempt] = useState(0);
  // One key per wait: a new wait (or a retry) starts the clock from zero.
  const key = pending ? `wait-${attempt}` : "idle";
  const [wait, setWait] = useState<{ key: string; waited: Waited }>({ key, waited: "short" });
  if (wait.key !== key) setWait({ key, waited: "short" });

  useEffect(() => {
    if (key === "idle") return;
    const mark = (waited: Waited) => setWait((w) => (w.key === key ? { key, waited } : w));
    const long = window.setTimeout(() => mark("long"), LOADING_TEXT_AFTER_MS);
    const tooLong = window.setTimeout(() => mark("too-long"), PAGE_ERROR_AFTER_MS);
    return () => {
      window.clearTimeout(long);
      window.clearTimeout(tooLong);
    };
  }, [key]);

  const current: Waited = wait.key === key ? wait.waited : "short";
  return {
    phase: pagePhase({ pending, failed, waited: current }),
    retry: () => {
      setAttempt((n) => n + 1);
      // A refetch would join a request that still hangs; cancel it first.
      void queryClient.cancelQueries({ queryKey }).then(() => query.refetch());
    },
  };
}
