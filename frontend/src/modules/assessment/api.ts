"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";
import { myTestsKey } from "@/modules/tests/api";

/** The Student's «KI-vurdering» of their Individual test (Story 12.2). */
export type MyAssessment = components["schemas"]["MyAssessmentOut"];
export type AssessedItem = components["schemas"]["AssessedItemOut"];
/** An AI item's written feedback (Story 12.3): text parts and quotes of the Student's answer. */
export type ItemFeedback = components["schemas"]["FeedbackOut"];

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

/** «Marker som feil» (`flagged`) or «Angre» on one item's written feedback (Story 12.5, FR-55):
 * answers the Student's view as it now stands; 409 `feedback_not_flaggable` when the view shows no
 * feedback for that item. */
export function setFeedbackFlag(classSessionId: string, itemId: string, flagged: boolean) {
  const params = { params: { path: { session_id: classSessionId, item_id: itemId } } };
  return request(() =>
    flagged
      ? api.PUT("/api/me/class-sessions/{session_id}/test/assessment/items/{item_id}/flag", params)
      : api.DELETE("/api/me/class-sessions/{session_id}/test/assessment/items/{item_id}/flag", params),
  );
}

/** «Veiledende bokstav» (Story 12.6, FR-56): the Student turns the Indicative letter on or off for
 * their own view; answers the view as it now stands; 409 `letter_not_available` when the view
 * offers no such choice. */
export function setLetterChoice(classSessionId: string, on: boolean) {
  return request(() =>
    api.PUT("/api/me/class-sessions/{session_id}/test/assessment/letter", {
      params: { path: { session_id: classSessionId } },
      body: { on },
    }),
  );
}

/** A Student's «KI-vurdering» as the staff of their Class read it (Story 12.5). */
export type StaffAssessment = components["schemas"]["StaffAssessmentOut"];
/** The Klasseøkt's list of the Students' AI assessments (Story 12.5). */
export type AssessmentRow = components["schemas"]["AssessmentRowOut"];

/** Under `["class-sessions", id]`, which the `session` event reads again. */
export const assessmentListKey = (sessionId: string) => ["class-sessions", sessionId, "assessments"] as const;

/** `/api/class-sessions/{id}/assessments`: for the staff of the Class; 403 `forbidden` otherwise. */
export function useAssessmentList(sessionId: string) {
  return useQuery({
    queryKey: assessmentListKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/assessments", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}
