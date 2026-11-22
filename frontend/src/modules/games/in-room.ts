import { nb } from "@/copy/nb";
import { osloDayAndTime } from "@/modules/sessions/dates";

import type { GameInRoom, InsightInRoom } from "./api";

const copy = nb.spillstyring.inRoom;
const studentCopy = nb.homes.student.inRoom;

/** The in-room limit's default and range in whole minutes (FR-36, EXPERIENCE.md → Spillstyring →
 * I rommet). The api judges the same range again (`minutes_out_of_range`). */
export const IN_ROOM_DEFAULT = 10;
export const IN_ROOM_MIN = 2;
export const IN_ROOM_MAX = 120;

/** «16:00»: an instant's clock time in Europe/Oslo. */
export function osloClock(iso: string): string {
  return osloDayAndTime(iso).time;
}

/** The whole number of minutes the field holds, or null for anything else: an empty field, a
 * decimal, a sign or a number outside 2 to 120. */
export function inRoomMinutes(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const minutes = Number(trimmed);
  return minutes >= IN_ROOM_MIN && minutes <= IN_ROOM_MAX ? minutes : null;
}

/** The field's error in the Ordrefelt pattern, or undefined when the value is whole and in range. */
export function inRoomError(text: string): string | undefined {
  return inRoomMinutes(text) === null ? copy.error : undefined;
}

/** «Marker som i rommet, 10 min» while the field holds a valid number, else without minutes. */
export function confirmLabel(text: string): string {
  return copy.confirm(inRoomMinutes(text));
}

/** Spillstyring's marked line: «I rommet til 16:00. KI tar over etter 10 min uten ordre.» */
export function markedText(inRoom: InsightInRoom): string {
  return copy.marked(osloClock(inRoom.until), inRoom.minutes);
}

/** The Student's line above Setestatus, with their own minutes: «I rommet til kl. 16:00. En
 * KI-spiller tar setet etter 10 min uten ordre.» Empty when the game is not marked. */
export function inRoomLine(inRoom: GameInRoom | null | undefined): string {
  return inRoom ? studentCopy.line(osloClock(inRoom.until), inRoom.minutes) : "";
}
