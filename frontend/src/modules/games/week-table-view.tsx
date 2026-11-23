"use client";

import type { CSSProperties } from "react";

import { AxisLabels } from "@/components/charts/axis-labels";
import { CostBars, costScale } from "@/components/charts/cost-bars";
import { NetGraph, netScale } from "@/components/charts/net-graph";
import { costAxisTop } from "@/components/charts/scales";
import { type FieldSize, type FixedLayout, fixedCell, type GraphField, GraphOverTable } from "@/components/graph-over-table";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import type { Projection } from "@/lib/preview";
import { cn } from "@/lib/utils";

import type { SeatState } from "./api";
import {
  type Cell,
  cellFor,
  type Column,
  type GraphSeries,
  graphSeries,
  ALL_ROWS,
  CAPPED_ROWS,
  type NetStep,
  type Row,
  ROWS,
  type TypedOrder,
  weekColumns,
} from "./week-table";

const copy = nb.games.play.table;
const graphCopy = nb.games.play.graph;

/** Matrix-step fills with their text token: `ink` on steps 1–2, `paper` on 3–4 (DESIGN.md). */
const NET_FILL: Record<NetStep, string> = {
  zero: "bg-net-zero text-ink",
  "pos-1": "bg-net-pos-1 text-ink",
  "pos-2": "bg-net-pos-2 text-ink",
  "pos-3": "bg-net-pos-3 text-paper",
  "pos-4": "bg-net-pos-4 text-paper",
  "neg-1": "bg-net-neg-1 text-ink",
  "neg-2": "bg-net-neg-2 text-ink",
  "neg-3": "bg-net-neg-3 text-paper",
  "neg-4": "bg-net-neg-4 text-paper",
};

// 1.6 em, so 12 columns fit at 360 px; a column whose number is wider grows to it plus a small
// side gap, so neighbouring numbers («−14», «−20», «27,5») never run together (DESIGN.md → Graf
// over tabell at narrow widths).
const WEEK_COL = "w-[1.6em] min-w-[1.6em] px-[0.1em] text-center";
/** A figure with few columns (the Landing's eight) widens them from 1024 px, so the graph is not
 * a narrow strip on a wide page. */
const WEEK_COL_WIDE = "lg:w-[5em] lg:min-w-[5em]";
/** Netto lager cells stand apart as separate squares, as drawn (`05-spill.png`). */
const NET_CELL = "shadow-[inset_0_0_0_1px_var(--color-paper)]";
const ROW_LABEL =
  "sticky left-0 z-10 min-w-row-label-phone bg-paper pr-2 text-left align-middle font-normal text-ink lg:min-w-row-label-laptop";

/** The Netto lager field's height and the Kost per uke field's, in em of the caption size. */
const NET_HEIGHT_EM = 7.5;
const COST_HEIGHT_EM = 3.2;

/** A column's visibility and tint: earlier than nå − 7 only in the laptop layout; right of nå on
 * `future-tint`. */
function columnClass(column: Column) {
  return cn(!column.phone && "hidden lg:table-cell", column.when === "future" && "bg-future-tint");
}

type ProjectionPoint = { week: number; x: number; value: number };

/**
 * The projection's line over the drawn columns (Story 10.4, UX-DR19): from Netto lager at nå to
 * its value at nå + horizon, at the centres of those columns. A horizon past the last drawn column
 * (the axis stops at nå + 4) keeps the same straight line up to that column, `clipped`, so no dot
 * stands where the axis ends. Null when no column right of nå is drawn.
 */
export function projectionPoints(
  size: Pick<FieldSize, "columns" | "xs">,
  net: number,
  projection: Projection,
): { points: ProjectionPoint[]; clipped: boolean } | null {
  const now = size.columns.findIndex((column) => column.when === "now");
  if (now < 0) return null;
  const nowWeek = size.columns[now]!.week;
  const start = { week: nowWeek, x: size.xs[now]!, value: net };
  const at = size.columns.findIndex((column) => column.week === projection.week);
  if (at >= 0) return { points: [start, { week: projection.week, x: size.xs[at]!, value: projection.value }], clipped: false };
  const last = size.columns.length - 1;
  const edge = size.columns[last]!.week;
  if (edge <= nowWeek || projection.horizon <= 0) return null;
  const share = (edge - nowWeek) / projection.horizon;
  return { points: [start, { week: edge, x: size.xs[last]!, value: net + share * (projection.value - net) }], clipped: true };
}

