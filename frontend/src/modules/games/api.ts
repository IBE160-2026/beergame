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

/** The play screen's one envelope (Story 6.6): the Student's own Seat in the open Week
 * (`seat_state`), who sits where (`table_status`) and the server's clock. */
export type PlayEnvelope = components["schemas"]["PlayOut"];
export type SeatState = PlayEnvelope["seat_state"];

export const playKey = (id: string) => ["games", "mine", id, "play"] as const;

/** `/api/me/games/{id}/play`, asked only while the game runs (`enabled`). */
export function usePlay(gameId: string, enabled: boolean) {
  return useQuery({
    queryKey: playKey(gameId),
    queryFn: () => request(() => api.GET("/api/me/games/{game_id}/play", { params: { path: { game_id: gameId } } })),
    enabled,
    retry: false,
  });
}

/** The Startoppgave (Story 6.3): the items in order, answered ones with their result. */
export const startingTaskKey = (id: string) => ["games", "mine", id, "starting-task"] as const;

export function useStartingTask(gameId: string) {
  return useQuery({
    queryKey: startingTaskKey(gameId),
    queryFn: () =>
      request(() => api.GET("/api/me/games/{game_id}/starting-task", { params: { path: { game_id: gameId } } })),
    retry: false,
  });
}

/** Sends one item's answer; the api scores it and stores it once. */
export function answerItem(gameId: string, itemId: string, answer: number) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/starting-task/answers", {
      params: { path: { game_id: gameId } },
      body: { item_id: itemId, answer },
    }),
  );
}

/** Answers or skips the final question; the Starting task is then done. */
export function finishTask(gameId: string, choice: components["schemas"]["Choice"]) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/starting-task/final", {
      params: { path: { game_id: gameId } },
      body: { choice },
    }),
  );
}

/** «Start spillet» (Story 6.5): starts the Student's own game, or finds it started already, and
 * answers the game as it now stands. */
export function startGame(gameId: string) {
  return request(() => api.POST("/api/me/games/{game_id}/start", { params: { path: { game_id: gameId } } }));
}
