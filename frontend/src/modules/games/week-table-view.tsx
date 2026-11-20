"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import type { SeatState } from "./api";
import { type Cell, cellFor, type Column, type NetStep, ROWS, weekColumns } from "./week-table";

const copy = nb.games.play.table;

/** Matrix-step fills with their text token: `ink` on steps 1–2, `paper` on 3–4 (DESIGN.md). */
const NET_FILL: Record<NetStep, string> = {
  zero: "bg-net-zero text-ink",
  "pos-1": "bg-net-pos-1 text-ink",
  "pos-2": "bg-net-pos-2 text-ink",
  "pos-3": "bg-net-pos-3 text-paper",
  "pos-4": "bg-net-pos-4 text-paper",
  "neg-1": "bg-net-neg-1 text-ink",
  "neg-2": "bg-net-neg-2 text-ink",
  "neg-3": "bg-net-neg-3 text-paper",
  "neg-4": "bg-net-neg-4 text-paper",
};

// 1.6 em, so 12 columns fit at 360 px; a column whose number is wider grows to it plus a small
// side gap, so neighbouring numbers («−14», «−20», «27,5») never run together (DESIGN.md → Graf
// over tabell at narrow widths).
const WEEK_COL = "w-[1.6em] min-w-[1.6em] px-[0.1em] text-center";
/** Netto lager cells stand apart as separate squares, as drawn (`05-spill.png`). */
const NET_CELL = "shadow-[inset_0_0_0_1px_var(--color-paper)]";
const ROW_LABEL =
  "sticky left-0 z-10 min-w-row-label-phone bg-paper pr-2 text-left align-middle font-normal text-ink lg:min-w-row-label-laptop";

/** A column's visibility and tint: earlier than nå − 7 only in the laptop layout; right of nå on
 * `future-tint`. */
function columnClass(column: Column) {
  return cn(!column.phone && "hidden lg:table-cell", column.when === "future" && "bg-future-tint");
}

/**
 * The week table (Story 6.6, FR-23, UX-DR17, UX-DR18): the Seat's Uker as columns up to nå + 4,
 * never the end of the game. One scroll region named «Graf og tabell» holds it, with sticky row
 * labels; on load and when the Uke changes it scrolls so that nå and as many of nå + 1 … nå + 4 as
 * fit are in view. «Sveip for tidligere uker» shows while earlier Uker are scrolled out of view.
 * The cells take no focus; the region does, so arrow keys scroll it.
 */
export function WeekTable({ state }: { state: SeatState }) {
  const region = useRef<HTMLDivElement>(null);
  const [earlierHidden, setEarlierHidden] = useState(false);
  const columns = weekColumns(state.week);

  const update = useCallback(() => {
    const element = region.current;
    if (element) setEarlierHidden(element.scrollLeft > 1);
  }, []);

  // Bring nå into view: nå at the left edge of the scrolled area, or as far right as the region
  // goes, whichever is less, so nå + 4 is the right edge whenever all columns from nå fit.
  const toNow = useCallback(() => {
    const element = region.current;
    const now = element?.querySelector<HTMLElement>("[data-now]");
    const label = element?.querySelector<HTMLElement>("th[scope=row]");
    if (!element || !now || !label) return;
    const offset = now.getBoundingClientRect().left - element.getBoundingClientRect().left + element.scrollLeft;
    const target = offset - label.getBoundingClientRect().width;
    element.scrollLeft = Math.max(0, Math.min(target, element.scrollWidth - element.clientWidth));
    update();
  }, [update]);

  useLayoutEffect(() => {
    toNow();
  }, [toNow, state.week]);

  useLayoutEffect(() => {
    const element = region.current;
    if (!element) return;
    // A changed layout (rotation, the laptop breakpoint, larger text) brings nå back into view.
    let size = `${element.clientWidth}x${element.scrollWidth}`;
    const observer = new ResizeObserver(() => {
      const now = `${element.clientWidth}x${element.scrollWidth}`;
      if (now !== size) {
        size = now;
        toNow();
      }
    });
    observer.observe(element);
    if (element.firstElementChild) observer.observe(element.firstElementChild);
    return () => observer.disconnect();
  }, [toNow]);

  return (
    <div className="-mx-[calc(var(--spacing-gutter-phone)-var(--spacing-gutter-phone-chart))] lg:mx-0">
      {/* `relative` keeps the screen-reader-only labels (absolutely placed) inside the scroll area. */}
      <div
        ref={region}
        role="region"
        aria-label={copy.region}
        tabIndex={0}
        onScroll={update}
        className="relative overflow-x-auto pb-1 [scrollbar-color:var(--color-ink-muted)_var(--color-hairline)] [scrollbar-width:thin] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <table className="border-collapse text-table-cell text-ink tabular-nums lining-nums lg:text-table-cell-laptop">
          <thead>
            <tr className="border-b border-axis">
              <th scope="row" className={ROW_LABEL}>
                {nb.terms.week}
              </th>
              {columns.map((column) => (
                <th
                  key={column.week}
                  scope="col"
                  data-now={column.when === "now" ? "" : undefined}
                  className={cn(
                    WEEK_COL,
                    "h-row-phone lg:h-row-laptop",
                    column.when === "now" ? "font-bold" : "font-normal",
                    columnClass(column),
                  )}
                >
                  <span className="sr-only">{nb.terms.week} </span>
                  {column.week}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.key} data-row={row.key} className={cn("border-b border-hairline", row.laptopOnly && "hidden lg:table-row")}>
                <th scope="row" className={ROW_LABEL}>
                  {row.label}
                </th>
                {columns.map((column) => (
                  <WeekCell key={column.week} column={column} cell={cellFor(state, row.key, column.week)} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap justify-between gap-x-4 px-[calc(var(--spacing-gutter-phone)-var(--spacing-gutter-phone-chart))] lg:px-0">
        <p className="mt-1 text-caption text-ink-secondary">
          <span aria-hidden="true" className="mr-1 inline-block h-[0.9em] w-[1.2em] border border-ink align-[-0.1em]" />
          {copy.arrivalKey}
        </p>
        {earlierHidden ? <p className="mt-1 text-caption text-ink-secondary">{copy.swipe}</p> : null}
      </div>
    </div>
  );
}

function WeekCell({ column, cell }: { column: Column; cell: Cell }) {
  const base = cn(WEEK_COL, "h-row-phone lg:h-row-laptop", columnClass(column));
  switch (cell.kind) {
    case "net":
      return <td className={cn(base, NET_CELL, NET_FILL[cell.step])}>{cell.text}</td>;
    case "plain":
      return <td className={base}>{cell.text}</td>;
    case "arrival":
      return (
        <td className={base}>
          <span className="inline-block min-w-[1.3em] border border-ink leading-tight">{cell.text}</span>
          <span className="sr-only">, {copy.arrival}</span>
        </td>
      );
    case "order-empty":
      return (
        <td className={base}>
          <span aria-hidden="true" className="mx-auto block h-[1.1em] w-[1.3em] border border-dashed border-ink-muted" />
          <span className="sr-only">{copy.noOrderYet}</span>
        </td>
      );
    default:
      return <td className={base} />;
  }
}
