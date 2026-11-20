"use client";

import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useEffect, useSyncExternalStore } from "react";

import { RECONNECTED_MS } from "@/lib/connection";
import { meKey, type SessionUser } from "@/modules/identity/api";

import { parseEvent, topicKeys } from "./topics";

/**
 * Live updates (AD-8, Story 6.4): one `EventSource` on `GET /api/events` while a User is logged
 * in. The stream sends `ready` once subscribed, then `{topic, id, version}` per change and a
 * `heartbeat` every 15 s. Each change invalidates the keys `topics.ts` maps it to, and TanStack
 * Query reads them again over REST; a `ready` after an earlier one (a reconnect) reads every
 * visible query again. No beat for `STALE_MS` marks live values stale for the Tilkoblingslinje.
 */
export const EVENTS_PATH = "/api/events";
/** One missed 15 s heartbeat, with slack for a slow network. */
export const STALE_MS = 20_000;
export const CHECK_MS = 5_000;
/** How long a stream the server refused (it ended `CLOSED`) waits before it opens again. */
export const REOPEN_MS = 5_000;

export type LiveStatus = "idle" | "connecting" | "live" | "stale";
export type LiveState = {
  status: LiveStatus;
  /** When live values were last known current: the last event or beat (ms since epoch). */
  lastBeat: number;
  /** Shown as «Tilkoblet igjen.» for `RECONNECTED_MS` after a stale stream is live again. */
  recovered: boolean;
};

const IDLE: LiveState = { status: "idle", lastBeat: 0, recovered: false };
let state: LiveState = IDLE;
const listeners = new Set<() => void>();
let recoveredTimer: ReturnType<typeof setTimeout> | undefined;

function set(next: Partial<LiveState>) {
  state = { ...state, ...next };
  // The status on the root element, for the end-to-end tests to wait on a live stream.
  if (typeof document !== "undefined") document.documentElement.dataset.live = state.status;
  for (const listener of listeners) listener();
}

export function liveState(): LiveState {
  return state;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The stream's state, for the Tilkoblingslinje. The server render has no stream. */
export function useLive(): LiveState {
  return useSyncExternalStore(subscribe, liveState, () => IDLE);
}

/** What `connectLive` needs of an `EventSource`. */
export type EventSourceLike = {
  readonly readyState: number;
  addEventListener(type: string, listener: (event: MessageEvent) => void): void;
  onerror: ((event: Event) => void) | null;
  close(): void;
};
const CLOSED = 2;

/** Open the stream and keep it open; returns what closes it. */
export function connectLive(
  queryClient: QueryClient,
  open: (url: string) => EventSourceLike = (url) => new EventSource(url),
): () => void {
  let source: EventSourceLike | undefined;
  let readyBefore = false;
  let reopen: ReturnType<typeof setTimeout> | undefined;
  set({ status: "connecting", lastBeat: Date.now(), recovered: false });

  const beat = () => {
    if (state.status === "stale") {
      clearTimeout(recoveredTimer);
      recoveredTimer = setTimeout(() => set({ recovered: false }), RECONNECTED_MS);
      set({ status: "live", lastBeat: Date.now(), recovered: true });
    } else {
      set({ status: "live", lastBeat: Date.now() });
    }
  };

  const start = () => {
    const current = open(EVENTS_PATH);
    source = current;
    current.addEventListener("ready", () => {
      // Back after a drop: anything may have changed meanwhile. Focus never moves.
      if (readyBefore) void queryClient.refetchQueries({ type: "active" });
      readyBefore = true;
      beat();
    });
    current.addEventListener("heartbeat", beat);
    current.addEventListener("message", (message) => {
      beat();
      const event = parseEvent(String(message.data));
      if (!event) return;
      for (const queryKey of topicKeys(event)) void queryClient.invalidateQueries({ queryKey });
    });
    current.onerror = () => {
      // The browser reconnects by itself unless the server refused the stream.
      if (current.readyState !== CLOSED || current !== source) return;
      current.close();
      // Refused, perhaps because the session ended: reading `/me` again sends an ended session to
      // «Logg inn» (and a logged-out one closes the stream) instead of retrying for ever.
      void queryClient.invalidateQueries({ queryKey: meKey });
      reopen = setTimeout(start, REOPEN_MS);
    };
  };

  const check = setInterval(() => {
    if (state.status !== "stale" && Date.now() - state.lastBeat > STALE_MS) set({ status: "stale" });
  }, CHECK_MS);
  start();

  return () => {
    clearInterval(check);
    clearTimeout(reopen);
    clearTimeout(recoveredTimer);
    source?.close();
    source = undefined;
    set(IDLE);
  };
}

/** Keeps the stream open while the cached session holds a User; never fetches `/me` itself. */
export function LiveUpdates() {
  const queryClient = useQueryClient();
  // Read from the cache, not through a query observer: an observer would bring options of its own
  // to the `/me` query.
  const userId = useSyncExternalStore(
    (onChange) => queryClient.getQueryCache().subscribe(onChange),
    () => queryClient.getQueryData<SessionUser | null>(meKey)?.id ?? null,
    () => null,
  );
  useEffect(() => {
    if (!userId) return;
    return connectLive(queryClient);
  }, [userId, queryClient]);
  return null;
}
