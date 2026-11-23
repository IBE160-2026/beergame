"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { SegmentedChoice } from "@/components/segmented-choice";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { formatTime } from "@/modules/admin/audit";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH, homeOf, SCORING_PATH, scoringAnswerPath, scoringListPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";

import { aiText, answerLabel, ownText, progressText, scaleOptions, submitError, testLine, typeText } from "./scoring";
import {
  myScoringKey,
  type ScoringItem,
  scoringAnswerKey,
  scoringListKey,
  useMyScoring,
  useScoringAnswer,
  useScoringList,
  useSubmitScore,
} from "./scoring-api";

const copy = nb.scoring;
const LINE = "text-body-phone lg:text-body";

function homeCrumb(user: SessionUser) {
  const home = homeOf(user);
  return { label: nb.homes[home], href: HOME_PATH[home] };
}

function codeOf(error: unknown): string | null {
  return error instanceof ApiRequestError ? error.code : null;
}

/**
 * «Sensur av Kontrolltest» (Story 12.9, FR-82, AD-27, UX-DR57): the Control tests the User is a
 * named scorer of, each a Lenke to its answers once its Test deadline has passed. Reached from the
 * scorer's own home (Lærerhjem, Hjem or Admin-område); no Admin role is needed.
 */
export function ScoringTestsPage() {
  return (
    <GuardedPage page="any">
      {(user, updatedAt) => <ScoringTests user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function ScoringTests({ user, updatedAt }: { user: SessionUser; updatedAt: number }) {
  const found = useMyScoring();
  const { phase, retry } = usePageState(found, myScoringKey);
  const tests = found.data?.tests;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={tests ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      crumbs={[homeCrumb(user), { label: copy.title, href: SCORING_PATH }]}
    >
      <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.lead}</p>
      {tests && tests.length === 0 ? <p className={`${LINE} mt-6 text-ink`}>{copy.tests.empty}</p> : null}
      {tests && tests.length > 0 ? (
        <ul className="mt-6 flex max-w-2xl flex-col border-t border-hairline">
          {tests.map((test) => (
            <li key={test.id} className="border-b border-hairline py-2">
              {test.open ? (
                <Link href={scoringListPath(test.id)} standalone>
                  {testLine(test)}
                </Link>
              ) : (
                <p className={`${LINE} text-ink`}>
                  <span className="font-semibold">{test.name}</span> {testLine(test)}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </PageShell>
  );
}

/**
 * One Control test's answers to score: «Svar 1» on, each with its type and question and «Vurdert»
 * or «Ikke vurdert» in text, never a name. Before the Test deadline it says when they open. The
 * Admin reads it too (each read is in the audit log) but scores only when named.
 */
export function ScoringListPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="any">
      {(user, updatedAt) => <ScoringListView sessionId={sessionId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function ScoringListView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useScoringList(sessionId);
  const { phase, retry } = usePageState(found, scoringListKey(sessionId));
  if (codeOf(found.error) === "forbidden") return <AccessDenied user={user} updatedAt={updatedAt} />;
  const list = found.data;
  return (
    <PageShell
      user={user}
      title={list ? list.test.name : copy.title}
      updatedAt={updatedAt}
      phase={list ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      crumbs={[
        homeCrumb(user),
        { label: copy.title, href: SCORING_PATH },
        { label: list ? list.test.name : copy.list.title, href: scoringListPath(sessionId) },
      ]}
    >
      {list ? (
        <>
          <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.lead}</p>
          {!list.can_score ? <p className={`${LINE} mt-3 font-semibold text-ink`}>{copy.list.readOnly}</p> : null}
          {!list.test.open ? (
            <p className={`${LINE} mt-6 text-ink`}>{list.test.test_deadline ? copy.list.notOpen(formatTime(list.test.test_deadline)) : copy.list.noDeadline}</p>
          ) : (
            <section aria-labelledby="scoring-answers" className="mt-8 max-w-2xl">
              <h2 id="scoring-answers" className="text-headline text-ink">
                {copy.list.title}
              </h2>
              {list.entries.length === 0 ? (
                <p className={`${LINE} mt-2 text-ink`}>{copy.list.empty}</p>
              ) : (
                <>
                  {list.can_score ? (
                    <p data-progress className={`${LINE} mt-2 text-ink tabular-nums`}>
                      {progressText(list.entries)}
                    </p>
                  ) : null}
                  <ul className="mt-3 flex flex-col border-t border-hairline">
                    {list.entries.map((entry) => (
                      <li key={entry.ref} data-answer={entry.number} className="border-b border-hairline py-2">
                        <Link
                          href={scoringAnswerPath(sessionId, entry.ref)}
                          standalone
                          className="min-w-tap-target-min tabular-nums"
                        >
                          {answerLabel(entry.number)}
                        </Link>
                        <p className={`${LINE} text-ink-secondary [overflow-wrap:anywhere]`}>
                          {typeText(entry.type)}: {entry.question}
                        </p>
                        {list.can_score ? (
                          <p data-scored={entry.scored} className={`${LINE} font-semibold text-ink`}>
                            {entry.scored ? copy.list.scored : copy.list.notScored}
                          </p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          )}
        </>
      ) : null}
    </PageShell>
  );
}

/**
 * One answer: the question, the original answer, an Adapted item's facts and the pinned Scoring
 * guide entry with its criteria and five-step scale. The scorer picks a step (Valgknapper) and
 * presses «Lagre vurdering»; that it cannot be changed afterwards stands above the button, and no
 * dialog follows. The AI's step shows only once the scorer's own score is saved (AD-27).
 */
export function ScoringAnswerPage({ sessionId, answerId }: { sessionId: string; answerId: string }) {
  return (
    <GuardedPage page="any">
      {(user, updatedAt) => <ScoringAnswer sessionId={sessionId} answerId={answerId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function ScoringAnswer({
  sessionId,
  answerId,
  user,
  updatedAt,
}: {
  sessionId: string;
  answerId: string;
  user: SessionUser;
  updatedAt: number;
}) {
  const found = useScoringAnswer(sessionId, answerId);
  const { phase, retry } = usePageState(found, scoringAnswerKey(sessionId, answerId));
  const code = codeOf(found.error);
  if (code === "forbidden") return <AccessDenied user={user} updatedAt={updatedAt} />;
  const item = found.data;
  const crumbs = [
    homeCrumb(user),
    { label: copy.title, href: SCORING_PATH },
    { label: item ? item.test.name : copy.list.title, href: scoringListPath(sessionId) },
    { label: item ? answerLabel(item.number) : copy.item.notFound, href: scoringAnswerPath(sessionId, answerId) },
  ];
  if (code === "not_found") {
    return (
      <PageShell user={user} title={copy.item.notFound} updatedAt={updatedAt} crumbs={crumbs}>
        <PageLink href={scoringListPath(sessionId)}>{copy.item.back}</PageLink>
      </PageShell>
    );
  }
  return (
    <PageShell
      user={user}
      title={item ? copy.item.title(formatNumber(item.number)) : copy.title}
      updatedAt={updatedAt}
      phase={item ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      crumbs={crumbs}
    >
      {item ? <AnswerView item={item} sessionId={sessionId} answerId={answerId} /> : null}
      <PageLink href={scoringListPath(sessionId)}>{copy.item.back}</PageLink>
    </PageShell>
  );
}

function AnswerView({ item, sessionId, answerId }: { item: ScoringItem; sessionId: string; answerId: string }) {
  return (
    <div className="mt-2 flex max-w-2xl flex-col gap-8">
      <p className={`${LINE} text-ink-secondary`}>{typeText(item.type)}</p>
      <section aria-labelledby="scoring-question">
        <h2 id="scoring-question" className="text-headline text-ink">
          {copy.item.question}
        </h2>
        <p className={`${LINE} mt-2 text-ink [overflow-wrap:anywhere]`}>{item.question}</p>
        {item.facts.length > 0 ? (
          <>
            <h3 className="mt-4 text-label text-ink">{copy.item.facts}</h3>
            <dl className={`${LINE} mt-1 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-ink tabular-nums`}>
              {item.facts.map((fact) => (
                <div key={fact.name} className="contents">
                  <dt className="text-ink-secondary [overflow-wrap:anywhere]">{fact.name}</dt>
                  <dd className="m-0 [overflow-wrap:anywhere]">{fact.value}</dd>
                </div>
              ))}
            </dl>
          </>
        ) : null}
      </section>
      <section aria-labelledby="scoring-answer">
        <h2 id="scoring-answer" className="text-headline text-ink">
          {copy.item.answer}
        </h2>
        <blockquote
          data-answer-text
          className={`${LINE} mt-2 border-l-2 border-axis pl-3 whitespace-pre-wrap text-ink [overflow-wrap:anywhere]`}
        >
          {item.answer}
        </blockquote>
      </section>
      <section aria-labelledby="scoring-guide">
        <h2 id="scoring-guide" className="text-headline text-ink">
          {copy.item.guide}
        </h2>
        {item.guide_title ? <p className={`${LINE} mt-2 font-semibold text-ink`}>{item.guide_title}</p> : null}
        {item.guide_text ? (
          <p className={`${LINE} mt-1 whitespace-pre-wrap text-ink [overflow-wrap:anywhere]`}>{item.guide_text}</p>
        ) : null}
        {item.criteria.length > 0 ? (
          <>
            <h3 className="mt-4 text-label text-ink">{copy.item.criteria}</h3>
            <ul className={`${LINE} mt-1 flex flex-col gap-1 text-ink`}>
              {item.criteria.map((criterion) => (
                <li key={criterion.code} className="[overflow-wrap:anywhere]">
                  <span className="font-semibold">{criterion.code}</span> ({copy.item.weight(formatNumber(criterion.weight))}):{" "}
                  {criterion.text}
                </li>
              ))}
            </ul>
          </>
        ) : null}
        <h3 className="mt-4 text-label text-ink">{copy.item.scale}</h3>
        <ol className={`${LINE} mt-1 flex flex-col gap-1 text-ink tabular-nums`}>
          {item.scale.map((step) => (
            <li key={step.step}>{copy.item.step(formatNumber(step.step), step.label)}</li>
          ))}
        </ol>
      </section>
      <ScoreBlock item={item} sessionId={sessionId} answerId={answerId} />
    </div>
  );
}

/** The scorer's own score: the form until it is saved, then the score and the AI's step. */
function ScoreBlock({ item, sessionId, answerId }: { item: ScoringItem; sessionId: string; answerId: string }) {
  const submit = useSubmitScore(sessionId, answerId);
  const [choice, setChoice] = useState<string>("");
  const [missing, setMissing] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);
  const own = ownText(item);
  const wasOwn = useRef(Boolean(item.own_score));

  useEffect(() => {
    if (item.own_score && !wasOwn.current) resultRef.current?.focus();
    wasOwn.current = Boolean(item.own_score);
  }, [item.own_score]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submit.isPending) return;
    if (choice === "") {
      setMissing(true);
      return;
    }
    setMissing(false);
    submit.mutate(Number(choice));
  }

  return (
    <section aria-labelledby="scoring-own" className="border-t border-axis pt-4">
      <h2 id="scoring-own" className="text-headline text-ink">
        {copy.item.choose}
      </h2>
      {own ? (
        <div ref={resultRef} tabIndex={-1} data-own-score className="mt-2 flex flex-col gap-1">
          {/* A stale page's second «Lagre vurdering»: the refusal stays in words above the score. */}
          <ActionError message={submit.isError ? submitError(submit.error) : undefined} />
          <p className={`${LINE} font-semibold text-ink`}>{own}</p>
          {item.own_score ? <p className={`${LINE} text-ink-secondary`}>{copy.item.ownAt(formatTime(item.own_score.submitted_at))}</p> : null}
          <p data-ai-score className={`${LINE} mt-2 text-ink`}>
            {aiText(item)}
          </p>
        </div>
      ) : item.can_score ? (
        <form method="post" noValidate onSubmit={onSubmit} className="mt-2 flex flex-col gap-4">
          <SegmentedChoice
            name="human-score"
            legend={copy.item.pick}
            value={choice}
            onChange={(value) => {
              setChoice(value);
              setMissing(false);
              submit.reset();
            }}
            options={scaleOptions(item)}
          />
          <p data-ai-score className={`${LINE} text-ink-secondary`}>
            {copy.item.aiHidden}
          </p>
          <p data-consequence className={`${LINE} font-semibold text-ink`}>
            {copy.item.consequence}
          </p>
          <ActionError message={missing ? copy.item.chooseFirst : submit.isError ? submitError(submit.error) : undefined} />
          <Button type="submit" variant="primary" unavailable={submit.isPending} className="w-full max-w-md">
            {copy.item.submit}
          </Button>
        </form>
      ) : (
        <p className={`${LINE} mt-2 text-ink`}>{copy.item.readOnly}</p>
      )}
    </section>
  );
}
