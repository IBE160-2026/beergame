import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

const copy = nb.overview.start;
const one = nb.spillstyring.start;

/** The Oversikt header's Lenke «Start spill som ikke har startet (12)» (Story 8.10, UX-DR52); none
 * with a count of 0. */
export function startLinkText(startable: number | null | undefined): string | null {
  return startable && startable > 0 ? copy.link(startable) : null;
}

/** The «Start spill» page's primary: «Start 12 spill». */
export function confirmText(count: number): string {
  return copy.confirm(count);
}

/** The count «Start 12 spill» carried back to the Oversikt (`?startet=12`): a whole number from 0,
 * else null (an address typed by hand says nothing). */
export function startedParam(params: Pick<URLSearchParams, "get">): number | null {
  const value = params.get("startet");
  if (value === null || !/^\d{1,4}$/.test(value)) return null;
  return Number(value);
}

/** The Oversikt's line after the batch: «12 spill er startet.» with the real count. */
export function startedText(count: number): string {
  return copy.done(count);
}

/** What a press of «Start spillet» came to: started now, or someone started it first. */
export type StartResult = { kind: "done" } | { kind: "first" };

/** Whether the refusal says the game was started first (Story 8.10, `game_already_started`). */
export function startedFirst(error: unknown): boolean {
  return error instanceof ApiRequestError && error.code === "game_already_started";
}

/** The result line: «Spillet er startet.», or who started it first by the name the view read again
 * gives (`startedBy`): «Spillet ble startet av Sara.». */
export function startResultText(result: StartResult, startedBy: string | null | undefined): string {
  if (result.kind === "done") return one.done;
  return startedBy ? one.startedBy(startedBy) : one.startedAlready;
}
