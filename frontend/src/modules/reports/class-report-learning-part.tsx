"use client";

import { useId } from "react";

import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";

import { type ClassLearning, useClassLearning } from "./class-report-api";
import { tenth } from "./class-report";
import {
  aiLine,
  bandRows,
  learningStatus,
  questionBars,
  questionLabel,
  questionRows,
  scoreSummary,
  startingBars,
  startingRows,
} from "./class-report-learning";
import {
  Bars,
  Distribution,
  SECONDARY,
  Section,
  Table,
  TEXT,
  Toggled,
} from "./class-report-parts";

const copy = nb.classReport.learning;

/**
 * The Klasserapport's learning part (Story 14.2, FR-64, FR-55, FR-56, FR-61, UX-DR55): the Starting
 * task beside the matching test items, results per question and the AI assessment totals with the
 * score on the Faste oppgaver. Read on its own (`useClassLearning`), so the games part shows while
 * it loads; `session:<id>` refetches both. Every number is the api's (AD-10); no Indicative letter
 * is ever shown (FR-56).
 */
export function LearningPart({ sessionId }: { sessionId: string }) {
  const found = useClassLearning(sessionId);
  const id = useId();
  const data = found.data;
  return (
    <section
      aria-labelledby={id}
      className="mt-14 min-w-0 border-t border-hairline pt-8"
      data-learning=""
    >
      <h2 id={id} className="text-headline text-ink">
        {copy.title}
      </h2>
      <p className={`mt-1 ${SECONDARY}`}>{copy.intro}</p>
      {data ? (
        <Learning data={data} />
      ) : found.isError ? (
        <p className={`mt-2 ${TEXT}`} data-learning-failed="">
          {copy.failed}{" "}
          <button
            type="button"
            className={LINK_BUTTON}
            onClick={() => void found.refetch()}
          >
            {nb.system.retry}
          </button>
        </p>
      ) : (
        <p className={`mt-2 ${SECONDARY}`} role="status">
          {nb.system.loading}
        </p>
      )}
    </section>
  );
}

function Learning({ data }: { data: ClassLearning }) {
  return (
    <>
      <p
        className={`mt-2 ${TEXT} font-semibold tabular-nums lining-nums`}
        data-learning-status=""
      >
        {learningStatus(data)}
      </p>
      <div className="mt-6 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
        <Starting starting={data.starting_task} />
        <Questions data={data} />
        <AiScores ai={data.ai} />
      </div>
    </>
  );
}

function Starting({ starting }: { starting: ClassLearning["starting_task"] }) {
  const shown = starting.students > 0 && starting.items.length > 0;
  return (
    <Section
      title={copy.starting.title}
      name="starting"
      intro={copy.starting.intro(starting.students)}
      level={3}
    >
      {!shown ? (
        <p className={`mt-2 ${TEXT}`}>{copy.starting.none}</p>
      ) : (
        <Toggled
          name="starting"
          chart={
            <ul data-starting-items="">
              {starting.items.map((item) => (
                <li
                  key={item.number}
                  className="mt-3 first:mt-1"
                  data-starting-item={item.number}
                >
                  <h4 className="text-label text-ink [overflow-wrap:anywhere]">
                    {copy.questionLabel(item.number, item.title)}
                  </h4>
                  <Bars
                    name={`starting-${item.number}`}
                    colour="border-order-history"
                    rows={startingBars(item)}
                  />
                </li>
              ))}
            </ul>
          }
          table={
            <Table
              name="starting"
              caption={copy.starting.tableCaption}
              columns={[
                copy.starting.questionColumn,
                copy.starting.studentsColumn,
                copy.starting.startColumn,
                copy.starting.rightColumn,
                copy.starting.meanColumn,
              ]}
              rows={startingRows(starting.items)}
            />
          }
        />
      )}
    </Section>
  );
}

function Questions({ data }: { data: ClassLearning }) {
  const excluded = data.questions.some((q) => q.excluded);
  return (
    <Section
      title={copy.questions.title}
      name="questions"
      intro={copy.questions.intro}
      level={3}
    >
      <Toggled
        name="questions"
        chart={
          <Bars
            name="questions"
            colour="border-lager"
            rows={questionBars(data.questions)}
          />
        }
        table={
          <Table
            name="questions"
            caption={copy.questions.tableCaption}
            columns={[
              copy.questions.questionColumn,
              copy.questions.handedInColumn,
              copy.questions.rightColumn,
              copy.questions.partlyColumn,
              copy.questions.wrongColumn,
              copy.questions.notAnsweredColumn,
              copy.questions.meanColumn,
            ]}
            rows={questionRows(data.questions)}
          />
        }
      />
      {excluded ? (
        <p className={`mt-2 ${SECONDARY}`} data-excluded-note="">
          {copy.questions.excludedNote}{" "}
          {data.questions
            .filter((q) => q.excluded)
            .map((q) => questionLabel(q))
            .join(", ")}
          .
        </p>
      ) : null}
      {data.adapted.weight > 0 ? (
        <p
          className={`mt-2 ${SECONDARY} tabular-nums lining-nums`}
          data-adapted-line=""
        >
          {copy.questions.adapted(
            data.adapted.weight,
            data.adapted.adapted,
            data.adapted.replaced,
          )}
        </p>
      ) : null}
    </Section>
  );
}

function AiScores({ ai }: { ai: ClassLearning["ai"] }) {
  const ready = ai.state === "ready" && (ai.total || ai.core);
  return (
    <Section title={copy.ai.title} name="ai-scores" level={3}>
      <p className={`mt-1 ${TEXT} font-semibold`} data-ai-label="">
        {copy.ai.label}
      </p>
      <p
        className={`mt-1 ${TEXT} tabular-nums lining-nums`}
        data-ai-state={ai.state}
      >
        {aiLine(ai)}
      </p>
      {ready ? (
        <>
          <p className={`mt-1 ${SECONDARY}`}>{copy.ai.note}</p>
          <Toggled
            name="ai-scores"
            chart={
              <ul>
                {(
                  [
                    ["total", copy.ai.totalTitle, ai.total],
                    ["core", copy.ai.coreTitle, ai.core],
                  ] as const
                )
                  .filter((entry) => entry[2] != null)
                  .map(([key, title, spread]) => (
                  <li key={key} className="mt-3 first:mt-1" data-score={key}>
                    <h4 className="text-label text-ink">{title}</h4>
                    <Distribution
                      name={`score-${key}`}
                      spread={spread!}
                      title={copy.ai.chartTitle(title, spread!.values.length)}
                      medianLabel={nb.classReport.median(tenth(spread!.median))}
                      formatTick={(tick) => tenth(tick).replace(/,0$/, "")}
                      highest={100}
                    />
                    <p
                      className={`${TEXT} tabular-nums lining-nums`}
                      data-score-line=""
                    >
                      {scoreSummary(spread!)}
                    </p>
                  </li>
                ))}
              </ul>
            }
            table={
              <Table
                name="ai-scores"
                caption={copy.ai.tableCaption}
                columns={[
                  copy.ai.bandColumn,
                  copy.ai.totalColumn,
                  copy.ai.coreColumn,
                ]}
                rows={bandRows(ai)}
              />
            }
          />
          <p className="mt-1 text-caption text-ink-secondary">{copy.ai.axis}</p>
        </>
      ) : null}
    </Section>
  );
}
