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

/** «Start testspill» (Story 6.20): a test Game on the session's stored settings, the Lecturer in
 * `role`, started at once. 404 `not_found` while the flag is off; 409 `session_locked`,
 * `test_game_running` or `llm_unavailable`. */
export function startTestGame(sessionId: string, role: components["schemas"]["Role"]) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/test-game", {
      params: { path: { session_id: sessionId } },
      body: { role },
    }),
  );
}

export type SettingsCheck = components["schemas"]["SettingsCheckOut"];
/** A draft of the Game settings as sent: any field, laid over the stored settings by the api. */
export type SettingsDraftBody = Record<string, unknown>;

/** What «Lagre Klasseøkt» sends of KI-modus, Innsatsnivå and Debrief-modus (Story 5.5), and of
 * Obligatorisk with its required share (Story 5.7). */
export type ChoicesBody = Pick<
  ClassSessionSaveIn,
  | "ai_mode"
  | "effort_level"
  | "debrief_mode"
  | "debrief_release"
  | "debrief_ai_text"
  | "obligatory"
  | "required_share_percent"
  | "allocation_method"
  | "ai_assessment"
  | "letter_setting"
  | "letter_thresholds"
>;
export type AllocationMethod = ClassSession["allocation_method"];
type ClassSessionSaveIn = components["schemas"]["ClassSessionSaveIn"];

/** «Lagre Klasseøkt»: saves the Class session as it stands, with its choices (Stories 5.5, 5.7),
 * its four dates (Story 5.2) and, while the settings block is open, its Game settings (Story 5.3)
 * and its Inactivity limit (Story 5.7). */
export function saveClassSession(
  id: string,
  choices: ChoicesBody,
  dates: DatesIn,
  gameSettings?: SettingsDraftBody,
  inactivityLimitHours?: number,
  replay?: ReplayScenarioBody,
) {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}", {
      params: { path: { session_id: id } },
      body: {
        ...choices,
        dates,
        ...(gameSettings ? { game_settings: gameSettings } : {}),
        ...(inactivityLimitHours !== undefined ? { inactivity_limit_hours: inactivityLimitHours } : {}),
        ...(replay ?? {}),
      },
    }),
  );
}

export type LabHour = components["schemas"]["LabHourOut"];
export type LabHourIn = components["schemas"]["LabHourIn"];

/** «Legg til Labtime»: stores a Lab hour at once and tells the Students (Story 5.6). */
export function addLabHour(sessionId: string, body: LabHourIn) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/lab-hours", { params: { path: { session_id: sessionId } }, body }),
  );
}

/** Changes a Lab hour that has not ended (Story 5.6). */
export function changeLabHour(sessionId: string, labHourId: string, body: LabHourIn) {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}/lab-hours/{lab_hour_id}", {
      params: { path: { session_id: sessionId, lab_hour_id: labHourId } },
      body,
    }),
  );
}

/** Removes a Lab hour that has not ended; the Students are told it is cancelled (Story 5.6). */
export function removeLabHour(sessionId: string, labHourId: string) {
  return request(() =>
    api.DELETE("/api/class-sessions/{session_id}/lab-hours/{lab_hour_id}", {
      params: { path: { session_id: sessionId, lab_hour_id: labHourId } },
    }),
  );
}

/** The Replay scenario as «Lagre Klasseøkt» sends it (Story 10.2): the choice, and for an own one
 * its template fields as typed. */
export type ReplayScenarioBody = {
  replay_scenario: "default" | "own";
  replay_template?: SettingsDraftBody;
};

/** What the api says of a draft of an own Replay scenario as a field is left (Story 10.2): errors
 * and the warnings of changes that probably make the Replay easier. Nothing is stored. */
export function checkReplayScenario(id: string, template: SettingsDraftBody) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/replay-scenario-check", {
      params: { path: { session_id: id } },
      body: { replay_template: template },
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

/** The customer demand Week by Week, as the engine materialises it from the saved Demand pattern
 * and seed (Story 5.4). Fetched when the Lecturer asks; the key holds the saved pattern, so a
 * saved change fetches it again. */
export function useDemandSeries(session: ClassSession, enabled: boolean) {
  const s = session.game_settings;
  return useQuery({
    queryKey: ["class-sessions", "demand-series", session.id, JSON.stringify([s.demand, s.demand_seed, s.weeks])],
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/demand-series", { params: { path: { session_id: session.id } } }),
      ),
    enabled,
    retry: false,
  });
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

