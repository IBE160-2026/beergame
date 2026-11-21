"use client";

import { useId } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { AxisLabels } from "@/components/charts/axis-labels";
import { DemandBand, demandAxis, demandScale } from "@/components/charts/demand-band";
import { type GraphColumn, type GraphField, GraphOverTable } from "@/components/graph-over-table";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";

import { DEBRIEF_STEPS, type Debrief, downstreamRole, type Reveal, type RevealWeek, useDebriefStep } from "./api";

const copy = nb.debrief.reveal;
const LINE = "text-body-phone lg:text-body";
/** One week column: 1.6 em, so 12 columns fit at 360 px (as the play screen's week table); wider
 * from 1024 px, so a whole game spreads over the laptop page. */
const WEEK_COL = "w-[1.6em] min-w-[1.6em] px-[0.1em] text-center lg:w-[2em] lg:min-w-[2em]";
const ROW_LABEL =
  "sticky left-0 z-10 min-w-row-label-phone bg-paper pr-2 text-left align-middle font-normal text-ink lg:min-w-row-label-laptop";
/** The band's height in em of the caption size (about 200 px at 13 px, `07-debrief.png`). */
const BAND_HEIGHT_EM = 15;

const ROWS: readonly { key: "demand" | "incoming_order" | "order"; label: string }[] = [
  { key: "demand", label: copy.rows.demand },
  { key: "incoming_order", label: copy.rows.incoming },
  { key: "order", label: copy.rows.order },
];

/**
 * Debrief step 2, the reveal (Story 9.4, FR-44, UX-DR31, UX-DR32, `07-debrief.png`): shown once
 * the Explanation is saved; the api checks the gate and answers the step. The heading is the
 * api's, rendered by code from the demand series. The Etterspørselsbånd stands over the table Uke
 * / Kundene / Ordre inn / Din ordre on the same columns, in one sideways scroll region with a
 * sticky label column (`GraphOverTable`); then the exercise is named. Every number is the api's
 * (AD-10).
 */
