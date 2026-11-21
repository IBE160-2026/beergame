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

/** The Oversikt of a Class session (Story 7.1): every Class game from its maintained summary. */
export type ClassOverview = components["schemas"]["ClassOverviewOut"];
export type OverviewGame = ClassOverview["items"][number];
export const classOverviewKey = (sessionId: string) => ["games", "overview", sessionId] as const;

/** `/api/class-sessions/{id}/overview`, for the Class's staff; anyone else, and a Class session
 * that does not exist, answers 403 `forbidden`. Read past the browser's cache: the answer carries
 * an ETag, and a body the cache revalidated would bring an old `server_now`, so waits and
 * «Oppdatert» would lag. */
export function useClassOverview(sessionId: string) {
  return useQuery({
    queryKey: classOverviewKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/overview", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}

/** The play screen's one envelope (Story 6.6): the Student's own Seat in the open Week
 * (`seat_state`), the own turn (`turn`, Story 6.10), who sits where (`table_status`) and the
 * server's clock. */
export type PlayEnvelope = components["schemas"]["PlayOut"];
export type SeatState = PlayEnvelope["seat_state"];
export type PlayTurn = PlayEnvelope["turn"];

/** The Student has the Guided Week `week` on screen (Story 6.10): in a Guided Week that counts as
 * their Order. A Week already viewed answers the same; one the game has left answers 409. */
export function viewWeek(gameId: string, week: number) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/weeks/{week}/view", { params: { path: { game_id: gameId, week } } }),
  );
}

/** «Bekreft ordre på 24» (Story 6.12): the Student's Order for the open Week, placed once; no
 * `version` is sent. Answers 204; a refusal carries the command's code (`order_exists`,
 * `week_not_open`, `seat_not_yours`, …), which Story 6.13 turns into copy. `signal` aborts a
 * send that took too long (it then fails as `network_error`). */
export function placeOrder(gameId: string, week: number, order: number, signal?: AbortSignal) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/weeks/{week}/order", {
      params: { path: { game_id: gameId, week } },
      body: { order },
      signal,
    }),
  );
}

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

/** «Send forslaget til gruppen» (Story 6.19): proposes a time to play, which replaces the open
 * proposal, and answers the game as it now stands. 422 `time_out_of_range` outside now to the Play
 * deadline. */
export function proposeTime(gameId: string, at: string) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/time-proposal", { params: { path: { game_id: gameId } }, body: { at } }),
  );
}

/** «Godta tidspunktet» (Story 6.19): accepts the open proposal with one press; a second press
 * answers the same. 409 `proposal_gone` once it was replaced or has passed. */
export function acceptTime(gameId: string, proposalId: string) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/time-proposal/{proposal_id}/accept", {
      params: { path: { game_id: gameId, proposal_id: proposalId } },
    }),
  );
}

/** «Spillet er ferdig» (Story 6.18): the finished game's cost per Role, the chain's and the
 * chain's per Uke. The api answers 409 `game_not_finished` before the end. */
export type GameResult = components["schemas"]["GameResult"];

export const resultKey = (id: string) => ["games", "mine", id, "result"] as const;

/** `/api/me/games/{id}/result`, asked only once the game has finished (`enabled`). */
export function useGameResult(gameId: string, enabled: boolean) {
  return useQuery({
    queryKey: resultKey(gameId),
    queryFn: () => request(() => api.GET("/api/me/games/{game_id}/result", { params: { path: { game_id: gameId } } })),
    enabled,
    retry: false,
  });
}
