"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SegmentedChoice } from "@/components/segmented-choice";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { useBelievability } from "@/modules/games/api";
import { BelievabilityBlock } from "@/modules/games/believability";

import { answerAnotherRound, anotherRoundKey, useAnotherRound } from "./api";

const copy = nb.replay.questions;
const LINE = "text-body-phone text-ink lg:text-body";

type YesNo = "yes" | "no";

/**
 * «Frivillige spørsmål» after the Replay-gjennomgang (Story 10.8, FR-50, FR-70): the shared
 * believability question, then «Ville du spilt en runde til?» as Ja or Nei. Both optional: nothing
 * waits on them and every later step stays open. Each is sent on its own and stored once; after
 * it, a line says what the Student answered. A read that fails leaves the question out.
 */
export function ReplayQuestions({ gameId }: { gameId: string }) {
  const id = useId();
  // The same reads the two questions make (one request each): the heading stands only over a
  // question that is asked.
  const believability = useBelievability(gameId);
  const round = useAnotherRound(gameId);
  if (!believability.data?.offered && !round.data) return null;
  return (
    <section aria-labelledby={`${id}-title`} data-replay-questions="" className="mt-10 border-t border-axis pt-4">
      <h2 id={`${id}-title`} className="text-headline text-ink">
        {copy.title}
      </h2>
      <div className="mt-3 flex flex-col gap-8">
        <BelievabilityBlock gameId={gameId} />
        <AnotherRound gameId={gameId} />
      </div>
    </section>
  );
}

function AnotherRound({ gameId }: { gameId: string }) {
  const queryClient = useQueryClient();
  const found = useAnotherRound(gameId);
  const [chosen, setChosen] = useState<YesNo | null>(null);
  const savedLine = useRef<HTMLParagraphElement>(null);
  const sent = useRef(false);
  const send = useAction({
    mutationFn: async (answer: boolean) => {
      try {
        return await answerAnotherRound(gameId, answer);
      } catch (error) {
        if (error instanceof ApiRequestError && error.code === "already_answered") {
          void queryClient.invalidateQueries({ queryKey: anotherRoundKey(gameId) });
        }
        throw error;
      }
    },
    fallback: copy.failed,
    onSuccess: (data) => queryClient.setQueryData(anotherRoundKey(gameId), data),
  });
  const answer = found.data?.answer ?? null;
  useEffect(() => {
    if (answer !== null && sent.current) savedLine.current?.focus();
  }, [answer]);
  if (!found.data) return null;
  if (answer !== null) {
    return (
      <p ref={savedLine} tabIndex={-1} role="status" data-another-round-saved="" className={LINE}>
        {copy.saved(answer)}
      </p>
    );
  }
  return (
    <div data-another-round="" className="max-w-sm">
      <SegmentedChoice
        name={`another-round-${gameId}`}
        legend={copy.anotherRound}
        options={[
          { value: "yes", label: copy.yes },
          { value: "no", label: copy.no },
        ]}
        value={(chosen ?? "") as YesNo}
        onChange={setChosen}
      />
      <Button
        className="mt-3"
        unavailable={chosen === null || send.isPending}
        onClick={() => {
          if (chosen === null) return;
          sent.current = true;
          send.mutate(chosen === "yes");
        }}
      >
        {copy.send}
      </Button>
      <ActionError message={send.errorMessage} className="mt-2" />
    </div>
  );
}
