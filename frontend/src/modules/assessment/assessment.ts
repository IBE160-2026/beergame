import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { AssessedItem, MyAssessment } from "./api";

const copy = nb.assessment.student;

/** «3», «3 og 6», «2, 3 og 6»: item numbers in words, through the number formatter. */
export function numbersText(numbers: readonly number[]): string {
  const words = numbers.map((n) => formatNumber(n));
  if (words.length <= 1) return words.join("");
  return `${words.slice(0, -1).join(", ")} ${copy.and} ${words.at(-1)}`;
}

/** The one line a state with no items says, or null for `ready` and `incomplete` (they list the
 * items; `incomplete` names the ones without a score). */
export function stateLine(assessment: Pick<MyAssessment, "state" | "unassessed">): string | null {
  switch (assessment.state) {
    case "not_ready":
      return copy.notReady;
    case "switched_off":
      return copy.switchedOff;
    case "no_test":
      return copy.noTest;
    case "failed":
      return copy.failed;
    case "incomplete":
      return copy.incomplete(numbersText(assessment.unassessed));
    default:
      return null;
  }
}

/** «7,5 av 10 poeng», or «Ikke vurdert ennå» while the item has no score. */
export function pointsText(item: Pick<AssessedItem, "points" | "weight">): string {
  return item.points == null ? copy.notAssessed : copy.points(formatNumber(item.points), formatNumber(item.weight));
}

/** The item's score in words: the AI's step on the scale («KI-vurdering: 3 av 4 (Godt)») for a
 * long-answer or Adapted item, the computed result for every other item. */
export function scoreText(item: Pick<AssessedItem, "ai" | "computed">): string {
  if (item.ai) {
    if (!item.ai.assessed || item.ai.step == null) return copy.notAssessed;
    return copy.aiStep(formatNumber(item.ai.step), formatNumber(item.ai.top), item.ai.label ?? "");
  }
  return item.computed ? copy.computed[item.computed.result] : "";
}

/** «Vektet sum: 57,75 av 100 poeng», or null with no total (never a partial one). */
export function totalText(assessment: Pick<MyAssessment, "total" | "total_max">): string | null {
  if (assessment.total == null || assessment.total_max == null) return null;
  return copy.total(formatNumber(assessment.total), formatNumber(assessment.total_max));
}
