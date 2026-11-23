"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** What the Meldingsskjema shows before a send (Story 7.9): the recipient's title parts, how many
 * Students it reaches now, the earlier Messages to it and the length limit. */
export type MessageForm = components["schemas"]["MessageFormOut"];
export type MessageSent = components["schemas"]["MessageSentOut"];
/** A Student who has not met the requirement, as the form's table lists them (Story 13.6). */
export type NotMetStudent = components["schemas"]["NotMetStudentOut"];

/** Whom the form writes to: a Student (with the game it was opened from, if any), a Class game,
 * the Students who have not met the requirement (Story 13.6, `requirement`), or, with none of
 * these, the whole Class session. */
export type MessageTo = { game?: string; student?: string; requirement?: true };

const REQUIREMENT_NOT_MET = "requirement_not_met" as const;

export const messageFormKey = (sessionId: string, to: MessageTo) =>
  ["messaging", "form", sessionId, to.game ?? "", to.student ?? "", to.requirement ? REQUIREMENT_NOT_MET : ""] as const;

/** `/api/class-sessions/{id}/messages/form`: anyone but the staff of the Class, and a recipient
 * outside the Class session, answers 403 `forbidden`. */
export function useMessageForm(sessionId: string, to: MessageTo) {
  return useQuery({
    queryKey: messageFormKey(sessionId, to),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/messages/form", {
          params: {
            path: { session_id: sessionId },
            query: { game_id: to.game, student_id: to.student, recipient: to.requirement ? REQUIREMENT_NOT_MET : undefined },
          },
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
      body: {
        key,
        text,
        game_id: to.game ?? null,
        student_id: to.student ?? null,
        recipient: to.requirement ? REQUIREMENT_NOT_MET : null,
      },
    }),
  );
}

/** A Message on the Student's Hjem (Story 7.10), and one in the staff's «Meldinger». */
export type MyMessage = components["schemas"]["MyMessageOut"];
export type SentMessages = components["schemas"]["SentMessagesOut"];
export type SentMessage = components["schemas"]["SentMessageOut"];

/** The Student's own Messages; `user:<id>` refetches it (`topics.ts`). */
export const myMessagesKey = ["messaging", "mine"] as const;

/** `/api/me/messages`: the Messages written to the User, newest first, held to the api's scope. */
export function useMyMessages() {
  return useQuery({
    queryKey: myMessagesKey,
    queryFn: () => request(() => api.GET("/api/me/messages", { cache: "no-store" })),
    retry: false,
  });
}

/** A Class session's sent Messages; `session:<id>` refetches it (`topics.ts`). */
export const sentMessagesKey = (sessionId: string) => ["messaging", "sent", sessionId] as const;

/** `/api/class-sessions/{id}/messages`: «Meldinger», for the staff of the Class; anyone else
 * answers 403 `forbidden`. */
export function useSentMessages(sessionId: string) {
  return useQuery({
    queryKey: sentMessagesKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/messages", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}