/** The two graph fields over the table (Story 6.7, UX-DR16): Netto lager with the Posisjon line,
 * then Kost per uke. Each draws the Uker of its columns up to nå, from the api's values; with
 * `projection` (the Replay, Story 10.4) the dashed projection runs on from nå. */
function graphFields(state: SeatState, series: GraphSeries, projection?: Projection, ended = false): GraphField[] {
  const byWeek = new Map(series.weeks.map((week) => [week.week, week]));
  const drawn = (size: FieldSize) =>
    size.columns.flatMap((column, i) => {
      const week = column.when === "future" ? undefined : byWeek.get(column.week);
      return week ? [{ ...week, x: size.xs[i]! }] : [];
    });
  const top = costAxisTop(series.highest);
  const grown = top > costAxisTop(series.highestBefore);
  const topText = formatNumber(top);
  return [
    {
      key: "net",
      caption: graphCopy.netTitle,
      heightEm: NET_HEIGHT_EM,
      render: (size) => {
        const points = drawn(size);
        const ahead = projection ? projectionPoints(size, state.net_inventory, projection) : null;
        const scale = netScale({ height: size.height, fontSize: size.fontSize, points, projection: ahead?.points });
        return {
          plot: (
            <NetGraph
              width={size.width}
              height={size.height}
              fontSize={size.fontSize}
              points={points}
              nowX={size.nowX}
              title={graphCopy.netSvg}
              netLabel={ended ? "" : graphCopy.netLabel(state.net_inventory, formatNumber(Math.abs(state.net_inventory)))}
              positionLabel={ended ? "" : graphCopy.positionLabel(formatNumber(state.position))}
              nowLabel={ended ? "" : graphCopy.now}
              projection={ahead?.points}
              projectionClipped={ahead?.clipped}
            />
          ),
          axis: (
            <AxisLabels
              width={size.labelWidth}
              height={size.height}
              fontSize={size.fontSize}
              title={graphCopy.netAxisSvg}
              ticks={scale.ticks.map((tick) => ({ y: scale.y(tick), text: formatNumber(tick) }))}
            />
          ),
        };
      },
    },
    {
      key: "cost",
      caption: <CostKey rates={series.rates} grownTo={grown ? topText : null} />,
      heightEm: COST_HEIGHT_EM,
      render: (size) => {
        const y = costScale(size.height, size.fontSize, top);
        return {
          plot: (
            <CostBars
              width={size.width}
              height={size.height}
              fontSize={size.fontSize}
              bars={drawn(size)}
              barWidth={Math.max(4, Math.round(size.columnWidth * 0.55))}
              top={top}
              nowX={size.nowX}
              title={graphCopy.costSvg}
            />
          ),
          axis: (
            <AxisLabels
              width={size.labelWidth}
              height={size.height}
              fontSize={size.fontSize}
              title={graphCopy.costAxisSvg}
              ticks={[{ y: y(top), text: graphCopy.costTick(topText) }]}
            />
          ),
        };
      },
    },
  ];
}

/** «Kost per uke ■ restordre 1,00 / ■ lager 0,50», and in the Uke the axis grows, the line that
 * says so. */
function CostKey({ rates, grownTo }: { rates: GraphSeries["rates"]; grownTo: string | null }) {
  // A filled square drawn as a border, so it is no text background.
  const swatch = "mr-1 inline-block h-0 w-0 border-[0.35em] align-[-0.05em]";
  return (
    <>
      <span className="mr-2 text-ink">{graphCopy.costTitle}</span>
      <span className="whitespace-nowrap">
        <span aria-hidden="true" className={cn(swatch, "border-restordre")} />
        {graphCopy.backorderKey(rates.backorder)}
      </span>
      {" / "}
      <span className="whitespace-nowrap">
        <span aria-hidden="true" className={cn(swatch, "border-lager")} />
        {graphCopy.holdingKey(rates.holding)}
      </span>
      {grownTo ? <span className="block text-ink">{graphCopy.axisGrown(grownTo)}</span> : null}
    </>
  );
}

