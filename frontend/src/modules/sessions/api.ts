"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

export type ClassSession = components["schemas"]["ClassSessionOut"];
export type ClassSessionListItem = components["schemas"]["ClassSessionListItem"];
export type GameSettings = components["schemas"]["GameSettings"];
export type AiMode = components["schemas"]["AiMode"];

/** The query keys of Class sessions (Story 5.1). */
export const classSessionKey = (id: string) => ["class-sessions", "detail", id] as const;
export const classSessionsKey = (classId: string) => ["class-sessions", "of-class", classId] as const;

/** One Class session. One the User may not read, or one that does not exist, fails with 403. */
export function useClassSession(id: string) {
  return useQuery({
    queryKey: classSessionKey(id),
    queryFn: () =>
      request(() => api.GET("/api/class-sessions/{session_id}", { params: { path: { session_id: id } } })),
    retry: false,
  });
}

/** The Class's sessions, newest first, for the Klasse page. */
export function useClassSessions(classId: string) {
  return useQuery({
    queryKey: classSessionsKey(classId),
    queryFn: () =>
      request(() => api.GET("/api/classes/{class_id}/class-sessions", { params: { path: { class_id: classId } } })),
    retry: false,
  });
}

/** «Lag Klasseøkt»: a Class session filled in with the Classic defaults. */
export function createClassSession(classId: string) {
  return request(() =>
    api.POST("/api/classes/{class_id}/class-sessions", { params: { path: { class_id: classId } } }),
  );
}

/** «Lagre Klasseøkt»: saves the Class session as it stands. */
export function saveClassSession(id: string, aiMode: AiMode) {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}", {
      params: { path: { session_id: id } },
      body: { ai_mode: aiMode },
    }),
  );
}
