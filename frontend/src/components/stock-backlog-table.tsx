"use client";

import { type ReactNode } from "react";

import { StockBacklog, StockBacklogLabels, type StockBacklogMost, type StockBacklogRow } from "@/components/charts/stock-backlog";
import { fixedCell, type FixedLayout, type GraphColumn, type GraphField, GraphOverTable } from "@/components/graph-over-table";

/** One Role, as the api gave it: its stored inventory and backlog per Uke. */
export type StockBacklogRole = {
  key: string;
  /** «Fabrikk». */
  name: string;
  weeks: readonly { week: number; inventory: number; backlog: number }[];
};

/** One week column, as the Ordrestolper's (`order-bars-table.tsx`), so the two charts line up. */
const WEEK_COL = "w-[1.6em] min-w-[1.6em] px-[0.1em] text-center lg:w-[1.65em] lg:min-w-[1.65em]";
const ROW_LABEL =
  "sticky left-0 z-10 min-w-row-label-phone bg-paper pr-2 text-left align-middle font-normal text-ink lg:min-w-row-label-laptop";
/** Four bands, each about five lines of `caption` high: bars, and a line above and below them for
 * the band's direct labels (its largest stock and largest backlog). */
const HEIGHT_EM = 20;

/**
 * «Lager og restordre» over its Uke header (Story 7.8, Spillinnsikt, FR-62, AD-18): one Graf over
 * tabell region whose field is `StockBacklog`, a band per Role in the order given (Fabrikk
 * first) with the Role names in the sticky label column, and the Uke numbers under it. The region
 * scrolls sideways on its own. The numbers are the caller's «Vis som tabell» (NFR-6); every
 * number is the api's.
 */
export function StockBacklogTable({
  label,
  roles,
  caption,
  texts,
  fixed,
  most,
  rows: tableRows,
}: {
  /** The scroll region's accessible name. */
  label: string;
  roles: readonly StockBacklogRole[];
  /** The line over the bars (a key); read by screen readers. */
  caption?: ReactNode;
  texts: { week: string; svg: string; axisSvg: string; swipe: string };
  /** Every width in px, for the server-rendered print page (the Student report, Story 13.8). */
  fixed?: FixedLayout;
  /** The game's largest stock and backlog when it is drawn in several blocks of Uker. */
  most?: StockBacklogMost;
  /** Table rows under the bands on the same columns (the Student report has no «Vis som tabell»):
   * a label and one printed cell per Uke. Left out, the caller gives the table elsewhere. */
  rows?: readonly { key: string; label: string; cells: readonly string[] }[];
}) {
  const weekCell = fixedCell(fixed, "week");
  const labelCell = fixedCell(fixed, "label");
  const weeks = [...new Set(roles.flatMap((role) => role.weeks.map((w) => w.week)))].sort((a, b) => a - b);
  const columns: GraphColumn[] = weeks.map((week) => ({ week, when: "past", phone: true }));
  const byWeek = roles.map((role) => new Map(role.weeks.map((w) => [w.week, w])));
  const field: GraphField = {
    key: "stock",
    caption,
    heightEm: HEIGHT_EM,
    render: (size) => {
      const rows: StockBacklogRow[] = roles.map((_, r) => ({
        stock: size.columns.map((column) => byWeek[r]!.get(column.week)?.inventory ?? null),
        backlog: size.columns.map((column) => byWeek[r]!.get(column.week)?.backlog ?? null),
      }));
      return {
        plot: (
          <StockBacklog
            width={size.width}
            height={size.height}
            xs={size.xs}
            columnWidth={size.columnWidth}
            rows={rows}
            title={texts.svg}
            fontSize={size.fontSize}
            most={most}
          />
        ),
        axis: (
          <StockBacklogLabels
            width={size.labelWidth}
            height={size.height}
            fontSize={size.fontSize}
            labels={roles.map((role) => role.name)}
            rows={rows}
            title={texts.axisSvg}
          />
        ),
      };
    },
  };
  return (
    <GraphOverTable
      label={label}
      columns={columns}
      fields={[field]}
      swipe={fixed ? undefined : texts.swipe}
      fixed={fixed}
      head={
        <tr className="border-b border-axis">
          <th scope="row" className={ROW_LABEL} style={labelCell}>
            {texts.week}
          </th>
          {weeks.map((week) => (
            <th
              key={week}
              scope="col"
              data-col={week}
              style={weekCell}
              className={`${WEEK_COL} h-row-phone font-normal text-ink-muted lg:h-row-laptop`}
            >
              <span className="sr-only">{texts.week} </span>
              {week}
            </th>
          ))}
        </tr>
      }
      body={
        tableRows
          ? tableRows.map((row) => (
              <tr key={row.key} data-row={row.key} className="border-b border-hairline">
                <th scope="row" className={ROW_LABEL} style={labelCell}>
                  {row.label}
                </th>
                {row.cells.map((cell, i) => (
                  <td key={weeks[i]} style={weekCell} className={`${WEEK_COL} h-row-phone lg:h-row-laptop`}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          : null
      }
    />
  );
}
