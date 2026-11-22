import type { QueryKey } from "@tanstack/react-query";

import { classesKey, enrolledClassesKey } from "@/modules/classes/api";
import { classOverviewKey, gameInsightKey } from "@/modules/games/api";
import { meKey } from "@/modules/identity/api";
import { myMessagesKey, sentMessagesKey } from "@/modules/messaging/api";
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
    // and the Lærerhjem, the «Velg spill og sete» list (Story 5.17), their own games, and the
    // Messages on Hjem (Story 7.10: a Message's notice emits `user:<id>`).
    case "user":
      return [
        meKey,
        enrolledSessionsKey,
        enrolledClassesKey,
        classesKey,
        lecturerHomeKey,
        ["class-sessions", "seat-choice"],
        ["games", "mine"],
        myMessagesKey,
      ];
    // A Class session, for its staff: the Klasseøkt, its allocation block, the Lærerhjem parts of
    // Stories 5.2 and 5.9, the Class page's list of its sessions, its Oversikt (Story 7.1) and its
    // «Meldinger» (Story 7.10), and the Studentsides under it (Story 8.9).
    case "session":
      return [
        classSessionKey(event.id),
        ["class-sessions", "students", event.id],
        allocationKey(event.id),
        lecturerHomeKey,
        ["class-sessions", "of-class"],
        classOverviewKey(event.id),
        sentMessagesKey(event.id),
      ];
    // A Game: the Student's own game and what hangs under it (briefing, Starting task, the play
    // screen's envelope), Hjem, whose Setestatus shows who has ordered (Story 6.14), and the
    // staff's Spillinnsikt of it (Story 7.7).
    case "game":
      return [["games", "mine", event.id], enrolledSessionsKey, gameInsightKey(event.id)];
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
