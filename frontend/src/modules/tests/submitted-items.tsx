"use client";

import { AnsweredTable } from "@/components/interactive-answer";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { MyTestItem } from "./api";
import type { AnswerValue } from "./autosave";
import { itemAnchor, itemLabel, itemLines } from "./individual-test";
import { numberValue } from "./interactive";

const copy = nb.tests.individual;
const LINE = "text-body-phone text-ink lg:text-body";

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
              <AnsweredTable table={item.table} value={item.answer?.value ?? null} />
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
