"use client";

import { type ReactNode, useId } from "react";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { gameInsightPath, studentDebriefPath } from "@/modules/identity/homes";
import { roleName } from "@/modules/sessions/sessions";

import {
  day,
  debriefLines,
  gameLines,
  quizLines,
  replayLine,
  type StudentRecord,
  testLines,
} from "./record";

const copy = nb.reports.record;

function Block({ title, name, children }: { title: string; name: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="mt-8 max-w-2xl border-t border-hairline pt-4" data-record={name}>
      <h2 id={id} className="text-headline text-ink">
        {title}
      </h2>
      <div className="mt-2 flex flex-col items-start gap-1 text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">
        {children}
      </div>
    </section>
  );
}

function Lines({ lines }: { lines: readonly string[] }) {
  return lines.map((line) => (
    <p key={line} className="tabular-nums lining-nums">
      {line}
    </p>
  ));
}

/**
 * The record blocks of the Studentside (Story 13.2, FR-63, UX-DR55), for the Lecturers and
 * Assistant lecturers of the Class, each read by the api through the owning module: «Spillet»
 * (with Spillinnsikt), «Debrief» (the Explanation as written, the summary's state, with the staff
 * Debrief summary), «Debrief-quiz» (each attempt, never the answers), «Replay» (with its
 * Spillinnsikt), «Individuell test» (status and which parts hold content, never the answers),
 * «KI-vurdering» (the state the api gives; Story 12.5's block takes this place) and the empty slot
 * for the Student report link that Story 13.12 fills.
 */
export function RecordBlocks({ record }: { record: StudentRecord }) {
  const sessionId = record.class_session_id;
  const test = testLines(record.test);
  const explanation = record.debrief.explanation;
  return (
    <>
      <Block title={copy.game.title} name="game">
        <Lines lines={gameLines(record.game, (role) => roleName(role as Parameters<typeof roleName>[0]))} />
        {record.game ? (
          <Link href={gameInsightPath(sessionId, record.game.game_id)} standalone data-record-insight="">
            {copy.game.insight}
          </Link>
        ) : null}
      </Block>
      <Block title={copy.debrief.title} name="debrief">
        <h3 className="text-label text-ink">{copy.debrief.explanation}</h3>
        {explanation ? (
          <>
            <p className="max-w-prose whitespace-pre-line" data-explanation="">
              {explanation}
            </p>
            {record.debrief.explanation_saved_at ? (
              <p className="text-ink-secondary">{copy.debrief.sent(day(record.debrief.explanation_saved_at))}</p>
            ) : null}
          </>
        ) : (
          <p>{copy.debrief.noExplanation}</p>
        )}
        <div className="mt-2">
          <Lines lines={debriefLines(record.debrief)} />
        </div>
        {record.debrief.finished_at || explanation ? (
          <Link href={studentDebriefPath(sessionId, record.user_id)} standalone data-record-summary="">
            {copy.debrief.summary}
          </Link>
        ) : null}
      </Block>
      <Block title={copy.quiz.title} name="quiz">
        <Lines lines={quizLines(record.quiz)} />
      </Block>
      <Block title={copy.replay.title} name="replay">
        <p>{replayLine(record.replay)}</p>
        {record.replay ? (
          <Link href={gameInsightPath(sessionId, record.replay.game_id)} standalone data-record-replay="">
            {copy.replay.insight}
          </Link>
        ) : null}
      </Block>
      <Block title={copy.test.title} name="test">
        <Lines lines={test.lines} />
        {test.parts.length > 0 ? (
          <>
            <h3 className="mt-2 text-label text-ink">{copy.test.partsTitle}</h3>
            <ul className="flex flex-col gap-1">
              {test.parts.map((part) => (
                <li key={part.name}>
                  {part.name}: {part.text}
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </Block>
      <Block title={copy.assessment.title} name="assessment">
        <p data-assessment-state={record.assessment.state}>{copy.assessment.states[record.assessment.state]}</p>
      </Block>
      {/* The link to the Student report goes here (Story 13.12). */}
      <div data-report-slot="" />
    </>
  );
}
