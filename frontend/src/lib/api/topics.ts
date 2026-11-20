import type { QueryKey } from "@tanstack/react-query";

import { classesKey, enrolledClassesKey } from "@/modules/classes/api";
import { meKey } from "@/modules/identity/api";
import {
  allocationKey,
  classSessionKey,
  enrolledSessionsKey,
  lecturerHomeKey,
} from "@/modules/sessions/api";

/**
 * The only map from a change event's topic to TanStack Query keys (AD-8, Story 6.4). Push
 * invalidates, pull reads: an event names what changed, never the data, and every key here is
 * refetched over REST through the generated client. Each key is a prefix: it invalidates every
 * query that starts with it.
 */
export type ChangeEvent = { topic: string; id: string; version: number | null };

export function topicKeys(event: ChangeEvent): QueryKey[] {
  switch (event.topic) {
    // The User's own pages: their roles and status, Hjem and «Mine Klasseøkter», «Klassene dine»
    // and the Lærerhjem, the «Velg spill og sete» list (Story 5.17) and their own games.
    case "user":
      return [
        meKey,
        enrolledSessionsKey,
        enrolledClassesKey,
        classesKey,
        lecturerHomeKey,
        ["class-sessions", "seat-choice"],
        ["games", "mine"],
      ];
    // A Class session, for its staff: the Klasseøkt, its allocation block, the Lærerhjem parts of
    // Stories 5.2 and 5.9, and the Class page's list of its sessions.
    case "session":
      return [classSessionKey(event.id), allocationKey(event.id), lecturerHomeKey, ["class-sessions", "of-class"]];
    // A Game: the Student's own game and what hangs under it (briefing, Starting task).
    case "game":
      return [["games", "mine", event.id]];
    default:
      return [];
  }
}

/** The event in an SSE message's data, or null when it is not one. */
export function parseEvent(data: string): ChangeEvent | null {
  try {
    const parsed: unknown = JSON.parse(data);
    if (typeof parsed !== "object" || parsed === null) return null;
    const { topic, id, version } = parsed as Record<string, unknown>;
    if (typeof topic !== "string" || typeof id !== "string" || id === "") return null;
    if (version !== null && typeof version !== "number") return null;
    return { topic, id, version };
  } catch {
    return null;
  }
}
