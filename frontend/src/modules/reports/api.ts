"use client";

import { type QueryKey, useQuery } from "@tanstack/react-query";

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
/** Story 13.11: the standard report and the one with the AI assessment section are two states. */
export const myReportKey = (sessionId: string, ai = false) => [...myReportsKey, sessionId, ai ? "ai" : "standard"] as const;

/** Where a report's download block reads and asks (Story 13.12): the Student's own report on Hjem,
 * or one Student's report for the staff on the Studentside. One block, one pipeline. */
export type ReportSource = {
  /** The query key of the state with or without the AI assessment section. */
  key: (ai: boolean) => QueryKey;
  /** The prefix read again after a refusal (the assessment changed meanwhile). */
  family: QueryKey;
  read: (ai: boolean) => Promise<ReportState>;
  request: (ai: boolean) => Promise<ReportState>;
  /** The download: a plain link to the api, which checks the policy and answers 303 to a signed
   * URL that lives five minutes (NFR-7). */
  filePath: (ai: boolean) => string;
};

/** A report's state for its source; while pending it is also read every 15 s, so a missed event
 * or a render that never ended (read as failed after two minutes) still shows. */
export function useReport(source: ReportSource, ai = false, enabled = true) {
  return useQuery({
    enabled,
    queryKey: source.key(ai),
    queryFn: () => source.read(ai),
    retry: false,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 15_000 : false),
  });
}

/** `/api/me/class-sessions/{id}/report`: 403 `forbidden` for a Class session not the Student's own.
 * `ai` (Story 13.11): the state of the report with the AI assessment section; while it cannot be
 * added the api answers the standard one's (`ai` false), with `ai_available` false. */
export function useMyReport(sessionId: string, ai = false, enabled = true) {
  return useReport(myReportSource(sessionId), ai, enabled);
}

/** «Lag Studentrapport»: records the request and answers the pending state; 409
 * `report_not_open` before the Testfrist, `not_counted` for a Student reports leave out,
 * `ai_assessment_unavailable` when `ai` asks for the AI section and it cannot be added. */
export function requestMyReport(sessionId: string, ai = false) {
  return request(() =>
    api.POST("/api/me/class-sessions/{session_id}/report", {
      params: { path: { session_id: sessionId } },
      body: { ai },
    }),
  );
}

export function myReportFilePath(sessionId: string, ai = false): string {
  return `/api/me/class-sessions/${encodeURIComponent(sessionId)}/report/file${ai ? "?ai=true" : ""}`;
}

/** The Student's own Student report (Stories 13.7, 13.11). */
export function myReportSource(sessionId: string): ReportSource {
  return {
    key: (ai) => myReportKey(sessionId, ai),
    family: myReportsKey,
    read: (ai) =>
      request(() =>
        api.GET("/api/me/class-sessions/{session_id}/report", {
          params: { path: { session_id: sessionId }, query: ai ? { ai: true } : {} },
          cache: "no-store",
        }),
      ),
    request: (ai) => requestMyReport(sessionId, ai),
    filePath: (ai) => myReportFilePath(sessionId, ai),
  };
}

/** Story 13.12: the staff's downloads of Students' reports, under `["reports", "staff"]`, which the
 * requester's `user:<id>` event reads again once the render has ended (`topics.ts`). */
export const staffReportsKey = ["reports", "staff"] as const;
export const staffReportKey = (sessionId: string, userId: string, ai = false) =>
  [...staffReportsKey, sessionId, userId, ai ? "ai" : "standard"] as const;

/** One Student's report for the staff of the Class (Story 13.12, FR-59): open at any time, shared
 * by its Lecturers and Assistant lecturers; `ai` adds the AI section, never the Indicative letter.
 * 403 `forbidden` for anyone else; 409 `not_counted`, `ai_assessment_unavailable`. */
export function staffReportSource(sessionId: string, userId: string): ReportSource {
  const path = { session_id: sessionId, user_id: userId };
  return {
    key: (ai) => staffReportKey(sessionId, userId, ai),
    family: [...staffReportsKey, sessionId, userId],
    read: (ai) =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/students/{user_id}/report", {
          params: { path, query: ai ? { ai: true } : {} },
          cache: "no-store",
        }),
      ),
    request: (ai) =>
      request(() =>
        api.POST("/api/class-sessions/{session_id}/students/{user_id}/report", {
          params: { path },
          body: { ai },
        }),
      ),
    filePath: (ai) =>
      `/api/class-sessions/${encodeURIComponent(sessionId)}/students/${encodeURIComponent(userId)}/report/file${ai ? "?ai=true" : ""}`,
  };
}

/** The ZIP of all Student reports of a Class session (Story 13.13, FR-59). */
export type ZipState = components["schemas"]["ZipStateOut"];

/** Under `staffReportsKey`, so the requester's `user:<id>` event (the job's end and its notice)
 * reads it again (`topics.ts`). */
export const reportsZipKey = (sessionId: string) => [...staffReportsKey, sessionId, "zip"] as const;

/** `/api/class-sessions/{id}/reports/zip`: for the Lecturers and Assistant lecturers of the Class;
 * 403 `forbidden` for anyone else. While pending it is also read every 15 s, so a missed event or a
 * job that never ended (read as failed after 15 minutes) still shows. */
export function useReportsZip(sessionId: string) {
  return useQuery({
    queryKey: reportsZipKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/reports/zip", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 15_000 : false),
  });
}

/** «Last ned alle Studentrapporter (ZIP)»: records the request and answers the pending state (a
 * second press answers the pending one); 409 `no_students`, `data_deleted`. */
export function requestReportsZip(sessionId: string) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/reports/zip", {
      params: { path: { session_id: sessionId } },
    }),
  );
}

/** The download: a plain link to the api, which checks the policy and answers 303 to a signed URL
 * that lives five minutes (NFR-7). */
export function reportsZipFilePath(sessionId: string): string {
  return `/api/class-sessions/${encodeURIComponent(sessionId)}/reports/zip/file`;
}

/** Story 13.14 (FR-60): the Completion export, for the Lecturers of the Class (`completion_export`
 * in the ZIP state says whether the reader may). A plain link to the api, which checks the policy
 * and answers the file itself (CSV for Norwegian Excel, or .xlsx), built now and never stored. */
export type CompletionExportFormat = "csv" | "xlsx";

export function completionExportPath(sessionId: string, format: CompletionExportFormat): string {
  return `/api/class-sessions/${encodeURIComponent(sessionId)}/completion-export?format=${format}`;
}
