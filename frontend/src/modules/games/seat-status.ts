import { useEffect, useState } from "react";

import type { SeatStatusRow } from "@/components/seat-status";
import { nb } from "@/copy/nb";
import { roleName } from "@/modules/sessions/sessions";

import type { MyGame } from "./api";
import { holderText } from "./home";

const copy = nb.homes.student;

/** A Seat as the api tells it, on Hjem and in the play envelope alike (`TableSeatOut`). */
export type StatusSeat = MyGame["seats"][number];

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

/** «under 1 min», «3 min», «5 t», «3 d»: how long the game has waited, in whole units counted
 * down (Story 6.14). [ASSUMPTION: the units are draft copy] */
export function waitDuration(ms: number): string {
  if (ms < MINUTE) return copy.duration.underMinute;
  if (ms < HOUR) return copy.duration.minutes(Math.floor(ms / MINUTE));
  if (ms < 48 * HOUR) return copy.duration.hours(Math.floor(ms / HOUR));
  return copy.duration.days(Math.floor(ms / (24 * HOUR)));
}

/** How long the game has waited for `seat` at `now` (ms on the server's clock); null when its
 * wait has no stored start, or for an AI player, whose wait is bounded (NFR-2, UX-DR62). */
function waited(seat: StatusSeat, now: number): string | null {
  if (seat.ordered !== false || seat.holder === "ai" || !seat.wait_started_at) return null;
  return waitDuration(Math.max(0, now - Date.parse(seat.wait_started_at)));
}

/** The Seat's holder in words; an AI Seat the Play guard switched says it is rule-based. */
function holder(seat: StatusSeat): string {
  if (seat.holder === "ai" && seat.mark === "guard_switch") return copy.guardSwitched;
  return holderText(seat);
}

/** The Setestatus rows (FR-25, UX-DR25): «har bestilt», «venter, 3 min», «venter» or «venter
 * (deg)»; a game that does not run tells no state. */
export function seatRows(seats: StatusSeat[], now: number): SeatStatusRow[] {
  return seats.map((seat) => {
    const state = seat.ordered == null ? null : seat.ordered ? "ordered" : "waiting";
    const duration = waited(seat, now);
    const status =
      state === null
        ? null
        : state === "ordered"
          ? copy.status.ordered
          : seat.mine
            ? copy.status.waitingYou
            : duration
              ? copy.status.waitingFor(duration)
              : copy.status.waiting;
    return {
      key: seat.role,
      role: roleName(seat.role),
      holder: holder(seat),
      named: seat.holder === "student" && seat.name != null,
      state,
      status,
    };
  });
}

const LIST = new Intl.ListFormat("nb", { type: "conjunction" });

/** Whom the game waits for, in list order with the viewer last as «deg»: «Jonas (3 min) og deg».
 * A Student by name (by Role when no name can be shown), an AI player by Role; null when the game
 * waits for no one. With `others`, the viewer is left out. */
export function waitedFor(seats: StatusSeat[], now: number, others = false): string | null {
  const waiting = seats.filter((seat) => seat.ordered === false);
  const names = waiting
    .filter((seat) => !seat.mine)
    .map((seat) =>
      copy.waitedFor(seat.holder === "student" && seat.name ? seat.name : roleName(seat.role), waited(seat, now)),
    );
  if (!others && waiting.some((seat) => seat.mine)) names.push(copy.waitingYou);
  return names.length ? LIST.format(names) : null;
}

/** The roles the game waits for: what decides when «Venter på» is announced again. */
function waitingKey(seats: StatusSeat[]): string {
  return seats
    .filter((seat) => seat.ordered === false)
    .map((seat) => seat.role)
    .join(",");
}

/** «Venter på: Jonas (3 min) og deg.», changed only when whom the game waits for changes (not
 * every minute), so the polite live region speaks once per change (Story 6.14). */
export function useWaitAnnouncement(seats: StatusSeat[], now: number): string | null {
  const key = waitingKey(seats);
  const who = waitedFor(seats, now);
  const text = who ? copy.waitingOn(who) : null;
  const [shown, setShown] = useState({ key, text });
  if (shown.key !== key) setShown({ key, text });
  return shown.key === key ? shown.text : text;
}

const TICK_MS = 15_000;

/** The server's clock now, in ms (AD-20): `serverNow` from the last read, moved on by the time
 * passed since, re-read every `TICK_MS`. The browser's clock gives only the time passed. */
export function useServerNow(serverNow: string): number {
  const [offset, setOffset] = useState(() => ({ at: serverNow, ms: Date.parse(serverNow) - Date.now() }));
  if (offset.at !== serverNow) setOffset({ at: serverNow, ms: Date.parse(serverNow) - Date.now() });
  const [, tick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => tick((n) => n + 1), TICK_MS);
    return () => clearInterval(timer);
  }, []);
  return Date.now() + offset.ms;
}
