"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useId } from "react";

import { BelievabilityQuestion } from "@/components/believability-question";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";

import { believabilityKey, rateBelievability, useBelievability } from "./api";

/**
 * The believability question of the Student's own game (Story 10.8, FR-70), where the api offers
 * it: a finished Class game an AI player held a Seat in, or a finished Replay. Nothing renders
 * while it is read, when it is not offered, or when the read fails: an optional question never
 * stands in the way. A sent answer is stored once; an answer the api already has, or a game that
 * no longer asks, reads the question again, which then shows where it stands.
 */
export function BelievabilityBlock({
  gameId,
  enabled = true,
  titled = false,
}: {
  gameId: string;
  enabled?: boolean;
  /** Under its own heading «Et frivillig spørsmål» (on «Spillet er ferdig»). */
  titled?: boolean;
}) {
  const queryClient = useQueryClient();
  const found = useBelievability(gameId, enabled);
  const send = useAction({
    mutationFn: async (rating: number) => {
      try {
        return await rateBelievability(gameId, rating);
      } catch (error) {
        if (error instanceof ApiRequestError && ["already_answered", "not_offered"].includes(error.code)) {
          void queryClient.invalidateQueries({ queryKey: believabilityKey(gameId) });
        }
        throw error;
      }
    },
    fallback: nb.believability.failed,
    onSuccess: (data) => queryClient.setQueryData(believabilityKey(gameId), data),
  });
  const id = useId();
  const data = found.data;
  if (!data?.offered) return null;
  const question = (
    <BelievabilityQuestion
      rating={data.rating ?? null}
      onSend={(rating) => send.mutate(rating)}
      sending={send.isPending}
      errorMessage={send.errorMessage}
      className={titled ? "mt-3" : undefined}
    />
  );
  if (!titled) return question;
  return (
    <section aria-labelledby={`${id}-title`} data-believability-block="" className="mt-10 border-t border-axis pt-4">
      <h2 id={`${id}-title`} className="text-headline text-ink">
        {nb.believability.title}
      </h2>
      {question}
    </section>
  );
}
