"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

import type { ChosenFilters } from "./cross-class-api";

/** «Tverrinstitusjonell statistikk» (Story 14.7, cut list): every figure, filter count, difference
 * label and withheld Institution is the api's, from the stored aggregates only (AD-10, AD-14). */
export type CrossInstitution = components["schemas"]["InstitutionStatisticsOut"];
export type ComparedInstitution = components["schemas"]["ComparedInstitutionOut"];
export type InstitutionMeasure = components["schemas"]["InstitutionMeasureOut"];

export const crossInstitutionKey = ["reports", "cross-institution"] as const;

/** `/api/institution-statistics`: the Admin only (403 `forbidden` for anyone else); it answers 404
 * while `FEATURE_CROSS_INSTITUTION_STATS` is off. The aggregates change only when a job writes
 * them, so it is read when the page opens or a filter changes; the previous answer stays on screen
 * while a filter's answer loads. */
export function useInstitutionStatistics(chosen: ChosenFilters = {}, enabled = true) {
  return useQuery({
    queryKey: [...crossInstitutionKey, chosen],
    queryFn: () =>
      request(() =>
        api.GET("/api/institution-statistics", {
          params: { query: chosen },
          cache: "no-store",
        }),
      ),
    placeholderData: keepPreviousData,
    retry: false,
    enabled,
  });
}
