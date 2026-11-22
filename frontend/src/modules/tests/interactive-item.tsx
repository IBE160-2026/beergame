"use client";

import { useId, useState } from "react";

import { ColumnItem } from "@/components/column-item";
import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { MyTestItem } from "./api";
import type { AnswerValue } from "./autosave";
import { cellText, numberValue, parseCell, sameValue, tableValues, withCell } from "./interactive";
import { SaveLine, useAutosave } from "./use-autosave";

const copy = nb.tests.individual.interactive;
const LINE = "text-body-phone text-ink lg:text-body";

type Table = NonNullable<MyTestItem["table"]>;
type Column = NonNullable<MyTestItem["column"]>;

/**
 * The texts the fields of an item show, kept in step with its answer: what the Student types
 * stays as typed (an invalid text is never sent), and an answer that changes from elsewhere
 * (another device, a refusal that brings back the stored one) replaces them. `send` hands a value
 * to the autosave and remembers it, so the answer coming back as stored changes no text.
 */
function useFieldTexts(value: AnswerValue, toTexts: (value: AnswerValue) => string[], pick: (value: AnswerValue) => void) {
  const [texts, setTexts] = useState(() => toTexts(value));
  const [errors, setErrors] = useState<ReadonlySet<number>>(() => new Set());
  const [sent, setSent] = useState<AnswerValue>(value);
  if (!sameValue(value, sent)) {
    // Set while rendering (React's pattern for state that follows a prop): no extra pass.
    setSent(value);
    setTexts(toTexts(value));
    setErrors(new Set());
  }
  const send = (next: AnswerValue) => {
    if (sameValue(next, sent)) return;
    setSent(next);
    pick(next);
  };
  return { texts, setTexts, errors, setErrors, sent, send };
}

/**
 * The value table of an Interaktiv oppgave (Story 11.5, FR-80, UX-DR38, DESIGN.md
 * `interactive-item`): an HTML table with its caption, column headings and one row per Uke, the
 * given columns, then one outlined numeric cell per Uke for the asked column. An Uke with no
 * value shows «Ikke besvart» in `ink-muted` beside its label. It scrolls sideways in its own
 * region with the row labels sticky, so the page never does (UX-DR75). Presentational: the values
 * come in and every typed text goes out, so the graph of Story 11.14 can sit over the same table.
 */
export function ValueTable({
  id,
  table,
  texts,
  answered,
  errors,
  onCellChange,
  onCellBlur,
}: {
  id: string;
  table: Table;
  texts: readonly string[];
  /** Per Uke: whether it holds a stored value (else «Ikke besvart»). */
  answered: readonly boolean[];
  /** The rows whose cell shows «Skriv et helt tall.». */
  errors: ReadonlySet<number>;
  onCellChange: (row: number, text: string) => void;
  onCellBlur: (row: number) => void;
}) {
  const captionId = `${id}-caption`;
  const errorId = `${id}-error`;
  const head = "border-b border-axis py-2 pr-4 text-left align-bottom text-label font-semibold text-ink";
  const given = "py-2 pr-4 text-right font-normal tabular-nums lining-nums";
  return (
    <div className="flex flex-col gap-2">
      {/* The caption shows over the region, so it never scrolls away with the columns. */}
      <p aria-hidden="true" className="text-label font-semibold text-ink">
        {table.caption}
      </p>
      <ScrollRegion labelledBy={captionId}>
        <table data-value-table className="border-collapse text-left text-table-cell text-ink lg:text-table-cell-laptop">
          <caption id={captionId} className="sr-only">
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
                <th scope="row" className="sticky left-0 z-10 min-w-24 bg-paper py-2 pr-4 text-left align-middle font-normal">
                  <span className="whitespace-nowrap">{label}</span>
                  {answered[row] ? null : (
                    <span data-not-answered className="block whitespace-nowrap text-label text-ink-muted">
                      {copy.notAnswered}
                    </span>
                  )}
                </th>
                {table.columns.map((column, index) => (
                  <td key={index} className={given}>
                    {column.values[row] === undefined ? "" : formatNumber(column.values[row])}
                  </td>
                ))}
                <td className="py-2 text-right">
                  <input
                    type="text"
                    // A phone's numeric keypad has no minus: a table that takes negative values
                    // gets the full keyboard.
                    inputMode={table.negative ? "text" : "numeric"}
                    autoComplete="off"
                    aria-label={copy.cell(table.asked_label, label)}
                    value={texts[row] ?? ""}
                    onChange={(event) => onCellChange(row, event.target.value)}
                    onBlur={() => onCellBlur(row)}
                    aria-invalid={errors.has(row) ? true : undefined}
                    aria-describedby={errors.has(row) ? errorId : undefined}
                    className="min-h-control-height-phone w-24 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-right text-button font-bold text-ink tabular-nums hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollRegion>
      {errors.size > 0 ? (
        <p id={errorId} role="alert" className="text-body-phone text-restordre">
          {copy.wholeNumber}
        </p>
      ) : null}
    </div>
  );
}

