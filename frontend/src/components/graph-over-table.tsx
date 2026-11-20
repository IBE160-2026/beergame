"use client";

import { type CSSProperties, Fragment, type ReactNode, useCallback, useLayoutEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Graf over tabell (Story 6.7, UX-DR16, UX-DR17, UX-DR18, AD-18, DESIGN.md → Graf over tabell):
 * graph fields over a week table on one x-axis, in one sideways scroll region. Shared by the play
 * screen and, later, the Landing (6.8), Hjem's Spillkort (6.17), the Debrief (Epic 9), the Replay
 * (Epic 10) and the report (Epic 13), and by the rules briefing's graph strip (6.2).
 *
 * The fields are rows of the same `<table>` as the week rows, so a graph spans exactly the week
 * columns and scrolls with them; its y-axis labels sit in the sticky row-label column. The graph
 * rows are `aria-hidden`: the table is the graph's alternative and the graph adds no second
 * reading of the same numbers (NFR-6). A field's caption row (title, key) is read.
 *
 * Two layouts give the charts their fixed width (AD-18):
 * - In the browser the component measures each week column's centre (`th[scope=col]`, keyed by
 *   `data-col`) and the field's cell, again whenever the table resizes, and draws with those px.
 *   The SVGs sit absolutely in their cells, so they never widen a column.
 * - With `fixed` (the server-rendered print page) every width is given in px and nothing is
 *   measured; the caller gives its week cells the same widths (`fixedCell`).
 *
 * Columns flagged `phone: false` show only from 1024 px (`lg`); each field then has a phone row
 * and a laptop row, each drawn over its own columns. The region scrolls so that nå is in view on
 * load, on each new nå and on a changed layout; «Sveip» shows while earlier columns are hidden.
 */

export type GraphColumn = { week: number; when: "past" | "now" | "future"; phone: boolean };

/** What a field is drawn with: its cell's size and each drawn column's centre, in px. */
export type FieldSize = {
  width: number;
  height: number;
  /** The field's font size in px (`caption` at the current text zoom). */
  fontSize: number;
  /** The width of the sticky label column, where the axis labels go. */
  labelWidth: number;
  columns: readonly GraphColumn[];
  /** The centre of each of `columns`, from the field's left edge. */
  xs: readonly number[];
  /** The right edge of the nå column, from the field's left edge. */
  nowX: number;
  /** The narrowest column's width. */
  columnWidth: number;
};

export type GraphField = {
  key: string;
  /** A line above the field (its title or key); read by screen readers. */
  caption?: ReactNode;
  /** The field's height in em of the `caption` text size, so it grows with the text. */
  heightEm: number;
  render: (size: FieldSize) => { plot: ReactNode; axis?: ReactNode };
};

/** Every width in px, for a render without measuring (print). */
export type FixedLayout = { labelWidth: number; columnWidth: number; fontSize: number };

/** The inline width of a week cell in the fixed layout, or nothing in the browser. */
export function fixedCell(fixed: FixedLayout | undefined, kind: "label" | "week"): CSSProperties | undefined {
  if (!fixed) return undefined;
  // Content-box with explicit padding: WeasyPrint sizes table cells by their content box whatever
  // `box-sizing` says, so this is the one way both renderers give the same column widths.
  const padding = kind === "label" ? LABEL_GAP : 0;
  const width = (kind === "label" ? fixed.labelWidth : fixed.columnWidth) - padding;
  return { width, minWidth: width, maxWidth: width, boxSizing: "content-box", padding: 0, paddingRight: padding };
}

type Variant = { name: "all" | "phone" | "laptop"; columns: GraphColumn[]; rowClass?: string };

function variantsOf(columns: readonly GraphColumn[]): Variant[] {
  if (columns.every((column) => column.phone)) return [{ name: "all", columns: [...columns] }];
  return [
    { name: "phone", columns: columns.filter((column) => column.phone), rowClass: "lg:hidden" },
    { name: "laptop", columns: [...columns], rowClass: "hidden lg:table-row" },
  ];
}

// Sticky is positioned, so it also holds the absolutely placed axis (no `relative`: it would
// replace `sticky`).
const STICKY_LABEL = "sticky left-0 z-10 bg-paper p-0";
/** The gap between a row label and the first week column in the fixed layout (Tailwind `pr-2`). */
const LABEL_GAP = 8;

type Measured = {
  /** Per `field:variant`, the size it is drawn with (only the shown variant). */
  fields: Record<string, FieldSize>;
  /** The now-line's x from the table wrapper's left edge. */
  nowLeft: number | null;
};

const EMPTY: Measured = { fields: {}, nowLeft: null };

