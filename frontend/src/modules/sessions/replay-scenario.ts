import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";

/** The Replay scenario template the api sends with the Klasseøkt (Story 10.1). */
export type ReplayTemplate = components["schemas"]["ReplayTemplate"];
type Ranged = number | components["schemas"]["IntRange"];

const copy = nb.sessions.replay;

export interface ScenarioRow {
  label: string;
  value: string;
}

function isRange(value: Ranged): value is components["schemas"]["IntRange"] {
  return typeof value !== "number";
}

/** A count of Weeks; 0 reads «Ingen», and a range of one value reads as that value. */
function count(value: Ranged): string {
  if (isRange(value) && value.minimum !== value.maximum) return copy.range(value.minimum, value.maximum);
  const single = isRange(value) ? value.minimum : value;
  return single === 0 ? copy.none : String(single);
}

function week(value: Ranged): string {
  if (!isRange(value)) return copy.week(value);
  return value.minimum === value.maximum ? copy.week(value.minimum) : copy.weekRange(value.minimum, value.maximum);
}

function ranged(value: Ranged): boolean {
  return isRange(value) && value.minimum !== value.maximum;
}

/** The demand in words: its levels, and the variation each Week when there is one. */
export function demandText(template: ReplayTemplate): string {
  const demand = template.demand;
  const levels =
    demand.kind === "step"
      ? copy.stepDemand(demand.start, demand.new_level)
      : demand.kind === "random"
        ? copy.randomDemand(demand.mean)
        : copy.fixedDemand;
  return demand.spread > 0 ? copy.spread(levels, demand.spread) : levels;
}

/** The rows the Replay block lists: demand, the change Week (a step only), the length and the
 * Guided Weeks, then that the rest follows the Game settings. Ranges show as «5 til 12». */
export function scenarioRows(template: ReplayTemplate): ScenarioRow[] {
  const rows: ScenarioRow[] = [{ label: copy.demand, value: demandText(template) }];
  if (template.demand.kind === "step") rows.push({ label: copy.changeWeek, value: week(template.demand.change_week) });
  rows.push(
    { label: copy.weeks, value: count(template.weeks) },
    { label: copy.guidedWeeks, value: count(template.guided_weeks) },
    { label: copy.rest, value: copy.restValue },
  );
  return rows;
}

/** The line under the list: what is drawn per Student and stays hidden. */
export function hiddenLine(template: ReplayTemplate): string {
  const change = template.demand.kind === "step" && ranged(template.demand.change_week);
  const weeks = ranged(template.weeks);
  if (change && weeks) return copy.hiddenBoth;
  if (weeks) return copy.hiddenWeeks;
  return copy.hiddenNone;
}
