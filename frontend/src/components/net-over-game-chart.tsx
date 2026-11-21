"use client";

import { useId, useRef, useState } from "react";

import { NetOverGame } from "@/components/charts/net-over-game";
import { LINK_BUTTON } from "@/components/link";
import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";

const copy = nb.debriefEntry.explanation;

/** One Uke of the Seat's Netto lager, as the api gave it. */
export type NetWeek = { week: number; net_inventory: number };

/** The chart's height in caption lines (about 140 px at 13 px, `07-debrief.png`). */
const CHART_LINES = 11;
/** The table's height cap, in em of the caption size (about ten rows): a whole game scrolls inside
 * its region, so the writing field stays near on a phone (Story 9.4 fix). */
const TABLE_MAX = "max-h-[22em] overflow-y-auto";
/** Until the box is measured (a server render): a phone column and the caption size. */
const FALLBACK = { width: 288, fontSize: 13 };

/**
 * «Ditt netto lager, hele spillet» (Story 9.3, Debrief step 1, UX-DR31, AD-18): the Student's own
 * Seat's Netto lager over every Uke of the finished game (`NetOverGame`), and «Vis som tabell»
 * that swaps it in place for Uke / Netto lager, and back. The chart is `aria-hidden`; the table is
 * its alternative. The Student's own Seat only: no customer demand, no other Role.
 */
export function NetOverGameChart({ weeks, className }: { weeks: readonly NetWeek[]; className?: string }) {
  const [asTable, setAsTable] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const id = useId();
  return (
    <section aria-labelledby={`${id}-title`} data-net-over-game="" className={className}>
      <h3 id={`${id}-title`} className="text-label text-ink">
        {copy.netTitle}
      </h3>
      <div ref={box} className="mt-2 text-caption">
        {asTable ? (
          // A long game outgrows a phone: the table scrolls on its own, down as well as sideways at
          // 200 % text, under a header that stays (UX-DR75).
          <ScrollRegion labelledBy={`${id}-title`} scrollClassName={TABLE_MAX}>
            <NetTable weeks={weeks} />
          </ScrollRegion>
        ) : (
          <NetOverGame
            width={size.width}
            height={Math.round(size.fontSize * CHART_LINES)}
            fontSize={size.fontSize}
            points={weeks.map((w) => ({ week: w.week, net: w.net_inventory }))}
            title={copy.chartSvg}
            formatTick={(value) => formatNumber(value)}
            weekLabel={copy.week}
          />
        )}
      </div>
      <button
        type="button"
        className={LINK_BUTTON}
        data-net-toggle=""
        aria-expanded={asTable}
        onClick={() => setAsTable((shown) => !shown)}
      >
        {asTable ? copy.showChart : copy.showTable}
      </button>
    </section>
  );
}

function NetTable({ weeks }: { weeks: readonly NetWeek[] }) {
  const cell = "py-1 pl-3 text-right";
  return (
    <table data-net-table="" className="w-full border-collapse text-caption text-ink tabular-nums lining-nums">
      <caption className="sr-only">{copy.tableCaption}</caption>
      <thead className="sticky top-0 bg-paper">
        <tr className="border-b border-axis text-ink-secondary">
          <th scope="col" className="py-1 text-left font-normal">
            {nb.terms.week}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.netColumn}
          </th>
        </tr>
      </thead>
      <tbody>
        {weeks.map((row) => (
          <tr key={row.week} className="border-b border-hairline">
            <th scope="row" className="py-1 text-left font-normal">
              {row.week}
            </th>
            <td className={cn(cell, row.net_inventory < 0 && "text-restordre")}>{formatNumber(row.net_inventory)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
