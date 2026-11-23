"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** Tverrklasse-statistikk (Stories 14.3 and 14.4): every figure, filter count and difference
 * label is the api's, from the stored aggregates (AD-10, AD-14). */
export type CrossClass = components["schemas"]["CrossClassOut"];
export type ComparedSession = components["schemas"]["ComparedSessionOut"];
export type ComparedMeasure = components["schemas"]["ComparedMeasureOut"];
export type CompareFilter = components["schemas"]["FilterOut"];
export type FilterOption = components["schemas"]["FilterOptionOut"];
export type FilterDimension = CompareFilter["dimension"];
export type DiffKey = ComparedSession["differs"][number];

/** The pressed option per dimension (its `value` token); a dimension left out is «Alle». */
export type ChosenFilters = Partial<Record<FilterDimension, string>>;

export const crossClassKey = ["reports", "cross-class"] as const;

/** `/api/class-statistics`: the caller's own Class sessions, compared under the chosen filters;
 * anyone without the Lecturer role answers 403 `forbidden`. The aggregates change only when a job
 * writes them, so no topic refetches it; it is read again when the page opens or a filter
 * changes. The previous answer stays on screen while a filter's answer loads. */
export function useClassStatistics(chosen: ChosenFilters = {}) {
  return useQuery({
    queryKey: [...crossClassKey, chosen],
    queryFn: () =>
      request(() =>
        api.GET("/api/class-statistics", {
          params: { query: chosen },
          cache: "no-store",
        }),
      ),
    placeholderData: keepPreviousData,
    retry: false,
  });
}
