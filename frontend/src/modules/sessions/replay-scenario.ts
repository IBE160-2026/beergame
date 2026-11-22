import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { formatNumber, parseNumber } from "@/lib/number-format";

import type { GameSettings } from "./api";
import { costText, infoVisibilityText } from "./sessions";
import {
  demandBody,
  draftOf,
  EDITABLE,
  type SettingName,
  type SettingsDraft,
  settingsBody,
  type SettingWarning,
} from "./settings";

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

/* Story 10.2 (FR-49): an own scenario, set from the Game settings fields. */

/** An own scenario as typed: the Game settings fields (no seed: every Replay draws its own), and
 * the highest Weeks and latest change Week, empty for one value for every Student. */
export type ReplayDraft = SettingsDraft & { weeksTo: string; changeWeekTo: string };

function low(value: Ranged): number {
  return isRange(value) ? value.minimum : value;
}

function highText(value: Ranged): string {
  return isRange(value) && value.minimum !== value.maximum ? String(value.maximum) : "";
}

/** The own scenario's form, opened on the Class session's Game settings (FR-49: «starting from the
 * Class session's»): every value as the Class game has it; Information visibility only while
 * `FEATURE_INFO_VISIBILITY` is on (Story 10.9). */
export function replayDraftOfSettings(settings: GameSettings, infoVisibilityEnabled = false): ReplayDraft {
  return { ...draftOf(settings, false, infoVisibilityEnabled), weeksTo: "", changeWeekTo: "" };
}

/** The own scenario's form, opened on a stored own template: a range shows as its two ends; a step
 * with a spread is «Trinn med tilfeldig variasjon», as the Game settings word it. The Replay's own
 * Information visibility only while its flag is on (Story 10.9). */
export function replayDraftOfTemplate(template: ReplayTemplate, infoVisibilityEnabled = false): ReplayDraft {
  const d = template.demand;
  const fields = Object.fromEntries(
    EDITABLE.map((field) => {
      const value = template[field.name];
      return [field.name, field.kind === "cost" ? costText(String(value)) : String(low(value as Ranged))];
    }),
  ) as Record<SettingName, string>;
  return {
    ...fields,
    demand: {
      kind: d.kind === "step" ? (d.spread > 0 ? "step+noise" : "step") : d.kind,
      values: d.kind === "fixed" ? d.values.join(" ") : "",
      start: d.kind === "step" ? String(d.start) : "",
      new_level: d.kind === "step" ? String(d.new_level) : "",
      change_week: d.kind === "step" ? String(low(d.change_week)) : "",
      mean: d.kind === "random" ? String(d.mean) : "",
      spread: d.kind === "fixed" ? "" : String(d.spread),
      seed: "",
    },
    weeksTo: highText(template.weeks),
    changeWeekTo: d.kind === "step" ? highText(d.change_week) : "",
    ...(infoVisibilityEnabled
      ? {
          infoVisibility: {
            upstream: template.info_visibility.upstream,
            downstream: template.info_visibility.downstream,
          },
        }
      : {}),
  };
}

/** The form the Klasseøkt opens: the stored own template, else the Game settings. */
export function replayDraftOf(item: {
  replay_scenario: string;
  replay_template: ReplayTemplate;
  game_settings: GameSettings;
  info_visibility_enabled: boolean;
}): ReplayDraft {
  return item.replay_scenario === "own"
    ? replayDraftOfTemplate(item.replay_template, item.info_visibility_enabled)
    : replayDraftOfSettings(item.game_settings, item.info_visibility_enabled);
}

/** One value, or a range when a different «høyst» value is typed. Anything that is not a whole
 * number goes as typed, so the api names what is wrong. */
function rangeBody(from: string, to: string): unknown {
  const lowest = wholeNumber(from);
  if (to.trim() === "") return lowest;
  const highest = wholeNumber(to);
  return highest === lowest ? lowest : { minimum: lowest, maximum: highest };
}

/** A whole number as the Game settings send it: «1 000» is 1000, anything else as typed. */
function wholeNumber(typed: string): unknown {
  const parsed = parseNumber(typed);
  return parsed !== null && /^-?\d+$/.test(parsed) ? Number(parsed) : typed;
}

/** The template's `demand`: a step with its spread (0 for «Trinn»), random with its spread, a fixed
 * series with none. The change Week may be a range. */
function replayDemandBody(draft: ReplayDraft): Record<string, unknown> {
  const body = demandBody(draft.demand);
  const kind = draft.demand.kind;
  if (kind === "step" || kind === "step+noise") {
    return {
      ...body,
      kind: "step",
      change_week: rangeBody(draft.demand.change_week, draft.changeWeekTo),
      spread: kind === "step" ? 0 : body.spread,
    };
  }
  return kind === "fixed" ? { ...body, spread: 0 } : body;
}

/** The body's `replay_template`: the template's editable fields, numbers as the Game settings send
 * them, Weeks and the change Week as one value or a range, and the Replay's own Information
 * visibility while its field is shown (Story 10.9). The chain and capacity are the Class
 * session's, and a visibility left out keeps the stored one; the api adds them. */
