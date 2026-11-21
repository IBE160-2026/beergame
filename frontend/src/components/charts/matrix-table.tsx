"use client";

import { type KeyboardEvent, useEffect, useLayoutEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

import { keepOrder, nextRow, nextSort, type SortDirection, sortRows, type TableSort } from "./matrix-table-sort";

/** One Class game in «Vis som tabell»: the same values as its Matrisevegg row (AD-10). */
export type TableRow = {
  id: string;
  /** The row header, «Spill 2». */
  label: string;
  /** The printed text of each extra column, by column key («Venter», «1 058»). */
  cells: Readonly<Record<string, string>>;
  /** The number each sortable column sorts by, by column key; null or absent sorts last. */
  keys: Readonly<Record<string, number | null | undefined>>;
  /** Uke 1 … the last Uke the game has. */
  values: readonly number[];
  /** The values are on their way: a Skjelett bar stands in the Uke cells. */
  loading?: boolean;
};

/** A column between the game column and the Uker. It is sortable when `first` is given. */
export type TableColumn = {
  key: string;
  header: string;
  align?: "start" | "end";
  first?: SortDirection;
};

/** A row under the games («Median, Fabrikk»), in the table's foot: never sorted, one printed
 * value per Uke (empty where there is none). */
export type TableFooterRow = { key: string; label: string; values: readonly (string | null)[] };

export type MatrixTableCopy = {
  /** The region's name, «Alle spill», the same as the wall's. */
  region: string;
  /** The table's caption (read, not shown): the wall's title. */
  caption: string;
  /** The game column's header, «Spill». */
  gameHeader: string;
  /** Read before each Uke number in the header, «Uke». */
  week: string;
};

/** The game column's key in `TableRow.keys` and in the sort. */
export const GAME_COLUMN = "game";

export type MatrixTableProps = {
  rows: readonly TableRow[];
  columns: readonly TableColumn[];
  copy: MatrixTableCopy;
  /** Formats a cell's number («−13»): the one Norwegian number formatter. */
  format: (value: number) => string;
  /** The game column sorts when given its first direction. */
  gameFirst?: SortDirection;
  /** The sort the table opens with; none keeps the rows as given. */
  initialSort?: TableSort | null;
  /** The sort, when the caller keeps it (so it outlasts a switch to the wall and back). */
  sort?: TableSort | null;
  onSort?: (sort: TableSort) => void;
  /** The game that holds the table's one Tab stop, shared with the wall (focus by Game id). */
  focusId?: string | null;
  onFocusId?: (id: string) => void;
  /** The class median rows under the games, from the api (Story 7.4). */
  footer?: readonly TableFooterRow[];
  maxHeight?: string;
  className?: string;
};

const CELL = "border-b border-hairline px-[0.5em] align-middle";
/** Uke columns of one width, so the numbers stand in even columns («−13» fits). */
const WEEK = "min-w-[2.75em]";
const ROW_HEAD = "sticky left-0 z-10 bg-paper text-left whitespace-nowrap";
const FOCUS_RING =
  "outline-none focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 focus-visible:outline-ink focus-visible:shadow-[inset_0_0_0_3px_var(--color-paper)]";

/**
 * «Vis som tabell» (Story 7.3, UX-DR42, NFR-6): the Matrisevegg's rows as an HTML table with a
 * printed signed number in every cell at `table-cell` size (13 px, 15 px on laptop), never
 * shrunk. Row headers (`th scope="row"`) and Uke headers (`th scope="col"`) give each cell its game
 * and Uke. It scrolls in its own region named as the wall's, with the game column and the header
 * row sticky. Headers the caller makes sortable sort by the numbers the caller gives
 * (`aria-sort`); nothing is computed here (AD-10). Reused by «Vis i plenum» (Epic 14) without the
 * cost column.
 *
 * Keyboard: one row header is in the Tab order (the game in `focusId`, else the first); Up and
 * Down move between games. While focus is inside the table the rows keep their places and their
 * values update in place; they re-sort when focus leaves or a header is activated.
 */
export function MatrixTable({
  rows,
  columns,
  copy,
  format,
  gameFirst,
  initialSort = null,
  sort: sortProp,
  onSort,
  focusId,
  onFocusId,
  footer = [],
  maxHeight = "70vh",
  className,
}: MatrixTableProps) {
  const body = useRef<HTMLTableSectionElement>(null);
  const rowFocused = useRef(false);
  const [ownSort, setOwnSort] = useState<TableSort | null>(initialSort);
  const sort = sortProp !== undefined ? sortProp : ownSort;
  const sortBy = (column: { key: string; first: SortDirection }) => {
    const next = nextSort(sort, column);
    setOwnSort(next);
    onSort?.(next);
  };
  const [inside, setInside] = useState(false);
  const [ownFocus, setOwnFocus] = useState<string | null>(null);
  const lastOrder = useRef<string[]>([]);
  const lastSort = useRef<TableSort | null>(sort);

  const sorted = sortRows(rows, sort);
  const ordered = inside && lastSort.current === sort ? keepOrder(lastOrder.current, sorted) : sorted;
  useEffect(() => {
    lastOrder.current = ordered.map((row) => row.id);
    lastSort.current = sort;
  });

  const wanted = focusId !== undefined ? focusId : ownFocus;
  const target = ordered.find((row) => row.id === wanted)?.id ?? ordered[0]?.id ?? null;
  const columnsCount = Math.max(
    rows.reduce((most, row) => Math.max(most, row.values.length), 0),
    ...footer.map((row) => row.values.length),
  );

  const headerOf = (id: string | null) =>
    id ? body.current?.querySelector<HTMLTableCellElement>(`th[data-game="${CSS.escape(id)}"]`) : null;
  const choose = (id: string) => {
    setOwnFocus(id);
    onFocusId?.(id);
  };

  // A row moved or re-sorted while its header had focus: put focus back on the same game.
  useLayoutEffect(() => {
    if (!rowFocused.current || !target) return;
    const element = headerOf(target);
    if (element && document.activeElement !== element) element.focus({ preventScroll: true });
  });

  const onKeyDown = (event: KeyboardEvent<HTMLTableSectionElement>) => {
    if (!target || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const next = nextRow(
      ordered.map((row) => row.id),
      target,
      event.key,
    );
    if (!next) return;
    event.preventDefault();
    choose(next);
    headerOf(next)?.focus();
  };

  const header = (key: string, text: string, first: SortDirection | undefined, align: "start" | "end", sticky: boolean) => {
    const active = sort?.key === key ? sort.direction : undefined;
    return (
      <th
        key={key}
        scope="col"
        aria-sort={active}
        data-column={key}
        className={cn(
          CELL,
          "sticky top-0 bg-paper font-normal whitespace-nowrap text-ink-secondary",
          sticky ? "left-0 z-30" : "z-20",
          align === "end" ? "text-right" : "text-left",
        )}
      >
        {first ? (
          <button
            type="button"
            onClick={() => sortBy({ key, first })}
            className={cn(
              "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center gap-1 whitespace-nowrap text-inherit hover:text-ink hover:underline",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
              active && "font-semibold text-ink underline",
            )}
          >
            {text}
            {active ? <span aria-hidden="true">{active === "ascending" ? "↑" : "↓"}</span> : null}
          </button>
        ) : (
          text
        )}
      </th>
    );
  };

  return (
    <div
      role="region"
      aria-label={copy.region}
      tabIndex={0}
      style={{ maxHeight }}
      onFocus={() => setInside(true)}
      onBlur={(event) => {
        // A header taken out of the DOM while its row moves keeps the table's focus.
        if (!(event.target as Node).isConnected) return;
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setInside(false);
      }}
      className={cn(
        "mt-3 overflow-auto overscroll-contain focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        className,
      )}
      data-matrix-table=""
    >
      <table className="min-w-full border-separate border-spacing-0 text-table-cell text-ink tabular-nums lining-nums lg:text-table-cell-laptop">
        <caption className="sr-only">{copy.caption}</caption>
        <thead>
          <tr>
            {header(GAME_COLUMN, copy.gameHeader, gameFirst, "start", true)}
            {columns.map((column) => header(column.key, column.header, column.first, column.align ?? "start", false))}
            {Array.from({ length: columnsCount }, (_, i) => (
              <th
                key={`week-${i + 1}`}
                scope="col"
                className={cn(CELL, WEEK, "sticky top-0 z-20 bg-paper text-right font-normal text-ink-secondary")}
              >
                <span className="sr-only">{copy.week} </span>
                {i + 1}
              </th>
            ))}
          </tr>
        </thead>
        <tbody ref={body} onKeyDown={onKeyDown}>
          {ordered.map((row) => (
            <tr key={row.id} data-row={row.id}>
              <th
                scope="row"
                data-game={row.id}
                tabIndex={row.id === target ? 0 : -1}
                onFocus={() => {
                  rowFocused.current = true;
                  if (row.id !== target) choose(row.id);
                }}
                onBlur={(event) => {
                  if (!event.currentTarget.isConnected) return;
                  const next = event.relatedTarget as Element | null;
                  if (!next?.closest?.("th[data-game]")) rowFocused.current = false;
                }}
                className={cn(CELL, ROW_HEAD, "font-normal", FOCUS_RING)}
              >
                {row.label}
              </th>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cn(CELL, "whitespace-nowrap", column.align === "end" ? "text-right" : "text-left")}
                >
                  {row.cells[column.key] ?? ""}
                </td>
              ))}
              {row.loading && row.values.length === 0 && columnsCount > 0 ? (
                <td colSpan={columnsCount} className={CELL}>
                  <div aria-hidden="true" data-skeleton="" className="h-[0.8em] w-[8em] max-w-full bg-hairline" />
                </td>
              ) : (
                Array.from({ length: columnsCount }, (_, i) => {
                  const value = row.values[i];
                  return (
                    <td key={i} data-week={i + 1} className={cn(CELL, WEEK, "text-right whitespace-nowrap")}>
                      {value === undefined ? "" : format(value)}
                    </td>
                  );
                })
              )}
            </tr>
          ))}
        </tbody>
        {footer.length > 0 ? (
          <tfoot>
            {footer.map((row, index) => (
              <tr key={row.key} data-summary={row.key}>
                <th
                  scope="row"
                  className={cn(CELL, ROW_HEAD, "font-semibold", index === 0 && "border-t border-t-axis")}
                >
                  {row.label}
                </th>
                {columns.map((column) => (
                  <td key={column.key} className={cn(CELL, index === 0 && "border-t border-t-axis")} />
                ))}
                {Array.from({ length: columnsCount }, (_, i) => (
                  <td
                    key={i}
                    data-week={i + 1}
                    className={cn(CELL, WEEK, "text-right whitespace-nowrap", index === 0 && "border-t border-t-axis")}
                  >
                    {row.values[i] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}
