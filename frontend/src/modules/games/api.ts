"use client";

import { keepPreviousData, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";

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

/** How long a failed background read of the Oversikt waits before it is tried again. */
export const OVERVIEW_RETRY_MS = 10_000;

/** One answer of the Oversikt: the body, its ETag and when it arrived (ms on the browser's clock,
 * only to measure the time since `server_now`). */
export type OverviewAnswer = { overview: ClassOverview; etag: string | null; receivedAt: number };

/**
 * Reads the Oversikt, revalidating `previous` with its ETag (Story 7.5, AD-25). An unchanged list
 * answers 304 and `previous` itself comes back, the same object, so nothing that reads it renders
 * again and its `server_now` stays tied to the time it arrived. The browser's own cache is passed
 * by: a body it revalidated would bring an old `server_now` as if new.
 */
export async function readOverview(
  sessionId: string,
  previous: OverviewAnswer | undefined,
  client: typeof api = api,
): Promise<OverviewAnswer> {
  const sent = previous?.etag;
  let notModified = false;
  let etag: string | null = null;
  const overview = await request(async () => {
    const result = await client.GET("/api/class-sessions/{session_id}/overview", {
      params: { path: { session_id: sessionId } },
      headers: sent ? { "If-None-Match": sent } : undefined,
      cache: "no-store",
    });
    // A 304 is not an error here: it says the list we hold is the current one.
    if (result.response.status === 304 && previous) {
      notModified = true;
      return { data: previous.overview, response: new Response(null, { status: 200 }) };
    }
    etag = result.response.headers.get("ETag");
    return result;
  });
  if (notModified && previous) return previous;
  return { overview, etag, receivedAt: Date.now() };
}

/** `/api/class-sessions/{id}/overview`, for the Class's staff; anyone else, and a Class session
 * that does not exist, answers 403 `forbidden`. Revalidated with its ETag (`readOverview`). */
export function useClassOverview(sessionId: string) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: classOverviewKey(sessionId),
    queryFn: () => readOverview(sessionId, queryClient.getQueryData<OverviewAnswer>(classOverviewKey(sessionId))),
    retry: false,
    // A background read that failed is tried again while the last answer stays on screen (the
    // page with no answer yet shows the page error with «Prøv igjen» instead).
    refetchInterval: (query: { state: { status: string; data: unknown } }) =>
      query.state.status === "error" && query.state.data !== undefined ? OVERVIEW_RETRY_MS : false,
  });
}

/** Spillinnsikt (Story 7.7): one Class game week by week, for the staff of its Class. */
export type GameInsight = components["schemas"]["GameInsightOut"];
export type InsightSeat = GameInsight["seats"][number];
export type InsightRole = GameInsight["roles"][number];
export type InsightWeek = InsightRole["weeks"][number];
export type SeatMark = InsightWeek["marks"][number];
export const gameInsightKey = (gameId: string) => ["games", "insight", gameId] as const;

/** `/api/games/{id}/insight`: anyone but the staff of the game's Class, and a game that does not
 * exist, answers 403 `forbidden`. Read again on the game's `game:<id>` event (`topics.ts`). */
export function useGameInsight(gameId: string) {
  return useQuery({
    queryKey: gameInsightKey(gameId),
    queryFn: () =>
      request(() =>
        api.GET("/api/games/{game_id}/insight", { params: { path: { game_id: gameId } }, cache: "no-store" }),
      ),
    retry: false,
  });
}

/** A Class game's opened Weeks, per Role (Story 7.2): the Matrisevegg's cells. */
export type GameWeeks = components["schemas"]["GameWeeksOut"];

/** Keyed by the Game's `version` too: a version the Oversikt has not seen is a new query, and a
 * Game whose version stands is never fetched again (AD-10, AD-25). */
export const gameWeeksKey = (gameId: string, version: number) => ["games", "weeks", gameId, version] as const;

/** How long a failed `/weeks` read waits before it is tried again. */
export const WEEKS_RETRY_MS = 10_000;

/**
 * `/api/games/{id}/weeks` for each game the Oversikt listed, fetched on demand and again only when
 * the summary list brings that game a new `version`. While a new version loads, the last one's
 * weeks stay on screen. Returns the weeks by game id; a game still loading has none yet.
 */
