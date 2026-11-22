"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Studentside of one Student (Story 8.9): for now the block «Tilrettelegging». */
export type StudentPage = components["schemas"]["StudentPageOut"];
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
