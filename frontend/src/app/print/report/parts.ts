import type { components } from "@/lib/api/schema";
import { formatNumber } from "@/lib/number-format";

import { reportCopy, reportDateTime } from "./copy";

/**
 * The Debrief, Replay and Individual test sections' words as pure steps (Story 13.10, FR-58): what
 * each line says from the snapshot alone. The renderers are `debrief-section.tsx`,
 * `replay-section.tsx` and `test-section.tsx`.
 */

export type DebriefSection = components["schemas"]["DebriefSectionOut"];
export type ReplaySection = components["schemas"]["ReplaySectionOut"];
export type ReplayData = components["schemas"]["ReportReplayOut"];
export type TestSection = components["schemas"]["TestSectionOut"];
export type TestData = components["schemas"]["ReportTestOut"];
export type TestItem = components["schemas"]["ReportTestItemOut"];
export type ReportText = components["schemas"]["ReportTextOut"];

/** «Debriefen ble fullført …», with «etter Debrieffristen» when it was late, or that it was not. */
export function debriefLine(section: Pick<DebriefSection, "finished_at" | "late">): string {
  const copy = reportCopy.debrief;
  if (!section.finished_at) return copy.notFinished;
  const when = reportDateTime(section.finished_at);
  return section.late ? copy.late(when) : copy.finished(when);
}

/** Points as the report writes them: «7,5», «10», «0». */
export function points(value: string | number): string {
  return formatNumber(value, { decimals: 2, narrow: true });
}

/** The Replay scenario's rows (FR-49): the Replay's own settings, in words. */
export function scenarioRows(replay: ReplayData, role: string): { name: string; value: string }[] {
  const copy = reportCopy.replay;
  const s = replay.scenario;
  const n = (value: number) => formatNumber(value);
  const kr = (value: string) => formatNumber(value, { decimals: 2 });
  return [
    { name: copy.facts.role, value: role },
    { name: copy.facts.weeks, value: copy.weeks(n(replay.replay.weeks.length), n(s.weeks)) },
    { name: copy.facts.guided, value: n(s.guided_weeks) },
    { name: copy.facts.start, value: copy.start(n(s.starting_inventory), n(s.starting_backlog)) },
    { name: copy.facts.delays, value: copy.delays(n(s.order_delay), n(s.shipping_delay), n(s.production_delay)) },
    { name: copy.facts.costs, value: copy.costs(kr(s.holding_cost), kr(s.backorder_cost)) },
  ];
}

/** «Levert …», «Levert automatisk …» or that the test was not handed in. */
export function testLine(test: Pick<TestData, "state" | "submitted_at">): string {
  const copy = reportCopy.test;
  if (test.state === "open" || !test.submitted_at) return copy.open;
  const when = reportDateTime(test.submitted_at);
  return test.state === "auto_submitted" ? copy.autoSubmitted(when) : copy.submitted(when);
}

/** The Uker of an Interaktiv oppgave in even blocks that fit A4 at the report's column width. */
export function answerBlocks(rows: number, most: number): { from: number; to: number }[] {
  if (rows <= 0) return [];
  const count = Math.ceil(rows / most);
  const size = Math.ceil(rows / count);
  return Array.from({ length: count }, (_, i) => ({ from: i * size + 1, to: Math.min(rows, (i + 1) * size) }));
}