export function useGameWeeks(games: readonly { game_id: string; version: number }[]) {
  // A new version is a new query with no data of its own (`useQueries` matches by key), so the
  // last weeks each game had stand in until it arrives: the cells never empty and focus stays.
  const last = useRef(new Map<string, GameWeeks>());
  const results = useQueries({
    queries: games.map((game) => ({
      queryKey: gameWeeksKey(game.game_id, game.version),
      queryFn: () =>
        request(() =>
          api.GET("/api/games/{game_id}/weeks", { params: { path: { game_id: game.game_id } }, cache: "no-store" }),
        ),
      staleTime: Number.POSITIVE_INFINITY,
      retry: false,
      // A read that failed is tried again until it succeeds, so a row is never left empty until
      // its game changes (Story 7.5); a read that succeeded stands for its version.
      refetchInterval: (query: { state: { status: string } }) =>
        query.state.status === "error" ? WEEKS_RETRY_MS : false,
    })),
  });
  const byGame = new Map<string, { data?: GameWeeks; failed: boolean }>();
  results.forEach((result, i) => {
    const id = games[i]!.game_id;
    if (result.data) last.current.set(id, result.data);
    const data = result.data ?? last.current.get(id);
    byGame.set(id, { data, failed: result.isError && !data });
  });
  return byGame;
}

/** The class median rows for one Veggfiltre combination (Story 7.4). */
export type WallAggregates = components["schemas"]["WallAggregatesOut"];
export type WallFilter = {
  role: WallAggregates["role"];
  cells: WallAggregates["cells"];
  status: WallAggregates["status"];
};

/** Under the Oversikt's key, so a `session:<id>` event (`topics.ts`) refetches it with the list. */
export const wallAggregatesKey = (sessionId: string, filter: WallFilter) =>
  [...classOverviewKey(sessionId), "aggregates", filter.role, filter.cells, filter.status] as const;

/**
 * `/api/class-sessions/{id}/overview/aggregates` for one filter combination (Story 7.4, AD-10):
 * the median, middle half and mean chain cost per Uke, computed by the api. While a new
 * combination loads, the last one's rows stay on screen. Revalidated with its ETag, so an
 * unchanged class answers 304.
 */
export function useWallAggregates(sessionId: string, filter: WallFilter) {
  return useQuery({
    queryKey: wallAggregatesKey(sessionId, filter),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/overview/aggregates", {
          params: { path: { session_id: sessionId }, query: filter },
          cache: "no-cache",
        }),
      ),
    placeholderData: keepPreviousData,
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

/** «Ta tilbake setet» (Story 8.4, FR-37): asks for the own Seat `role` back from the next Uke and
 * answers the game as it now stands; a repeat answers the same. 409 `seat_not_yours`,
 * `game_finished` or `game_not_running`. */
export function reclaimSeat(gameId: string, role: components["schemas"]["Role"]) {
  return request(() =>
    api.POST("/api/me/games/{game_id}/seats/{role}/reclaim", {
      params: { path: { game_id: gameId, role } },
    }),
  );
}

/** «Ta pause uten avtalt tid» (Story 8.6, FR-89): a Student of the game pauses it; no time is sent.
 * Answers the game as it now stands; 409 `already_paused` when someone paused first. */
export function pauseGame(gameId: string) {
  return request(() => api.POST("/api/me/games/{game_id}/pause", { params: { path: { game_id: gameId } } }));
}

/** The pause line the api sent (Story 8.6). */
export type GamePause = NonNullable<MyGame["pause"]>;

/** «Sett inn KI-spiller for …» (Story 8.5, FR-37): a Lecturer or Assistant lecturer puts an AI
 * player in the Seat `role`; answers Spillinnsikt as it now stands. 409 `takeover_exists` carries
 * `acted_by` and `acted_at`, by id only. */
export function takeOverSeat(gameId: string, role: components["schemas"]["Role"]) {
  return request(() =>
    api.POST("/api/games/{game_id}/seats/{role}/takeover", {
      params: { path: { game_id: gameId, role } },
    }),
  );
}

/** «Pause spillet» (Story 8.7, FR-89): a Lecturer of the game's Class pauses it, with the agreed
 * time `resumeAt` (ISO) or without one (null). Answers Spillinnsikt as it now stands; 422
 * `time_out_of_range`, 409 `already_paused` with `acted_by` and `acted_at`. */
export function pauseGameAsLecturer(gameId: string, resumeAt: string | null) {
  return request(() =>
    api.POST("/api/games/{game_id}/pause", {
      params: { path: { game_id: gameId } },
      body: { resume_at: resumeAt },
    }),
  );
}

/** «Endre avtalt tid» (Story 8.7): sets, changes or (null) clears the agreed time. */
export function setPauseAgreedTime(gameId: string, resumeAt: string | null) {
  return request(() =>
    api.PUT("/api/games/{game_id}/pause/agreed-time", {
      params: { path: { game_id: gameId } },
      body: { resume_at: resumeAt },
    }),
  );
}

/** «Avslutt pausen» (Story 8.7): ends the Pause in force, whoever set it. */
export function endPause(gameId: string) {
  return request(() => api.DELETE("/api/games/{game_id}/pause", { params: { path: { game_id: gameId } } }));
}

/** The Pause in force on Spillinnsikt (Story 8.7). */
export type InsightPause = NonNullable<GameInsight["pause"]>;

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
