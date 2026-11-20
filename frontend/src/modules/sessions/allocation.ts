import { nb } from "@/copy/nb";

import type { Allocation, AllocationGame, AllocationSeat } from "./api";
import { roleName } from "./sessions";

const copy = nb.sessions.allocation;

/** Who holds a Seat, in words: the Student's name, «KI-spiller» for an empty Seat, or «Ikke
 * lenger i Klassen» for a Student removed since the draw (Story 5.8). */
export function holderName(seat: AllocationSeat): string {
  if (seat.user_id == null) return copy.aiPlayer;
  return seat.name ?? copy.removed;
}

/** How the chart draws a Seat: a filled cell for a Student, an outlined one for an empty Seat (an
 * AI player gets it), and a dashed outline for a Student removed from the Klasse since the draw,
 * whose Seat the confirmation will free (Story 5.9, issue 106). */
export type SeatMark = "student" | "empty" | "removed";

export function seatMark(seat: AllocationSeat): SeatMark {
  if (seat.user_id == null) return "empty";
  return seat.name == null ? "removed" : "student";
}

/** Why «Bekreft fordeling» committed nothing (409 `allocation_changed`), by its `fields.draft`. */
export function changedReason(fields: Readonly<Record<string, unknown>> | undefined): string {
  return fields?.draft === "students_removed" ? copy.studentsRemoved : copy.changed;
}

/** A game's four Seats in the order the line reads them: Detaljist first, as the customer sees the
 * chain («Ida, Detaljist. Sara, Grossist. …»); the api lists Fabrikk first, as the chart draws it. */
export function seatsInReadingOrder(game: AllocationGame): AllocationSeat[] {
  return [...game.seats].reverse();
}

/** «Ida, Detaljist. Sara, Grossist. Mikkel, Distributør. KI-spiller, Fabrikk.» */
export function gameLine(game: AllocationGame): string {
  return seatsInReadingOrder(game)
    .map((seat) => `${copy.seat(holderName(seat), roleName(seat.role))}.`)
    .join(" ");
}

/** An opened Class game's state (Story 5.12), «Ikke startet.»; "" before the games are open. */
export function gameState(game: AllocationGame): string {
  return game.lifecycle ? copy.lifecycle[game.lifecycle] : "";
}

/** The game's whole line for a screen reader: its Seats, then its state when open. */
export function gameLabel(game: AllocationGame): string {
  return [copy.game(game.number) + ":", gameLine(game), gameState(game)].filter(Boolean).join(" ");
}

/** The numbers under the chart: the first game, the selected one and the last, each once. The
 * first or last is left out when it would sit within `minGap` columns of the selected one, so
 * narrow columns never draw two numbers on top of each other. */
export function ticks(count: number, selected: number, minGap = 1): number[] {
  if (count === 0) return [];
  const near = (n: number) => n !== selected && Math.abs(n - selected) < minGap;
  return [...new Set([1, selected, count])].filter((n) => !near(n)).sort((a, b) => a - b);
}

/** The game the arrow keys move to from `selected`, or null for any other key. */
export function nextGame(key: string, selected: number, count: number): number | null {
  switch (key) {
    case "ArrowRight":
    case "ArrowDown":
      return Math.min(count, selected + 1);
    case "ArrowLeft":
    case "ArrowUp":
      return Math.max(1, selected - 1);
    case "Home":
      return 1;
    case "End":
      return count;
    default:
      return null;
  }
}

/** A Seat in the allocation, by its game: what a move starts from or goes to (Story 5.10). */
export type SeatAt = { game: number; seat: AllocationSeat };

/** The button that picks a Student to move: «Flytt eller bytt Ida, Detaljist i Spill 3». */
export function pickLabel({ game, seat }: SeatAt): string {
  return copy.pick(holderName(seat), roleName(seat.role), game);
}

/** The button on another Seat once a Student is picked: a swap when a Student holds it, otherwise
 * a move to the free Seat. Each names the Student, the Role and the Klassespill (UX-DR50). */
export function targetLabel(picked: SeatAt, target: SeatAt): string {
  const name = holderName(picked.seat);
  const role = roleName(picked.seat.role);
  if (target.seat.user_id != null) {
    return copy.swapWith(
      name,
      role,
      picked.game,
      holderName(target.seat),
      roleName(target.seat.role),
      target.game,
    );
  }
  return copy.moveTo(name, role, picked.game, roleName(target.seat.role), target.game);
}

/** What the status line says once the move or swap is stored. */
export function movedLine(picked: SeatAt, target: SeatAt): string {
  if (target.seat.user_id != null) return copy.swapped(holderName(picked.seat), holderName(target.seat));
  return copy.moved(holderName(picked.seat), roleName(target.seat.role), target.game);
}

/** Why a move was refused (422 `invalid_move`), by its `fields`. */
export function invalidMoveReason(fields: Readonly<Record<string, unknown>> | undefined): string {
  return fields?.from === "last_student" ? copy.moveLastStudent : copy.moveInvalid;
}

/** After the lock, the registered Students no Class game could seat, in one line (Story 5.13);
 * "" when there are none. */
export function withoutSeatLine(allocation: Allocation): string {
  const names = allocation.without_seat.map((student) => student.name);
  return names.length > 0 ? copy.withoutSeat(names) : "";
}
