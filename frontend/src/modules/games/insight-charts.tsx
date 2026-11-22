"use client";

import { type ReactNode, useId, useState } from "react";

import { LINK_BUTTON } from "@/components/link";
import { OrderBarsTable } from "@/components/order-bars-table";
import { ScrollRegion } from "@/components/scroll-region";
import { StockBacklogTable } from "@/components/stock-backlog-table";
import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import type { GameInsight } from "./api";
import { type ChartTableRow, chartWeeks, orderRoles, orderTableRows, stockRoles, stockTableRows } from "./insight";

const copy = nb.insight.charts;

/**
 * Spillinnsikt's charts (Story 7.8, FR-62, UX-DR33, UX-DR55): «Ordre», the shared Ordrestolper over
 * the Rolle × Uke Orders with the customers' demand as the bottom row, and «Lager og restordre»,
 * both Fabrikk at the top and each with «Vis som tabell» under it. Every number is the insight
 * endpoint's (AD-10); the charts follow the page's query, so a running game's new Week appears on
 * `game:<id>`. Staff have no own Role, so `ownRole` stays unset.
 */
export function InsightCharts({ data }: { data: GameInsight }) {
  const id = useId();
  const weeks = chartWeeks(data);
  return (
    <section aria-labelledby={id} className="mt-10" data-insight-charts="">
      <h2 id={id} className="text-headline text-ink">
        {copy.title}
      </h2>
      <ChartBlock
        kind="orders"
        title={copy.orders.title}
        chart={
          <OrderBarsTable
            label={copy.orders.region}
            roles={orderRoles(data)}
            caption={copy.orders.key}
            texts={{
              week: copy.week,
              weekLabel: copy.weekLabel,
              amplification: copy.orders.amplification,
              own: copy.orders.own,
              none: copy.orders.none,
              svg: copy.orders.svg,
              axisSvg: copy.axisSvg,
              swipe: copy.swipe,
            }}
          />
        }
        table={<ChartTable label={copy.orders.tableRegion} weeks={weeks} rows={orderTableRows(data)} />}
      />
      <ChartBlock
        kind="stock"
        title={copy.stock.title}
        chart={
          <StockBacklogTable
            label={copy.stock.region}
            roles={stockRoles(data)}
            caption={copy.stock.key}
            texts={{ week: copy.week, svg: copy.stock.svg, axisSvg: copy.axisSvg, swipe: copy.swipe }}
          />
        }
        table={<ChartTable label={copy.stock.tableRegion} weeks={weeks} rows={stockTableRows(data)} />}
      />
    </section>
  );
}

/** One chart with «Vis som tabell» under it, swapping it in place for its table and back; the
 * button stays the same element, so focus stays on it. */
function ChartBlock({ kind, title, chart, table }: { kind: string; title: string; chart: ReactNode; table: ReactNode }) {
  const id = useId();
  const [asTable, setAsTable] = useState(false);
  return (
    <section aria-labelledby={id} className="mt-6" data-chart-block={kind} data-view={asTable ? "table" : "chart"}>
      <h3 id={id} className="text-label text-ink">
        {title}
      </h3>
      <div className="mt-2">{asTable ? table : chart}</div>
      {/* Both charts' buttons read alike: each is described by its chart's heading. */}
      <button type="button" aria-describedby={id} className={cn(LINK_BUTTON, "mt-1")} onClick={() => setAsTable((was) => !was)}>
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </section>
  );
}

const CELL = "border-b border-hairline px-[0.4em] py-[0.35em] text-right whitespace-nowrap";
/** Every Uke column the same width, so the numbers line up from row to row and between the two tables. */
const WEEK_CELL = "min-w-[2.75em]";

/** A chart's «Vis som tabell»: a Rolle × Uke table, every cell printing its number (NFR-6), in its
 * own sideways-scrolling region with the row labels sticky. */
function ChartTable({ label, weeks, rows }: { label: string; weeks: readonly number[]; rows: readonly ChartTableRow[] }) {
  const id = useId();
  return (
    <ScrollRegion labelledBy={id}>
      <table className="border-separate border-spacing-0 text-table-cell text-ink tabular-nums lining-nums lg:text-table-cell-laptop">
        <caption id={id} className="sr-only">
          {label}
        </caption>
        <thead>
          <tr>
            <th scope="col" className={cn(CELL, "sticky left-0 z-10 bg-paper text-left font-normal text-ink-secondary")}>
              {copy.week}
            </th>
            {weeks.map((week) => (
              <th key={week} scope="col" className={cn(CELL, WEEK_CELL, "font-normal text-ink-secondary")}>
                {week}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} data-row={row.key}>
              <th scope="row" className={cn(CELL, "sticky left-0 z-10 bg-paper text-left font-normal")}>
                {row.label}
              </th>
              {row.cells.map((cell, i) => (
                <td key={weeks[i]} className={cn(CELL, WEEK_CELL)}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollRegion>
  );
}
