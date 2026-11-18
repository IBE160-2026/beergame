"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

/** How long «Tilkoblet igjen.» stays before the line goes (EXPERIENCE.md → State Patterns). */
export const RECONNECTED_MS = 5_000;

function subscribe(onChange: () => void) {
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

/** Whether the device has a connection, from `navigator.onLine` and its events. The server
 * render assumes it has. */
export function useOnline(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
}

export type Connection = "online" | "offline" | "reconnected";

/** `offline` while the device has no connection; `reconnected` for `RECONNECTED_MS` after it
 * comes back; otherwise `online`. */
export function useConnection(): Connection {
  const online = useOnline();
  const wasOffline = useRef(false);
  const [reconnected, setReconnected] = useState(false);

  useEffect(() => {
    if (!online) {
      wasOffline.current = true;
      return;
    }
    if (!wasOffline.current) return;
    wasOffline.current = false;
    setReconnected(true);
    const timer = window.setTimeout(() => setReconnected(false), RECONNECTED_MS);
    return () => window.clearTimeout(timer);
  }, [online]);

  if (!online) return "offline";
  return reconnected ? "reconnected" : "online";
}

/** «21:14»: the clock time in Europe/Oslo, always with a colon (EXPERIENCE.md's «Sist oppdatert
 * 21:14»), whatever separator the runtime's locale data uses. */
export function formatClock(ms: number): string {
  const parts = new Intl.DateTimeFormat("nb-NO", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date(ms));
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
  return `${part("hour")}:${part("minute")}`;
}
