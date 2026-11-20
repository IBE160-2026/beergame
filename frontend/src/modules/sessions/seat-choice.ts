import { nb } from "@/copy/nb";

import type { EnrolledSession, SeatChoice, SeatChoiceGame, SeatChoiceSeat } from "./api";
import { osloDayAndTime } from "./dates";
import { roleName } from "./sessions";

const copy = nb.sessions.seatChoice;

type Role = SeatChoiceSeat["role"];

/** A Seat in words, its state never in colour alone (UX-DR62): «Grossist, ledig», «Grossist,
 * Ida Hansen», «Grossist, ditt sete», «Grossist, KI-spiller» after the lock, or «Grossist, Ikke
 * lenger i Klassen» for a Student removed since they chose. */
export function seatText(seat: SeatChoiceSeat): string {
  const role = roleName(seat.role);
  if (seat.holder === "free") return copy.free(role);
  if (seat.mine) return copy.own(role);
  if (seat.holder === "ai") return copy.held(role, copy.aiPlayer);
  return copy.held(role, seat.name ?? copy.removed);
}

/** How many of the game's Seats are free. */
export function freeCount(game: SeatChoiceGame): number {
  return game.seats.filter((seat) => seat.holder === "free").length;
}

/** Whether the Student may press the Seat: the choice is open and nobody holds it. */
export function canTake(choice: Pick<SeatChoice, "open">, seat: SeatChoiceSeat): boolean {
  return choice.open && seat.holder === "free";
}

/** «Ta setet Grossist i Spill 17». */
export function takeLabel(game: number, role: Role): string {
  return copy.take(roleName(role), game);
}

/** The line on the Student's own Seat: the draw's («Du fikk et sete ved trekning: Grossist i
 * Spill 17.»), their own choice («Ditt sete: …») or none yet. */
export function ownLine(choice: Pick<SeatChoice, "my_seat" | "drawn">): string {
  const seat = choice.my_seat;
  if (!seat) return copy.none;
  return choice.drawn ? copy.drawn(roleName(seat.role), seat.game_number) : copy.mine(roleName(seat.role), seat.game_number);
}

/** Until when the Student may choose, and that they may change Seat until then, or that the
 * session has started. */
export function whenLine(choice: Pick<SeatChoice, "open" | "start_at">): string {
  if (!choice.open) return copy.closed;
  if (!choice.start_at) return copy.beforeNoDate;
  const { day, time } = osloDayAndTime(choice.start_at);
  return copy.before(day, time);
}

/** What Hjem says of a Class session with Student choice (Story 5.17): the Lenke to «Velg spill og
 * sete» while it is open, the drawn Seat once the lock drew one; null otherwise. */
export function homeLine(session: EnrolledSession): { kind: "open" } | { kind: "drawn"; text: string } | null {
  if (session.seat_choice_open) return { kind: "open" };
  const seat = session.drawn_seat;
  if (seat) return { kind: "drawn", text: copy.drawn(roleName(seat.role), seat.game_number) };
  return null;
}
