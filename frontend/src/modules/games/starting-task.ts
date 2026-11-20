import { nb } from "@/copy/nb";
import { formatNumber, MINUS } from "@/lib/number-format";
import type { components } from "@/lib/api/schema";

/** The Startoppgave as the api gives it (Story 6.3): the items in order, answered ones with their
 * result. The web app scores nothing and sums nothing (AD-1): it writes out the api's terms. */
export type StartingTask = components["schemas"]["StartingTaskOut"];
export type StartingTaskItem = components["schemas"]["StartingTaskItemOut"];
export type ItemResult = components["schemas"]["ItemResultOut"];
export type FinalChoice = components["schemas"]["Choice"];

const copy = nb.games.startingTask;

/** The largest answer the api takes, either way. */
const LIMIT = 1_000_000;

/** A whole number typed into an item («13», «−13», «-13», « 4 »), or null for letters, decimals,
 * nothing or a number past the api's limit, which read «Skriv et helt tall.». */
export function parseWholeNumber(text: string): number | null {
  const plain = text.trim().replace(/^[−–]/, "-");
  if (!/^-?\d{1,7}$/.test(plain)) return null;
  const value = Number(plain);
  if (Math.abs(value) > LIMIT) return null;
  return value === 0 ? 0 : value; // never −0
}

/** The api's terms as the sum the result line shows: «0 − 13 + 16». A first term taken away
 * reads «−13»; a negative value added reads «+ (−3)» so no two signs meet. */
export function sumText(terms: ItemResult["terms"]): string {
  return terms
    .map(({ sign, value }, i) => {
      const shown = value < 0 ? `(${formatNumber(value)})` : formatNumber(value);
      if (i === 0) return sign < 0 && value !== 0 ? `${MINUS}${shown}` : shown;
      return `${sign < 0 ? MINUS : "+"} ${shown}`;
    })
    .join(" ");
}

/** «Riktig. Svaret er 3: 0 − 13 + 16.» or «Ikke riktig. …»: right and wrong in words, never by
 * colour alone. */
export function resultLine(result: ItemResult): string {
  const line = result.correct ? copy.right : copy.wrong;
  return line(formatNumber(result.expected), sumText(result.terms));
}

/** The index of the first item without a result, where the Student resumes; −1 when all are
 * answered. */
export function firstOpen(task: StartingTask): number {
  return task.items.findIndex((item) => item.result === null || item.result === undefined);
}
