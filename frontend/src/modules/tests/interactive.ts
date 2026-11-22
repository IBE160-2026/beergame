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
  if (item.type === "table") return item.table !== null;
  if (item.type === "number") return item.column !== null && !item.column.starting_task;
  return false;
}
