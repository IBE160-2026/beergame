import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import type { ClassSession } from "@/modules/sessions/api";

import type { MyTest } from "./api";

const copy = nb.tests.sitting;

/**
 * One timed sitting of the Individual test (Story 11.12, FR-51). Display only: the api stores the
 * limit, sets when each sitting ends and refuses a late save (`sitting_ended`); the page only
 * counts the time left from the api's `server_now` and says when it is up.
 */

/** The whole minutes left until `endsAt` at the server's `nowMs`, rounded up, never below 0: the
 * last seconds read «Tid igjen 1 min», and the time is up only at 0. */
export function minutesLeft(endsAt: string, nowMs: number): number {
  return Math.max(0, Math.ceil((Date.parse(endsAt) - nowMs) / 60_000));
}

/** When the open test's timed sitting ends, if it ends before its Testfrist: the case the page
 * counts down and, at 0, shows as handed in; null otherwise. A sitting that would end after the
 * Testfrist ends with it, as an untimed test does. */
export function sittingEnd(test: Pick<MyTest, "sitting_ends_at" | "test_deadline">): string | null {
  if (!test.sitting_ends_at) return null;
  if (test.test_deadline && Date.parse(test.sitting_ends_at) >= Date.parse(test.test_deadline)) return null;
  return test.sitting_ends_at;
}

/** The Lecturer's draft of the time limit: switched on or off, and the minutes as typed. */
export type SittingDraft = { on: boolean; minutes: string };

/** The default minutes a switched-on limit starts with when none is stored. [ASSUMPTION] */
export const DEFAULT_MINUTES = 90;

export function sittingDraftOf(item: Pick<ClassSession, "test_sitting">): SittingDraft {
  const minutes = item.test_sitting.minutes;
  return { on: minutes !== null, minutes: String(minutes ?? DEFAULT_MINUTES) };
}

/** «Skriv et helt antall minutter fra 15 til 240.» for a switched-on limit that is not a whole
 * number in the range; nothing when switched off or valid. The api judges it again. */
export function minutesProblem(draft: SittingDraft, item: Pick<ClassSession, "test_sitting">): string | undefined {
  if (!draft.on) return undefined;
  const { min_minutes: min, max_minutes: max } = item.test_sitting;
  const text = draft.minutes.trim();
  const value = Number(text);
  if (!/^\d+$/.test(text) || value < min || value > max) return copy.error(min, max);
  return undefined;
}

/** The save body's `test_sitting` for a changed draft: the minutes, or null switched off. */
export function sittingBody(draft: SittingDraft): { minutes: number | null } {
  return { minutes: draft.on ? Number(draft.minutes.trim()) : null };
}

/** Whether the draft differs from what is stored, so a save sends it. */
export function sittingChanged(draft: SittingDraft, item: Pick<ClassSession, "test_sitting">): boolean {
  const stored = item.test_sitting.minutes;
  if (!draft.on) return stored !== null;
  return stored === null || Number(draft.minutes.trim()) !== stored;
}

/** The api's refusal of the limit (`invalid_session_values` naming `test_sitting_minutes`), as
 * the field's error with the range. */
export function refusedMinutes(error: unknown, item: Pick<ClassSession, "test_sitting">): string | undefined {
  if (!(error instanceof ApiRequestError) || error.code !== "invalid_session_values") return undefined;
  if (!("test_sitting_minutes" in error.fields)) return undefined;
  return copy.error(item.test_sitting.min_minutes, item.test_sitting.max_minutes);
}
