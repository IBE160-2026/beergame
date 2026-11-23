"use client";

import { useId } from "react";

import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { MyTestItem } from "./api";
import type { AnswerValue } from "./autosave";
import { itemAnchor, itemLabel, itemLines } from "./individual-test";
import { numberValue, tableValues } from "./interactive";

const copy = nb.tests.individual;
const LINE = "text-body-phone text-ink lg:text-body";

type Table = NonNullable<MyTestItem["table"]>;

const valueOf = (item: MyTestItem): AnswerValue => (item.answer?.value ?? null) as AnswerValue;

/** One handed-in answer as text, never a field: «Ditt svar: Alternativ B», the number, the long
 * text with its paragraphs, or «Ikke besvart». No right or wrong state (FR-54). */
function AnswerText({ item }: { item: MyTestItem }) {
  const value = valueOf(item);
  const muted = `${LINE} mt-2 text-ink-muted`;
  if (item.type === "choice") {
    return typeof value === "string" ? (
      <p className={`${LINE} mt-2`}>{copy.submit.answerLine(copy.submit.yourAnswer, copy.option(value))}</p>
    ) : (
      <p className={muted}>{copy.interactive.notAnswered}</p>
    );
  }
  if (item.type === "number") {
    const number = numberValue(value);
    const label = item.column?.asked_label ?? copy.submit.yourAnswer;
    return number === null ? (
      <p className={muted}>{copy.interactive.notAnswered}</p>
    ) : (
      <p className={`${LINE} mt-2 tabular-nums`}>{copy.submit.answerLine(label, formatNumber(number))}</p>
    );
  }
  if (typeof value === "string" && value.trim() !== "") {
    return (
      <div className="mt-2">
        <p className="text-label font-semibold text-ink-secondary">{copy.submit.yourAnswer}</p>
        <p className={`${LINE} mt-1 max-w-2xl whitespace-pre-wrap break-words`}>{value}</p>
      </div>
    );
  }
  return <p className={muted}>{copy.interactive.notAnswered}</p>;
}

/** A table item's answer, read-only: the given columns and the Student's value per Uke, or «Ikke
 * besvart» (the value table of Story 11.5 without its fields), in its own scrolling region. */
function AnsweredTable({ item, table }: { item: MyTestItem; table: Table }) {
  const id = useId();
  const values = tableValues(valueOf(item), table.rows.length);
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
                {copy.interactive.rowHeader}
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
                  {values[row] === null ? <span className="font-normal text-ink-muted">{copy.interactive.notAnswered}</span> : formatNumber(values[row])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollRegion>
    </div>
  );
}

/**
 * The handed-in test (Story 11.10, FR-51, UX-DR65): every item in order with its question and the
 * Student's answer as text. Nothing can be changed, and no score shows (FR-54).
 */
export function SubmittedItems({ items }: { items: readonly MyTestItem[] }) {
  return (
    <ol className="mt-2">
      {items.map((item) => {
        const lines = itemLines(item);
        return (
          <li key={item.id} id={itemAnchor(item.number)} data-test-item={item.id} className="border-t border-hairline py-4">
            <h3 className="text-step-title font-semibold text-ink">
              {lines.heading}
              <span className="ml-3 text-body-phone font-normal text-ink-secondary lg:text-body">{lines.type}</span>
            </h3>
            {(item.type === "table" || item.type === "drawn") && item.table ? (
              <AnsweredTable item={item} table={item.table} />
            ) : (
              <>
                <p className={`${LINE} mt-2 max-w-2xl`}>{item.type === "number" && item.column ? item.column.prompt : itemLabel(item).label}</p>
                <AnswerText item={item} />
              </>
            )}
          </li>
        );
      })}
    </ol>
  );
}