function fixedSizes(fields: readonly GraphField[], variants: readonly Variant[], fixed: FixedLayout): Measured {
  const sizes: Record<string, FieldSize> = {};
  let nowLeft: number | null = null;
  for (const variant of variants) {
    const n = variant.columns.length;
    const nowIndex = variant.columns.findIndex((column) => column.when === "now");
    // With no nå column (a finished game), the now-line and the tint sit past the last column.
    const nowX = (nowIndex < 0 ? n : nowIndex + 1) * fixed.columnWidth;
    for (const field of fields) {
      sizes[`${field.key}:${variant.name}`] = {
        width: n * fixed.columnWidth,
        height: Math.round(field.heightEm * fixed.fontSize),
        fontSize: fixed.fontSize,
        labelWidth: fixed.labelWidth,
        columns: variant.columns,
        xs: variant.columns.map((_, i) => (i + 0.5) * fixed.columnWidth),
        nowX,
        columnWidth: fixed.columnWidth,
      };
    }
    // The print page is narrower than `lg`: the phone (or only) variant is the one shown.
    if (variant.name !== "laptop" && nowIndex >= 0) nowLeft = fixed.labelWidth + nowX;
  }
  return { fields: sizes, nowLeft };
}

export function GraphOverTable({
  label,
  columns,
  fields,
  head,
  body,
  fixed,
  swipe,
  footer,
}: {
  /** The region's accessible name («Graf og tabell»). */
  label: string;
  columns: readonly GraphColumn[];
  fields: readonly GraphField[];
  /** The header row(s) under the graph: the «Uke» row with a `th[scope=col][data-col]` per column. */
  head: ReactNode;
  body: ReactNode;
  fixed?: FixedLayout;
  /** «Sveip for tidligere uker», shown while earlier columns are scrolled out of view. */
  swipe?: string;
  /** A line under the region, beside «Sveip» (a key). */
  footer?: ReactNode;
}) {
  const region = useRef<HTMLDivElement>(null);
  const wrapper = useRef<HTMLDivElement>(null);
  const variants = variantsOf(columns);
  const [measured, setMeasured] = useState<Measured>(EMPTY);
  const [earlierHidden, setEarlierHidden] = useState(false);
  const shown = fixed ? fixedSizes(fields, variants, fixed) : measured;
  const nowWeek = columns.find((column) => column.when === "now")?.week;
  const columnKey = columns.map((column) => `${column.week}${column.phone ? "p" : ""}`).join(",");

  const measure = useCallback(() => {
    const box = wrapper.current;
    if (!box || fixed) return;
    const origin = box.getBoundingClientRect().left;
    const centre = new Map<number, { centre: number; right: number; width: number }>();
    for (const th of box.querySelectorAll<HTMLElement>("th[scope=col][data-col]")) {
      if (th.getClientRects().length === 0) continue; // not shown in this layout
      const rect = th.getBoundingClientRect();
      centre.set(Number(th.dataset.col), { centre: rect.left + rect.width / 2, right: rect.right, width: rect.width });
    }
    const sizes: Record<string, FieldSize> = {};
    for (const row of box.querySelectorAll<HTMLElement>("tr[data-field]")) {
      if (row.getClientRects().length === 0) continue;
      const plot = row.querySelector<HTMLElement>("td[data-plot]");
      const axis = row.querySelector<HTMLElement>("td[data-axis]");
      const variant = variants.find((v) => v.name === row.dataset.variant);
      if (!plot || !axis || !variant) continue;
      const left = plot.getBoundingClientRect().left;
      const found = variant.columns.map((column) => centre.get(column.week));
      if (found.some((item) => !item)) continue;
      const nowIndex = variant.columns.findIndex((column) => column.when === "now");
      sizes[`${row.dataset.field}:${variant.name}`] = {
        width: plot.clientWidth,
        height: plot.clientHeight,
        fontSize: parseFloat(getComputedStyle(plot).fontSize),
        labelWidth: axis.clientWidth,
        columns: variant.columns,
        xs: found.map((item) => item!.centre - left),
        nowX: nowIndex < 0 ? plot.clientWidth : found[nowIndex]!.right - left,
        columnWidth: Math.min(...found.map((item) => item!.width)),
      };
    }
    const now = nowWeek === undefined ? undefined : centre.get(nowWeek);
    const next: Measured = { fields: sizes, nowLeft: now ? now.right - origin : null };
    setMeasured((was) => (JSON.stringify(was) === JSON.stringify(next) ? was : next));
    // `variants` follows `columnKey`; listing it would measure again on every render.
  }, [fixed, nowWeek, columnKey]);

  const update = useCallback(() => {
    const element = region.current;
    if (element) setEarlierHidden(element.scrollLeft > 1);
  }, []);

  // Bring nå into view: nå at the left edge of the scrolled area, or as far right as the region
  // goes, whichever is less, so nå + 4 is the right edge whenever all columns from nå fit.
  const toNow = useCallback(() => {
    const element = region.current;
    const now = element?.querySelector<HTMLElement>("th[data-now]");
    const rowLabel = element?.querySelector<HTMLElement>("thead th[scope=row]");
    if (!element || !now || !rowLabel) return;
    const offset = now.getBoundingClientRect().left - element.getBoundingClientRect().left + element.scrollLeft;
    const target = offset - rowLabel.getBoundingClientRect().width;
    element.scrollLeft = Math.max(0, Math.min(target, element.scrollWidth - element.clientWidth));
    update();
  }, [update]);

  useLayoutEffect(() => {
    measure();
    toNow();
  }, [measure, toNow, nowWeek]);

  useLayoutEffect(() => {
    const element = region.current;
    const table = wrapper.current;
    if (!element || !table) return;
    // A changed layout (rotation, the laptop breakpoint, larger text, a loaded font) measures the
    // columns again and brings nå back into view.
    let size = `${element.clientWidth}x${element.scrollWidth}x${table.offsetHeight}`;
    const observer = new ResizeObserver(() => {
      measure();
      const now = `${element.clientWidth}x${element.scrollWidth}x${table.offsetHeight}`;
      if (now !== size) {
        size = now;
        toNow();
      }
    });
    observer.observe(element);
    observer.observe(table);
    return () => observer.disconnect();
  }, [measure, toNow]);

  const tint = (nowLeft: number | null): CSSProperties | undefined =>
    nowLeft === null
      ? undefined
      : {
          backgroundImage: `linear-gradient(to right, transparent ${nowLeft}px, var(--color-future-tint) ${nowLeft}px)`,
        };

  return (
    <div className={fixed ? undefined : "-mx-[calc(var(--spacing-gutter-phone)-var(--spacing-gutter-phone-chart))] lg:mx-0"}>
      <div
        ref={region}
        role="region"
        aria-label={label}
        tabIndex={0}
        onScroll={update}
        className={cn(
          !fixed &&
            "overflow-x-auto pb-1 [scrollbar-color:var(--color-ink-muted)_var(--color-hairline)] [scrollbar-width:thin] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        )}
      >
        {/* `relative` keeps the now-line and the screen-reader-only labels inside the scroll area. */}
        <div ref={wrapper} className="relative w-max">
          <table className="border-collapse text-table-cell text-ink tabular-nums lining-nums lg:text-table-cell-laptop">
            <thead>
              {fields.map((field) =>
                variants.map((variant) => {
                  const id = `${field.key}:${variant.name}`;
                  const size = shown.fields[id];
                  const drawn = size ? field.render(size) : null;
                  const span = variant.columns.length;
                  return (
                    <Fragment key={id}>
                      {field.caption ? (
                        <tr className={variant.rowClass}>
                          <td colSpan={span + 1} className="p-0 pt-2 text-caption text-ink-secondary" style={tint(shown.nowLeft)}>
                            <div className="sticky left-0 z-20 w-fit max-w-[calc(100vw-2rem)] bg-paper pr-2 lg:max-w-[24rem]">{field.caption}</div>
                          </td>
                        </tr>
                      ) : null}
                      <tr aria-hidden="true" data-field={field.key} data-variant={variant.name} className={variant.rowClass}>
                        <td
                          data-axis=""
                          className={cn(STICKY_LABEL, "text-caption")}
                          style={fixed ? { ...fixedCell(fixed, "week"), width: fixed.labelWidth, minWidth: fixed.labelWidth, maxWidth: fixed.labelWidth } : undefined}
                        >
                          {drawn?.axis ? <div className={fixed ? undefined : "absolute inset-0"}>{drawn.axis}</div> : null}
                        </td>
                        <td
                          data-plot=""
                          colSpan={span}
                          className="relative p-0 text-caption"
                          style={{ height: size && fixed ? size.height : `${field.heightEm}em` }}
                        >
                          {drawn ? <div className={fixed ? undefined : "absolute inset-0"}>{drawn.plot}</div> : null}
                        </td>
                      </tr>
                    </Fragment>
                  );
                }),
              )}
              {head}
            </thead>
            <tbody>{body}</tbody>
          </table>
          {shown.nowLeft !== null ? (
            <div
              aria-hidden="true"
              data-now-line=""
              className="pointer-events-none absolute top-0 bottom-0 z-[5] w-0 border-l-[1.4px] border-ink"
              style={{ left: shown.nowLeft - 0.7 }}
            />
          ) : null}
        </div>
      </div>
      {footer || swipe ? (
        <div
          className={cn(
            "flex flex-wrap justify-between gap-x-4",
            !fixed && "px-[calc(var(--spacing-gutter-phone)-var(--spacing-gutter-phone-chart))] lg:px-0",
          )}
        >
          {footer ?? <span />}
          {swipe && earlierHidden ? <p className="mt-1 text-caption text-ink-secondary">{swipe}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
