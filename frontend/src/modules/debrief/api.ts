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

/** The Student's own Netto lager per Uke (Story 9.3, step 1). */
export type NetInventory = components["schemas"]["NetInventoryOut"];
/** A sent Explanation: the text as typed, its length and when it was saved. */
export type Explanation = components["schemas"]["ExplanationOut"];

export const netInventoryKey = (debriefId: string) => [...debriefsKey, debriefId, "net-inventory"] as const;
export const explanationKey = (debriefId: string) => [...debriefsKey, debriefId, "explanation"] as const;

/** «Ditt netto lager, hele spillet»: the Student's own Seat only, every Uke (no demand). */
export function useNetInventory(debriefId: string) {
  return useQuery({
    queryKey: netInventoryKey(debriefId),
    queryFn: () =>
      request(() => api.GET("/api/debriefs/{debrief_id}/net-inventory", { params: { path: { debrief_id: debriefId } } })),
    retry: false,
  });
}

/** The Student's own Explanation, `explanation` null before it is sent. */
export function useMyExplanation(debriefId: string) {
  return useQuery({
    queryKey: explanationKey(debriefId),
    queryFn: () =>
      request(() => api.GET("/api/debriefs/{debrief_id}/explanation", { params: { path: { debrief_id: debriefId } } })),
    retry: false,
  });
}

/** «Send Forklaring»: stores the Explanation once (FR-41). Nothing here sends on its own. */
export function sendExplanation(debriefId: string, text: string): Promise<Explanation> {
  return request(() =>
    api.POST("/api/debriefs/{debrief_id}/explanation", {
      params: { path: { debrief_id: debriefId } },
      body: { text },
    }),
  );
}

/** The draft field of the Explanation in a Class session (`lib/drafts.ts`). */
export const explanationDraftField = (classSessionId: string) => `debrief-explanation:${classSessionId}`;

/** Whether typed text may be sent: more than white space (the api refuses the rest). */
export function hasText(text: string): boolean {
  return text.trim() !== "";
}

/** A Debrief step after step 1 (Story 9.3): 403 `explanation_required` until the Explanation is
 * saved. Step 2 carries `reveal` (Story 9.4). */
export type DebriefStep = components["schemas"]["DebriefStepOut"];
/** Step 2, the reveal of customer demand: the heading from the api and Kundene, Ordre inn and Din
 * ordre per Uke of the Student's own Seat. */
export type Reveal = components["schemas"]["RevealOut"];
export type RevealWeek = components["schemas"]["RevealWeekOut"];

export const debriefStepKey = (debriefId: string, step: number) => [...debriefsKey, debriefId, "steps", step] as const;

/** A step's content, read once the Explanation is saved (`enabled`): the api checks the gate. */
export function useDebriefStep(debriefId: string, step: number, enabled: boolean) {
  return useQuery({
    queryKey: debriefStepKey(debriefId, step),
    queryFn: () =>
      request(() =>
        api.GET("/api/debriefs/{debrief_id}/steps/{step}", { params: { path: { debrief_id: debriefId, step } } }),
      ),
    enabled,
    retry: false,
  });
}

/** The Role whose Orders reached a Seat: the next one down the chain toward the customers
 * (EXPERIENCE.md → Chain convention). None for the Detaljist, who saw the customers. */
export function downstreamRole(role: Debrief["role"]): Debrief["role"] | null {
  const chain = ["factory", "distributor", "wholesaler", "retailer"] as const;
  const at = chain.indexOf(role);
  return at >= 0 && at < chain.length - 1 ? chain[at + 1]! : null;
}
