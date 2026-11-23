/**
 * An Interaktiv oppgave's answer as it is shown (Stories 11.5 and 11.14, FR-80, UX-DR38): the values
 * a table answer holds, a number answer's value, the graph's range and where an unanswered Uke's
 * point sits. Display only: the api scores the stored values (AD-1). Moved here from the test's
 * module in Story 13.10, because the Student report draws the same answer.
 */

/** A table answer as one value or null per row, whatever was stored (a missing answer, one of
 * another shape). */
export function tableValues(value: unknown, rows: number): (number | null)[] {
  const cells = Array.isArray(value) ? value : [];
  return Array.from({ length: rows }, (_, i) => {
    const cell: unknown = cells[i];
    return typeof cell === "number" ? cell : null;
  });
}

/** A number answer's value, or null. */
export function numberValue(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

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

export function clamp(value: number, [low, high]: readonly [number, number]): number {
  return Math.min(high, Math.max(low, value));
}

/** A table item's graph axis: its own (a drawn item), else one that holds 0 and the given and
 * answered values (a «Fyll inn kolonnen» item has none; the report still draws its answer). */
export function answerAxis(
  axis: { min: number; max: number } | null | undefined,
  columns: readonly { values: readonly number[] }[],
): { min: number; max: number } {
  if (axis) return axis;
  const given = columns.flatMap((column) => column.values);
  return { min: Math.min(0, ...given), max: Math.max(10, ...given) };
}
