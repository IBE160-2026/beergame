"use client";

import { type CSSProperties, type ReactNode, useId, useState } from "react";

import { LINK_BUTTON } from "@/components/link";
import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";
import { levelName } from "@/modules/admin/ai-models";

import type { ErrorHour, Operations } from "./api";
import {
  barPercent,
  fallbackName,
  hourAxis,
  hourText,
  hourTotal,
  msText,
  shareText,
  SOURCE_FILL,
  SOURCES,
  sourceName,
} from "./operations";

const copy = nb.admin.operations;

const TABLE =
  "w-full max-w-2xl border-collapse text-left text-table-cell tabular-nums lining-nums text-ink lg:text-table-cell-laptop";
const HEAD = "border-b border-axis py-2 pr-4 align-bottom text-label font-semibold text-ink";
const CELL = "border-b border-hairline py-1.5 pr-4";
const NUM = "text-right";

/** A chart's table in its own sideways-scrolling region, named by its caption, so a wide table
 * never scrolls the page at 320 px. */
function TableRegion({ caption, children }: { caption: string; children: ReactNode }) {
  const id = useId();
  return (
    <ScrollRegion labelledBy={id}>
      <table className={TABLE}>
        <caption id={id} className="sr-only">
          {caption}
        </caption>
        {children}
      </table>
    </ScrollRegion>
  );
}

/** One chart with «Vis som tabell» under it, swapping it in place for its table and back; the
 * button stays the same element, so focus stays on it (as Spillinnsikt's, Story 7.8). */
export function ChartBlock({
  kind,
  title,
  lead,
  chart,
  table,
}: {
  kind: string;
  title: string;
  lead?: ReactNode;
  chart: ReactNode;
  table: ReactNode;
}) {
  const id = useId();
  const [asTable, setAsTable] = useState(false);
  return (
    <section aria-labelledby={id} className="mt-10" data-chart-block={kind} data-view={asTable ? "table" : "chart"}>
      <h2 id={id} className="text-headline text-ink">
        {title}
      </h2>
      {lead ? <div className="mt-2 mb-4 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{lead}</div> : null}
      <div>{asTable ? table : chart}</div>
      <button
        type="button"
        aria-describedby={id}
        className={cn(LINK_BUTTON, "mt-1")}
        onClick={() => setAsTable((was) => !was)}
      >
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </section>
  );
}

/** A filled box in a theme colour: SVG, as the registration bar draws its parts (Story 4.5), so
 * a fill is never taken for a text background. */
function Fill({ colour, className, style }: { colour: string; className?: string; style?: CSSProperties }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 1 1" preserveAspectRatio="none" className={className} style={style}>
      <rect width={1} height={1} fill={colour} />
    </svg>
  );
}

function Key({ fill, label }: { fill: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Fill colour={fill} className="block size-3 shrink-0" />
      {label}
    </span>
  );
}

/** «Feil per time»: one column per hour, the sources stacked (Bokføringskontroll at the bottom),
 * over an `axis` baseline, with `hairline` gridlines and their counts at round steps up to a top at
 * or over the busiest hour. The columns are `aria-hidden`: the counts in the section's lead and
 * «Vis som tabell» (every hour by source) carry the numbers. */
