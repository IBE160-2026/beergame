"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Studentside of one Student (Story 8.9): «Tilrettelegging» and «Frister» for its owners
 * (`can_manage`); the «KI-vurdering» block reads its own endpoint (Story 12.5). */
export type StudentPage = components["schemas"]["StudentPageOut"];
/** The Studentside as its owners read it (Story 12.5): «Frister» is there. An Assistant lecturer's
 * page has `can_manage` false and neither «Tilrettelegging» nor «Frister». */
export type ManagedStudentPage = StudentPage & { deadlines: components["schemas"]["StudentDeadlinesOut"] };
export type Adjustment = components["schemas"]["AdjustmentOut"];
export type AdjustmentIn = components["schemas"]["AdjustmentIn"];

/** Under the Class session's prefix, so its `session:<id>` event reads it again (`topics.ts`). */
export const studentPageKey = (sessionId: string, userId: string) =>
  ["class-sessions", "students", sessionId, userId] as const;

/** `/api/class-sessions/{id}/students/{user_id}`: anyone but a Lecturer of the Class, and a User
 * who is no Student of it, answers 403 `forbidden`. */
export function useStudentPage(sessionId: string, userId: string) {
  return useQuery({
    queryKey: studentPageKey(sessionId, userId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/students/{user_id}", {
          params: { path: { session_id: sessionId, user_id: userId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}

/** «Lagre frist» (Story 11.13): answers the block «Frister» as it now stands; 422
 * `invalid_extension` names the reason in `fields.test_deadline`, 409 `attempt_submitted` once the
 * Student has handed the test in. */
export function extendTestDeadline(sessionId: string, userId: string, testDeadline: string) {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}/students/{user_id}/deadline", {
      params: { path: { session_id: sessionId, user_id: userId } },
      body: { test_deadline: testDeadline },
    }),
  );
}

/** «Lagre tilrettelegging» (Story 8.9): answers the Studentside as it now stands; 422
 * `invalid_adjustment` names the refused fields. */
export function saveAdjustment(sessionId: string, userId: string, body: AdjustmentIn) {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}/students/{user_id}/adjustment", {
      params: { path: { session_id: sessionId, user_id: userId } },
      body,
    }),
  );
}
