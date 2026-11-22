import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import type { ClassSession } from "@/modules/sessions/api";

/** The Indicative letter of a Class session as the Klasseøkt reads it (Story 12.6, FR-56). */
export type LetterSetting = ClassSession["ai_assessment"]["letter"];
export type LetterChoice = LetterSetting["setting"];
export type LetterBounds = LetterSetting["thresholds"];

/** The letters with a bound the Lecturer sets; F is what lies under E. */
export const BOUNDED = ["A", "B", "C", "D", "E"] as const;
export type BoundedLetter = (typeof BOUNDED)[number];

/** The bound fields as typed. */
export type BoundsDraft = Record<BoundedLetter, string>;

export function boundsDraftOf(bounds: LetterBounds): BoundsDraft {
  return Object.fromEntries(BOUNDED.map((letter) => [letter, String(bounds[letter])])) as BoundsDraft;
}

const WHOLE = /^\d{1,3}$/;

/** The web's own check of the bounds, as the api judges them: whole numbers from 1 to 100,
 * strictly falling from A to E. */
export function boundsProblem(draft: BoundsDraft): "out_of_range" | "out_of_order" | undefined {
  const values: number[] = [];
  for (const letter of BOUNDED) {
    const text = draft[letter].trim();
    if (!WHOLE.test(text)) return "out_of_range";
    const value = Number(text);
    if (value < 1 || value > 100) return "out_of_range";
    values.push(value);
  }
  return values.some((value, i) => i > 0 && value >= values[i - 1]) ? "out_of_order" : undefined;
}

/** The bounds as sent; call only when `boundsProblem` is undefined. */
export function boundsBody(draft: BoundsDraft): LetterBounds {
  return Object.fromEntries(BOUNDED.map((letter) => [letter, Number(draft[letter].trim())])) as LetterBounds;
}

/** Whether the typed bounds differ from the ones in force (an unchanged set is never sent). */
export function boundsChanged(draft: BoundsDraft, bounds: LetterBounds): boolean {
  return BOUNDED.some((letter) => draft[letter].trim() !== String(bounds[letter]));
}

/** «A fra 90 %, B fra 80 %, C fra 60 %, D fra 50 %, E fra 40 %», through the number formatter. */
export function boundsText(bounds: LetterBounds): string {
  return BOUNDED.map((letter) => nb.assessment.letterBlock.boundText(letter, formatNumber(bounds[letter]))).join(", ");
}
