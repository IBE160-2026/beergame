import { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RECONNECTED_MS } from "@/lib/connection";
import { meKey } from "@/modules/identity/api";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { connectLive, EVENTS_PATH, type EventSourceLike, liveState, REOPEN_MS, STALE_MS } from "./live";

/** A stand-in `EventSource` the test drives by hand. */
class FakeSource implements EventSourceLike {
  readyState = 0;
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  private listeners = new Map<string, ((event: MessageEvent) => void)[]>();
  constructor(readonly url: string) {}
  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }
  emit(type: string, data = "") {
    this.readyState = 1;
    for (const listener of this.listeners.get(type) ?? []) listener({ data } as MessageEvent);
  }
  fail(readyState: number) {
    this.readyState = readyState;
    this.onerror?.(new Event("error"));
  }
  close() {
    this.closed = true;
    this.readyState = 2;
  }
}

let sources: FakeSource[];
let client: QueryClient;
let stop: () => void;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(Date.UTC(2026, 10, 20, 20, 14));
  sources = [];
  client = new QueryClient();
  stop = connectLive(client, (url) => {
    const source = new FakeSource(url);
    sources.push(source);
    return source;
  });
});

afterEach(() => {
  stop();
  vi.useRealTimers();
});

describe("connectLive", () => {
  it("opens the stream and is live on ready", () => {
    expect(sources.map((s) => s.url)).toEqual([EVENTS_PATH]);
    expect(liveState().status).toBe("connecting");
    sources[0].emit("ready");
    expect(liveState().status).toBe("live");
  });

  it("invalidates the keys an event maps to, and ignores what is not an event", () => {
    const invalidate = vi.spyOn(client, "invalidateQueries");
    sources[0].emit("ready");
    sources[0].emit("message", '{"topic":"user","id":"u1","version":null}');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: enrolledSessionsKey });
    invalidate.mockClear();
    sources[0].emit("message", "nonsense");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("reads every visible query again on a ready after a reconnect, not on the first", () => {
    const refetch = vi.spyOn(client, "refetchQueries");
    sources[0].emit("ready");
    expect(refetch).not.toHaveBeenCalled();
    sources[0].fail(0); // the browser reconnects by itself
    sources[0].emit("ready");
    expect(refetch).toHaveBeenCalledWith({ type: "active" });
  });

  it("goes stale after a missed heartbeat, then shows «Tilkoblet igjen.» for 5 s", () => {
    sources[0].emit("ready");
    const beat = liveState().lastBeat;
    vi.advanceTimersByTime(STALE_MS - 1_000);
    sources[0].emit("heartbeat");
    vi.advanceTimersByTime(STALE_MS - 1_000);
    expect(liveState().status).toBe("live");
    vi.advanceTimersByTime(10_000);
    expect(liveState()).toMatchObject({ status: "stale", recovered: false });
    expect(liveState().lastBeat).toBe(beat + STALE_MS - 1_000);
    sources[0].emit("heartbeat");
    expect(liveState()).toMatchObject({ status: "live", recovered: true });
    vi.advanceTimersByTime(RECONNECTED_MS);
    expect(liveState().recovered).toBe(false);
  });

  it("goes stale when the stream never opens", () => {
    vi.advanceTimersByTime(STALE_MS + 5_000);
    expect(liveState().status).toBe("stale");
  });

  it("opens a new stream after the server refused one, and reads the session again", () => {
    const invalidate = vi.spyOn(client, "invalidateQueries");
    sources[0].fail(2);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: meKey });
    expect(sources[0].closed).toBe(true);
    vi.advanceTimersByTime(REOPEN_MS);
    expect(sources).toHaveLength(2);
  });

  it("closes the stream and goes idle when stopped", () => {
    stop();
    expect(sources[0].closed).toBe(true);
    expect(liveState().status).toBe("idle");
    vi.advanceTimersByTime(REOPEN_MS * 4);
    expect(sources).toHaveLength(1);
    stop = () => {};
  });
});
