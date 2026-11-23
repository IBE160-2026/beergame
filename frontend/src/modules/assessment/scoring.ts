import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { actionErrorMessage } from "@/lib/api/mutation";
import { formatNumber } from "@/lib/number-format";
import { formatTime } from "@/modules/admin/audit";

import type { ScoringEntry, ScoringItem, ScoringTest } from "./scoring-api";

const copy = nb.scoring;

/** «Åpner etter testfristen 12. des. 2026 kl. 23:59.» or the Lenke text that opens the answers. */
export function testLine(test: ScoringTest): string {
  if (test.open) return copy.tests.open(test.name);
  return test.test_deadline ? copy.tests.closed(formatTime(test.test_deadline)) : copy.tests.noDeadline;
}

/** «3 av 12 vurdert»: the reader's own progress through the list. */
export function progressText(entries: readonly ScoringEntry[]): string {
  const scored = entries.filter((entry) => entry.scored).length;
  return copy.list.progress(formatNumber(scored), formatNumber(entries.length));
}

/** «Svar 3» (a neutral number, never a name). */
export function answerLabel(number: number): string {
  return copy.list.answer(formatNumber(number));
}

/** The item's type in words. */
export function typeText(type: string): string {
  return Object.hasOwn(copy.list.types, type) ? copy.list.types[type] : type;
}

/** The scale as Valgknapper options: «3: godt». */
export function scaleOptions(item: Pick<ScoringItem, "scale">): { value: string; label: string }[] {
  return item.scale.map((step) => ({ value: String(step.step), label: copy.item.step(formatNumber(step.step), step.label) }));
}

function labelOf(item: Pick<ScoringItem, "scale">, step: number): string {
  return item.scale.find((each) => each.step === step)?.label ?? "";
}

/** «Din vurdering: 3 av 4, godt.», once the reader has scored the answer. */
export function ownText(item: ScoringItem): string | null {
  if (!item.own_score) return null;
  return copy.item.own(formatNumber(item.own_score.score), labelOf(item, item.own_score.score));
}

/** The AI's step in words after the reader's own score; before it, that it is hidden. */
export function aiText(item: ScoringItem): string {
  if (!item.own_score) return copy.item.aiHidden;
  if (!item.ai) return copy.item.aiMissing;
  return copy.item.ai(formatNumber(item.ai.step), item.ai.label ?? labelOf(item, item.ai.step));
}

/** The line beside «Lagre vurdering» when it was refused or failed. */
export function submitError(error: unknown): string {
  return actionErrorMessage(error, copy.item.errors);
}

/** A refused «Utnevn som sensor» as the line under the address field. */
export function scorerError(error: unknown): string {
  if (error instanceof ApiRequestError && error.code === "invalid_request") {
    const reason = error.fields.email;
    if (typeof reason === "string" && Object.hasOwn(copy.scorers.errors, reason)) return copy.scorers.errors[reason];
  }
  return copy.scorers.failed;
}