/**
 * Graf over tabell on the play screen (Stories 6.6 and 6.7, FR-23, UX-DR16, UX-DR17, UX-DR18): the
 * Seat's Uker as columns up to nå + 4, never the end of the game, with the Netto lager and
 * Posisjon graph and Kost per uke over them on the same columns, and the now-line «Nå» through
 * both. One scroll region named «Graf og tabell»; see `GraphOverTable`. The cells take no focus;
 * the region does, so arrow keys scroll it. With `fixed`, every width is given (the print page).
 */
export function WeekTable({
  state,
  fixed,
  nowOrder,
  typed,
  labelledBy,
  wide = false,
  movedFrom,
  skipMove,
  onMoving,
  allRows = false,
  capped = false,
  label,
  projection,
  span,
}: {
  state: SeatState;
  /**
   * A finished game's Uker `from` … `to` (the Student report, Story 13.8): every column is past,
   * with no nå, no Uker ahead, no «Nå» and no direct labels, and Din ordre of the last Uke
   * (`nowOrder`) is a plain number. `state` is the Seat in its last opened Week. The report draws
   * a long game in several blocks, each a `span` of at most the columns A4 holds.
   */
  span?: { from: number; to: number };
  /** The Replay's projection (Story 10.4, UX-DR19): the dashed line over the graph and its
   * sentence under the table. Only a play envelope with `projection` passes it. */
  projection?: Projection;
  fixed?: FixedLayout;
  /** An Order already placed at nå (a Veiledet uke's fixed Order), written in Din ordre. */
  nowOrder?: number;
  /** A valid typed Order (Story 6.11), or the sent one (`confirmed`, Story 6.12): written at nå
   * and at its arrival Uke, joined by a thin line. Ignored when `nowOrder` is given. */
  typed?: TypedOrder;
  /** The id of the element that names the table (the Landing's caption). */
  labelledBy?: string;
  /** Wider week columns from 1024 px (see `WEEK_COL_WIDE`). */
  wide?: boolean;
  /** The Uke that was nå before a live advance: the now-line moves from it (Story 6.15). */
  movedFrom?: number;
  /** Raised by «Hopp over» to end the move at once. */
  skipMove?: number;
  onMoving?: (moving: boolean) => void;
  /** Every row at every width, with Lager, Restordre and «Sum, kr» (Alle rader, Story 6.16). */
  allRows?: boolean;
  /** A capped Seat (Story 6.22): Lager and Restordre above Netto lager at every width. */
  capped?: boolean;
  /** The region's name when not the play screen's «Graf og tabell» (the Debrief's moments). */
  label?: string;
}) {
  const columns: Column[] = span
    ? Array.from({ length: Math.max(0, Math.min(span.to, state.week) - span.from + 1) }, (_, i) => ({
        week: span.from + i,
        when: "past",
        phone: true,
      }))
    : weekColumns(state.week);
  const series = graphSeries(state);
  const weekCol = cn(WEEK_COL, wide && WEEK_COL_WIDE);
  const weekCell = fixedCell(fixed, "week");
  const labelCell = fixedCell(fixed, "label");
  const table = (
    <GraphOverTable
      label={label ?? copy.region}
      columns={columns}
      fields={graphFields(state, series, projection, span !== undefined)}
      fixed={fixed}
      labelledBy={labelledBy}
      swipe={copy.swipe}
      joinKey={typed && nowOrder === undefined ? `${typed.order}@${typed.arrivalWeek}` : undefined}
      movedFrom={movedFrom}
      skip={skipMove}
      onMoving={onMoving}
      footer={
        span ? undefined : (
        <p className="mt-1 text-caption text-ink-secondary">
          <span aria-hidden="true" className="mr-1 inline-block h-[0.9em] w-[1.2em] border border-ink align-[-0.1em]" />
          {copy.arrivalKey}
        </p>
        )
      }
      head={
        <tr className="border-b border-axis">
          <th scope="row" className={ROW_LABEL} style={labelCell}>
            {nb.terms.week}
          </th>
          {columns.map((column) => (
            <th
              key={column.week}
              scope="col"
              data-col={column.week}
              data-now={column.when === "now" ? "" : undefined}
              style={weekCell}
              className={cn(
                weekCol,
                "h-row-phone lg:h-row-laptop",
                // Only nå is bold ink; the other Uke numbers are grey, as axis labels (`05-spill.png`).
                column.when === "now" ? "font-bold text-ink" : "font-normal text-ink-muted",
                columnClass(column),
              )}
            >
              <span className="sr-only">{nb.terms.week} </span>
              {column.week}
            </th>
          ))}
        </tr>
      }
      body={(allRows ? ALL_ROWS : capped ? CAPPED_ROWS : ROWS).map((row) => (
        <tr key={row.key} data-row={row.key} className={cn("border-b border-hairline", row.laptopOnly && "hidden lg:table-row")}>
          <th scope="row" className={ROW_LABEL} style={labelCell}>
            {row.label}
          </th>
          {columns.map((column) => (
            <WeekCell
              key={column.week}
              column={column}
              cell={span ? endedCell(cellFor(state, row.key, column.week, nowOrder)) : cellFor(state, row.key, column.week, nowOrder, typed)}
              weekCol={weekCol}
              style={weekCell}
            />
          ))}
        </tr>
      ))}
    />
  );
  if (!projection) return table;
  return (
    <>
      {table}
      <ProjectionSentence projection={projection} />
    </>
  );
}

