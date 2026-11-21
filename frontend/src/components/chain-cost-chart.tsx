"use client";

import { useId, useRef, useState } from "react";

import { CostArea, type CostAreaPoint } from "@/components/charts/cost-area";
import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";

const copy = nb.games.play.chain;

/** One Uke of the table alternative, formatted by the caller: the chain's running sums. */
export type ChainCostRow = { week: number; holding: string; backorder: string; total: string };

/** The chart's height in caption lines (about 140 px at 13 px). */
const CHART_LINES = 11;
/** Until the box is measured (a server render): a phone column and the caption size. */
const FALLBACK = { width: 288, fontSize: 13 };

/**
 * Kjedens kostnad over tid (`chain-cost-chart`, Story 6.18, UX-DR30, NFR-6, DESIGN.md,
 * `06-spilldynamikk.png` F): the chain's running cost from Uke 1 to the last Uke as a stacked
 * area, holding cost below and backlog cost above, on a true zero, with the final values labelled
 * at the right end (`CostArea`, the chart module's own). The chart is `aria-hidden`; «Vis som
 * tabell» swaps it in place for Uke / Lager / Restordre / Sum of the chain, and back. Shared with
 * the Debrief (Epic 9); chain level only, never per name.
 */
export function ChainCostChart({
  points,
  rows,
  endLabels,
  className,
}: {
  /** Uke 1 … last Uke, oldest first, in kroner. */
  points: readonly CostAreaPoint[];
  rows: readonly ChainCostRow[];
  endLabels: { holding: string; backorder: string };
  className?: string;
}) {
  const [asTable, setAsTable] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const id = useId();
  const first = points[0]?.week ?? 1;
  const last = points[points.length - 1]?.week ?? first;
  return (
    <section aria-labelledby={`${id}-title`} data-chain-cost-chart="" className={className}>
      <h2 id={`${id}-title`} className="text-headline text-ink">
        {copy.overTime}
      </h2>
      <div ref={box} className="mt-2 text-caption">
        {asTable ? (
          <ChainCostTable id={`${id}-table`} rows={rows} />
        ) : (
          <CostArea
            width={size.width}
            height={Math.round(size.fontSize * CHART_LINES)}
            fontSize={size.fontSize}
            points={points}
            title={copy.chartSvg}
            formatTick={(value) => formatNumber(value)}
            firstLabel={copy.week(first)}
            lastLabel={copy.week(last)}
            endLabels={endLabels}
          />
        )}
      </div>
      <button
        type="button"
        className={LINK_BUTTON}
        data-chain-cost-toggle=""
        aria-expanded={asTable}
        onClick={() => setAsTable((shown) => !shown)}
      >
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </section>
  );
}

function ChainCostTable({ id, rows }: { id: string; rows: readonly ChainCostRow[] }) {
  const cell = "py-1 pl-3 text-right";
  return (
    <table id={id} data-chain-cost-table="" className="w-full border-collapse text-caption text-ink tabular-nums lining-nums">
      <caption className="sr-only">{copy.tableCaption}</caption>
      <thead>
        <tr className="border-b border-axis text-ink-secondary">
          <th scope="col" className="py-1 text-left font-normal">
            {nb.terms.week}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.holding}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.backorder}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.sum}
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.week} className="border-b border-hairline">
            <th scope="row" className="py-1 text-left font-normal">
              {row.week}
            </th>
            <td className={cell}>{row.holding}</td>
            <td className={cell}>{row.backorder}</td>
            <td className={cn(cell, "font-semibold")}>{row.total}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
