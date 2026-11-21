"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** What the Meldingsskjema shows before a send (Story 7.9): the recipient's title parts, how many
 * Students it reaches now, the earlier Messages to it and the length limit. */
export type MessageForm = components["schemas"]["MessageFormOut"];
export type MessageSent = components["schemas"]["MessageSentOut"];

/** Whom the form writes to: a Student (with the game it was opened from, if any), a Class game,
 * or, with neither, the whole Class session. */
export type MessageTo = { game?: string; student?: string };

export const messageFormKey = (sessionId: string, to: MessageTo) =>
  ["messaging", "form", sessionId, to.game ?? "", to.student ?? ""] as const;

/** `/api/class-sessions/{id}/messages/form`: anyone but the staff of the Class, and a recipient
 * outside the Class session, answers 403 `forbidden`. */
export function useMessageForm(sessionId: string, to: MessageTo) {
  return useQuery({
    queryKey: messageFormKey(sessionId, to),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/messages/form", {
          params: { path: { session_id: sessionId }, query: { game_id: to.game, student_id: to.student } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}

/** «Send Melding»: one Message with the client-made `key`; a repeat with the same key answers as
 * the first and sends nothing. 422 `message_empty`, `message_too_long`, `no_recipients`; 409
 * `class_archived`, `message_key_conflict`. */
export function sendMessage(sessionId: string, to: MessageTo, text: string, key: string) {
  return request(() =>
    api.POST("/api/class-sessions/{session_id}/messages", {
      params: { path: { session_id: sessionId } },
      body: { key, text, game_id: to.game ?? null, student_id: to.student ?? null },
    }),
  );
}