/**
 * The projection's sentence (Story 10.4, UX-DR19, NFR-6): the dashed line's text alternative, read
 * as text (the graph is `aria-hidden`) and wrapped to the page width under the table. A short
 * dashed rule before it ties it to the line by stroke, not by colour alone. Its sum keeps to one
 * line (non-breaking spaces in `nb.ts`, Story 10.6); only on a line narrower than the sum itself
 * (200 % text at 320 px) does `overflow-wrap` break it, so the page never scrolls sideways.
 */
export function ProjectionSentence({ projection }: { projection: Projection }) {
  const text = graphCopy.projection(
    projection.horizon,
    formatNumber(projection.position),
    projection.order === null ? null : formatNumber(projection.order),
    formatNumber(projection.horizon),
    formatNumber(projection.incoming),
    formatNumber(projection.value),
  );
  return (
    <p
      data-projection-sentence=""
      className="mt-2 max-w-prose px-[calc(var(--spacing-gutter-phone)-var(--spacing-gutter-phone-chart))] text-body-phone text-ink-secondary [overflow-wrap:anywhere] lg:px-0 lg:text-body"
    >
      <span aria-hidden="true" className="mr-2 inline-block w-[1.6em] border-t-2 border-dashed border-projection align-middle" />
      {text}
    </p>
  );
}

/** The Netto lager field's height in Hjem's Spillkort, in em of the caption size. */
const MINI_NET_HEIGHT_EM = 6.5;

/** The Spillkort's three rows (DESIGN.md → Spillkort): Uke (the header row), Netto lager, Din ordre. */
const MINI_ROWS: readonly Row[] = ROWS.filter((row) => row.key === "netInventory" || row.key === "order");

/**
 * Graf over tabell at mini scale, for Hjem's Spillkort (Story 6.17, UX-DR28, DESIGN.md → Spillkort):
 * the phone's window nå − 7 … nå + 4 at every width, never further right than nå + 4. Over the
 * rows Uke, Netto lager and Din ordre stands the Netto lager line alone (`NetGraph` `mini`). It
 * reuses the play screen's cells and graph tokens and adds no mark. `nowOrder` is the own Order
 * at nå once placed. The graph is `aria-hidden`; the table is real text.
 */
