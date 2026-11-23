import { nb } from "@/copy/nb";
import { formatNumber, MINUS } from "@/lib/number-format";
import { formatTime } from "@/modules/admin/audit";

import type { ControlResults } from "./scoring-api";

const copy = nb.scoring.results;

/** «50 %», «33,3 %»: a share of 0 to 1 as a percentage with at most one decimal; «Ikke beregnet»
 * when there is nothing to compute. Every number goes through the shared formatter. */
export function percentText(share: number | null | undefined): string {
  if (share === null || share === undefined) return copy.measures.none;
  return `${formatNumber((share * 100).toFixed(2), { decimals: 1, narrow: true })} %`;
}

/** «+0,75 trinn», «−0,5 trinn», «0 trinn»: the AI's mean step minus the scorer's. */
export function offsetText(offset: number | null | undefined): string {
  if (offset === null || offset === undefined) return copy.measures.none;
  const text = formatNumber(offset.toFixed(4), { decimals: 2, narrow: true });
  const signed = offset > 0 && !text.startsWith(MINUS) && text !== "0" ? `+${text}` : text;
  return copy.measures.steps(signed);
}

/** «0,45»: the AI's spread over the scorers'. */
export function compressionText(compression: number | null | undefined): string {
  if (compression === null || compression === undefined) return copy.measures.none;
  return formatNumber(compression.toFixed(4), { decimals: 2, narrow: true });
}

/** The column heading of a named scorer: their name, or «Sensor 2» when the User has none. */
export function scorerHeading(name: string, index: number): string {
  return name.trim() || copy.table.scorer(formatNumber(index + 1));
}

/** A scorer's cell: the step, or «Ikke vurdert». */
export function humanCell(step: number | null | undefined): string {
  return step === null || step === undefined ? copy.table.notScored : formatNumber(step);
}

/** The AI's cell: the step, «Skjult» while withheld from a scorer, or «Mangler». */
export function aiCell(step: number | null | undefined, withheld: boolean): string {
  if (withheld) return copy.table.hidden;
  return step === null || step === undefined ? copy.table.aiMissing : formatNumber(step);
}

/** The status lines above the measures, in order: checked or preliminary, then what is missing. */
export function statusLines(page: ControlResults): string[] {
  if (!page.test.open) return [copy.notOpen(formatTime(page.test.test_deadline))];
  // «Kontrollert» only once this Control test is complete; a pair another Control test checked
  // first still reads as preliminary here while scores are missing.
  const head = page.complete && page.checked ? copy.checked : page.checked ? copy.preliminaryCheckedElsewhere : copy.preliminary;
  const lines: string[] = [head];
  if (page.scorers.length === 0) lines.push(copy.noScorers);
  if (page.missing > 0) lines.push(copy.missing(page.missing, formatNumber(page.missing)));
  if (page.open_attempts > 0) lines.push(copy.openAttempts(page.open_attempts, formatNumber(page.open_attempts)));
  if (page.ai_missing > 0 && !page.withheld) lines.push(copy.aiMissing(page.ai_missing, formatNumber(page.ai_missing)));
  return lines;
}
