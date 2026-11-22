import type { Ref } from "react";

import { formatNumber } from "@/lib/number-format";

export type ColumnRow = { label: string; value: number };

/**
 * One column of the week table with one asked row (Story 6.3, UX-DR63; reused by the Individual
 * test, Epic 11): the given rows with their numbers, then the asked row with a number field
 * (`inputmode="numeric"`) whose label is the row's name. In the invalid state the field has the
 * `restordre` border and the reason sits under the table, tied to the field and announced as it
 * appears (`role="alert"`, on leaving the field or pressing the button). Once answered, the field
 * gives way to the answer, and `result` (the right or wrong line, in words) sits under the table;
 * `resultRef` takes focus there. Epic 11 renders no result, and names a scroll region by the
 * caption (`${id}-caption`).
 */
export function ColumnItem({
  id,
  caption,
  rows,
  askedLabel,
  hint,
  value,
  onChange,
  onBlur,
  onEnter,
  error,
  answer,
  result,
  inputRef,
  resultRef,
}: {
  id: string;
  caption: string;
  rows: readonly ColumnRow[];
  askedLabel: string;
  hint?: string | null;
  value?: string;
  onChange?: (text: string) => void;
  onBlur?: () => void;
  /** Enter in the field, e.g. to send the answer. */
  onEnter?: () => void;
  error?: string;
  /** The stored answer: the row shows it instead of the field. */
  answer?: string;
  result?: string;
  inputRef?: Ref<HTMLInputElement>;
  resultRef?: Ref<HTMLParagraphElement>;
}) {
  const inputId = `${id}-answer`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : "", error ? errorId : ""].filter(Boolean).join(" ") || undefined;
  const answered = answer !== undefined;
  const cell = "py-2 text-right font-normal tabular-nums lining-nums";
  return (
    <div className="flex flex-col gap-2">
      <table className="w-full max-w-xs border-collapse text-left text-table-cell text-ink lg:text-table-cell-laptop">
        <caption id={`${id}-caption`} className="mb-2 text-left text-label font-semibold text-ink">
          {caption}
        </caption>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-hairline">
              <th scope="row" className="py-2 pr-4 font-normal">
                {row.label}
              </th>
              <td className={cell}>{formatNumber(row.value)}</td>
            </tr>
          ))}
          <tr className="border-t border-axis">
            <th scope="row" className="py-2 pr-4 font-semibold">
              {answered ? askedLabel : <label htmlFor={inputId}>{askedLabel}</label>}
            </th>
            <td className={answered ? cell : "py-2 text-right"}>
              {answered ? (
                // The Student's own number, in a read-only box, so it never reads as a given cell.
                <span className="inline-block min-w-24 rounded-sm border border-axis bg-future-tint px-3 py-2">
                  {answer}
                </span>
              ) : (
                <input
                  id={inputId}
                  ref={inputRef}
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  value={value ?? ""}
                  onChange={(event) => onChange?.(event.target.value)}
                  onBlur={onBlur}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && onEnter) {
                      event.preventDefault();
                      onEnter();
                    }
                  }}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={describedBy}
                  className="min-h-control-height-phone w-24 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-right text-button font-bold text-ink tabular-nums hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre"
                />
              )}
            </td>
          </tr>
        </tbody>
      </table>
      {hint ? (
        <p id={hintId} className="text-body-phone text-ink-secondary">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-body-phone text-restordre">
          {error}
        </p>
      ) : null}
      {result ? (
        <p ref={resultRef} tabIndex={-1} className="text-body-phone font-semibold text-ink lg:text-body">
          {result}
        </p>
      ) : null}
    </div>
  );
}