export function ErrorHoursChart({ hours }: { hours: readonly ErrorHour[] }) {
  const { top, ticks } = hourAxis(hours);
  const at = (value: number) => barPercent(value, top);
  return (
    <div className="max-w-2xl">
      <p className="flex flex-wrap gap-x-5 gap-y-1 text-label text-ink">
        {SOURCES.map((source) => (
          <Key key={source} fill={SOURCE_FILL[source]} label={sourceName(source)} />
        ))}
      </p>
      <div
        aria-hidden="true"
        className="mt-4 grid grid-cols-[auto_1fr] gap-x-2 pt-2 text-label text-ink-secondary tabular-nums lining-nums"
      >
        <div className="relative h-32" data-axis="error-hours">
          {/* The widest tick keeps the column wide enough; the ticks themselves sit on the lines. */}
          <span className="invisible block leading-none">{formatNumber(top)}</span>
          {ticks.map((tick) => (
            <span
              key={tick}
              className="absolute right-0 translate-y-1/2 leading-none"
              style={{ bottom: tick === 0 ? "0%" : at(tick) }}
              data-tick={tick}
            >
              {formatNumber(tick)}
            </span>
          ))}
        </div>
        <div className="relative h-32">
          {ticks
            .filter((tick) => tick > 0)
            .map((tick) => (
              <div key={tick} className="absolute inset-x-0 border-t border-hairline" style={{ bottom: at(tick) }} />
            ))}
          <div className="absolute inset-0 flex items-stretch gap-px" data-chart="error-hours">
            {hours.map((hour) => (
              <div
                key={hour.hour}
                className="flex min-w-0 flex-1 flex-col-reverse"
                data-mark="hour"
                data-total={hourTotal(hour)}
              >
                {SOURCES.map((source) =>
                  hour[source] > 0 ? (
                    <Fill
                      key={source}
                      colour={SOURCE_FILL[source]}
                      className="block w-full shrink-0"
                      style={{ height: at(hour[source]) }}
                    />
                  ) : null,
                )}
              </div>
            ))}
          </div>
          {/* The baseline over the columns' feet, in the same box as the ticks' column. */}
          <div className="absolute inset-x-0 bottom-0 border-t border-axis" />
        </div>
        <div />
        <div className="flex gap-px">
          {hours.map((hour, index) => (
            <div key={hour.hour} className="min-w-0 flex-1 overflow-visible whitespace-nowrap">
              {index % 6 === 0 || index === hours.length - 1 ? hourText(hour.hour) : ""}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** «Feil per time» as a table: one row per hour, a column per source and the sum. */
export function ErrorHoursTable({ hours }: { hours: readonly ErrorHour[] }) {
  return (
    <TableRegion caption={copy.errors.tableRegion}>
      <thead>
        <tr>
          <th scope="col" className={HEAD}>
            {copy.errors.hour}
          </th>
          {SOURCES.map((source) => (
            <th key={source} scope="col" className={cn(HEAD, NUM)}>
              {sourceName(source)}
            </th>
          ))}
          <th scope="col" className={cn(HEAD, NUM)}>
            {copy.errors.sum}
          </th>
        </tr>
      </thead>
      <tbody>
        {hours.map((hour) => (
          <tr key={hour.hour}>
            <th scope="row" className={cn(CELL, "font-normal")}>
              {hourText(hour.hour)}
            </th>
            {SOURCES.map((source) => (
              <td key={source} className={cn(CELL, NUM)}>
                {formatNumber(hour[source])}
              </td>
            ))}
            <td className={cn(CELL, NUM)}>{formatNumber(hourTotal(hour))}</td>
          </tr>
        ))}
      </tbody>
    </TableRegion>
  );
}

const TRACK = "var(--color-hairline)";

/** A horizontal bar: its track across the row, and one or more fills from the left. */
function Bar({ parts }: { parts: readonly { width: string; colour: string }[] }) {
  return (
    <span aria-hidden="true" className="relative block h-3 w-full">
      <Fill colour={TRACK} className="absolute inset-0 block size-full" />
      {parts.map((part) => (
        <Fill
          key={part.colour}
          colour={part.colour}
          className="absolute inset-y-0 left-0 block h-full"
          style={{ width: part.width }}
        />
      ))}
    </span>
  );
}

/** «Reserveordrer per type»: a bar per fallback kind, its share of the LLM players' Orders. */
export function FallbackChart({ found }: { found: Operations }) {
  return (
    <ul className="flex max-w-2xl flex-col gap-3" data-chart="fallbacks">
      {found.fallbacks.map((line) => (
        <li key={line.kind} className="grid grid-cols-1 gap-1 sm:grid-cols-[12em_1fr_9em] sm:items-center sm:gap-4">
          <span className="text-body-phone text-ink lg:text-body">{fallbackName(line.kind)}</span>
          <Bar
            parts={[
              {
                width: line.share === null ? "0%" : barPercent(Number(line.share), 1),
                colour: "var(--color-restordre)",
              },
            ]}
          />
          <span className="text-body-phone text-ink tabular-nums lining-nums lg:text-body">
            {shareText(line.share)} ({formatNumber(line.orders)})
          </span>
        </li>
      ))}
    </ul>
  );
}

export function FallbackTable({ found }: { found: Operations }) {
  const columns = copy.fallback.columns;
  return (
    <TableRegion caption={copy.fallback.title}>
      <thead>
        <tr>
          <th scope="col" className={HEAD}>
            {columns.kind}
          </th>
          <th scope="col" className={cn(HEAD, NUM)}>
            {columns.orders}
          </th>
          <th scope="col" className={cn(HEAD, NUM)}>
            {columns.share}
          </th>
        </tr>
      </thead>
      <tbody>
        {found.fallbacks.map((line) => (
          <tr key={line.kind}>
            <th scope="row" className={cn(CELL, "font-normal")}>
              {fallbackName(line.kind)}
            </th>
            <td className={cn(CELL, NUM)}>{formatNumber(line.orders)}</td>
            <td className={cn(CELL, NUM)}>{shareText(line.share)}</td>
          </tr>
        ))}
      </tbody>
    </TableRegion>
  );
}

const MEDIAN = "var(--color-lager)";
const P95 = "var(--color-lager-fill)";

/** «Svartid per innsatsnivå»: per Effort level the 95th percentile as a light bar with the median
 * drawn over it, on one scale (the slowest level's 95th percentile). */
export function ResponseTimesChart({ found }: { found: Operations }) {
  const top = Math.max(1, ...found.response_times.map((line) => line.p95_ms));
  return (
    <div className="max-w-2xl" data-chart="response-times">
      <p className="flex flex-wrap gap-x-5 gap-y-1 text-label text-ink">
        <Key fill={MEDIAN} label={copy.times.median} />
        <Key fill={P95} label={copy.times.p95} />
      </p>
      <ul className="mt-3 flex flex-col gap-3">
        {found.response_times.map((line) => (
          <li
            key={line.effort_level}
            className="grid grid-cols-1 gap-1 sm:grid-cols-[8em_1fr_20em] sm:items-center sm:gap-4"
          >
            <span className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">
              {levelName({ name: line.effort_level, label: line.label })}
            </span>
            <Bar
              parts={[
                { width: barPercent(line.p95_ms, top), colour: P95 },
                { width: barPercent(line.median_ms, top), colour: MEDIAN },
              ]}
            />
            <span className="text-body-phone text-ink tabular-nums lining-nums lg:text-body">
              {copy.times.median} {msText(line.median_ms)} · {copy.times.p95} {msText(line.p95_ms)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ResponseTimesTable({ found }: { found: Operations }) {
  const columns = copy.times.columns;
  return (
    <TableRegion caption={copy.times.title}>
      <thead>
        <tr>
          <th scope="col" className={HEAD}>
            {columns.level}
          </th>
          <th scope="col" className={cn(HEAD, NUM)}>
            {columns.calls}
          </th>
          <th scope="col" className={cn(HEAD, NUM)}>
            {columns.median}
          </th>
          <th scope="col" className={cn(HEAD, NUM)}>
            {columns.p95}
          </th>
        </tr>
      </thead>
      <tbody>
        {found.response_times.map((line) => (
          <tr key={line.effort_level}>
            <th scope="row" className={cn(CELL, "font-normal")}>
              {levelName({ name: line.effort_level, label: line.label })}
            </th>
            <td className={cn(CELL, NUM)}>{formatNumber(line.calls)}</td>
            <td className={cn(CELL, NUM)}>{msText(line.median_ms)}</td>
            <td className={cn(CELL, NUM)}>{msText(line.p95_ms)}</td>
          </tr>
        ))}
      </tbody>
    </TableRegion>
  );
}
