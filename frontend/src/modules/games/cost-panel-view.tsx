"use client";

import { type Ref, type RefObject, useId, useLayoutEffect, useRef, useState } from "react";

import { CostArea } from "@/components/charts/cost-area";
import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";

import type { SeatState } from "./api";
import { type CostPart, costPanel } from "./cost-panel";

const copy = nb.games.play.costPanel;

/** The chart's height in caption lines, as drawn (about 120 px at 13 px). */
const CHART_LINES = 9;
/** Until the panel is measured (a server render): the laptop column's width and the caption size. */
const FALLBACK = { width: 288, fontSize: 13 };

/**
 * «Kostnad så langt» (`cost-panel`, Story 6.16, UX-DR22, DESIGN.md, `05-spill.png` and
 * `01-landing.png`): the Seat's own running cost from the api, never another Seat's or the chain's
 * and never what to order (UX-DR72, UX-DR78). «Lagerkostnad» and «Restordrekostnad» with a thin
 * bar each for their share, the amount at the right; an `axis` rule and «Totalkostnad»; then
 * «Totalkostnad over tid» from Uke 1 to nå; last the Uke's sum line. It reads `seat_state` only,
 * so it changes when a Uke is charged, never while the Student types.
 *
 * The chart is `aria-hidden`; its table alternative (EXPERIENCE.md → Charts) is either «Vis som
 * tabell», which swaps the chart in place for Uke / Lager / Restordre / «Sum, kr» (`table="toggle"`:
 * the pinned laptop panel and the Landing), or the «Sum, kr» row of the table above it
 * (`table="sumRow"`: inside Alle rader on phone), which a screen reader is told.
 */
export function CostPanel({
  state,
  table,
  headingRef,
  demoData,
  className,
}: {
  state: SeatState;
  table: "toggle" | "sumRow";
  /** The heading takes focus when «Kostnad så langt» opened Alle rader at it. */
  headingRef?: Ref<HTMLHeadingElement>;
  /** «Demodata» under the panel (the Landing, UX-DR70). */
  demoData?: string;
  className?: string;
}) {
  const model = costPanel(state);
  const [asTable, setAsTable] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const size = useSize(box);
  const id = useId();
  const tableId = `${id}-table`;
  return (
    <section aria-labelledby={`${id}-title`} data-cost-panel="" className={cn("max-w-md", className)}>
      <h2 id={`${id}-title`} ref={headingRef} tabIndex={-1} className="text-label text-ink outline-none">
        {copy.title}
      </h2>
      <dl className="mt-2 text-body-phone text-ink tabular-nums lining-nums lg:text-body">
        <Part part={model.holding} tone="lager" />
        <Part part={model.backorder} tone="restordre" />
        <div className="flex justify-between gap-4 border-t border-axis pt-2 font-bold">
          <dt>{copy.total}</dt>
          <dd className="text-right" data-cost-total="">
            {model.total}
          </dd>
        </div>
      </dl>
      <h3 className="mt-5 text-caption font-semibold text-ink">{copy.overTime}</h3>
      <div ref={box} className="mt-1 text-caption">
        {asTable ? (
          <CostTable id={tableId} rows={model.rows} />
        ) : (
          <CostArea
            width={size.width}
            height={Math.round(size.fontSize * CHART_LINES)}
            fontSize={size.fontSize}
            points={model.points}
            title={copy.chartSvg}
            formatTick={(value) => formatNumber(value)}
            firstLabel={copy.week(model.points[0]?.week ?? 1)}
            lastLabel={copy.week(model.week)}
          />
        )}
      </div>
      {table === "toggle" ? (
        <button
          type="button"
          className={LINK_BUTTON}
          data-cost-toggle=""
          onClick={() => setAsTable((shown) => !shown)}
        >
          {asTable ? copy.showChart : copy.showTable}
        </button>
      ) : (
        <p className="sr-only">{nb.games.play.allRows.sumRowNote}</p>
      )}
      <p className="mt-3 text-caption text-ink" data-cost-week="">
        {model.weekCost}
      </p>
      {demoData ? <p className="mt-4 text-caption text-ink-muted">{demoData}</p> : null}
    </section>
  );
}

/** A cost part's row: the label with its thin bar under it, and the amount right-aligned. */
function Part({ part, tone }: { part: CostPart; tone: "lager" | "restordre" }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1">
      <dt className="min-w-0 flex-1">
        {part.label}
        {/* Drawn as a top border, so the bar is no text background. */}
        <span aria-hidden="true" className="mt-1 block w-full">
          <span
            data-cost-bar={tone}
            className={cn("block h-0 border-t-[3px]", tone === "lager" ? "border-lager" : "border-restordre")}
            style={{ width: `${(part.share * 100).toFixed(2)}%` }}
          />
        </span>
      </dt>
      <dd className="text-right font-semibold">{part.amount}</dd>
    </div>
  );
}

function CostTable({ id, rows }: { id: string; rows: ReturnType<typeof costPanel>["rows"] }) {
  const cell = "py-1 pl-3 text-right";
  return (
    <table id={id} data-cost-table="" className="w-full border-collapse text-caption text-ink tabular-nums lining-nums">
      <caption className="sr-only">{copy.tableCaption}</caption>
      <thead>
        <tr className="border-b border-axis text-ink-secondary">
          <th scope="col" className="py-1 text-left font-normal">
            {nb.terms.week}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.holdingColumn}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.backorderColumn}
          </th>
          <th scope="col" className={cn(cell, "font-normal")}>
            {copy.sumColumn}
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

/** The box's width and caption size in px, measured again when it resizes (text zoom, a font
 * loading, the breakpoint); the chart takes them as fixed sizes (AD-18). */
function useSize(box: RefObject<HTMLDivElement | null>) {
  const [size, setSize] = useState(FALLBACK);
  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const measure = () => {
      const width = Math.floor(element.clientWidth);
      const fontSize = parseFloat(getComputedStyle(element).fontSize) || FALLBACK.fontSize;
      if (width > 0) setSize((was) => (was.width === width && was.fontSize === fontSize ? was : { width, fontSize }));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [box]);
  return size;
}