export function RevealStep({ debrief }: { debrief: Debrief }) {
  const step = useDebriefStep(debrief.id, 2, true);
  const reveal = step.data?.reveal ?? null;
  const id = useId();
  if (step.isError) {
    return (
      <section aria-label={nb.debriefEntry.stepOf(2, DEBRIEF_STEPS)} data-debrief-reveal="failed" className="mt-10 border-t border-axis pt-4">
        <div className="flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void step.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  if (!reveal) return null;
  const downstream = downstreamRole(debrief.role);
  return (
    <section aria-labelledby={`${id}-heading`} data-debrief-reveal="" className="mt-10 border-t border-axis pt-4">
      <h2 id={`${id}-heading`} className="max-w-3xl text-headline text-ink">
        <span className="sr-only">{nb.debriefEntry.stepOf(2, DEBRIEF_STEPS)}: </span>
        <span aria-hidden="true" className="mr-3 tabular-nums">
          2
        </span>
        {reveal.heading}
      </h2>
      <div className="mt-4">
        <RevealTable reveal={reveal} labelledBy={`${id}-heading`} />
      </div>
      <div className={`${LINE} mt-4 flex max-w-2xl flex-col gap-2 text-ink`}>
        <p data-exercise-named="">{copy.named}</p>
        <p>{downstream ? copy.saw(copy.definite[downstream]) : copy.sawRetailer}</p>
        <p>{copy.structure}</p>
      </div>
    </section>
  );
}

function bandField(reveal: Reveal): GraphField {
  const byWeek = new Map(reveal.weeks.map((week) => [week.week, week]));
  const highest = Math.max(0, ...reveal.weeks.flatMap((w) => [w.demand, w.incoming_order, w.order]));
  const axis = demandAxis(highest);
  const last = reveal.weeks[reveal.weeks.length - 1];
  const largest = reveal.largest_order;
  return {
    key: "demand",
    caption: <BandKey />,
    heightEm: BAND_HEIGHT_EM,
    render: (size) => {
      const points = size.columns.flatMap((column, i) => {
        const week = byWeek.get(column.week);
        return week ? [{ week: week.week, x: size.xs[i]!, demand: week.demand, incoming: week.incoming_order, order: week.order }] : [];
      });
      const y = demandScale(size.height, size.fontSize, axis.top);
      return {
        plot: (
          <DemandBand
            width={size.width}
            height={size.height}
            fontSize={size.fontSize}
            points={points}
            columnWidth={size.columnWidth}
            top={axis.top}
            demandLabel={copy.demandLabel(last ? formatNumber(last.demand) : "")}
            largest={largest ? { week: largest.week, text: copy.largestOrder(formatNumber(largest.order), largest.week) } : null}
            title={copy.svg}
          />
        ),
        axis: (
          <AxisLabels
            width={size.labelWidth}
            height={size.height}
            fontSize={size.fontSize}
            title={copy.axisSvg}
            ticks={axis.ticks.map((tick) => ({ y: y(tick), text: formatNumber(tick) }))}
          />
        ),
      };
    },
  };
}

/** The band's key: a swatch for each of its three marks, as text (never colour alone). */
function BandKey() {
  const swatch = "mr-1 inline-block align-[-0.05em]";
  return (
    <span className="flex flex-wrap gap-x-4">
      <span className="whitespace-nowrap">
        <span aria-hidden="true" className={cn(swatch, "h-[0.8em] w-[1.2em] border-t border-lager bg-lager-fill")} />
        {copy.demandKey}
      </span>
      {/* The longest key wraps at 200 % text rather than run out of the caption. */}
      <span>
        <span aria-hidden="true" className={cn(swatch, "h-0 w-[1.2em] border-t-[1.5px] border-ink-secondary align-[0.3em]")} />
        {copy.incomingKey}
      </span>
      <span className="whitespace-nowrap">
        {/* A filled bar drawn as a border, so it is no text background. */}
        <span aria-hidden="true" className={cn(swatch, "h-[0.8em] w-0 border-l-[0.5em] border-ink")} />
        {copy.orderKey}
      </span>
    </span>
  );
}

/** The band over the table Uke / Kundene / Ordre inn / Din ordre: every Uke of the game, one
 * column each, `th` scopes on both axes (NFR-6). */
function RevealTable({ reveal, labelledBy }: { reveal: Reveal; labelledBy: string }) {
  const columns: GraphColumn[] = reveal.weeks.map((week) => ({ week: week.week, when: "past", phone: true }));
  return (
    <GraphOverTable
      label={copy.region}
      columns={columns}
      fields={[bandField(reveal)]}
      labelledBy={labelledBy}
      swipe={copy.swipe}
      head={
        <tr className="border-b border-axis">
          <th scope="row" className={ROW_LABEL}>
            {nb.terms.week}
          </th>
          {reveal.weeks.map((week) => (
            <th key={week.week} scope="col" data-col={week.week} className={cn(WEEK_COL, "h-row-phone font-normal text-ink-muted lg:h-row-laptop")}>
              <span className="sr-only">{nb.terms.week} </span>
              {week.week}
            </th>
          ))}
        </tr>
      }
      body={ROWS.map((row) => (
        <tr key={row.key} data-row={row.key} className="border-b border-hairline">
          <th scope="row" className={ROW_LABEL}>
            {row.label}
          </th>
          {reveal.weeks.map((week: RevealWeek) => (
            <td
              key={week.week}
              className={cn(
                WEEK_COL,
                "h-row-phone lg:h-row-laptop",
                row.key === "order" && reveal.largest_order?.week === week.week && "font-bold",
              )}
            >
              {formatNumber(week[row.key])}
            </td>
          ))}
        </tr>
      ))}
    />
  );
}