export function replayTemplateBody(draft: ReplayDraft): Record<string, unknown> {
  const settings = settingsBody(draft);
  const body: Record<string, unknown> = {};
  for (const field of EDITABLE) body[field.name] = settings[field.name];
  body.weeks = rangeBody(draft.weeks, draft.weeksTo);
  body.demand = replayDemandBody(draft);
  if (draft.infoVisibility) body.info_visibility = { ...draft.infoVisibility };
  return body;
}

export type OwnRow = ScenarioRow & { key: string };

/** An own scenario as a list: every setting, ranges as «30 til 40», and «Synlige naboer» while
 * `FEATURE_INFO_VISIBILITY` is on (Story 10.9). Keys are the api's, so a warning stands under its
 * row. */
export function ownRows(template: ReplayTemplate, infoVisibilityEnabled = false): OwnRow[] {
  const s = nb.sessions.settings;
  const whole = (value: Ranged) =>
    isRange(value) && value.minimum !== value.maximum ? copy.range(value.minimum, value.maximum) : String(low(value));
  const d = template.demand;
  const demand = d.kind === "fixed" ? withSpread(copy.ownFixedDemand(d.values.length), d.spread) : demandText(template);
  const rows: OwnRow[] = [
    { key: "starting_inventory", label: s.startingInventory, value: whole(template.starting_inventory) },
    { key: "starting_backlog", label: s.startingBacklog, value: whole(template.starting_backlog) },
    { key: "supply_line", label: s.supplyLine, value: whole(template.supply_line) },
    { key: "order_delay", label: s.orderDelay, value: whole(template.order_delay) },
    { key: "shipping_delay", label: s.shippingDelay, value: whole(template.shipping_delay) },
    { key: "production_delay", label: s.productionDelay, value: whole(template.production_delay) },
    { key: "holding_cost", label: s.holdingCost, value: costText(template.holding_cost) },
    { key: "backorder_cost", label: s.backorderCost, value: costText(template.backorder_cost) },
    { key: "weeks", label: copy.weeks, value: count(template.weeks) },
    { key: "guided_weeks", label: copy.guidedWeeks, value: count(template.guided_weeks) },
    { key: "max_order", label: s.maxOrder, value: whole(template.max_order) },
    { key: "demand", label: copy.demand, value: demand },
  ];
  if (d.kind === "step") rows.push({ key: "demand.change_week", label: copy.changeWeek, value: week(d.change_week) });
  if (infoVisibilityEnabled) {
    rows.push({ key: "info_visibility", label: s.infoVisibility, value: infoVisibilityText(template) });
  }
  return rows;
}

function withSpread(text: string, spread: number): string {
  return spread > 0 ? copy.spread(text, spread) : text;
}

/** The line under an own scenario: what is drawn per Student, else that every Student gets the same
 * values (and, with a spread, their own demand around the levels). */
export function ownHiddenLine(template: ReplayTemplate): string {
  const change = template.demand.kind === "step" && ranged(template.demand.change_week);
  const weeks = ranged(template.weeks);
  if (change && weeks) return copy.hiddenBoth;
  if (weeks) return copy.hiddenWeeks;
  if (change) return copy.hiddenChange;
  return template.demand.spread > 0 ? copy.hiddenOwnNoise : copy.hiddenOwnNone;
}

const DELAY_LABELS: Record<string, string> = {
  order_delay: nb.sessions.settings.orderDelay,
  shipping_delay: nb.sessions.settings.shippingDelay,
  production_delay: nb.sessions.settings.productionDelay,
};

function warningLine(warning: SettingWarning): string {
  const w = copy.warnings;
  const replay = formatNumber(warning.values.replay ?? "");
  const classGame = formatNumber(warning.values.class_game ?? "");
  switch (warning.code) {
    case "replay_inventory_higher":
      return w.inventory(replay, classGame);
    case "replay_delay_shorter":
      return w.delay(DELAY_LABELS[warning.field] ?? warning.field, replay, classGame);
    case "replay_guided_weeks":
      return w.guided(replay);
    case "replay_demand_lower":
      return w.lower(replay, classGame);
    case "replay_demand_less_variable":
      return w.lessVariable(replay, classGame);
    case "replay_demand_no_change":
      return w.noChange;
    case "replay_neighbour_visible":
      if (warning.values.view === "upstream") return w.upstreamVisible;
      return warning.values.view === "downstream" ? w.downstreamVisible : w.other;
    default:
      return w.other;
  }
}

/** A warning of a change that probably makes the Replay easier (`replay_*` codes), in words: what
 * changed against the Class game, then that it probably makes the Replay easier. */
export function replayWarningText(warning: SettingWarning): string {
  return `${warningLine(warning)} ${copy.warnings.easier}`;
}

/** The warnings in words by the field they stand under. */
export function replayWarningsByField(warnings: readonly SettingWarning[]): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const warning of warnings) (result[warning.field] ??= []).push(replayWarningText(warning));
  return result;
}