export type Allocation = components["schemas"]["AllocationOut"];
export type AllocationGame = components["schemas"]["AllocationGameOut"];
export type AllocationSeat = components["schemas"]["AllocationSeatOut"];

/** The «Fordeling» block of a Class session (Story 5.8). */
export const allocationKey = (id: string) => ["class-sessions", "allocation", id] as const;

/** The «Fordeling» block as stored: the registered Students and the draft, None until drawn. */
export function useAllocation(sessionId: string) {
  return useQuery({
    queryKey: allocationKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/allocation", { params: { path: { session_id: sessionId } } }),
      ),
    retry: false,
  });
}

/** Opening the preview: the stored draft, or one drawn now when none is stored (Story 5.8). */
export function openAllocation(sessionId: string) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/allocation", { params: { path: { session_id: sessionId } } }),
  );
}

/** «Bekreft fordeling»: commits the draft shown, by its id and revision (Story 5.9). */
export function confirmAllocation(sessionId: string, draftId: string, revision: number) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/allocation/confirm", {
      params: { path: { session_id: sessionId } },
      body: { draft_id: draftId, revision },
    }),
  );
}

/** «Kjør fordeling på nytt»: a new draft under a new id; nobody is told (Story 5.8). */
export function redrawAllocation(sessionId: string) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/allocation/redraw", { params: { path: { session_id: sessionId } } }),
  );
}

export type AllocationMove = Omit<components["schemas"]["AllocationMoveIn"], "draft_id" | "revision">;

/** Move a Student to a free Seat, or swap two, in the draft shown, by its id and revision
 * (Story 5.10). Once confirmed the Class games change too, and the Students who moved are told. */
export function moveInAllocation(sessionId: string, draftId: string, revision: number, move: AllocationMove) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/allocation/move", {
      params: { path: { session_id: sessionId } },
      body: { draft_id: draftId, revision, ...move },
    }),
  );
}

export type EnrolledSession = components["schemas"]["EnrolledSessionOut"];
export type SeatChoice = components["schemas"]["SeatChoiceOut"];
export type SeatChoiceGame = components["schemas"]["SeatChoiceGameOut"];
export type SeatChoiceSeat = components["schemas"]["SeatChoiceSeatOut"];

/** The Student's Class sessions (Story 5.2): Hjem reads Student choice from it (Story 5.17). */
export const enrolledSessionsKey = ["class-sessions", "enrolled"] as const;

export function useEnrolledSessions() {
  return useQuery({
    queryKey: enrolledSessionsKey,
    queryFn: () => request(() => api.GET("/api/me/class-sessions")),
    retry: false,
  });
}

/** «Velg spill og sete» (Story 5.17): fetched when the screen opens and after each own action;
 * refetching on `user:<id>` comes with Story 6.4's topic map. */
export const seatChoiceKey = (id: string) => ["class-sessions", "seat-choice", id] as const;

export function useSeatChoice(sessionId: string) {
  return useQuery({
    queryKey: seatChoiceKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/me/class-sessions/{session_id}/seat-choice", { params: { path: { session_id: sessionId } } }),
      ),
    retry: false,
  });
}

/** «Ta setet …»: takes the free Seat, or moves the Student to it (Story 5.17). */
export function takeSeat(sessionId: string, gameNumber: number, role: string) {
  return request(() =>
    api.PUT("/api/me/class-sessions/{session_id}/seat-choice", {
      params: { path: { session_id: sessionId } },
      body: { game_number: gameNumber, role },
    }),
  );
}

export type CopySource = components["schemas"]["CopySourceOut"];

/** The Class sessions a rerun may copy into the Class (Story 5.18), fetched when the panel opens. */
export const copySourcesKey = (classId: string) => ["class-sessions", "copy-sources", classId] as const;

export function useCopySources(classId: string, enabled: boolean) {
  return useQuery({
    queryKey: copySourcesKey(classId),
    queryFn: () =>
      request(() =>
        api.GET("/api/classes/{class_id}/class-sessions/copy-sources", { params: { path: { class_id: classId } } }),
      ),
    enabled,
    retry: false,
  });
}

/** «Lag kopi»: a new Class session in the Class with the source's settings (Story 5.18). */
export function copyClassSession(classId: string, sourceId: string, keepSeed: boolean) {
  return request(() =>
    api.POST("/api/classes/{class_id}/class-sessions/copy", {
      params: { path: { class_id: classId } },
      body: { source_id: sourceId, keep_seed: keepSeed },
    }),
  );
}
