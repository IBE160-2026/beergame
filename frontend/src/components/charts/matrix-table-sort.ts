/** A sort direction as `aria-sort` names it. */
export type SortDirection = "ascending" | "descending";

/** The column a table is sorted by, and which way. */
export type TableSort = { key: string; direction: SortDirection };

/** A sortable column: its key and the direction its first activation sorts in. */
export type SortableColumn = { key: string; first: SortDirection };

/**
 * The rows in `sort`'s order (Story 7.3, UX-DR72). Each row gives its own number per column
 * (`keys`), so nothing is read from the printed text (AD-10). A row with no number for the column
 * (a game that waits for nobody, has no cost yet) stays last in both directions, and equal rows
 * keep the order they came in. No sort keeps the order as given.
 */
export function sortRows<R extends { keys: Readonly<Record<string, number | null | undefined>> }>(
  rows: readonly R[],
  sort: TableSort | null,
): R[] {
  if (!sort) return [...rows];
  const sign = sort.direction === "ascending" ? 1 : -1;
  return rows
    .map((row, index) => ({ row, index, key: row.keys[sort.key] }))
    .sort((a, b) => {
      const aMissing = a.key == null;
      const bMissing = b.key == null;
      if (aMissing || bMissing) return aMissing === bMissing ? a.index - b.index : aMissing ? 1 : -1;
      return sign * (a.key! - b.key!) || a.index - b.index;
    })
    .map((entry) => entry.row);
}

/** The sort after a header is activated: its first direction when it is not the sorted column,
 * else the other way. */
export function nextSort(sort: TableSort | null, column: SortableColumn): TableSort {
  if (sort?.key !== column.key) return { key: column.key, direction: column.first };
  return { key: column.key, direction: sort.direction === "ascending" ? "descending" : "ascending" };
}

/** The game an Up or Down key moves to from `id` among `ids` in their drawn order: the one above or
 * below, the same at an edge; null for any other key. */
export function nextRow(ids: readonly string[], id: string, key: string): string | null {
  if (key !== "ArrowUp" && key !== "ArrowDown") return null;
  const index = ids.indexOf(id);
  if (index < 0) return null;
  return ids[Math.min(ids.length - 1, Math.max(0, index + (key === "ArrowUp" ? -1 : 1)))] ?? null;
}

/**
 * The row order while keyboard focus is inside the table (EXPERIENCE.md → Oppdater automatisk):
 * rows stay where they were, values update in place, a row that left is dropped and a new one is
 * added at the end in `sorted`'s order.
 */
export function keepOrder<R extends { id: string }>(previous: readonly string[], sorted: readonly R[]): R[] {
  const byId = new Map(sorted.map((row) => [row.id, row]));
  const kept = previous.flatMap((id) => {
    const row = byId.get(id);
    return row ? [row] : [];
  });
  const seen = new Set(previous);
  return [...kept, ...sorted.filter((row) => !seen.has(row.id))];
}
