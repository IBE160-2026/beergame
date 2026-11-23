"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** Blind scoring of a Control test (Story 12.9, FR-82, AD-27). */
export type MyScoring = components["schemas"]["MyScoringOut"];
export type ScoringTest = components["schemas"]["ScoringTestOut"];
export type ScoringList = components["schemas"]["ScoringListOut"];
export type ScoringEntry = components["schemas"]["ScoringEntryOut"];
export type ScoringItem = components["schemas"]["ScoringItemOut"];
export type Scorers = components["schemas"]["ScorersOut"];
export type Scorer = components["schemas"]["ScorerOut"];

export const myScoringKey = ["scoring", "mine"] as const;
export const scoringListKey = (sessionId: string) => ["scoring", sessionId] as const;
export const scoringAnswerKey = (sessionId: string, answerId: string) => ["scoring", sessionId, answerId] as const;
export const scorersKey = (sessionId: string) => ["admin", "control-tests", sessionId, "scorers"] as const;

/** The Control tests the User is a named scorer of: their home shows the Lenke while there is one. */
export function useMyScoring() {
  return useQuery({
    queryKey: myScoringKey,
    queryFn: () => request(() => api.GET("/api/scoring", { cache: "no-store" })),
    retry: false,
  });
}

/** One Control test's answers to score; 403 `forbidden` for anyone but its scorers and the Admin. */
export function useScoringList(sessionId: string) {
  return useQuery({
    queryKey: scoringListKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/scoring/{session_id}", { params: { path: { session_id: sessionId } }, cache: "no-store" }),
      ),
    retry: false,
  });
}

/** One answer to score; 404 `not_found` for an answer the list does not hold. */
export function useScoringAnswer(sessionId: string, answerId: string) {
  return useQuery({
    queryKey: scoringAnswerKey(sessionId, answerId),
    queryFn: () =>
      request(() =>
        api.GET("/api/scoring/{session_id}/answers/{ref}", {
          params: { path: { session_id: sessionId, ref: answerId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}

/** «Lagre vurdering»: the scorer's step, stored once. The answer comes back with the AI's step;
 * a second score is 409 `human_score_exists`. The list reads again (the answer is now scored). */
export function useSubmitScore(sessionId: string, answerId: string) {
  const queryClient = useQueryClient();
  return useMutation<ScoringItem, unknown, number>({
    mutationFn: (score) =>
      request(() =>
        api.POST("/api/scoring/{session_id}/answers/{ref}", {
          params: { path: { session_id: sessionId, ref: answerId } },
          body: { score },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSuccess: (item) => queryClient.setQueryData(scoringAnswerKey(sessionId, answerId), item),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: scoringListKey(sessionId), exact: true });
      void queryClient.invalidateQueries({ queryKey: scoringAnswerKey(sessionId, answerId) });
    },
  });
}

/** Admin-område → «Kontrolltest» → «Sensorer»: the named scorers of one Control test. */
export function useScorers(sessionId: string) {
  return useQuery({
    queryKey: scorersKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/admin/control-tests/{session_id}/scorers", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}

/** «Utnevn som sensor» by e-mail address; 422 with `fields.email` (`unknown`, `test_student`). */
export function useNameScorer(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation<Scorers, unknown, string>({
    mutationFn: (email) =>
      request(() =>
        api.POST("/api/admin/control-tests/{session_id}/scorers", {
          params: { path: { session_id: sessionId } },
          body: { email },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSuccess: (scorers) => queryClient.setQueryData(scorersKey(sessionId), scorers),
  });
}

/** «Fjern» a scorer; their scores stay. */
export function useRemoveScorer(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation<Scorers, unknown, string>({
    mutationFn: (userId) =>
      request(() =>
        api.DELETE("/api/admin/control-tests/{session_id}/scorers/{user_id}", {
          params: { path: { session_id: sessionId, user_id: userId } },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSuccess: (scorers) => queryClient.setQueryData(scorersKey(sessionId), scorers),
  });
}
