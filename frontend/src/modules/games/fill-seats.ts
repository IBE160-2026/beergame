import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { roleName } from "@/modules/sessions/sessions";

import { waitDuration } from "./seat-status";

const copy = nb.overview.fill;
const one = nb.spillstyring.fill;

type WaitedSeat = components["schemas"]["WaitedSeatOut"];
type WaitingSeat = components["schemas"]["WaitingSeatOut"];

/** A waited-for Seat's Student by name, or by Role when no longer named in the Class. */
export function seatName(seat: WaitedSeat): string {
  return seat.name ?? roleName(seat.role);
}

/** «Noah, Emma og Jonas»: names joined the Norwegian way. */
export function namesText(names: readonly string[]): string {
  return new Intl.ListFormat("nb", { type: "conjunction" }).format(names);
}

/** The Oversikt header's Lenke «Sett inn KI-spiller i alle seter som blir ventet på (9)» (Story
 * 8.12, UX-DR52); none with a count of 0. */
export function fillLinkText(fillable: number | null | undefined): string | null {
  return fillable && fillable > 0 ? copy.link(fillable) : null;
}

/** «Ikke med (tilrettelegging): Jonas» for the Seats left out; null when none is. */
export function leftOutText(leftOut: readonly WaitedSeat[]): string | null {
  return leftOut.length > 0 ? one.leftOut(namesText(leftOut.map(seatName))) : null;
}

/** «Noah, 23 t»: a listed Seat with how long it has been waited for at `now` (ms, server clock). */
export function waitingSeatText(seat: WaitingSeat, now: number): string {
  return copy.seat(seatName(seat), waitDuration(Math.max(0, now - Date.parse(seat.since))));
}

/** The per-game result line: «2 KI-spillere satt inn.», or that none was when every Seat had
 * ordered or been taken meanwhile. */
export function filledText(inserted: number): string {
  return inserted > 0 ? one.done(inserted) : one.none;
}

/** A fill that put no AI player in while a Seat failed (`failed`): said as a failure inline, the
 * button kept, rather than as a result. */
export function fillFailed(answer: { inserted: number; skipped: readonly { reason: string }[] }): boolean {
  return answer.inserted === 0 && answer.skipped.some((seat) => seat.reason === "failed");
}

/** The count «Sett inn 9 KI-spillere» carried back to the Oversikt (`?satt-inn=9`): a whole number
 * from 0, else null (an address typed by hand says nothing). */
export function filledParam(params: Pick<URLSearchParams, "get">): number | null {
  const value = params.get("satt-inn");
  if (value === null || !/^\d{1,4}$/.test(value)) return null;
  return Number(value);
}