export function MiniWeekTable({ state, nowOrder, label }: { state: SeatState; nowOrder?: number; label: string }) {
  // The phone's columns only: each is flagged `phone`, so no column is hidden at any width.
  const columns = weekColumns(state.week).filter((column) => column.phone);
  const series = graphSeries(state);
  const byWeek = new Map(series.weeks.map((week) => [week.week, week]));
  const field: GraphField = {
    key: "net",
    heightEm: MINI_NET_HEIGHT_EM,
    render: (size) => {
      const points = size.columns.flatMap((column, i) => {
        const week = column.when === "future" ? undefined : byWeek.get(column.week);
        return week ? [{ ...week, x: size.xs[i]! }] : [];
      });
      const scale = netScale({ height: size.height, fontSize: size.fontSize, points, mini: true });
      return {
        plot: (
          <NetGraph
            mini
            width={size.width}
            height={size.height}
            fontSize={size.fontSize}
            points={points}
            nowX={size.nowX}
            title={graphCopy.netMiniSvg}
            netLabel=""
            positionLabel=""
            nowLabel={graphCopy.now}
          />
        ),
        axis: (
          <AxisLabels
            width={size.labelWidth}
            height={size.height}
            fontSize={size.fontSize}
            title={graphCopy.netMiniAxisSvg}
            ticks={scale.ticks.map((tick) => ({ y: scale.y(tick), text: formatNumber(tick) }))}
          />
        ),
      };
    },
  };
  return (
    <GraphOverTable
      label={label}
      columns={columns}
      fields={[field]}
      bleed={false}
      head={
        <tr className="border-b border-axis">
          <th scope="row" className={ROW_LABEL}>
            {nb.terms.week}
          </th>
          {columns.map((column) => (
            <th
              key={column.week}
              scope="col"
              data-col={column.week}
              data-now={column.when === "now" ? "" : undefined}
              className={cn(
                WEEK_COL,
                "h-row-phone lg:h-row-laptop",
                column.when === "now" ? "font-bold text-ink" : "font-normal text-ink-muted",
                columnClass(column),
              )}
            >
              <span className="sr-only">{nb.terms.week} </span>
              {column.week}
            </th>
          ))}
        </tr>
      }
      body={MINI_ROWS.map((row) => (
        <tr key={row.key} data-row={row.key} className="border-b border-hairline">
          <th scope="row" className={ROW_LABEL}>
            {row.label}
          </th>
          {columns.map((column) => (
            <WeekCell key={column.week} column={column} cell={cellFor(state, row.key, column.week, nowOrder)} weekCol={WEEK_COL} />
          ))}
        </tr>
      ))}
    />
  );
}

/** A finished game's cell (`span`): its last Uke's Order is a plain number like every other Uke's,
 * and a missing one an empty cell, never nå's block or the dashed box. */
function endedCell(cell: Cell): Cell {
  if (cell.kind === "order-placed") return { kind: "plain", text: cell.text };
  if (cell.kind === "order-empty") return { kind: "empty" };
  return cell;
}

function WeekCell({ column, cell, weekCol, style }: { column: Column; cell: Cell; weekCol: string; style?: CSSProperties }) {
  const base = cn(weekCol, "h-row-phone lg:h-row-laptop", columnClass(column));
  switch (cell.kind) {
    case "net":
      return (
        <td style={style} className={cn(base, NET_CELL, NET_FILL[cell.step])}>
          {cell.text}
        </td>
      );
    case "plain":
      return (
        <td style={style} className={base}>
          {cell.text}
        </td>
      );
    case "arrival":
      return (
        <td style={style} className={base}>
          <span className="inline-block min-w-[1.3em] border border-ink leading-tight">{cell.text}</span>
          <span className="sr-only">, {copy.arrival}</span>
        </td>
      );
    case "order-placed":
      return (
        // DESIGN.md → Graf over tabell: the Din ordre cell for nå is an `ink` block with a `paper` number.
        <td style={style} className={cn(base, NET_CELL, "bg-ink font-bold text-paper")}>
          {cell.text}
        </td>
      );
    case "order-typed":
      return (
        <td data-join="from" style={style} className={cn(base, NET_CELL, "bg-ink font-bold text-paper")}>
          {cell.text}
          <span className="sr-only">, {cell.confirmed ? copy.confirmed : copy.typed}</span>
        </td>
      );
    case "arrival-typed":
      return (
        <td style={style} className={base}>
          {cell.known === null ? null : (
            <>
              <span className="inline-block min-w-[1.3em] border border-ink leading-tight">{cell.known}</span>
              <span className="sr-only">, {copy.arrival}, </span>
            </>
          )}
          {/* The typed Order's arrival: a 1.5 px `ink` box, the number bold (`05-spill.png`). */}
          <span data-join="to" className="inline-block min-w-[1.3em] border-[1.5px] border-ink font-bold leading-tight">
            {cell.text}
          </span>
          <span className="sr-only">, {cell.confirmed ? copy.confirmed : copy.typed}</span>
        </td>
      );
    case "order-empty":
      return (
        <td style={style} className={base}>
          <span aria-hidden="true" className="mx-auto block h-[1.1em] w-[1.3em] border border-dashed border-ink-muted" />
          <span className="sr-only">{copy.noOrderYet}</span>
        </td>
      );
    default:
      return <td style={style} className={base} />;
  }
}
