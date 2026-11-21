"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { useAction } from "@/lib/api/mutation";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { type MyGame, myGameKey, reclaimSeat } from "./api";

const copy = nb.homes.student.takeover;

/**
 * «Ta tilbake setet» (Story 8.4, FR-37, UX-DR62, UX-DR76): under «KI-spiller har bestilt for deg.»
 * the Student whose Seat an AI player took over asks for it back. A secondary button, at least
 * 44 px and full width below 1024 px; one press, no dialog. Once the request is queued (`queued`,
 * from the api, or this press) the line «Du får setet tilbake når neste Uke åpner.» replaces it,
 * and after a press it takes focus, which reads it (`role="status"`, `tabindex="-1"`). A refusal is said inline and the button stays active.
 */
export function ReclaimControl({
  gameId,
  role,
  queued,
}: {
  gameId: string;
  role: components["schemas"]["Role"];
  queued: boolean;
}) {
  const queryClient = useQueryClient();
  const [pressed, setPressed] = useState(false);
  const lineRef = useRef<HTMLParagraphElement>(null);
  // After a press the line takes focus once it is drawn, from this press or the api's answer.
  const focusLine = useRef(false);
  const reread = () => {
    // The game and its play envelope (`["games", "mine", id, …]`) and Hjem read again.
    void queryClient.invalidateQueries({ queryKey: myGameKey(gameId) });
    void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
  };
  const reclaiming = useAction({
    mutationFn: () => reclaimSeat(gameId, role),
    messages: copy.reclaimRefusals,
    fallback: copy.reclaimFailed,
    onSuccess: (game: MyGame) => {
      queryClient.setQueryData(myGameKey(gameId), game);
      reread();
      focusLine.current = true;
      setPressed(true);
    },
  });
  useEffect(() => {
    if (focusLine.current && lineRef.current) {
      focusLine.current = false;
      lineRef.current.focus();
    }
  });
  // Once the api says it is queued, the press has done its part: a later Takeover of the Seat,
  // after it came back, shows the button again.
  if (pressed && queued) setPressed(false);
  if (queued || pressed) {
    return (
      <p
        ref={lineRef}
        tabIndex={-1}
        role="status"
        data-reclaim-queued=""
        className="mt-3 text-body-phone text-ink focus:outline-none lg:text-body"
      >
        {copy.reclaimQueued}
      </p>
    );
  }
  return (
    <div className="mt-3 flex flex-col items-start gap-2">
      <Button
        data-reclaim=""
        className="w-full lg:w-auto"
        unavailable={reclaiming.isPending}
        onClick={() => reclaiming.mutate(undefined, { onError: reread })}
      >
        {copy.reclaim}
      </Button>
      <ActionError message={reclaiming.errorMessage} />
    </div>
  );
}
