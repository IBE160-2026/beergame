"use client";

import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { WeekTable } from "@/modules/games/week-table-view";
import { roleName } from "@/modules/sessions/sessions";

import { DEBRIEF_STEPS, type Debrief, type Moment, type Moments, type RenderedText, useDebriefStep, useMyExplanation } from "./api";

const copy = nb.debrief.moments;
const LINE = "text-body-phone lg:text-body";
const LABEL = "text-label text-ink";
const CELL = "py-1 pr-3 text-right tabular-nums lining-nums";

/**
 * Debrief step 4, the Student's own moments (Story 9.7, FR-44, FR-41, UX-DR31, `07-debrief.png`):
 * shown once every reflection question is answered; the api checks the gate. The heading and every
 * sentence are the api's, rendered by code from the stored facts (`ai_generated` false, so no
 * «KI-generert» prefix). The moments are paged one at a time; «Forrige» and «Neste» move focus to
 * the new moment's heading. Each shows «Dette så du» (the play screen's Graf over tabell at that
 * Uke, with the Order at nå), «Dette regnet du», «Dette kostet det senere», the pattern of the
 * Uke and «Dette så de andre i Uke N», beside the Student's own Explanation, which only they see
 * (FR-41, FR-43). With fewer than 10 own Orders the step says the game was played mostly by AI
 * players. Every number is the api's (AD-10).
 */
export function MomentsStep({ debrief }: { debrief: Debrief }) {
  const step = useDebriefStep(debrief.id, 4, true);
  const moments = step.data?.moments ?? null;
  const id = useId();
  const label = nb.debriefEntry.stepOf(4, DEBRIEF_STEPS);
  if (step.isError && !moments) {
    return (
      <section aria-label={label} data-debrief-moments="failed" className="mt-10 border-t border-axis pt-4">
        <div className="flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void step.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  if (!moments) return null;
  return (
    <section aria-labelledby={`${id}-heading`} data-debrief-moments="" className="mt-10 border-t border-axis pt-4">
      <h2 id={`${id}-heading`} className="max-w-3xl text-headline text-ink">
        <span className="sr-only">{label}: </span>
        <span aria-hidden="true" className="mr-3 tabular-nums">
          4
        </span>
        {moments.heading ? <Text text={moments.heading} /> : copy.heading}
      </h2>
      {moments.mostly_ai || moments.moments.length === 0 ? (
        <div className={`${LINE} mt-4 flex max-w-2xl flex-col gap-2 text-ink`}>
          <p data-moments-mostly-ai="">{copy.mostlyAi}</p>
          <p>{copy.mostlyAiChain}</p>
        </div>
      ) : (
        <Paged debrief={debrief} moments={moments} />
      )}
    </section>
  );
}

/** Code-rendered text as written; AI text (Story 9.14) gets its prefix from `ai_generated` only. */
function Text({ text }: { text: RenderedText }) {
  return <>{text.ai_generated ? `${nb.debrief.aiPrefix} ${text.text}` : text.text}</>;
}

function Paged({ debrief, moments }: { debrief: Debrief; moments: Moments }) {
  const [at, setAt] = useState(0);
  const [moved, setMoved] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const id = useId();
  const count = moments.moments.length;
  const index = Math.min(at, count - 1);
  const moment = moments.moments[index]!;
  // Paging moves focus to the new moment's heading (UX-DR31); never on the page's first view.
  useEffect(() => {
    if (moved > 0) heading.current?.focus();
  }, [moved]);
  const go = (to: number) => {
    setAt(to);
    setMoved((n) => n + 1);
  };
  return (
    <div data-moment={moment.id} className="mt-4">
      <h3 ref={heading} id={`${id}-moment`} tabIndex={-1} className="max-w-3xl text-body-lead text-ink focus:outline-none">
        <span className="mr-2 text-label text-ink-secondary">
          {copy.counter(index + 1, count)}
          <span className="sr-only">: </span>
        </span>
        <Text text={moment.heading} />
      </h3>
      <div role="group" aria-label={copy.paging} className="mt-3 flex flex-wrap gap-2">
        <Button unavailable={index === 0} onClick={() => index > 0 && go(index - 1)}>
          {copy.previous}
        </Button>
        <Button unavailable={index === count - 1} onClick={() => index < count - 1 && go(index + 1)}>
          {copy.next}
        </Button>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="min-w-0">
          <h4 className={LABEL}>{copy.saw}</h4>
          <div className="mt-2">
            <WeekTable key={moment.id} state={moment.seen} nowOrder={moment.order} label={copy.region(moment.week)} />
          </div>
        </div>
        <div className={`${LINE} flex min-w-0 flex-col gap-5 text-ink`}>
          <div>
            <h4 className={LABEL}>{copy.reckoned}</h4>
            <p className="mt-1" data-moment-reckoning="">
              <Text text={moment.reckoning} />
            </p>
          </div>
          <div>
            <h4 className={LABEL}>{copy.later}</h4>
            <p className="mt-1" data-moment-later="">
              <Text text={moment.later} />
            </p>
          </div>
          <div>
            <h4 className={LABEL}>{copy.pattern}</h4>
            {moment.patterns.map((text, i) => (
              <p key={i} className="mt-1" data-moment-pattern="">
                <Text text={text} />
              </p>
            ))}
          </div>
          <Others moment={moment} />
          <Explanation debrief={debrief} />
        </div>
      </div>
    </div>
  );
}

function Others({ moment }: { moment: Moment }) {
  const id = useId();
  return (
    <div>
      <h4 id={`${id}-others`} className={LABEL}>
        {copy.others(moment.week)}
      </h4>
      <table aria-labelledby={`${id}-others`} data-moment-others="" className="mt-1 w-full border-collapse text-table-cell lg:text-table-cell-laptop">
        <thead>
          <tr className="border-b border-axis text-ink-secondary">
            <th scope="col" className="py-1 pr-3 text-left font-normal">
              {copy.role}
            </th>
            <th scope="col" className={`${CELL} font-normal`}>
              {nb.terms.incomingOrder}
            </th>
            <th scope="col" className={`${CELL} font-normal`}>
              {nb.terms.inventory}
            </th>
            <th scope="col" className={`${CELL} font-normal`}>
              {nb.terms.backlog}
            </th>
            <th scope="col" className={`${CELL} font-normal`}>
              {nb.terms.supplyLine}
            </th>
          </tr>
        </thead>
        <tbody>
          {moment.others.map((other) => (
            <tr key={other.role} className="border-b border-hairline">
              <th scope="row" className="py-1 pr-3 text-left font-normal">
                {roleName(other.role)}
              </th>
              <td className={CELL}>{formatNumber(other.incoming_order)}</td>
              <td className={CELL}>{formatNumber(other.inventory)}</td>
              <td className={CELL}>{formatNumber(other.backlog)}</td>
              <td className={CELL}>{formatNumber(other.supply_line)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The Student's own Explanation beside the data (FR-44, FR-41): read from their own endpoint, so
 * no one else's can appear here. */
function Explanation({ debrief }: { debrief: Debrief }) {
  const sent = useMyExplanation(debrief.id).data?.explanation;
  if (!sent) return null;
  return (
    <div data-moment-explanation="">
      <h4 className={LABEL}>{copy.explanation}</h4>
      <p className="mt-1 text-caption text-ink-secondary">{copy.explanationNote}</p>
      <p className="mt-1 border-l-2 border-axis pl-3 whitespace-pre-wrap">{sent.text}</p>
    </div>
  );
}
