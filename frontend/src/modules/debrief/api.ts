"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Student's Debrief session (Story 9.2): its id (the `debrief:<id>` topic), the game it
 * reviews and the step pointer, 1 to 5. */
export type Debrief = components["schemas"]["DebriefOut"];

/** The prefix of every Debrief query: the `user` and `debrief` topics invalidate it. */
export const debriefsKey = ["debriefs"] as const;
export const myDebriefKey = (classSessionId: string) => [...debriefsKey, "mine", classSessionId] as const;

/** The Debrief's five steps (EXPERIENCE.md → Debrief sequence). */
export const DEBRIEF_STEPS = 5;

/**
 * Opens the Student's Debrief in the Class session and reads it: the api creates the Debrief
 * session at step 1 the first time and answers the same session after that, so the page, «Gå til
 * Debrief» and Stegene share one way in (FR-42). 403 `debrief_not_open`, `debrief_held` or
 * `forbidden` before it may open.
 */
export function useMyDebrief(classSessionId: string) {
  return useQuery({
    queryKey: myDebriefKey(classSessionId),
    queryFn: () =>
      request(() =>
        api.POST("/api/me/class-sessions/{session_id}/debrief", { params: { path: { session_id: classSessionId } } }),
      ),
    retry: false,
  });
}

/** Where the Debrief page stands, from the api's answer or refusal: the web app decides nothing. */
export type DebriefView = "open" | "notOpen" | "held" | "denied" | "other";

export function debriefView(data: Debrief | undefined, code: string | null): DebriefView {
  if (data) return "open";
  if (code === "debrief_not_open") return "notOpen";
  if (code === "debrief_held") return "held";
  if (code === "forbidden") return "denied";
  return "other";
}
