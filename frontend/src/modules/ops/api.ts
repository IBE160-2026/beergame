"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

export type OperationsSession = components["schemas"]["OperationsSessionOut"];
export type Operations = components["schemas"]["OperationsOut"];
export type ErrorHour = components["schemas"]["ErrorHourOut"];

/** The query keys of «Drift» (Story 15.8). */
export const operationsKey = ["admin", "operations"] as const;
export const operationsSessionsKey = [...operationsKey, "class-sessions"] as const;
export const sessionOperationsKey = (id: string) => [...operationsKey, "class-session", id] as const;

/** How often an open «Drift» page reads its figures again (Story 15.8, UX-DR58). */
export const OPERATIONS_REFETCH_MS = 30_000;

/** Every saved Class session with its errors of the last 24 hours, read again every 30 s. */
export function useOperationsSessions() {
  return useQuery({
    queryKey: operationsSessionsKey,
    queryFn: () => request(() => api.GET("/api/admin/operations/class-sessions")),
    refetchInterval: OPERATIONS_REFETCH_MS,
    retry: false,
  });
}

/** One Class session's errors, fallback, response times, Play guard share and AI cost, read again
 * every 30 s; a failed read keeps the last figures. */
export function useSessionOperations(id: string) {
  return useQuery({
    queryKey: sessionOperationsKey(id),
    queryFn: () =>
      request(() =>
        api.GET("/api/admin/operations/class-sessions/{class_session_id}", {
          params: { path: { class_session_id: id } },
        }),
      ),
    refetchInterval: OPERATIONS_REFETCH_MS,
    retry: false,
  });
}