const tableTexts = (rows: number) => (value: AnswerValue) => tableValues(value, rows).map(cellText);

/**
 * A «Fyll inn kolonnen» item (Story 11.5): the prompt, the value table and the autosave line. A
 * cell's change is saved at once through Story 11.4's path: a whole number as typed, an emptied
 * cell or a text that is no whole number as no value for that Uke (the invalid text is never
 * sent, so what is stored never differs from what the cell holds as a number). On leaving such a
 * cell it shows «Skriv et helt tall.» with the error border (the Ordrefelt pattern). No right or
 * wrong state (FR-54).
 */
export function TableItem({ classSessionId, userId, item, table }: { classSessionId: string; userId: string; item: MyTestItem; table: Table }) {
  const id = useId();
  const { entry, line, pick } = useAutosave(classSessionId, userId, item);
  const rows = table.rows.length;
  const [toTexts] = useState(() => tableTexts(rows));
  const { texts, setTexts, errors, setErrors, sent, send } = useFieldTexts(entry.value, toTexts, pick);
  const change = (row: number, text: string) => {
    setTexts((was) => was.map((t, i) => (i === row ? text : t)));
    const cell = parseCell(text, table.negative);
    if (cell.kind !== "invalid") setErrors((was) => (was.has(row) ? new Set([...was].filter((r) => r !== row)) : was));
    send(withCell(tableValues(sent, rows), row, cell.kind === "value" ? cell.value : null));
  };
  const blur = (row: number) => {
    if (parseCell(texts[row] ?? "", table.negative).kind === "invalid") setErrors((was) => new Set(was).add(row));
  };
  return (
    <div className="mt-3">
      <p className={`${LINE} max-w-md`}>{table.prompt}</p>
      {table.hint ? <p className="mt-1 max-w-md text-body-phone text-ink-secondary">{table.hint}</p> : null}
      <div className="mt-3">
        <ValueTable
          id={id}
          table={table}
          texts={texts}
          answered={tableValues(sent, rows).map((v) => v !== null)}
          errors={errors}
          onCellChange={change}
          onCellBlur={blur}
        />
      </div>
      <SaveLine entry={entry} line={line} />
    </div>
  );
}

const numberTexts = (value: AnswerValue) => [cellText(numberValue(value))];

/**
 * A number item (Story 11.5): one column of given rows and the asked row, the Startoppgave's
 * column item reused (`components/column-item.tsx`, Story 6.3) with no result line. A Starting
 * task item takes its text from the Class session's Starting task; an Interactive number item has
 * its own. Each change is saved at once, a text that is no whole number as no answer; it shows
 * «Skriv et helt tall.» on leaving the field and is never sent.
 */
export function NumberItem({ classSessionId, userId, item, column }: { classSessionId: string; userId: string; item: MyTestItem; column: Column }) {
  const id = useId();
  const { entry, line, pick } = useAutosave(classSessionId, userId, item);
  const { texts, setTexts, errors, setErrors, send } = useFieldTexts(entry.value, numberTexts, pick);
  const text = texts[0] ?? "";
  const change = (next: string) => {
    setTexts([next]);
    const cell = parseCell(next, column.negative);
    if (cell.kind !== "invalid") setErrors(new Set());
    send(cell.kind === "value" ? cell.value : null);
  };
  const blur = () => {
    if (parseCell(text, column.negative).kind === "invalid") setErrors(new Set([0]));
  };
  return (
    <div className="mt-3 max-w-md">
      <p className={LINE}>{column.prompt}</p>
      {/* At 200 % text on a phone the column is wider than the screen: it scrolls on its own. */}
      <ScrollRegion labelledBy={`${id}-caption`} className="mt-3">
        <ColumnItem
          id={id}
          caption={column.caption}
          rows={column.rows}
          askedLabel={column.asked_label}
          hint={column.hint}
          value={text}
          onChange={change}
          onBlur={blur}
          error={errors.size > 0 ? copy.wholeNumber : undefined}
        />
      </ScrollRegion>
      <SaveLine entry={entry} line={line} />
    </div>
  );
}
