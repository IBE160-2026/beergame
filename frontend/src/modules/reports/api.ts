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
export function useStudentPage(sessionId: string, userId: string, enabled = true) {
  return useQuery({
    enabled,
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

/** The Studentside's record (Story 13.2): under the Student's Studentside key, so the Class
 * session's `session:<id>` event reads it again (`topics.ts`) when a step is recorded. */
export const studentRecordKey = (sessionId: string, userId: string) =>
  [...studentPageKey(sessionId, userId), "record"] as const;

/** `/api/class-sessions/{id}/students/{user_id}/record`: for the Lecturers and Assistant lecturers
 * of the Class; anyone else, and a User who is no Student of it, answers 403 `forbidden`. */
export function useStudentRecord(sessionId: string, userId: string) {
  return useQuery({
    queryKey: studentRecordKey(sessionId, userId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/students/{user_id}/record", {
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

export type CorrectionIn = components["schemas"]["CorrectionIn"];

/** «Lagre retting» (Story 13.3): a new correction of one step; answers the Studentside's record as
 * it now stands. 422 `invalid_correction` names the reason in `fields.reason` (`required`,
 * `too_long`); 409 `not_obligatory` or `class_archived`. */
export function correctCompletion(sessionId: string, userId: string, body: CorrectionIn) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/students/{user_id}/corrections", {
      params: { path: { session_id: sessionId, user_id: userId } },
      body,
    }),
  );
}

/** «Gi oppfølgingsspill» (Story 13.4): the Student gets an Oppfølgingsspill; answers the
 * Studentside's record as it now stands (a second press answers the same one). 409
 * `session_not_locked`, `no_test_deadline`, `test_deadline_passed` or `class_archived`. */
export function giveMakeup(sessionId: string, userId: string) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/students/{user_id}/makeup", {
      params: { path: { session_id: sessionId, user_id: userId } },
    }),
  );
}

/** The Student's own Student report (Story 13.7, FR-57): when it opens, its status, and when the
 * PDF to download was made. */
export type ReportState = components["schemas"]["ReportStateOut"];

/** Under `["reports", "mine"]`, which the Student's `user:<id>` event reads again (`topics.ts`):
 * the finished render emits it, so the page updates without a reload (AD-8). */
export const myReportsKey = ["reports", "mine"] as const;
export const myReportKey = (sessionId: string) => [...myReportsKey, sessionId] as const;

/** `/api/me/class-sessions/{id}/report`: 403 `forbidden` for a Class session not the Student's own. */
export function useMyReport(sessionId: string) {
  return useQuery({
    queryKey: myReportKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/me/class-sessions/{session_id}/report", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
    // The render's `user` event updates it; while pending it is also read every 15 s, so a missed
    // event or a render that never ended (read as failed after two minutes) still shows.
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 15_000 : false),
  });
}

/** «Lag Studentrapport»: records the request and answers the pending state; 409
 * `report_not_open` before the Testfrist, `not_counted` for a Student reports leave out. */
export function requestMyReport(sessionId: string) {
  return request(() =>
    api.POST("/api/me/class-sessions/{session_id}/report", {
      params: { path: { session_id: sessionId } },
    }),
  );
}

/** The download: a plain link to the api, which checks the policy and answers 303 to a signed URL
 * that lives five minutes (NFR-7). */
export function myReportFilePath(sessionId: string): string {
  return `/api/me/class-sessions/${encodeURIComponent(sessionId)}/report/file`;
}
