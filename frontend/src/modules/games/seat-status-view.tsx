"use client";

import { SeatStatus } from "@/components/seat-status";
import { nb } from "@/copy/nb";

import { seatRows, type StatusSeat, useWaitAnnouncement } from "./seat-status";

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
