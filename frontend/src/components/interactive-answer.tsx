"use client";

import { type ReactNode, useId } from "react";

import { AxisLabels } from "@/components/charts/axis-labels";
import { PointMarks, TARGET } from "@/components/charts/point-graph";
import { niceTicks, scaleY } from "@/components/charts/scales";
import { type FieldSize, type FixedLayout, fixedCell, type GraphField, GraphOverTable } from "@/components/graph-over-table";
import { answerAxis, graphDomain, startValue, tableValues } from "@/components/interactive-values";
import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

const copy = nb.tests.individual.interactive;
const drawn = nb.tests.individual.drawn;
const LINE = "text-body-phone text-ink lg:text-body";

/**
 * The Interaktiv oppgave (Stories 11.5 and 11.14, FR-80, UX-DR38, AD-18): one graph over one value
 * table as one answer. The drawn item's graph field, the read-only table of a handed-in answer and
 * the answer's image over its table live here since Story 13.10, when the Student report became the
 * second slice to show them (the test page is the first).
 */

/** A value table as the api sends it (`TableOut`): one row label per Uke, the given columns, the
 * asked column's label and, for a drawn item, its graph's axis. */
export type InteractiveTable = {
  prompt: string;
  hint?: string | null;
  caption: string;
  rows: readonly string[];
  columns: readonly { label: string; values: readonly number[] }[];
  asked_label: string;
  negative: boolean;
  axis?: { min: number; max: number } | null;
};

/** A number item's column as the api sends it (`ColumnOut`). */
export type InteractiveColumn = {
  prompt: string;
  caption: string;
  rows: readonly { label: string; value: number }[];
  asked_label: string;
};

/** Where the points sit: the shown range, the plot's top and bottom, the ticks and each unanswered
 * Uke's resting place. */
export type PointGeometry = {
  domain: [number, number];
  top: number;
  bottom: number;
  ticks: number[];
  starts: number[];
};

/** About eleven lines of `caption` high: room for the axis' labels at any text size. */
export const POINT_FIELD_EM = 11;

/**
 * The graph field of an Interaktiv oppgave over its table's Uke columns: the range (the axis widened
 * to every value), the ticks and the axis labels, with `plot` drawing the points. With `targets` the
 * plot keeps half a 44 px slider target free above and below (the test page's sliders); without, a
 * caption line (the report's still image).
 */
export function pointField({
  key,
  values,
  axis,
  targets,
  plot,
}: {
  key: string;
  values: readonly (number | null)[];
  axis: { min: number; max: number };
  targets: boolean;
  plot: (size: FieldSize, geometry: PointGeometry) => ReactNode;
}): GraphField {
  const domain = graphDomain(axis, values);
  return {
    key,
    heightEm: POINT_FIELD_EM,
    interactive: targets,
    render: (size) => {
      // Room for half a point's target above the top and below the bottom of the range.
      const pad = targets ? Math.max(TARGET / 2, size.fontSize * 0.75) : size.fontSize * 0.75;
      const top = pad;
      const bottom = size.height - pad;
      const ticks = niceTicks(domain, bottom - top, size.fontSize);
      const y = scaleY(domain, top, bottom);
      const starts = values.map((_, i) => startValue(values, i, domain));
      return {
        plot: plot(size, { domain, top, bottom, ticks, starts }),
        axis: (
          <AxisLabels
            width={size.labelWidth}
            height={size.height}
            fontSize={size.fontSize}
            title={drawn.axisSvg}
            ticks={ticks.map((tick) => ({ y: y(tick), text: formatNumber(tick) }))}
          />
        ),
      };
    },
  };
}

/** A table item's answer, read-only: the given columns and the Student's value per Uke, or «Ikke
 * besvart» (the value table of Story 11.5 without its fields), in its own scrolling region. */
