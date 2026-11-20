"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Student's own Class game (Story 6.1), with the rules the briefing states (Story 6.2). */
export type MyGame = components["schemas"]["StudentGameOut"];
export type GameRules = components["schemas"]["GameRulesOut"];

export const myGameKey = (id: string) => ["games", "mine", id] as const;

/** `/api/me/games/{id}`: the Student's own game; any other id answers 403 `forbidden`. */
export function useMyGame(gameId: string) {
  return useQuery({
    queryKey: myGameKey(gameId),
    queryFn: () => request(() => api.GET("/api/me/games/{game_id}", { params: { path: { game_id: gameId } } })),
    retry: false,
  });
}
