"use client";

import { useId, useRef, useState } from "react";

import { AxisLabels } from "@/components/charts/axis-labels";
import { PointGraph, TARGET } from "@/components/charts/point-graph";
import { niceTicks, scaleY } from "@/components/charts/scales";
import { type GraphColumn, type GraphField, GraphOverTable } from "@/components/graph-over-table";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { MyTestItem } from "./api";
import type { AnswerValue } from "./autosave";
import { cellText, graphDomain, parseCell, pointValue, startValue, stepValue, tableValues, withCell } from "./interactive";
import { CellInput, useFieldTexts } from "./interactive-item";
import { SaveLine, useAutosave } from "./use-autosave";

const copy = nb.tests.individual.interactive;
const drawn = nb.tests.individual.drawn;
const LINE = "text-body-phone text-ink lg:text-body";

type Table = NonNullable<MyTestItem["table"]>;

/** About eleven lines of `caption` high: room for the axis' labels at any text size. */
const HEIGHT_EM = 11;
const ROW_LABEL = "sticky left-0 z-10 min-w-row-label-phone bg-paper py-2 pr-4 text-left align-middle font-normal text-ink lg:min-w-row-label-laptop";
const UKE_COL = "border-b border-axis px-2 py-2 text-right align-bottom text-label font-semibold whitespace-nowrap text-ink";

const tableTexts = (rows: number) => (value: AnswerValue) => tableValues(value, rows).map(cellText);

/**
 * A drawn Interactive item (Story 11.14, FR-80, UX-DR38, AD-18): its prompt, then one graph over
 * its value table in one sideways scroll region (`GraphOverTable`), with the Uker as the table's
 * columns so each point stands over its Uke's cell. The graph and the table are one answer: a
 * point dragged, tapped or moved by keys writes its Uke's cell, and a typed cell moves its point;
 * each change is saved through Story 11.4's path as the table item's list of values. A text that
 * is no whole number is saved as no value for that Uke, never sent, and shows «Skriv et helt
 * tall.» on leaving the cell. A screen reader answers in the table; the points are the graph's
 * sliders. No right or wrong state (FR-54).
 */
