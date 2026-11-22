import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

const copy = nb.reports.adjustment;

/** A no-break space: «2 ×» and «60 %» never part at a line end. */
const NBSP = " ";

/** The factors «Mer tid før KI tar over» offers (EXPERIENCE.md → Tilrettelegging), as the api
 * takes them; 1 is «Som klassen». */
export const FACTORS = ["1", "1.5", "2", "3"] as const;
export type FactorChoice = (typeof FACTORS)[number];

/** «2 ×», «1,5 ×». */
export function factorText(factor: number | string): string {
  return `${formatNumber(String(Number(factor)))}${NBSP}×`;
}

/** «60 %». */
export function percentText(percent: number): string {
  return `${percent}${NBSP}%`;
}

/** The Valgknapper's options: «Som klassen», «1,5 ×», «2 ×», «3 ×». */
export const FACTOR_OPTIONS = FACTORS.map((value) => ({
  value,
  label: value === "1" ? copy.asClass : factorText(value),
}));

/** The block's idle line: «Ingen tilrettelegging.», or «Mer tid: 2 ×. Andel uker: 60 %.» with each
 * part only when it applies. */
export function summaryText(adjustment: { time_factor: number; share_percent?: number | null } | null | undefined): string {
  if (!adjustment) return copy.none;
  const parts = [
    adjustment.time_factor > 1 ? copy.moreTime(factorText(adjustment.time_factor)) : null,
    adjustment.share_percent != null ? copy.share(percentText(adjustment.share_percent)) : null,
  ].filter((part): part is string => part !== null);
  return parts.length > 0 ? parts.join(" ") : copy.none;
}

/** The form's choice of factor from the stored one; anything not offered reads «Som klassen». */
export function factorChoice(factor: number | null | undefined): FactorChoice {
  const found = FACTORS.find((value) => Number(value) === factor);
  return found ?? "1";
}

/** The share as typed, or the reason it is refused: a whole number from 0 to the class share
 * («Skriv et helt tall fra 0 til 80.»). The api judges the same rule again. */
export function checkShare(text: string, classShare: number): { share: number } | { error: string } {
  const plain = text.trim().replace(/\s*%$/, "");
  if (!/^\d+$/.test(plain) || Number(plain) > classShare) return { error: copy.shareError(classShare) };
  return { share: Number(plain) };
}

/** The Student's own lines on Hjem, under Stegene (UX-DR53): «Du har mer tid før en KI-spiller
 * tar setet ditt (2 × vanlig ventetid).» and «For deg er kravet 60 % av ukene.», each only when
 * the api gives it. */
export function ownLines(adjustment: { time_factor?: number | null; share_percent?: number | null } | null | undefined): string[] {
  if (!adjustment) return [];
  const own = nb.homes.student.adjustment;
  return [
    adjustment.time_factor != null && adjustment.time_factor > 1 ? own.moreTime(factorText(adjustment.time_factor)) : null,
    adjustment.share_percent != null ? own.share(percentText(adjustment.share_percent)) : null,
  ].filter((line): line is string => line !== null);
}
