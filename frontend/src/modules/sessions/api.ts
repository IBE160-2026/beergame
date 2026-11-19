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
/** The Lærerhjem's «Venter» and «Neste frist» (Story 5.2). */
export const lecturerHomeKey = ["class-sessions", "lecturer-home"] as const;

export type LecturerOverview = components["schemas"]["LecturerOverviewOut"];
export type DatesIn = components["schemas"]["DatesIn"];

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

export type SettingsCheck = components["schemas"]["SettingsCheckOut"];
/** A draft of the Game settings as sent: any field, laid over the stored settings by the api. */
export type SettingsDraftBody = Record<string, unknown>;

/** «Lagre Klasseøkt»: saves the Class session as it stands, with its four dates (Story 5.2) and,
 * while the settings block is open, its Game settings (Story 5.3). */
export function saveClassSession(id: string, aiMode: AiMode, dates: DatesIn, gameSettings?: SettingsDraftBody) {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}", {
      params: { path: { session_id: id } },
      body: { ai_mode: aiMode, dates, ...(gameSettings ? { game_settings: gameSettings } : {}) },
    }),
  );
}

/** The api's errors and warnings on a draft of the Game settings; nothing is stored (Story 5.3). */
export function checkClassSessionSettings(id: string, gameSettings: SettingsDraftBody) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/settings-check", {
      params: { path: { session_id: id } },
      body: { game_settings: gameSettings },
    }),
  );
}

/** The Lærerhjem's «Venter» and «Neste frist», fetched when the Lærerhjem opens (Story 5.2);
 * refetching on `session:<id>` comes with Story 6.4. */
export function useLecturerOverview() {
  return useQuery({
    queryKey: lecturerHomeKey,
    queryFn: () => request(() => api.GET("/api/lecturer-home/class-sessions")),
    retry: false,
  });
}
