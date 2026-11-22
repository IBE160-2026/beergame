"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { osloWeekdayTime } from "@/modules/sessions/dates";
import { enrolledSessionsKey } from "@/modules/sessions/api";
import { roleName } from "@/modules/sessions/sessions";

import { insertAiPlayer, type MyGame, myGameKey } from "./api";
import type { StatusSeat } from "./seat-status";
import { type ActedBy, actedKind, takenText } from "./spillstyring";

const copy = nb.homes.student.insert;

/** The line before another Student's insert time (Story 8.8, UX-DR27): «Avtalt tid to. 19:00. Etter
 * det kan dere sette inn en KI-spiller.» with the Lecturer's agreed time, else «Etter on. 10:00 kan
 * dere sette inn en KI-spiller.» with the Seat's own time; null when the api sends none. It never
 * says why one Seat's time is later. */
export function insertLine(seat: StatusSeat): string | null {
  if (!seat.insert_at) return null;
  const when = osloWeekdayTime(seat.insert_at);
  return seat.insert_agreed ? copy.agreed(when) : copy.after(when);
}

/** The name the control uses for the absent Student: their name, else the Seat's Role. */
export function absentName(seat: StatusSeat): string {
  return seat.name ?? roleName(seat.role);
}

/** Who came first, as the Student reads it: «Sara har allerede satt inn en KI-spiller.» (the name
 * from the view read again), the Lecturer, or the automatic Takeover. */
export function conflictText(kind: ActedBy, insertedBy: string | null | undefined): string {
  return kind === "staff" ? copy.takenByStaff : takenText(kind, insertedBy);
}

/** A line that takes focus once it is drawn (`tabindex="-1"`), read by screen readers. */
export function FocusedLine({ text, kind }: { text: string; kind: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <p
      ref={ref}
      tabIndex={-1}
      role="status"
      data-insert-result={kind}
      className="mt-2 text-body-phone text-ink focus:outline-none lg:text-body"
    >
      {text}
    </p>
  );
}

/**
 * «Sett inn KI-spiller for Jonas» on another Student's Setestatus row (Story 8.8, FR-89, FR-37,
 * UX-DR27, UX-DR76): shown only while the api says `can_insert` (AD-10). The consequence stands
 * directly above the secondary button, at least 44 px and full width below 1024 px; one press, no
 * dialog. After the api commits, the game it answers is shown and `onDone` moves focus to the row,
 * now «KI-spiller bestiller for Jonas». When someone came first (`takeover_exists`), the game is read
 * again and `onTaken` names who; any other refusal is said inline and the button stays active.
 */
export function InsertControl({
  gameId,
  seat,
  onDone,
  onTaken,
}: {
  gameId: string;
  seat: StatusSeat;
  onDone: () => void;
  onTaken: (kind: ActedBy) => void;
}) {
  const queryClient = useQueryClient();
  const name = absentName(seat);
  const reread = () =>
    Promise.all([
      // The game and its play envelope (`["games", "mine", id, …]`) and Hjem read again.
      queryClient.invalidateQueries({ queryKey: myGameKey(gameId) }),
      queryClient.invalidateQueries({ queryKey: enrolledSessionsKey }),
    ]);
  const inserting = useAction({
    mutationFn: () => insertAiPlayer(gameId, seat.role),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (game: MyGame) => {
      queryClient.setQueryData(myGameKey(gameId), game);
      void reread();
      onDone();
    },
  });
  return (
    <div className="mt-2 flex flex-col items-start gap-2" data-insert={seat.role}>
      <p className="text-caption text-ink-secondary" data-insert-consequence="">
        {nb.spillstyring.thisWeek(name)}
      </p>
      <Button
        className="w-full lg:w-auto"
        unavailable={inserting.isPending}
        onClick={() =>
          inserting.mutate(undefined, {
            onError: (error) => {
              const kind = actedKind(error);
              // Who came first is named from the game read again: the line waits for that read.
              void reread().then(() => {
                if (kind !== null) onTaken(kind);
              });
            },
          })
        }
      >
        {nb.spillstyring.takeover(name)}
      </Button>
      {errorCode(inserting.error) === "takeover_exists" ? null : <ActionError message={inserting.errorMessage} />}
    </div>
  );
}
