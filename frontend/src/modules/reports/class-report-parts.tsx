"use client";

import { type ReactNode, useId, useRef, useState } from "react";

import { CostDistribution } from "@/components/charts/cost-distribution";
import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";

import type { ReportDistribution } from "./class-report-api";

/**
 * The Klasserapport's building blocks (Stories 14.1 and 14.2, UX-DR55): a titled section, a chart
 * with «Vis som tabell» under it, the table, a row of `aria-hidden` bars and a Kostnadsfordeling
 * sized to its own box. They format and lay out only; every number is the api's (AD-10).
 */
const copy = nb.classReport;

/** Until a chart's box is measured (a server render): a laptop column and the caption size. */
export const FALLBACK = { width: 480, fontSize: 13 };

export const TEXT = "text-body-phone text-ink lg:text-body";
export const SECONDARY = "text-body-phone text-ink-secondary lg:text-body";
export const CELL = "py-1.5 tabular-nums lining-nums";
export const REGION = "mt-2 max-w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink";

/** A titled section; `level` 3 for a section under another heading (the learning part). */
export function Section({
  title,
  name,
  intro,
  level = 2,
  children,
}: {
  title: string;
  name: string;
  intro?: string;
  level?: 2 | 3;
  children: ReactNode;
}) {
  const id = useId();
  const Heading = level === 2 ? "h2" : "h3";
  return (
    <section aria-labelledby={id} className="min-w-0" data-report-section={name}>
      <Heading id={id} className="text-headline text-ink">
        {title}
      </Heading>
      {intro ? <p className={`mt-1 ${SECONDARY}`}>{intro}</p> : null}
      {children}
    </section>
  );
}

/** A chart with «Vis som tabell» under it (UX-DR55): the button swaps the chart for its table. */
export function Toggled({ chart, table, name }: { chart: ReactNode; table: ReactNode; name: string }) {
  const [asTable, setAsTable] = useState(false);
  return (
    <div className="mt-3" data-toggled={name}>
      {asTable ? table : chart}
      <button
        type="button"
        className={LINK_BUTTON}
        data-table-toggle={name}
        onClick={() => setAsTable((shown) => !shown)}
      >
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </div>
  );
}

export function Table({
  caption,
  columns,
  rows,
  name,
}: {
  caption: string;
  columns: readonly string[];
  rows: readonly { key: string; head: string; cells: readonly string[] }[];
  name: string;
}) {
  const id = useId();
  return (
    <div role="region" aria-labelledby={id} tabIndex={0} className={REGION}>
      <table className="w-full border-collapse text-left text-caption text-ink" data-report-table={name}>
        <caption id={id} className="mb-1 text-left text-caption text-ink-secondary">
          {caption}
        </caption>
        <thead>
          <tr className="border-b border-axis">
            {columns.map((column, i) => (
              <th key={column} scope="col" className={`py-1.5 font-semibold ${i === 0 ? "pr-4 text-left" : "px-2 text-right"}`}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b border-hairline">
              <th scope="row" className={`${CELL} pr-4 text-left font-normal whitespace-nowrap`}>
                {row.head}
              </th>
              {row.cells.map((cell, i) => (
                <td key={i} className={`${CELL} px-2 text-right whitespace-nowrap`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A row of `aria-hidden` bars beside its label and count (the Trakt's form), the text in `reads`. */
export function Bars({
  rows,
  name,
  colour,
}: {
  rows: readonly { key: string; label: string; count: string; share: number; reads: string }[];
  name: string;
  colour: string;
}) {
  return (
    <ol className="mt-1" data-bars={name}>
      {rows.map((row) => (
        <li key={row.key} className="grid grid-cols-[minmax(0,1fr)_3rem_minmax(4rem,1fr)] items-center lg:grid-cols-[minmax(0,min(12rem,40%))_3.5rem_minmax(4rem,1fr)] gap-x-3 py-0.5 text-body-phone lg:text-body">
          <span className="sr-only">{row.reads}</span>
          <span aria-hidden="true" className="[overflow-wrap:anywhere]">
            {row.label}
          </span>
          <span aria-hidden="true" className="text-right font-semibold tabular-nums lining-nums">
            {row.count}
          </span>
          <span aria-hidden="true" className="flex h-3 min-w-0">
            {/* Drawn as a top border, so the bar is no text background. */}
            <span className={`block h-0 border-t-[0.75rem] ${colour}`} style={{ width: `${(row.share * 100).toFixed(2)}%` }} />
          </span>
        </li>
      ))}
    </ol>
  );
}

/** A Kostnadsfordeling sized to its own box (AD-18: the chart takes fixed sizes from its caller). */
export function Distribution({
  spread,
  title,
  medianLabel,
  formatTick,
  highest,
  name,
  previous,
  previousLabel,
}: {
  spread: ReportDistribution;
  title: string;
  medianLabel: string;
  formatTick: (value: number) => string;
  highest?: number;
  name: string;
  /** Story 14.3: «Fjoråret», the previous Class session's stored median, and its label. */
  previous?: number | null;
  previousLabel?: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  return (
    <div ref={box} className="min-w-0 text-caption" data-distribution={name}>
      <CostDistribution
        width={size.width}
        fontSize={size.fontSize}
        values={spread.values.map(Number)}
        median={Number(spread.median)}
        lower={Number(spread.lower_quartile)}
        upper={Number(spread.upper_quartile)}
        medianLabel={medianLabel}
        title={title}
        formatTick={formatTick}
        highest={highest}
        previous={previous}
        previousLabel={previousLabel}
      />
    </div>
  );
}
