"use client";

import { useId, useRef, useState } from "react";

import { NetOverGame } from "@/components/charts/net-over-game";
import { LINK_BUTTON } from "@/components/link";
import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";

import type { Walkthrough } from "./api";
import { type RunCells, walkthroughRows } from "./walkthrough";

const copy = nb.replay.walkthrough;

/** The chart's height in caption lines (about 140 px at 13 px, as the Debrief's Netto lager). */
export const CHART_LINES = 11;
/** The table's height cap, in em of the caption size: a whole run scrolls inside its region. */
const TABLE_MAX = "max-h-[22em] overflow-y-auto";
/** Until the box is measured (a server render): a phone column and the caption size. */
const FALLBACK = { width: 288, fontSize: 13 };
const CELL = "py-1 pl-3 text-right whitespace-nowrap";
/** Headers wrap (they are long at 320 px); the cells never do. */
const HEAD = "py-1 pl-3 text-right align-bottom font-normal";

/**
 * The walkthrough's chart (Story 10.7, FR-50, AD-18, `09-alle-sider.png` → Replay-gjennomgang):
 * the Replay's Netto lager as `NetOverGame` draws it, and the Student's Class game as a thin grey
 * line on the same Uke axis; the legend names both in words, so the runs are told apart by more
 * than colour. «Vis som tabell» swaps it in place for every Uke of both runs (Netto lager, Din
 * ordre, Kostnad så langt). The chart is `aria-hidden`; the table is its alternative. With the
 * Class game left out (`mostly_ai`) it is the Replay alone. Every number is the api's (AD-10).
 */
export function WalkthroughChart({ data }: { data: Walkthrough }) {
  const [asTable, setAsTable] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const id = useId();
  const both = data.class_game != null;
  const points = (data.replay?.weeks ?? []).map((w) => ({ week: w.week, net: w.net_inventory }));
  const compare = data.class_game?.weeks.map((w) => ({ week: w.week, net: w.net_inventory }));
  return (
    <section aria-labelledby={`${id}-title`} data-walkthrough-chart="" className="mt-6">
      <h2 id={`${id}-title`} className="text-label text-ink">
        {both ? copy.chartTitle : copy.chartTitleAlone}
      </h2>
      {both ? <p className="mt-1 text-caption text-ink-secondary">{copy.legend}</p> : null}
      <div ref={box} className="mt-2 text-caption">
        {asTable ? (
          <ScrollRegion labelledBy={`${id}-title`} scrollClassName={TABLE_MAX}>
            <WalkthroughTable data={data} />
          </ScrollRegion>
        ) : (
          <NetOverGame
            width={size.width}
            height={Math.round(size.fontSize * CHART_LINES)}
            fontSize={size.fontSize}
            points={points}
            compare={compare}
            title={both ? copy.chartSvg : copy.chartSvgAlone}
            formatTick={(value) => formatNumber(value)}
            weekLabel={copy.week}
          />
        )}
      </div>
      <button
        type="button"
        className={LINK_BUTTON}
        data-walkthrough-toggle=""
        aria-expanded={asTable}
        onClick={() => setAsTable((shown) => !shown)}
      >
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </section>
  );
}

function Cells({ run }: { run: RunCells | null }) {
  if (!run) {
    return (
      <>
        <td className={CELL}>{copy.noWeek}</td>
        <td className={CELL}>{copy.noWeek}</td>
        <td className={CELL}>{copy.noWeek}</td>
      </>
    );
  }
  return (
    <>
      <td className={cn(CELL, run.net < 0 && "text-restordre")}>{formatNumber(run.net)}</td>
      <td className={CELL}>{run.order}</td>
      <td className={CELL}>{run.cost}</td>
    </>
  );
}

function WalkthroughTable({ data }: { data: Walkthrough }) {
  const both = data.class_game != null;
  const runs = both ? [copy.runReplay, copy.runClass] : [copy.runReplay];
  return (
    <table data-walkthrough-table="" className="w-full border-collapse text-caption text-ink tabular-nums lining-nums">
      <caption className="sr-only">{both ? copy.tableCaption : copy.tableCaptionAlone}</caption>
      <thead className="sticky top-0 bg-paper">
        <tr className="border-b border-axis text-ink-secondary">
          <th scope="col" className="py-1 text-left align-bottom font-normal">
            {nb.terms.week}
          </th>
          {runs.map((run) => (
            <RunHeaders key={run} run={run} />
          ))}
        </tr>
      </thead>
      <tbody>
        {walkthroughRows(data).map((row) => (
          <tr key={row.week} className="border-b border-hairline">
            <th scope="row" className="py-1 text-left font-normal">
              {row.week}
            </th>
            <Cells run={row.replay} />
            {both ? <Cells run={row.klass} /> : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RunHeaders({ run }: { run: string }) {
  return (
    <>
      <th scope="col" className={HEAD}>
        {copy.columnNet(run)}
      </th>
      <th scope="col" className={HEAD}>
        {copy.columnOrder(run)}
      </th>
      <th scope="col" className={HEAD}>
        {copy.columnCost(run)}
      </th>
    </>
  );
}
