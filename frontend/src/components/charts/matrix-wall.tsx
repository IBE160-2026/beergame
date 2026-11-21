"use client";

import { type KeyboardEvent, useCallback, useId, useLayoutEffect, useRef, useState } from "react";

import {
  cellText,
  headerWeeks,
  moveFocus,
  NET_STEPS,
  netStep,
  SKELETON_CELLS,
  type NetStep,
  stepFill,
  stepText,
  type WallPosition,
  wallSizes,
} from "./matrix-wall-layout";
import { CHART_FONT, colour } from "./palette";

/** One Class game: its label and figure in the sticky game column, its detail after the cells,
 * and its Netto lager per Uke from Uke 1 (the api's numbers, AD-10). */
export type WallRow = {
  id: string;
  /** «Spill 2». */
  label: string;
  /** The row's figure, right-aligned in the game column («1 058»). */
  figure?: string;
  /** Status and wait after the cells («Venter på Noah (Grossist), 23 t»). */
  detail?: string;
  /** The row header as read: game number, status, wait and kjedekost in words. */
  rowName: string;
  /** Uke 1 … the last Uke the game has; empty before it starts or while loading. */
  values: readonly number[];
  /** The values are on their way: a Skjelett bar stands in the row. */
  loading?: boolean;
};

export type WallGroup = { key: string; title: string; rows: readonly WallRow[] };

export type MatrixWallCopy = {
  /** The region's name, «Alle spill». */
  region: string;
  /** The SVG `<title>` (AD-18). */
  title: string;
  /** The corner header over the game column, and over the figures when there are any. */
  gameHeader: string;
  figureHeader?: string;
  week: (week: number) => string;
  /** «Spill 2, Uke 14: Netto lager −13.» */
  cell: (row: WallRow, week: number, value: string) => string;
  /** The legend's bins in step order (`NET_STEPS`), and its line about the minus. */
  bins: readonly string[];
  minusNote: string;
  legend: string;
};

export type MatrixWallProps = {
  /** Fixed width in px from the caller (AD-18); the drawing grows past it when the Uker need room. */
  width: number;
  /** The caption size in px at the current text zoom. */
  fontSize: number;
  groups: readonly WallGroup[];
  copy: MatrixWallCopy;
  /** Formats a cell's number («−13»): the one Norwegian number formatter. */
  format: (value: number) => string;
  /** The region's height limit (CSS), so the Uke header stays in view in a long wall. */
  maxHeight?: string;
  className?: string;
  /** The cell that holds the wall's one Tab stop, when the caller keeps it (the Oversikt shares
   * the game with «Vis som tabell», Story 7.3); else the wall keeps its own. */
  position?: WallPosition | null;
  onPosition?: (position: WallPosition) => void;
};

const PAPER = colour("paper");
const INK = colour("ink");

/**
 * The Matrisevegg (`matrix-wall`, Story 7.2, UX-DR41, AD-18): one row per Class game and one
 * column per Uke, each cell Netto lager in the matrix steps with square corners, grouped under
 * the caller's headers. Hand-made SVG with a fixed width, reused by the Landing and by «Vis i
 * plenum» (Epic 14).
 *
 * Readable in place (founder decision 2026-11-14): the SVG is an ARIA grid (a table to assistive
 * technology, never `aria-hidden`) with Uke column headers, a row header per game and a named
 * cell per Uke. The grid is one Tab stop; arrow keys, Home and End move cell by cell, the focused
 * cell draws `focus-ring-inset`, and focus stays on the same game (by id) and Uke across every
 * re-render. The game column and the Uke header stay put while the region scrolls (README.md).
 */
