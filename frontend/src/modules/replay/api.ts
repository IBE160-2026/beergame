"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";
import { myGameKey } from "@/modules/games/api";

/** The Replay-gjennomgang (Story 10.7): `pending` while its line is worded, then `ready`. */
export type Walkthrough = components["schemas"]["ReplayWalkthroughOut"];
export type WalkthroughRun = components["schemas"]["WalkthroughRunOut"];
export type WalkthroughMoment = components["schemas"]["WalkthroughMomentOut"];

/** Under `["games", "mine", id]`, so `user:<id>` (the job storing the line) reads it again. */
export const walkthroughKey = (gameId: string) => [...myGameKey(gameId), "walkthrough"] as const;

/** The longest wait between two reads while `pending`, in seconds: a missed `user:<id>` event
 * (a dropped connection, a phone in the background) costs at most this. */
const PENDING_POLL_MAX = 10;

/** The wait before asking again while `pending`: the api's `retry_after_seconds`, at most
 * `PENDING_POLL_MAX`, so the page shows the code walkthrough once the wait limit has passed even
 * when no event comes. */
export function pendingRefetch(data: Walkthrough | undefined): number | false {
  if (data?.state !== "pending") return false;
  return Math.min(PENDING_POLL_MAX, Math.max(1, data.retry_after_seconds ?? PENDING_POLL_MAX)) * 1000;
}

/** `GET /api/me/games/{id}/walkthrough`: 403 `forbidden` for any Game that is not the Student's
 * own Replay, 409 `replay_closed` or `replay_not_finished`. */
export function useWalkthrough(gameId: string) {
  return useQuery({
    queryKey: walkthroughKey(gameId),
    queryFn: () =>
      request(() => api.GET("/api/me/games/{game_id}/walkthrough", { params: { path: { game_id: gameId } } })),
    retry: false,
    refetchInterval: (query) => pendingRefetch(query.state.data),
  });
}

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
