"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { errorCode, useAction } from "@/lib/api/mutation";
import { clearDrafts } from "@/lib/drafts";
import { usePageState } from "@/lib/page-state";
import { useServerNow } from "@/modules/games/seat-status";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";

import { type MyTest, myTestKey, openMyTest, submitMyTest, useMyTest } from "./api";
import { draftPrefix } from "./autosave";
import { ChoiceItem } from "./choice-item";
import { DrawnItem } from "./drawn-item";
import {
  deadlineLine,
  itemAnchor,
  itemLines,
  listSeparator,
  submittedLine,
  testView,
  unansweredNumbers,
} from "./individual-test";
import { isInteractive } from "./interactive";
import { NumberItem, TableItem } from "./interactive-item";
import { LongItem } from "./long-item";
import { minutesLeft, sittingEnd } from "./sitting";
import { SubmittedItems } from "./submitted-items";
import { UnsentContext } from "./use-autosave";

const copy = nb.tests.individual;
const LINE = "text-body-phone lg:text-body";
const STATEMENT_HEADING_ID = "test-statement";
const ITEMS_HEADING_ID = "test-items";
const REVIEW_HEADING_ID = "test-review";
const ANSWERS_HEADING_ID = "test-answers";
/** The minutes left at which the page says once, politely, that time is short (Story 11.12). */
const WARN_AT_MINUTES = 5;
/** How often a sitting that has ended is read again until the sweep has handed it in. */
const ENDED_REREAD_MS = 20_000;

/**
 * The Individual test (Story 11.3, FR-51, UX-DR65, EXPERIENCE.md → Individuell test), reached from
 * Stegene's current test step. Before the Replay is completed it says when it opens; then the
 * own-work statement comes first, with one primary button named by its effect, and the api serves
 * no item before it is accepted. Once accepted the items show in their frozen order and focus moves
 * to their heading; the statement is never asked again, on any device. After the Testfrist with no
 * attempt it says the test was not handed in. Another Student's or an unknown session shows the
 * permission-denied page. Every state comes from the api (AD-10). Multiple-choice items are
 * answered with autosave (Story 11.4), table and number items too (Story 11.5), and long answers,
 * saved when typing pauses (Story 11.6). «Lever testen» opens a review on the page, then hands the
 * test in once; the handed-in test shows when, with every answer read-only (Story 11.10). In one
 * timed sitting (Story 11.12) the statement names the limit, the open test keeps «Tid igjen 38 min»
 * at the top, and when the time is up the answers stand read-only under «Tiden er ute. Testen er
 * levert.».
 */