export function DrawnItem({ classSessionId, userId, item, table }: { classSessionId: string; userId: string; item: MyTestItem; table: Table }) {
  const id = useId();
  const { entry, line, pick } = useAutosave(classSessionId, userId, item);
  const rows = table.rows.length;
  const [toTexts] = useState(() => tableTexts(rows));
  const { texts, setTexts, errors, setErrors, sent, send } = useFieldTexts(entry.value, toTexts, pick);
  const values = tableValues(sent, rows);
  const axis = table.axis ?? { min: 0, max: 10 };
  const domain = graphDomain(axis, values);
  const captionId = `${id}-caption`;
  const errorId = `${id}-error`;

  const clearError = (row: number) => setErrors((was) => (was.has(row) ? new Set([...was].filter((r) => r !== row)) : was));
  const change = (row: number, text: string) => {
    setTexts((was) => was.map((t, i) => (i === row ? text : t)));
    const cell = parseCell(text, table.negative);
    if (cell.kind !== "invalid") clearError(row);
    placed.current[row] = cell.kind === "value" ? cell.value : null;
    send(withCell(values, row, cell.kind === "value" ? cell.value : null));
  };
  const blur = (row: number) => {
    if (parseCell(texts[row] ?? "", table.negative).kind === "invalid") setErrors((was) => new Set(was).add(row));
  };
  // The last value a pointer placed per Uke: several moves before the next render place it once.
  const placed = useRef<(number | null)[]>([]);
  const place = (row: number, value: number) => {
    placed.current[row] = value;
    setTexts((was) => was.map((t, i) => (i === row ? cellText(value) : t)));
    clearError(row);
    send(withCell(values, row, value));
  };

  const columns: GraphColumn[] = table.rows.map((_, i) => ({
    week: i + 1,
    when: "past",
    phone: true,
  }));
  const field: GraphField = {
    key: "drawn",
    heightEm: HEIGHT_EM,
    interactive: true,
    render: (size) => {
      // Room for half a point's target above the top and below the bottom of the range.
      const pad = Math.max(TARGET / 2, size.fontSize * 0.75);
      const top = pad;
      const bottom = size.height - pad;
      const ticks = niceTicks(domain, bottom - top, size.fontSize);
      const y = scaleY(domain, top, bottom);
      const starts = values.map((_, i) => startValue(values, i, domain));
      return {
        plot: (
          <PointGraph
            width={size.width}
            height={size.height}
            xs={size.xs}
            values={values}
            starts={starts}
            domain={domain}
            top={top}
            bottom={bottom}
            title={drawn.svg(table.caption)}
            label={drawn.graph}
            names={table.rows}
            valueText={(i) => {
              const v = values[i];
              const week = table.rows[i] ?? "";
              return v === null || v === undefined ? drawn.notAnsweredText(week) : drawn.valueText(week, formatNumber(v), v);
            }}
            ticks={ticks}
            onKey={(i, key) => stepValue(key, values[i] ?? starts[i] ?? 0, domain)}
            onPointer={(i, at) => {
              const value = pointValue(at, top, bottom, domain, axis);
              if (placed.current[i] !== value) place(i, value);
            }}
            onPlace={place}
          />
        ),
        axis: (
          <AxisLabels
            width={size.labelWidth}
            height={size.height}
            fontSize={size.fontSize}
            title={drawn.axisSvg}
            ticks={ticks.map((tick) => ({
              y: y(tick),
              text: formatNumber(tick),
            }))}
          />
        ),
      };
    },
  };

  return (
    // On a laptop the graph and table reach past the items' text column, up to 64rem, so a test's
    // Uker fit without a sideways scroll while the screen has room (Epic 11 close-out).
    <div className="mt-3 lg:w-[min(64rem,calc(100vw-10rem))]" data-drawn-item="">
      <p className={`${LINE} max-w-md`}>{table.prompt}</p>
      {table.hint ? <p className="mt-1 max-w-md text-body-phone text-ink-secondary">{table.hint}</p> : null}
      <p className="mt-1 max-w-md text-body-phone text-ink-secondary">{drawn.howTo}</p>
      {/* The caption shows over the region, so it never scrolls away with the columns. */}
      <p aria-hidden="true" className="mt-3 mb-2 text-label font-semibold text-ink">
        {table.caption}
      </p>
      <GraphOverTable
        label={drawn.region(table.caption)}
        labelledBy={captionId}
        columns={columns}
        fields={[field]}
        bleed={false}
        head={
          <tr>
            <th scope="row" className={`${ROW_LABEL} border-b border-axis text-label font-semibold`}>
              {copy.rowHeader}
            </th>
            {table.rows.map((label, i) => (
              <th key={i} scope="col" data-col={i + 1} className={UKE_COL}>
                {label}
              </th>
            ))}
          </tr>
        }
        body={
          <>
            {table.columns.map((column, index) => (
              <tr key={index} className="border-b border-hairline">
                <th scope="row" className={ROW_LABEL}>
                  {column.label}
                </th>
                {table.rows.map((_, i) => (
                  <td key={i} className="px-2 py-2 text-right">
                    {column.values[i] === undefined ? "" : formatNumber(column.values[i])}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="border-b border-hairline">
              <th scope="row" className={ROW_LABEL}>
                {table.asked_label}
              </th>
              {table.rows.map((label, i) => (
                <td key={i} className="px-2 py-2 text-right align-top">
                  <CellInput
                    label={copy.cell(table.asked_label, label)}
                    text={texts[i] ?? ""}
                    negative={table.negative}
                    invalid={errors.has(i)}
                    errorId={errorId}
                    onChange={(text) => change(i, text)}
                    onBlur={() => blur(i)}
                  />
                  {values[i] === null ? (
                    <span data-not-answered className="mt-1 block text-label whitespace-nowrap text-ink-muted">
                      {copy.notAnswered}
                    </span>
                  ) : null}
                </td>
              ))}
            </tr>
          </>
        }
      />
      {/* The table's name for assistive technology (the visible caption is above the region). */}
      <span id={captionId} className="sr-only">
        {table.caption}
      </span>
      {errors.size > 0 ? (
        <p id={errorId} role="alert" className="mt-2 text-body-phone text-restordre">
          {copy.wholeNumber}
        </p>
      ) : null}
      <SaveLine entry={entry} line={line} />
    </div>
  );
}