export function AnsweredTable({ table, value }: { table: InteractiveTable; value: unknown }) {
  const id = useId();
  const values = tableValues(value, table.rows.length);
  const head = "border-b border-axis py-2 pr-4 text-left align-bottom text-label font-semibold text-ink";
  const cell = "py-2 pr-4 text-right tabular-nums lining-nums";
  return (
    <div className="mt-3 flex flex-col gap-2">
      <p className={`${LINE} max-w-md`}>{table.prompt}</p>
      <ScrollRegion labelledBy={`${id}-caption`}>
        <table className="border-collapse text-left text-table-cell text-ink lg:text-table-cell-laptop">
          <caption id={`${id}-caption`} className="text-left text-label font-semibold text-ink">
            {table.caption}
          </caption>
          <thead>
            <tr>
              <th scope="col" className={`${head} sticky left-0 z-10 bg-paper`}>
                {copy.rowHeader}
              </th>
              {table.columns.map((column, index) => (
                <th key={index} scope="col" className={`${head} text-right`}>
                  {column.label}
                </th>
              ))}
              <th scope="col" className={`${head} text-right`}>
                {table.asked_label}
              </th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((label, row) => (
              <tr key={row} className="border-b border-hairline">
                <th scope="row" className="sticky left-0 z-10 min-w-24 bg-paper py-2 pr-4 text-left font-normal whitespace-nowrap">
                  {label}
                </th>
                {table.columns.map((column, index) => (
                  <td key={index} className={cell}>
                    {column.values[row] === undefined ? "" : formatNumber(column.values[row])}
                  </td>
                ))}
                <td className={`${cell} font-bold`}>
                  {values[row] === null ? <span className="font-normal text-ink-muted">{copy.notAnswered}</span> : formatNumber(values[row])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollRegion>
    </div>
  );
}

/** The text of an Uke the Student left empty, in the report's narrow cells; its words are said
 * under the table. */
export const EMPTY_CELL = "–";

/**
 * A handed-in table or drawn answer as an image over its value table, at a fixed width for print
 * (Story 13.10, FR-58, AD-18): the Student's values as the drawn item's points and line (no point for
 * an Uke left empty) over the table with the Uker as columns, the given rows and then the Student's
 * row, every cell headed by its Uke (`th scope="col"`) and its row (`th scope="row"`). `from`/`to`
 * (1-based) draw a block of the Uker; the axis is the item's own, or one that holds 0, the given and
 * the answered values when the item has none (a «Fyll inn kolonnen» item).
 */
export function InteractiveAnswer({
  table,
  value,
  fixed,
  label,
  from = 1,
  to = table.rows.length,
}: {
  table: InteractiveTable;
  value: unknown;
  fixed: FixedLayout;
  label: string;
  from?: number;
  to?: number;
}) {
  const all = tableValues(value, table.rows.length);
  const axis = answerAxis(table.axis, [...table.columns, { values: all.filter((v): v is number => v !== null) }]);
  const shown = all.slice(from - 1, to);
  const rows = table.rows.slice(from - 1, to);
  const columns = rows.map((_, i) => ({ week: from + i, when: "past" as const, phone: true }));
  const field = pointField({
    key: "answer",
    // The range holds every value of the item, so each block is drawn on the same scale.
    values: all,
    axis,
    targets: false,
    plot: (size, geometry) => (
      <PointMarks
        width={size.width}
        height={size.height}
        xs={size.xs}
        values={shown}
        domain={geometry.domain}
        top={geometry.top}
        bottom={geometry.bottom}
        title={drawn.svg(table.caption)}
        ticks={geometry.ticks}
      />
    ),
  });
  const labelCell = "py-1 text-left align-top text-label font-normal text-ink";
  const valueCell = "py-1 text-right align-top tabular-nums lining-nums";
  return (
    <GraphOverTable
      label={label}
      columns={columns}
      fields={[field]}
      fixed={fixed}
      bleed={false}
      head={
        <tr className="border-b border-axis">
          <th scope="row" style={fixedCell(fixed, "label")} className={`${labelCell} font-semibold`}>
            {copy.rowHeader}
          </th>
          {rows.map((row, i) => (
            <th key={row} scope="col" data-col={from + i} style={fixedCell(fixed, "week")} className="py-1 text-right align-bottom text-label font-semibold text-ink">
              {row}
            </th>
          ))}
        </tr>
      }
      body={
        <>
          {table.columns.map((column) => (
            <tr key={column.label} className="border-b border-hairline">
              <th scope="row" style={fixedCell(fixed, "label")} className={labelCell}>
                {column.label}
              </th>
              {rows.map((row, i) => {
                const given = column.values[from - 1 + i];
                return (
                  <td key={row} style={fixedCell(fixed, "week")} className={valueCell}>
                    {given === undefined ? EMPTY_CELL : formatNumber(given)}
                  </td>
                );
              })}
            </tr>
          ))}
          <tr className="border-b border-hairline" data-answer-row="">
            <th scope="row" style={fixedCell(fixed, "label")} className={`${labelCell} font-semibold`}>
              {table.asked_label}
            </th>
            {shown.map((cell, i) => (
              <td key={i} style={fixedCell(fixed, "week")} className={`${valueCell} font-semibold`}>
                {cell === null ? EMPTY_CELL : formatNumber(cell)}
              </td>
            ))}
          </tr>
        </>
      }
    />
  );
}

/** A number item's column with the Student's answer in its asked row, for print (Story 13.10): a
 * plain table with its caption and header cells. */
export function AnsweredColumn({ column, value, texts }: { column: InteractiveColumn; value: number | null; texts: { row: string; value: string } }) {
  const head = "border-b border-axis py-1 pr-4 text-left align-bottom font-semibold";
  return (
    <table className="mt-3 w-full max-w-md table-fixed border-collapse text-body" data-answer-column="">
      <caption className="text-left text-label text-ink-secondary">{column.caption}</caption>
      <thead>
        <tr>
          <th scope="col" className={`w-3/5 ${head}`}>
            {texts.row}
          </th>
          <th scope="col" className={`${head} text-right`}>
            {texts.value}
          </th>
        </tr>
      </thead>
      <tbody>
        {column.rows.map((row) => (
          <tr key={row.label} className="border-b border-hairline">
            <th scope="row" className="py-1 pr-4 text-left font-normal">
              {row.label}
            </th>
            <td className="py-1 text-right tabular-nums">{formatNumber(row.value)}</td>
          </tr>
        ))}
        <tr className="border-b border-hairline" data-answer-row="">
          <th scope="row" className="py-1 pr-4 text-left font-semibold">
            {column.asked_label}
          </th>
          <td className="py-1 text-right font-semibold tabular-nums">{value === null ? copy.notAnswered : formatNumber(value)}</td>
        </tr>
      </tbody>
    </table>
  );
}