export function IndividualTestPage({ classSessionId }: { classSessionId: string }) {
  return (
    <GuardedPage page="home">
      {(user, updatedAt) => <TestPage classSessionId={classSessionId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function TestPage({ classSessionId, user, updatedAt }: { classSessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useMyTest(classSessionId);
  const { phase, retry } = usePageState(found, myTestKey(classSessionId));
  // Accepted on this page just now: the items' heading takes focus once they show.
  const [accepted, setAccepted] = useState(false);
  // Handed in on this page just now: the «Levert …» line takes focus.
  const [submitted, setSubmitted] = useState(false);
  const code = found.error instanceof ApiRequestError ? found.error.code : null;
  const view = testView(found.data, code);
  if (view === "denied") return <AccessDenied user={user} updatedAt={updatedAt} />;
  const test = found.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={test || view === "locked" ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {view === "locked" ? <Line state="locked" text={copy.errors.replay_required} /> : null}
      {test?.state === "closed" ? <Line state="closed" text={copy.closed} /> : null}
      {test?.state === "statement" ? (
        <Statement test={test} classSessionId={classSessionId} onAccepted={() => setAccepted(true)} />
      ) : null}
      {test?.state === "open" && test.sitting_ends_at ? (
        <TimedItems test={test} focus={accepted} classSessionId={classSessionId} userId={user.id} onSubmitted={() => setSubmitted(true)} />
      ) : test?.state === "open" ? (
        <Items test={test} focus={accepted} classSessionId={classSessionId} userId={user.id} onSubmitted={() => setSubmitted(true)} />
      ) : null}
      {test?.state === "submitted" || test?.state === "auto_submitted" ? (
        <Submitted test={test} focus={submitted} classSessionId={classSessionId} userId={user.id} />
      ) : null}
      {view !== "other" ? <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink> : null}
    </PageShell>
  );
}

function Line({ state, text }: { state: string; text: string }) {
  return (
    <p data-test-state={state} className={`${LINE} mt-4 max-w-md text-ink`}>
      {text}
    </p>
  );
}

/** The own-work statement (FR-51): what the Student confirms, how the test works and the
 * Testfrist, over the one primary «Bekreft og åpne testen». A refusal stays in words under the
 * button, which stays active, and the test is read again (after the Testfrist it says so). */
function Statement({ test, classSessionId, onAccepted }: { test: MyTest; classSessionId: string; onAccepted: () => void }) {
  const queryClient = useQueryClient();
  const opening = useAction({
    mutationFn: () => openMyTest(classSessionId),
    messages: copy.errors,
    fallback: copy.failed,
    onSuccess: (opened) => {
      onAccepted();
      queryClient.setQueryData(myTestKey(classSessionId), opened);
    },
  });
  // A refusal means the page was out of date (the Testfrist passed): it is read again.
  const press = () =>
    opening.mutate(undefined, {
      onError: () => void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) }),
    });
  const deadline = deadlineLine(test);
  return (
    <section aria-labelledby={STATEMENT_HEADING_ID} data-test-state="statement" className="mt-6 max-w-md border-t border-axis pt-4">
      <h2 id={STATEMENT_HEADING_ID} className="text-headline text-ink">
        {copy.statementHeading}
      </h2>
      <p className={`${LINE} mt-3 text-ink`}>{copy.statement}</p>
      {/* Story 11.12: the limit, and that the time cannot be paused, before the button. */}
      {test.time_limit_minutes != null ? (
        <p data-time-limit className={`${LINE} mt-3 font-semibold text-ink`}>
          {copy.timed.limit(test.time_limit_minutes)}
        </p>
      ) : null}
      <p className={`${LINE} mt-3 text-ink-secondary`}>
        {test.time_limit_minutes != null ? copy.timed.howItWorks : copy.howItWorks}
      </p>
      {deadline ? <p className={`${LINE} mt-3 text-ink-secondary`}>{deadline}</p> : null}
      <div className="mt-5 flex flex-col items-start gap-3">
        <Button variant="primary" unavailable={opening.isPending || opening.isSuccess} onClick={press}>
          {copy.accept}
        </Button>
        <ActionError message={opening.errorMessage} />
      </div>
    </section>
  );
}

/**
 * A timed sitting (Story 11.12, FR-51, UX-DR65): «Tid igjen 38 min» fixed at the top while the
 * Student scrolls, in whole minutes counted from the api's `server_now` to `answering_ends_at`
 * (their time factor is in it). The line changes without moving focus and is no live region; one
 * polite line says «5 minutter igjen. Svarene dine er lagret.» once. Closing the page does not stop
 * the clock: the end is the api's. At 0 the answers stand read-only, handed in by the sweep within
 * the minute.
 */
function TimedItems(props: { test: MyTest; focus: boolean; classSessionId: string; userId: string; onSubmitted: () => void }) {
  const { test } = props;
  const now = useServerNow(test.server_now);
  const ends = test.answering_ends_at ?? test.sitting_ends_at;
  const left = ends ? minutesLeft(ends, now) : 0;
  // Set after the page is shown, so the status line changes and is announced also when the test
  // is opened with less than five minutes left.
  const [warned, setWarned] = useState(false);
  const short = left > 0 && left <= WARN_AT_MINUTES;
  useEffect(() => {
    if (short) setWarned(true);
  }, [short]);
  if (left === 0) {
    return <TimeUp test={test} classSessionId={props.classSessionId} userId={props.userId} />;
  }
  return (
    <>
      <div data-time-left className="sticky top-0 z-10 -mx-4 mt-4 border-b border-axis bg-paper px-4 py-2 lg:mx-0 lg:px-0">
        <p className="text-body-phone font-semibold text-ink tabular-nums lg:text-body">{copy.timed.timeLeft(left)}</p>
      </div>
      {/* Always there, so the one line is announced when it appears. */}
      <p role="status" data-time-warning className="sr-only">
        {warned ? copy.timed.fiveMinutes : ""}
      </p>
      <Items {...props} />
    </>
  );
}

/**
 * The time is up (Story 11.12): «Tiden er ute. Testen er levert.», which takes focus, then every
 * answer read-only. Nothing more can be saved (the api answers `sitting_ended`), so the drafts of
 * this test are dropped; the test is read again until the sweep has handed it in. A timed sitting
 * that would have ended after the Testfrist ends with it and says so.
 */
function TimeUp({ test, classSessionId, userId }: { test: MyTest; classSessionId: string; userId: string }) {
  const queryClient = useQueryClient();
  const line = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    line.current?.focus();
    clearDrafts(userId, draftPrefix(classSessionId));
    const reread = () => void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) });
    reread();
    const timer = window.setInterval(reread, ENDED_REREAD_MS);
    return () => window.clearInterval(timer);
  }, [classSessionId, queryClient, userId]);
  return (
    <section aria-labelledby={ANSWERS_HEADING_ID} data-test-state="time-up" className="mt-6 max-w-2xl">
      <p ref={line} tabIndex={-1} data-submitted-line className={`${LINE} max-w-md font-semibold text-ink focus:outline-none`}>
        {sittingEnd(test) ? copy.timed.ended : copy.submit.autoSubmitted}
      </p>
      <h2 id={ANSWERS_HEADING_ID} className="mt-6 text-headline text-ink">
        {copy.submit.answersHeading}
      </h2>
      <SubmittedItems items={test.items} />
    </section>
  );
}

