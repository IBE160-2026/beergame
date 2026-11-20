import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

/** «Ventetid før KI tar over» is whole hours, never under this (EXPERIENCE.md, FR-36). The api
 * holds the same floor; the copy names it. */
export const MIN_INACTIVITY_HOURS = 20;
/** «Andel uker som kreves» is a whole percent in this range (Story 5.7, FR-17). */
export const SHARE_RANGE = { min: 1, max: 100 } as const;

/** A whole number typed in a field («24», « 24 »), else null: empty, a decimal («2,5», «2.5»), a
 * sign or any other character is no whole number. */
export function wholeNumber(text: string): number | null {
  const trimmed = text.trim();
  return /^\d{1,6}$/.test(trimmed) ? Number(trimmed) : null;
}

/** Why the Ventetid cannot be saved, or undefined: empty, not whole or under 20 hours. */
export function inactivityProblem(text: string): string | undefined {
  const hours = wholeNumber(text);
  return hours === null || hours < MIN_INACTIVITY_HOURS ? nb.sessions.edit.inactivityError : undefined;
}

/** Why the required share cannot be saved, or undefined: not a whole percent from 1 to 100. */
export function shareProblem(text: string): string | undefined {
  const percent = wholeNumber(text);
  return percent === null || percent < SHARE_RANGE.min || percent > SHARE_RANGE.max
    ? nb.sessions.choices.shareError
    : undefined;
}

/** The api's refusal of the share or the Ventetid (`invalid_session_values`), each under its
 * field. */
export function valueErrorsOf(error: unknown): { share?: string; inactivity?: string } {
  if (!(error instanceof ApiRequestError) || error.code !== "invalid_session_values") return {};
  return {
    share: "required_share_percent" in error.fields ? nb.sessions.choices.shareError : undefined,
    inactivity: "inactivity_limit_hours" in error.fields ? nb.sessions.edit.inactivityError : undefined,
  };
}
