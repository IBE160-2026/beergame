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