/** The open test: the Testfrist, then the items in order, each «Oppgave 3» with its type in words
 * and its text; a multiple-choice item is answered under it (its text is the choice's legend), a
 * table item in its value table and a number item in its column (Story 11.5), an Interactive
 * item after the line that says these items are hard; a long answer in a multi-line Tekstfelt
 * labelled by its question (Story 11.6), and so an Adapted item, whose question is its text frozen
 * from the Student's own game or Replay (Story 11.7). */
function Items({
  test,
  focus,
  classSessionId,
  userId,
  onSubmitted,
}: {
  test: MyTest;
  focus: boolean;
  classSessionId: string;
  userId: string;
  onSubmitted: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (focus) heading.current?.focus();
  }, [focus]);
  // The items with a change not yet stored on the api (`UnsentContext`).
  const [unsent, setUnsent] = useState<ReadonlySet<string>>(() => new Set());
  const report = useCallback((itemId: string, waiting: boolean) => {
    setUnsent((was) => {
      if (was.has(itemId) === waiting) return was;
      const next = new Set(was);
      if (waiting) next.add(itemId);
      else next.delete(itemId);
      return next;
    });
  }, []);
  const deadline = deadlineLine(test);
  return (
    <UnsentContext.Provider value={report}>
      <section aria-labelledby={ITEMS_HEADING_ID} data-test-state="open" className="mt-6 max-w-2xl">
        {deadline ? <p className={`${LINE} text-ink-secondary`}>{deadline}</p> : null}
        <h2 ref={heading} id={ITEMS_HEADING_ID} tabIndex={-1} className="mt-4 text-headline text-ink focus:outline-none">
          {copy.itemsHeading}
        </h2>
        <ol className="mt-2">
          {test.items.map((item) => {
            const lines = itemLines(item);
            return (
              <li
                key={item.id}
                id={itemAnchor(item.number)}
                tabIndex={-1}
                data-test-item={item.id}
                className="scroll-mt-4 border-t border-hairline py-4 focus:outline-none"
              >
                <h3 className="text-step-title font-semibold text-ink">
                  {lines.heading}
                  <span className="ml-3 text-body-phone font-normal text-ink-secondary lg:text-body">{lines.type}</span>
                </h3>
                {isInteractive(item) ? <p className={`${LINE} mt-2 max-w-md text-ink-secondary`}>{copy.interactive.intro}</p> : null}
                {item.type === "choice" ? (
                  <ChoiceItem classSessionId={classSessionId} userId={userId} item={item} />
                ) : item.type === "table" && item.table ? (
                  <TableItem classSessionId={classSessionId} userId={userId} item={item} table={item.table} />
                ) : item.type === "drawn" && item.table ? (
                  <DrawnItem classSessionId={classSessionId} userId={userId} item={item} table={item.table} />
                ) : item.type === "number" && item.column ? (
                  <NumberItem classSessionId={classSessionId} userId={userId} item={item} column={item.column} />
                ) : item.type === "long" || item.type === "adapted" ? (
                  <LongItem classSessionId={classSessionId} userId={userId} item={item} />
                ) : (
                  <p className={`${LINE} mt-2 max-w-md text-ink`}>{item.title}</p>
                )}
              </li>
            );
          })}
        </ol>
        <Submit test={test} classSessionId={classSessionId} waiting={unsent.size > 0} onSubmitted={onSubmitted} />
      </section>
    </UnsentContext.Provider>
  );
}

/**
 * «Lever testen» (Story 11.10, FR-51, UX-DR65): under the items one primary button opens the review
 * in its place, with focus on its heading: the items not answered, each number a link to its item
 * («3 oppgaver er ikke besvart: 4, 7 og 9.»), or that all are; the warning; and the one primary
 * «Lever testen», which hands the test in. No dialog follows. While an answer typed on this device
 * is not yet stored the button waits, saying so. A failure stays in words under the button, which
 * stays active; a test handed in elsewhere, or past its Testfrist, is read again.
 */
