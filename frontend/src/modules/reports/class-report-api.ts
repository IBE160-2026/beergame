"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Klasserapport of a Class session (Story 14.1): every figure is the api's (AD-10). */
export type ClassReport = components["schemas"]["ClassReportOut"];
export type ReportDistribution = components["schemas"]["DistributionOut"];

export const classReportKey = (sessionId: string) => ["reports", "class", sessionId] as const;

/** `/api/class-sessions/{id}/class-report`: for the Lecturers of the Class; anyone else answers
 * 403 `forbidden`. `session:<id>` refetches it (`lib/api/topics.ts`). */
export function useClassReport(sessionId: string) {
  return useQuery({
    queryKey: classReportKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/class-report", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}

/** The Klasserapport's learning part (Story 14.2): every figure is the api's (AD-10). */
export type ClassLearning = components["schemas"]["ClassLearningOut"];

/** Under the report's key, so `session:<id>` refetches it with the report (`lib/api/topics.ts`). */
export const classLearningKey = (sessionId: string) => [...classReportKey(sessionId), "learning"] as const;

/** `/api/class-sessions/{id}/class-report/learning`: the same readers as the report. */
export function useClassLearning(sessionId: string) {
  return useQuery({
    queryKey: classLearningKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/class-report/learning", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}
