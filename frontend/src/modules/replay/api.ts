import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Replay on Hjem (Story 10.3): whether «Start Replay» shows and the started Replay. */
export type StudentReplay = components["schemas"]["StudentReplayOut"];
export type ReplayGame = components["schemas"]["ReplayGameOut"];

/** «Start Replay» (Story 10.3, FR-48): makes and starts the Student's one Replay in the Class
 * session, or answers the one they have. 403 `quiz_required` before the Debrief quiz is passed,
 * 409 `test_deadline_passed` after the Testfrist. */
export function startReplay(sessionId: string) {
  return request(() =>
    api.POST("/api/me/class-sessions/{session_id}/replay", {
      params: { path: { session_id: sessionId } },
    }),
  );
}
