"use client";

// A client module only because the Interaktiv oppgave's graph field is drawn by a function the
// shared `GraphOverTable` calls: the print route still renders it on the server to complete HTML,
// and WeasyPrint runs no script (AD-18).
import type { FixedLayout } from "@/components/graph-over-table";
import { AnsweredColumn, InteractiveAnswer } from "@/components/interactive-answer";
import { numberValue, tableValues } from "@/components/interactive-values";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { DebriefText } from "@/modules/debrief/ai-text";

import { reportCopy } from "./copy";
import { answerBlocks, points, type TestData, type TestItem, type TestSection, testLine } from "./parts";

const copy = reportCopy.test;
const individual = nb.tests.individual;
const TEXT = "text-body text-ink";
const KEEP = "break-after-avoid";
/** An Interaktiv oppgave's columns at 13 px: «Uke 10» and five-digit values in 48 px, its row
 * labels in 160 px, ten Uker a block (640 px of A4's 672). */
const FIXED: FixedLayout = { labelWidth: 160, columnWidth: 48, fontSize: 13 };
const MOST_UKER = 10;

/**
 * The Individual test section (Story 13.10, FR-58, C-2): when it was handed in, then every item in
 * its frozen order with its question (an Adapted item's wording, «KI-generert, kan ta feil: «…»»
 * and `data-ai-generated` when an AI worded it), the Student's answer and, for multiple-choice and
 * Interactive items, the points the code computed and stored at the hand-in. A table or drawn
 * Interaktiv oppgave is drawn as an image of the answer over its value table (the components'
 * `InteractiveAnswer`), a number item as its column with the answer. No AI score, feedback or
 * Indicative letter.
 */
export function TestSectionView({ section }: { section: TestSection }) {
  const test = section.test;
  return (
    <section aria-labelledby="report-test" className="mt-8" data-section="test">
      <h2 id="report-test" className="text-step-title font-semibold text-ink">
        {copy.title}
      </h2>
      {test ? <Taken test={test} /> : <p className={`mt-3 ${TEXT}`}>{copy.none}</p>}
    </section>
  );
}

function Taken({ test }: { test: TestData }) {
  return (
    <>
      <p className={`mt-3 ${TEXT}`} data-test-state={test.state}>
        {testLine(test)}
      </p>
      <p className={`mt-2 ${TEXT}`}>{copy.scoring}</p>
      {test.points !== null ? (
        <p className={`mt-2 ${TEXT} font-semibold`} data-test-total="">
          {copy.total(points(test.points), points(test.points_of))}
        </p>
      ) : null}
      <ol className="mt-2 list-none pl-0">
        {test.items.map((item) => (
          <Item key={item.number} item={item} />
        ))}
      </ol>
    </>
  );
}

function Item({ item }: { item: TestItem }) {
  const question = item.table ? item.table.prompt : item.type === "number" && item.column ? item.column.prompt : null;
  return (
    <li className="mt-4 border-t border-hairline pt-3" data-test-item={item.number}>
      <h3 className={`text-label font-semibold text-ink ${KEEP}`}>
        {`${individual.item(item.number)}, ${individual.types[item.type]}`}
      </h3>
      <p className={`mt-1 ${TEXT} ${KEEP}`}>{question ?? <DebriefText text={item.title} />}</p>
      <Answer item={item} />
      {scoreLine(item) ? (
        <p className="mt-2 text-label text-ink-secondary" data-points="">
          {scoreLine(item)}
        </p>
      ) : null}
    </li>
  );
}

/** «Poeng: 7,5 av 15», that the code scores no long answer, or nothing (an attempt not handed in). */
export function scoreLine(item: Pick<TestItem, "points" | "weight" | "type">): string | null {
  if (item.points !== null && item.points !== undefined) return copy.points(points(item.points), points(item.weight));
  return item.type === "long" || item.type === "adapted" ? copy.notScored : null;
}

function Answer({ item }: { item: TestItem }) {
  const value: unknown = item.answer ?? null;
  const none = <p className={`mt-1 ${TEXT}`}>{individual.interactive.notAnswered}</p>;
  if ((item.type === "table" || item.type === "drawn") && item.table) {
    const table = item.table;
    const empty = tableValues(value, table.rows.length).some((cell) => cell === null);
    return (
      <>
        <p className={`mt-3 text-label font-semibold text-ink ${KEEP}`}>{table.caption}</p>
        {answerBlocks(table.rows.length, MOST_UKER).map((block) => (
          <div key={block.from} className="mt-2 break-inside-avoid" data-answer-image="">
            <InteractiveAnswer table={table} value={value} fixed={FIXED} label={copy.region(table.caption)} from={block.from} to={block.to} />
          </div>
        ))}
        {empty ? <p className="mt-1 text-label text-ink-secondary">{copy.empty}</p> : null}
      </>
    );
  }
  if (item.type === "number" && item.column) {
    return <AnsweredColumn column={item.column} value={numberValue(value)} texts={copy.column} />;
  }
  if (item.type === "choice") {
    return typeof value === "string" ? (
      <p className={`mt-1 ${TEXT}`}>{individual.submit.answerLine(copy.answer, individual.option(value))}</p>
    ) : (
      none
    );
  }
  if (item.type === "number") {
    const number = numberValue(value);
    return number === null ? none : <p className={`mt-1 ${TEXT}`}>{individual.submit.answerLine(copy.answer, formatNumber(number))}</p>;
  }
  if (typeof value === "string" && value.trim() !== "") {
    return (
      <>
        <p className="mt-1 text-label font-semibold text-ink-secondary">{copy.answer}</p>
        <p className={`mt-1 ${TEXT} border-l-2 border-axis pl-3 whitespace-pre-wrap`}>{value}</p>
      </>
    );
  }
  return none;
}
