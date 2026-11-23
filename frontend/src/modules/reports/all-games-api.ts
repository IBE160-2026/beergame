"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** «Alle spill side om side» (Story 14.5): Orders per Role and Week keyed by game number only. */
export type ClassGames = components["schemas"]["ClassGamesOut"];
export type RoleOrders = components["schemas"]["RoleOrdersOut"];

export const classGamesKey = (sessionId: string) => ["reports", "all-games", sessionId] as const;

/** `/api/me/class-sessions/{id}/all-games`: 403 `all_games_locked` until the Student's Debrief is
 * done and the Play deadline has passed, 403 `forbidden` for a session that is not their own. */
export function useClassGames(sessionId: string) {
  return useQuery({
    queryKey: classGamesKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/me/class-sessions/{session_id}/all-games", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}
