"use client";

import { useState } from "react";

import { SeatStatus } from "@/components/seat-status";
import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import { conflictText, FocusedLine, InsertControl, insertLine } from "./peer-insert";
import { ReclaimControl } from "./reclaim-view";
import { seatRows, type StatusSeat, useWaitAnnouncement } from "./seat-status";
import type { ActedBy } from "./spillstyring";

const copy = nb.homes.student;

/** A press of «Sett inn KI-spiller» on this screen: done (`by` null) or someone came first, and
 * whether the view has shown the Seat taken over since. */
type Pressed = { by: ActedBy | null; seen: boolean };

/**
 * The Student's Setestatus (Story 6.14, FR-25): the game's Seats from the api, each with whether
 * it has ordered this Uke and how long the game has waited for it, counted from the stored start on
 * the server's clock (`now`, from `useServerNow`), with «Venter på: …» announced politely when
 * whom the game waits for changes. On the play screen under the Ordrefelt and on Hjem.
 *
 * Story 8.8 (FR-89, UX-DR27): on another Student's row, the line before its insert time, or, while
 * the api says `can_insert`, the consequence and «Sett inn KI-spiller for Jonas». After a press the
 * row («KI-spiller  bestiller for Jonas») takes focus; when someone came first, the line naming them
 * stands under the row and takes focus.
 */
export function GameSeatStatus({
  gameId,
  seats,
  now,
  titleId,
  level = 2,
  className,
}: {
  gameId: string;
  seats: StatusSeat[];
  now: number;
  titleId: string;
  level?: 2 | 4;
  className?: string;
}) {
  const announcement = useWaitAnnouncement(seats, now);
  // The Seats pressed here: the one put in now takes focus; one someone else took first, its line.
  const [pressed, setPressed] = useState<ReadonlyMap<string, Pressed>>(new Map());
  // A press is kept while its Seat is taken over; once a Student holds the Seat again (a Reclaim)
  // it is forgotten, so a later Takeover neither takes focus nor repeats who came first. Until
  // the view read again shows the Seat taken over, the press waits (`seen` false).
  const next = new Map(
    [...pressed].flatMap(([role, press]): [string, Pressed][] => {
      const taken = seats.find((seat) => seat.role === role)?.taken_over ?? false;
      if (taken) return [[role, { ...press, seen: true }]];
      return press.seen ? [] : [[role, press]];
    }),
  );
  if ([...next].some(([role, press]) => pressed.get(role)?.seen !== press.seen) || next.size !== pressed.size) {
    setPressed(next);
  }
  const press = (role: string, by: ActedBy | null) => setPressed((before) => new Map(before).set(role, { by, seen: false }));
  const rows = seatRows(seats, now).map((row, i) => {
    const seat = seats[i];
    const own = seat.taken_over ? pressed.get(seat.role) : undefined;
    const kind = own?.by ?? undefined;
    const before = insertLine(seat);
    return {
      ...row,
      focus: own !== undefined && own.by === null,
      detail:
        kind !== undefined ? (
          <FocusedLine kind="taken" text={conflictText(kind, seat.inserted_by)} />
        ) : before ? (
          <p className="mt-1 text-caption text-ink-secondary" data-insert-before="">
            {before}
          </p>
        ) : null,
      action:
        // Gone once pressed: until the view read again arrives, a second press cannot follow.
        seat.can_insert && !pressed.has(seat.role) ? (
          <InsertControl
            gameId={gameId}
            seat={seat}
            onDone={() => press(seat.role, null)}
            onTaken={(by) => press(seat.role, by)}
          />
        ) : null,
    };
  });
  return (
    <SeatStatus
      title={nb.homes.student.seats}
      titleId={titleId}
      level={level}
      rows={rows}
      announcement={announcement}
      className={className}
    />
  );
}

/**
 * «KI-spiller har bestilt for deg.» (Story 8.2, UX-DR62, EXPERIENCE.md → Takeover): the Student
 * whose Seat an AI player took over sees it on Spill, where it stands instead of the Ordrefelt,
 * and on Hjem. In an Obligatorisk Class session the warning that it may affect the requirement
 * follows; it never says how many Uker (FR-17, FR-14). The Setestatus's polite line announces
 * the Takeover («Grossist: KI-spiller bestiller for deg.»), so this note is not a live region.
 * «Ta tilbake setet» follows under it (Story 8.4).
 */
export function TakenOverNote({
  obligatory,
  gameId,
  seats,
  className,
}: {
  obligatory: boolean;
  gameId: string;
  /** The game's Seats: the own one, taken over, carries its Role and whether a Reclaim is queued. */
  seats: StatusSeat[];
  className?: string;
}) {
  const own = seats.find((seat) => seat.mine && seat.taken_over);
  return (
    <div data-taken-over="" className={cn("max-w-md", className)}>
      <p className="text-body-phone font-semibold text-ink lg:text-body">{copy.takeover.takenOver}</p>
      {obligatory ? (
        <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{copy.takeover.requirementWarning}</p>
      ) : null}
      {/* Story 8.4: «Ta tilbake setet» under the line, then the line that replaces it. */}
      {own ? <ReclaimControl gameId={gameId} role={own.role} queued={own.reclaim_queued} /> : null}
    </div>
  );
}
