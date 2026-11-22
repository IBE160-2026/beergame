"use client";

import { useEffect, useRef, useState } from "react";

/** The least time between two polite announcements of the same live value (UX-DR44). */
export const ANNOUNCE_EVERY_MS = 60_000;

/** What was last put in the region, and when (ms); null before anything was. */
export type Said = { text: string; at: number } | null;

/**
 * In how many ms `text` should be put in the region, or null when it says nothing new: the value
 * shown when the page opened (`first`) and the value last said are not said again; the first
 * change is said at once, a later one no sooner than `everyMs` after the last.
 */
export function announceIn(text: string, first: string, said: Said, now: number, everyMs: number): number | null {
  if (text === (said?.text ?? first)) return null;
  return said ? Math.max(0, said.at + everyMs - now) : 0;
}

/**
 * The text a polite live region should hold for a value that changes on its own (Story 7.5,
 * EXPERIENCE.md → Oppdater automatisk): empty at first, so the value on screen when the page opens
 * is not read out; each later change is put in the region at most once per `everyMs`, and a change
 * inside that time waits for its end, with only the latest text read.
 */
export function useThrottledAnnouncement(text: string, everyMs: number = ANNOUNCE_EVERY_MS): string {
  const [said, setSaid] = useState("");
  const first = useRef(text);
  const last = useRef<Said>(null);
  useEffect(() => {
    const wait = announceIn(text, first.current, last.current, Date.now(), everyMs);
    if (wait === null) return;
    const timer = window.setTimeout(() => {
      last.current = { text, at: Date.now() };
      setSaid(text);
    }, wait);
    return () => window.clearTimeout(timer);
  }, [text, everyMs]);
  return said;
}
