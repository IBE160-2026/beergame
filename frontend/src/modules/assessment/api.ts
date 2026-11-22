"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";
import { myTestsKey } from "@/modules/tests/api";

/** The Student's «KI-vurdering» of their Individual test (Story 12.2). */
export type MyAssessment = components["schemas"]["MyAssessmentOut"];
export type AssessedItem = components["schemas"]["AssessedItemOut"];

/** Under the Student's own tests, so the `user` topic (a finished run, a hand-in) reads it again. */
export const myAssessmentKey = (classSessionId: string) => [...myTestsKey, classSessionId, "assessment"] as const;

/** The Student's assessment in the Class session; 403 `forbidden` for a session that is not theirs. */
export function useMyAssessment(classSessionId: string) {
  return useQuery({
    queryKey: myAssessmentKey(classSessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/me/class-sessions/{session_id}/test/assessment", { params: { path: { session_id: classSessionId } } }),
      ),
    retry: false,
  });
}
