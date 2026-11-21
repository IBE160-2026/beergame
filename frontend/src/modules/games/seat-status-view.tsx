"use client";

import { SeatStatus } from "@/components/seat-status";
import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import { ReclaimControl } from "./reclaim-view";
import { seatRows, type StatusSeat, useWaitAnnouncement } from "./seat-status";

const copy = nb.homes.student;

/**
 * The Student's Setestatus (Story 6.14, FR-25): the game's Seats from the api, each with whether
 * it has ordered this Uke and how long the game has waited for it, counted from the stored start on
 * the server's clock (`now`, from `useServerNow`), with «Venter på: …» announced politely when
 * whom the game waits for changes. On the play screen under the Ordrefelt and on Hjem.
 */
export function GameSeatStatus({
  seats,
  now,
  titleId,
  level = 2,
  className,
}: {
  seats: StatusSeat[];
  now: number;
  titleId: string;
  level?: 2 | 4;
  className?: string;
}) {
  const announcement = useWaitAnnouncement(seats, now);
  return (
    <SeatStatus
      title={nb.homes.student.seats}
      titleId={titleId}
      level={level}
      rows={seatRows(seats, now)}
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
