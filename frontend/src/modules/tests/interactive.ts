import { parseWholeNumber } from "@/modules/games/starting-task";

import type { MyTestItem } from "./api";
import type { AnswerValue } from "./autosave";

/**
 * Table and number Interactive items (Story 11.5, FR-80, UX-DR38) as pure steps: a cell's text
 * read as a whole number, the values a table answer holds, and the text a stored value shows. The
 * web app scores nothing (AD-1): what the api stores is what the Student typed.
 */

/** What a typed cell holds: a whole number, nothing (an empty cell: not answered), or text that
 * is no whole number («1,5», letters, a minus where the item takes none), which is never sent. */
export type Cell = { kind: "value"; value: number } | { kind: "empty" } | { kind: "invalid" };

export function parseCell(text: string, negative: boolean): Cell {
  if (text.trim() === "") return { kind: "empty" };
  const value = parseWholeNumber(text);
  if (value === null || (!negative && value < 0)) return { kind: "invalid" };
  return { kind: "value", value };
}

/** A table answer as one value or null per row, whatever was stored (a missing answer, one of
 * another shape). */
export function tableValues(value: AnswerValue, rows: number): (number | null)[] {
  const cells = Array.isArray(value) ? value : [];
  return Array.from({ length: rows }, (_, i) => {
    const cell = cells[i];
    return typeof cell === "number" ? cell : null;
  });
}

/** A number answer's value, or null. */
export function numberValue(value: AnswerValue): number | null {
  return typeof value === "number" ? value : null;
}

/** The text a stored value shows in its field: plain digits with a leading minus. */
export function cellText(value: number | null): string {
  return value === null ? "" : String(value);
}

/** The values with row `index` set. */
export function withCell(values: readonly (number | null)[], index: number, value: number | null): (number | null)[] {
  return values.map((v, i) => (i === index ? value : v));
}

/** Whether two answers hold the same values. */
export function sameValue(a: AnswerValue, b: AnswerValue): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/** Whether the item is an Interactive item with its own table (its introduction says that these
 * items are hard, FR-80); a Starting task item is answered like in the Startoppgave. */
export function isInteractive(item: Pick<MyTestItem, "type" | "table" | "column">): boolean {
  if (item.type === "table" || item.type === "drawn") return item.table !== null;
  if (item.type === "number") return item.column !== null && !item.column.starting_task;
  return false;
}

/**
 * A drawn item's graph (Story 11.14, FR-80, UX-DR38) as pure steps: where its value axis runs,
 * where an unanswered Uke's point starts, a key's step and the value a pointer's height gives.
 * Display only: the values are what the table holds, and the api scores them (AD-1).
 */

/** The shown range: the item's axis, widened to hold every answered value so no point is cut. */
export function graphDomain(axis: { min: number; max: number }, values: readonly (number | null)[]): [number, number] {
  const answered = values.filter((v): v is number => v !== null);
  return [Math.min(axis.min, ...answered), Math.max(axis.max, ...answered)];
}

/** Where an unanswered Uke's point starts: the nearest answered Uke before it, else 0, inside the
 * range. */
export function startValue(values: readonly (number | null)[], index: number, domain: readonly [number, number]): number {
  for (let i = index - 1; i >= 0; i--) {
    const v = values[i];
    if (v !== null && v !== undefined) return clamp(v, domain);
  }
  return clamp(0, domain);
}

/** The keys a point answers (the slider pattern): Up and Right by 1, Down and Left by −1, Page Up
 * and Page Down by 10, Home and End to the range's ends. Null for any other key. */
export function stepValue(key: string, from: number, domain: readonly [number, number]): number | null {
  const by: Record<string, number> = { ArrowUp: 1, ArrowRight: 1, ArrowDown: -1, ArrowLeft: -1, PageUp: 10, PageDown: -10 };
  if (key === "Home") return domain[0];
  if (key === "End") return domain[1];
  const step = by[key];
  return step === undefined ? null : clamp(from + step, domain);
}

/** The whole number a pointer at `y` (from the plot's top) places, on a plot whose range runs from
 * `top` (the range's high end) to `bottom` (its low end), held inside `axis`. */
export function pointValue(y: number, top: number, bottom: number, domain: readonly [number, number], axis: { min: number; max: number }): number {
  const [low, high] = domain;
  const share = bottom === top ? 0 : (bottom - y) / (bottom - top);
  const value = Math.round(low + share * (high - low));
  return Math.min(axis.max, Math.max(axis.min, value === 0 ? 0 : value));
}

function clamp(value: number, [low, high]: readonly [number, number]): number {
  return Math.min(high, Math.max(low, value));
}