export function MatrixWall({
  width,
  fontSize,
  groups,
  copy,
  format,
  maxHeight = "70vh",
  className,
  position,
  onPosition,
}: MatrixWallProps) {
  const id = useId();
  const region = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const cellsClip = useRef<SVGRectElement>(null);
  const labelsClip = useRef<SVGRectElement>(null);
  const headerClip = useRef<SVGRectElement>(null);
  const focused = useRef(false);
  const [own, setOwn] = useState<WallPosition | null>(null);
  const active = position !== undefined ? position : own;
  const setActive = (next: WallPosition) => {
    setOwn(next);
    onPosition?.(next);
  };
  const [hasFocus, setHasFocus] = useState(false);

  const rows = groups.flatMap((group) => group.rows);
  const columns = rows.reduce((most, row) => Math.max(most, row.values.length), 0);
  const size = wallSizes({
    width,
    fontSize,
    columns,
    labels: [copy.gameHeader, ...rows.map((row) => row.label)],
    figures: [...(copy.figureHeader ? [copy.figureHeader] : []), ...rows.flatMap((row) => (row.figure ? [row.figure] : []))],
    details: rows.flatMap((row) => (row.detail ? [row.detail] : [])),
  });
  const reachable = rows.map((row) => ({ id: row.id, cells: row.values.length }));
  const first = reachable.find((row) => row.cells > 0);
  // The cell in the Tab order: the one last focused while its game still has it, else the first.
  const target: WallPosition | null = (() => {
    const row = active ? reachable.find((r) => r.id === active.id && r.cells > 0) : undefined;
    if (row && active) return { id: row.id, week: Math.min(active.week, row.cells) };
    return first ? { id: first.id, week: 1 } : null;
  })();

  // The region's scroll moves the game column and the Uke header with it, and the clip paths
  // keep the cells out from under them: CSS `sticky` cannot act inside an SVG (README.md).
  const stick = useCallback(() => {
    const box = region.current;
    if (!box || !svg.current) return;
    const { scrollLeft: x, scrollTop: y } = box;
    svg.current.style.setProperty("--wall-x", `${x}px`);
    svg.current.style.setProperty("--wall-y", `${y}px`);
    cellsClip.current?.setAttribute("x", String(size.labelWidth + x));
    cellsClip.current?.setAttribute("y", String(size.headerHeight + y));
    labelsClip.current?.setAttribute("y", String(size.headerHeight + y));
    headerClip.current?.setAttribute("x", String(size.labelWidth + x));
  }, [size.labelWidth, size.headerHeight]);
  useLayoutEffect(stick);

  const cellElement = (at: WallPosition | null) =>
    at ? svg.current?.querySelector<SVGGElement>(`[data-row="${CSS.escape(at.id)}"] [data-week="${at.week}"]`) : null;

  /** Scroll the region so the cell is clear of the sticky game column and Uke header. */
  const reveal = (element: SVGGElement, at: WallPosition) => {
    const box = region.current;
    const row = element.closest<SVGGElement>("[data-row]");
    if (!box || !row) return;
    const x = size.labelWidth + (at.week - 1) * size.cellWidth;
    const y = Number(row.dataset.y);
    if (x < box.scrollLeft + size.labelWidth) box.scrollLeft = x - size.labelWidth;
    else if (x + size.cellWidth > box.scrollLeft + box.clientWidth) box.scrollLeft = x + size.cellWidth - box.clientWidth;
    if (y < box.scrollTop + size.headerHeight) box.scrollTop = y - size.headerHeight;
    else if (y + size.rowHeight > box.scrollTop + box.clientHeight) box.scrollTop = y + size.rowHeight - box.clientHeight;
  };

  // Rows that move between groups are moved in the DOM, which drops focus: put it back on the
  // same game and Uke after every render while the wall has it.
  useLayoutEffect(() => {
    if (!focused.current || !target) return;
    const element = cellElement(target);
    if (element && document.activeElement !== element) element.focus({ preventScroll: true });
  });

  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    if (!target || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const next = moveFocus(reachable, target, event.key);
    if (!next) return;
    event.preventDefault();
    setActive(next);
    const element = cellElement(next);
    if (element) {
      element.focus({ preventScroll: true });
      reveal(element, next);
    }
  };

  let y = size.headerHeight;
  const drawn = groups.map((group) => {
    const top = y;
    y += size.groupHeight;
    const placed = group.rows.map((row) => {
      const at = y;
      y += size.rowHeight;
      return { row, y: at };
    });
    return { group, top, placed };
  });
  const height = y + 1;
  const weeks = headerWeeks(size.columns, size.cellWidth, fontSize);
  const titleId = `${id}-title`;
  const clipCells = `${id}-cells`;
  const clipLabels = `${id}-labels`;
  const clipHeader = `${id}-header`;
  const stuckX = { transform: "translate(var(--wall-x, 0px), 0px)" };
  const stuckY = { transform: "translate(0px, var(--wall-y, 0px))" };
  const stuckXY = { transform: "translate(var(--wall-x, 0px), var(--wall-y, 0px))" };
  const textY = (top: number, h: number) => top + h / 2 + fontSize * 0.35;
  let rowIndex = 1;

  return (
    <div className={className} data-matrix-wall="">
      <Legend copy={copy} />
      <div
        ref={region}
        role="region"
        aria-label={copy.region}
        tabIndex={0}
        onScroll={stick}
        style={{ maxHeight }}
        className="mt-3 overflow-auto overscroll-contain focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <svg
          ref={svg}
          role="grid"
          aria-labelledby={titleId}
          aria-rowcount={1 + groups.length + rows.length}
          aria-colcount={1 + size.columns}
          width={size.width}
          height={height}
          viewBox={`0 0 ${size.width} ${height}`}
          fontFamily={CHART_FONT}
          fontSize={fontSize}
          className="block"
          data-chart="matrix-wall"
          onKeyDown={onKeyDown}
          onFocus={(event) => {
            focused.current = true;
            setHasFocus(true);
            const week = (event.target as Element).getAttribute("data-week");
            const row = (event.target as Element).closest("[data-row]")?.getAttribute("data-row");
            if (week && row && (row !== target?.id || Number(week) !== target?.week)) {
              setActive({ id: row, week: Number(week) });
            }
          }}
          onBlur={(event) => {
            // A cell taken out of the DOM while its row moves keeps the wall's focus: it is put back.
            if (!(event.target as Node).isConnected) return;
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              focused.current = false;
              setHasFocus(false);
            }
          }}
        >
          <title id={titleId}>{copy.title}</title>
          <defs>
            <clipPath id={clipCells}>
              <rect ref={cellsClip} x={size.labelWidth} y={size.headerHeight} width={size.width} height={height} />
            </clipPath>
            <clipPath id={clipHeader}>
              <rect ref={headerClip} x={size.labelWidth} y={0} width={size.width} height={height} />
            </clipPath>
            <clipPath id={clipLabels}>
              <rect ref={labelsClip} x={0} y={size.headerHeight} width={size.width} height={height} />
            </clipPath>
          </defs>

          <g role="row" aria-rowindex={rowIndex++}>
            <g clipPath={`url(#${clipHeader})`}>
              <g style={stuckY}>
                <rect x={0} y={0} width={size.width} height={size.headerHeight} fill={PAPER} aria-hidden="true" />
                {Array.from({ length: size.columns }, (_, i) => {
                  const week = i + 1;
                  const x = size.labelWidth + i * size.cellWidth;
                  return (
                    <g key={week} role="columnheader" aria-label={copy.week(week)} aria-colindex={week + 1}>
                      {weeks.includes(week) ? (
                        <text x={x + size.cellWidth / 2} y={textY(0, size.headerHeight)} textAnchor="middle" fill={colour("ink-secondary")} className="tabular-nums">
                          {week}
                        </text>
                      ) : null}
                    </g>
                  );
                })}
              </g>
            </g>
            <g style={stuckXY}>
              <rect x={0} y={0} width={size.labelWidth} height={size.headerHeight} fill={PAPER} aria-hidden="true" />
              <g role="columnheader" aria-colindex={1}>
                <text x={1} y={textY(0, size.headerHeight)} fill={colour("ink-secondary")}>
                  {copy.gameHeader}
                </text>
                {copy.figureHeader ? (
                  <text x={size.figureRight} y={textY(0, size.headerHeight)} textAnchor="end" fill={colour("ink-secondary")}>
                    {copy.figureHeader}
                  </text>
                ) : null}
              </g>
              <line x1={0} x2={size.labelWidth} y1={size.headerHeight - 0.5} y2={size.headerHeight - 0.5} stroke={colour("axis")} aria-hidden="true" />
            </g>
          </g>

          {drawn.map(({ group, top, placed }) => (
            <g key={group.key} data-group={group.key}>
              <g role="row" aria-rowindex={rowIndex++}>
                <g clipPath={`url(#${clipLabels})`}>
                  <g style={stuckX}>
                    <g role="rowheader" aria-colspan={1 + size.columns}>
                      <text x={1} y={textY(top, size.groupHeight) + fontSize * 0.2} fontWeight={600} fill={INK} className="tabular-nums">
                        {group.title}
                      </text>
                    </g>
                  </g>
                </g>
              </g>
              {placed.map(({ row, y: rowY }) => (
                <Row
                  key={row.id}
                  row={row}
                  y={rowY}
                  rowIndex={rowIndex++}
                  size={size}
                  copy={copy}
                  format={format}
                  target={target}
                  showRing={hasFocus}
                  clipCells={clipCells}
                  clipLabels={clipLabels}
                  stuckX={stuckX}
                  textY={textY}
                />
              ))}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

function Row({
  row,
  y,
  rowIndex,
  size,
  copy,
  format,
  target,
  showRing,
  clipCells,
  clipLabels,
  stuckX,
  textY,
}: {
  row: WallRow;
  y: number;
  rowIndex: number;
  size: ReturnType<typeof wallSizes>;
  copy: MatrixWallCopy;
  format: (value: number) => string;
  target: WallPosition | null;
  showRing: boolean;
  clipCells: string;
  clipLabels: string;
  stuckX: { transform: string };
  textY: (top: number, h: number) => number;
}) {
  const h = size.rowHeight;
  const cellsEnd = size.labelWidth + row.values.length * size.cellWidth;
  return (
    <g role="row" aria-rowindex={rowIndex} data-row={row.id} data-y={y}>
      <g clipPath={`url(#${clipLabels})`}>
        <g style={stuckX}>
          <g role="rowheader" aria-label={row.rowName} aria-colindex={1}>
            <rect x={0} y={y} width={size.labelWidth} height={h} fill={PAPER} />
            <text x={1} y={textY(y, h)} fill={INK}>
              {row.label}
            </text>
            {row.figure ? (
              <text x={size.figureRight} y={textY(y, h)} textAnchor="end" fill={INK} className="tabular-nums">
                {row.figure}
              </text>
            ) : null}
          </g>
        </g>
      </g>
      <g clipPath={`url(#${clipCells})`}>
        {row.loading ? (
          <rect
            x={size.labelWidth}
            y={y + 2}
            width={SKELETON_CELLS * size.cellWidth}
            height={h - 4}
            fill={colour("hairline")}
            aria-hidden="true"
            data-skeleton=""
          />
        ) : null}
        {row.values.map((value, i) => {
          const week = i + 1;
          const step: NetStep = netStep(value);
          const x = size.labelWidth + i * size.cellWidth;
          const formatted = format(value);
          const shown = cellText(value, formatted, size.cellWidth, size.cellFont);
          const isTarget = target?.id === row.id && target.week === week;
          return (
            <g
              key={week}
              role="gridcell"
              aria-colindex={week + 1}
              aria-label={copy.cell(row, week, formatted)}
              tabIndex={isTarget ? 0 : -1}
              data-week={week}
              data-step={step}
              data-text={shown.kind}
              className="outline-none"
            >
              <rect x={x} y={y} width={size.cellWidth} height={h} fill={colour(stepFill(step))} stroke={PAPER} strokeWidth={1} />
              {shown.kind !== "blank" ? (
                <text
                  x={x + size.cellWidth / 2}
                  y={y + h / 2 + size.cellFont * 0.35}
                  textAnchor="middle"
                  fontSize={size.cellFont}
                  fill={colour(stepText(step))}
                  className="tabular-nums"
                >
                  {shown.text}
                </text>
              ) : null}
              {isTarget && showRing ? (
                // `focus-ring-inset`: a 2 px `ink` frame with a 1 px `paper` line inside it.
                <g aria-hidden="true" data-focus-ring="">
                  <rect x={x + 1} y={y + 1} width={size.cellWidth - 2} height={h - 2} fill="none" stroke={INK} strokeWidth={2} />
                  <rect x={x + 2.5} y={y + 2.5} width={size.cellWidth - 5} height={h - 5} fill="none" stroke={PAPER} strokeWidth={1} />
                </g>
              ) : null}
            </g>
          );
        })}
        {row.detail ? (
          // Its words are in the row header's name; drawn here as in `08-laerer-oversikt.png`.
          <text
            x={cellsEnd + Math.round(size.fontSize * 0.75)}
            y={textY(y, h)}
            fill={colour("ink-secondary")}
            aria-hidden="true"
            data-detail=""
          >
            {row.detail}
          </text>
        ) : null}
      </g>
    </g>
  );
}

/** Always visible above the wall: the swatches in step order with their bins, and what a «−» in
 * a cell means (DESIGN.md → Components → Matrisevegg → Legend). */
function Legend({ copy }: { copy: MatrixWallCopy }) {
  return (
    <div className="text-caption text-ink-secondary" data-wall-legend="">
      <ul aria-label={copy.legend} className="flex flex-wrap gap-x-4 gap-y-1">
        {NET_STEPS.map((step, i) => (
          <li key={step} className="inline-flex items-center gap-1.5 tabular-nums lining-nums">
            <svg width="12" height="12" aria-hidden="true" className="shrink-0">
              <rect width="12" height="12" fill={colour(stepFill(step))} />
            </svg>
            {copy.bins[i]}
          </li>
        ))}
      </ul>
      <p className="mt-1">{copy.minusNote}</p>
    </div>
  );
}
