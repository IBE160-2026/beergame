"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { type GamePause, type MyGame, myGameKey, pauseGame } from "./api";

const copy = nb.homes.student.pause;
const LINE = "text-body-phone text-ink lg:text-body";

/** «Pause, satt av Sara.», «Pause, satt av deg.», «Pausen er over. Sara har bestilt.» (Story 8.6,
 * EXPERIENCE.md → State Patterns → Student game): the line the api sent, in words. Nothing in it
 * says how many Uker remain (FR-14). */
export function pauseText(pause: GamePause | null | undefined): string {
  if (!pause) return "";
  if (pause.state === "paused") {
    if (pause.mine) return copy.pausedByYou;
    return pause.name ? copy.pausedBy(pause.name) : copy.pausedByUnknown;
  }
  if (pause.mine) return copy.endedByYou;
  return pause.name ? copy.endedBy(pause.name) : copy.endedByUnknown;
}

/** The id of the game's pause line, which a confirmed «Ta pause» moves focus to. */
export const pauseLineId = (gameId: string) => `pause-line-${gameId}`;

/**
 * The pause line above Setestatus on Spill and Hjem (Story 8.6, FR-89, UX-DR62), for every Student
 * of the game, ordered or not. A polite live region that is always there and is filled after it
 * is drawn, so the line is read also when the page opens with it: on a phone it can sit below the
 * first screen. Takes focus after the reader's own «Ta pause» (`tabindex="-1"`).
 */
export function PauseLine({ gameId, pause, className }: { gameId: string; pause: GamePause | null | undefined; className?: string }) {
  const text = pauseText(pause);
  const [said, setSaid] = useState("");
  useEffect(() => setSaid(text), [text]);
  return (
    <div aria-live="polite" data-pause-line={pause?.state ?? ""} className={said ? className : undefined}>
      {said ? (
        <p id={pauseLineId(gameId)} tabIndex={-1} className={cn(LINE, "max-w-md font-semibold focus:outline-none")}>
          {said}
        </p>
      ) : null}
    </div>
  );
}

/**
 * «Ta pause» and the Pausevalg (Story 8.6, FR-89, UX-DR26, UX-DR76, EXPERIENCE.md → Pausevalg): a
 * secondary button under Setestatus, at least 44 px and full width below 1024 px, while the api
 * says the reader may pause (`canPause`). It opens the Pausevalg in place, with no date or time
 * field: the two consequence lines, the primary «Ta pause uten avtalt tid», which takes focus, and
 * «Avbryt», which closes it and gives focus back to «Ta pause». Once the api has paused the game the
 * pause line shows and takes focus; when someone paused first (`already_paused`) the form closes and
 * the line read again shows. Any other refusal is said in the form. `onFormOpen` tells the screen
 * the form's primary is shown, so its own primary steps back (UX-DR8).
 */
export function PauseControl({
  gameId,
  canPause,
  onFormOpen,
  className,
}: {
  gameId: string;
  canPause: boolean;
  onFormOpen?: (open: boolean) => void;
  className?: string;
}) {
  const id = useId();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const openerRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  // Where focus goes on the next draw: the form's primary, back to «Ta pause», or the pause line
  // once the answer has drawn it.
  const focusNext = useRef<"confirm" | "opener" | "line" | null>(null);
  const reread = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: myGameKey(gameId) }),
      queryClient.invalidateQueries({ queryKey: enrolledSessionsKey }),
    ]);
  const pausing = useAction({
    mutationFn: () => pauseGame(gameId),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (game: MyGame) => {
      queryClient.setQueryData(myGameKey(gameId), game);
      void reread();
      focusNext.current = "line";
      setOpen(false);
    },
  });
  useEffect(() => {
    const target = focusNext.current;
    if (target === "confirm" && confirmRef.current) confirmRef.current.focus();
    else if (target === "opener" && openerRef.current) openerRef.current.focus();
    else if (target === "line") {
      // The line fills in after its own draw (and after a read again): look for it a few frames.
      const focusLine = (frames: number) => {
        const line = document.getElementById(pauseLineId(gameId));
        if (line) line.focus();
        else if (frames > 0) requestAnimationFrame(() => focusLine(frames - 1));
      };
      focusLine(60);
    } else return;
    focusNext.current = null;
  });
  const shown = open && canPause;
  const told = useRef(onFormOpen);
  useEffect(() => {
    told.current = onFormOpen;
  });
  useEffect(() => {
    told.current?.(shown);
    return () => told.current?.(false);
  }, [shown]);
  if (!canPause) {
    // Paused by someone else (or the game moved on) while the form was open: it closes for good,
    // and focus goes to the pause line when there is one, never to the page's start.
    if (open) {
      focusNext.current = "line";
      setOpen(false);
    }
    return null;
  }
  if (!open) {
    return (
      <div className={cn("flex max-w-md flex-col items-start", className)}>
        <Button
          ref={openerRef}
          data-pause-open=""
          className="w-full lg:w-auto"
          onClick={() => {
            pausing.reset();
            focusNext.current = "confirm";
            setOpen(true);
          }}
        >
          {copy.open}
        </Button>
      </div>
    );
  }
  const lines = `${id}-lines`;
  return (
    <section
      aria-labelledby={`${id}-title`}
      data-pausevalg=""
      className={cn("flex w-full max-w-md flex-col items-start gap-3 rounded-sm border border-axis px-4 py-4", className)}
    >
      <h3 id={`${id}-title`} className="text-label text-ink">
        {copy.open}
      </h3>
      <div id={lines} className="flex flex-col gap-2">
        <p className="text-body-phone text-ink lg:text-body">{copy.noTakeover}</p>
        <p className="text-body-phone text-ink-secondary lg:text-body">{copy.onlyLecturer}</p>
      </div>
      <div className="flex w-full flex-col items-stretch gap-x-6 gap-y-2 lg:flex-row lg:items-center">
        <Button
          ref={confirmRef}
          variant="primary"
          data-pause-confirm=""
          className="w-full lg:w-auto"
          aria-describedby={lines}
          unavailable={pausing.isPending}
          onClick={() =>
            pausing.mutate(undefined, {
              onError: (error) => {
                const first = errorCode(error) === "already_paused";
                void reread().then(() => {
                  if (!first) return;
                  // Someone paused first: once read again, the form closes and the line says who.
                  pausing.reset();
                  focusNext.current = "line";
                  setOpen(false);
                });
              },
            })
          }
        >
          {copy.confirm}
        </Button>
        <button
          type="button"
          data-pause-cancel=""
          className={cn(LINK_BUTTON, "self-start")}
          onClick={() => {
            if (pausing.isPending) return;
            focusNext.current = "opener";
            setOpen(false);
          }}
        >
          {copy.cancel}
        </button>
      </div>
      {/* Someone paused first: no error, the line read again says who. */}
      {errorCode(pausing.error) === "already_paused" ? null : <ActionError message={pausing.errorMessage} />}
    </section>
  );
}
