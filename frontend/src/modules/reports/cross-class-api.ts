"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** Tverrklasse-statistikk (Story 14.3): every figure is a stored aggregate's (AD-10, AD-14). */
export type CrossClass = components["schemas"]["CrossClassOut"];
export type ComparedSession = components["schemas"]["ComparedSessionOut"];
export type ComparedMeasure = components["schemas"]["ComparedMeasureOut"];

export const crossClassKey = ["reports", "cross-class"] as const;

/** `/api/class-statistics`: the caller's own Class sessions; anyone without the Lecturer role
 * answers 403 `forbidden`. The aggregates change only when a job writes them, so no topic
 * refetches it; it is read again when the page opens. */
export function useClassStatistics() {
  return useQuery({
    queryKey: crossClassKey,
    queryFn: () => request(() => api.GET("/api/class-statistics", { cache: "no-store" })),
    retry: false,
  });
}