function Submit({ test, classSessionId, waiting, onSubmitted }: { test: MyTest; classSessionId: string; waiting: boolean; onSubmitted: () => void }) {
  const queryClient = useQueryClient();
  const [reviewing, setReviewing] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (reviewing) heading.current?.focus();
  }, [reviewing]);
  const submitting = useAction({
    mutationFn: () => submitMyTest(classSessionId),
    messages: copy.submit.errors,
    fallback: copy.submit.failed,
    onSuccess: (handedIn) => {
      onSubmitted();
      queryClient.setQueryData(myTestKey(classSessionId), handedIn);
    },
  });
  const press = () =>
    submitting.mutate(undefined, {
      onError: (error) => {
        // Handed in already (another device, a reply that never came): the test is read again and
        // shows as handed in. Past the Testfrist: read again too.
        const code = errorCode(error);
        // The handed-in view that replaces the review takes focus, as after a hand-in here.
        if (code === "attempt_submitted") onSubmitted();
        if (code === "attempt_submitted" || code === "test_deadline_passed" || code === "sitting_ended") {
          void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) });
        }
      },
    });
  if (!reviewing) {
    return (
      <div className="mt-4 border-t border-axis pt-6">
        <Button variant="primary" onClick={() => setReviewing(true)}>
          {copy.submit.button}
        </Button>
      </div>
    );
  }
  const missing = unansweredNumbers(test);
  return (
    <section aria-labelledby={REVIEW_HEADING_ID} data-test-review className="mt-4 max-w-md border-t border-axis pt-6">
      <h2 ref={heading} id={REVIEW_HEADING_ID} tabIndex={-1} className="text-headline text-ink focus:outline-none">
        {copy.submit.reviewHeading}
      </h2>
      {missing.length > 0 ? (
        <p data-unanswered className={`${LINE} mt-3 text-ink`}>
          {copy.submit.unanswered(missing.length)}{" "}
          {missing.map((number, index) => {
            // A comma after the number sits inside its 44 px target, so it stays next to the
            // number instead of across the target's padding («1, 2» not «1 , 2»).
            const comma = index + 1 < missing.length && listSeparator(index + 1, missing.length) === copy.submit.listComma;
            const before = listSeparator(index, missing.length);
            return (
              <span key={number}>
                {before === copy.submit.listComma ? copy.submit.listComma.slice(1) : before}
                <a
                  href={`#${itemAnchor(number)}`}
                  aria-label={copy.submit.itemLink(number)}
                  className="inline-flex min-h-11 min-w-11 items-center justify-center font-semibold text-ink"
                >
                  <span className="underline underline-offset-4 hover:no-underline">{number}</span>
                  {comma ? <span className="font-normal">,</span> : null}
                </a>
              </span>
            );
          })}
          {copy.submit.listEnd}
        </p>
      ) : (
        <p data-all-answered className={`${LINE} mt-3 text-ink`}>
          {copy.submit.allAnswered}
        </p>
      )}
      <p className={`${LINE} mt-3 text-ink`}>{copy.submit.warning}</p>
      <div className="mt-5 flex flex-col items-start gap-3">
        <Button variant="primary" unavailable={submitting.isPending || waiting} onClick={press}>
          {copy.submit.button}
        </Button>
        {/* The status region is always there, so the line is announced when it appears. */}
        <p role="status" data-submit-waiting className="text-label text-ink-secondary empty:hidden">
          {waiting ? copy.submit.saving : ""}
        </p>
        <ActionError message={submitting.errorMessage} />
      </div>
    </section>
  );
}

/**
 * The handed-in test (Story 11.10, FR-51, UX-DR65): «Levert to. 18. des. kl. 21:40. Du kan ikke
 * endre svarene.» (or, from the Testfrist, that it was handed in automatically), which takes focus
 * when the Student has just handed it in, then every answer read-only. Drafts of this test still on
 * the device are dropped: nothing more can be saved.
 */
function Submitted({ test, focus, classSessionId, userId }: { test: MyTest; focus: boolean; classSessionId: string; userId: string }) {
  const line = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (focus) line.current?.focus();
  }, [focus]);
  useEffect(() => {
    clearDrafts(userId, draftPrefix(classSessionId));
  }, [classSessionId, userId]);
  return (
    <section aria-labelledby={ANSWERS_HEADING_ID} data-test-state={test.state} className="mt-6 max-w-2xl">
      <p ref={line} tabIndex={-1} data-submitted-line className={`${LINE} max-w-md font-semibold text-ink focus:outline-none`}>
        {submittedLine(test)}
      </p>
      <h2 id={ANSWERS_HEADING_ID} className="mt-6 text-headline text-ink">
        {copy.submit.answersHeading}
      </h2>
      <SubmittedItems items={test.items} />
    </section>
  );
}
