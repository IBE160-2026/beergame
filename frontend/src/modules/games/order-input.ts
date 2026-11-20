import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

const copy = nb.games.play.order;

/**
 * What the Ordrefelt's text says (Story 6.11, FR-24, EXPERIENCE.md → Ordrefelt): a whole number
 * from 0 to the Game settings maximum, typed as digits only. Letters, decimals, a minus or spaces
 * are not a whole number; digits above the maximum are out of range.
 */
export type ParsedOrder =
  | { kind: "empty" }
  | { kind: "valid"; value: number }
  | { kind: "invalid" }
  | { kind: "too-large"; digits: string };

const DIGITS = /^[0-9]+$/;

export function parseOrder(text: string, max: number): ParsedOrder {
  if (text === "") return { kind: "empty" };
  if (!DIGITS.test(text)) return { kind: "invalid" };
  const value = Number(text);
  if (value > max) return { kind: "too-large", digits: text.replace(/^0+(?=\d)/, "") };
  return { kind: "valid", value };
}

/** «Sist Uke bestilte du n.»: the Order of the Uke before nå, from the last `history` row (in the
 * first free Uke, the last fixed Order); none in Uke 1. */
export function lastOrder(history: readonly { order: number }[]): number | undefined {
  return history.at(-1)?.order;
}

/** The reason under the help line, or null when there is none to show. */
export function orderError(parsed: ParsedOrder, max: number): string | null {
  const limit = formatNumber(max);
  if (parsed.kind === "invalid") return copy.invalid(limit);
  if (parsed.kind === "too-large") {
    const value = Number(parsed.digits);
    return copy.tooLarge(Number.isSafeInteger(value) ? formatNumber(value) : parsed.digits, limit);
  }
  return null;
}

/**
 * The − and + segments: the value each would give, or null where it cannot act. − cannot act on
 * an empty field or at 0; + gives 1 on an empty field and cannot act at the maximum. While the text
 * is not digits neither acts; − on a number above the maximum gives the maximum.
 */
export function stepOrder(parsed: ParsedOrder, max: number, direction: -1 | 1): number | null {
  switch (parsed.kind) {
    case "empty":
      return direction === 1 && max >= 1 ? 1 : null;
    case "invalid":
      return null;
    case "too-large":
      return direction === -1 ? max : null;
    case "valid": {
      const next = parsed.value + direction;
      return next < 0 || next > max ? null : next;
    }
  }
}
