"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";

import { type MyTest, myTestKey, openMyTest, useMyTest } from "./api";
import { deadlineLine, itemLines, testView } from "./individual-test";

const copy = nb.tests.individual;
const LINE = "text-body-phone lg:text-body";
const STATEMENT_HEADING_ID = "test-statement";
const ITEMS_HEADING_ID = "test-items";

/**
 * The Individual test (Story 11.3, FR-51, UX-DR65, EXPERIENCE.md → Individuell test), reached from
 * Stegene's current test step. Before the Replay is completed it says when it opens; then the
 * own-work statement comes first, with one primary button named by its effect, and the api serves
 * no item before it is accepted. Once accepted the items show in their frozen order and focus moves
 * to their heading; the statement is never asked again, on any device. After the Testfrist with no
 * attempt it says the test was not handed in. Another Student's or an unknown session shows the
 * permission-denied page. Every state comes from the api (AD-10). Answering the items arrives with
 * Stories 11.4 to 11.6.
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
      {test?.state === "open" ? <Items test={test} focus={accepted} /> : null}
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
      <p className={`${LINE} mt-3 text-ink-secondary`}>{copy.howItWorks}</p>
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

/** The open test: the Testfrist, then the items in order, each «Oppgave 3» with its type in words
 * and its text. */
function Items({ test, focus }: { test: MyTest; focus: boolean }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (focus) heading.current?.focus();
  }, [focus]);
  const deadline = deadlineLine(test);
  return (
    <section aria-labelledby={ITEMS_HEADING_ID} data-test-state="open" className="mt-6 max-w-2xl">
      {deadline ? <p className={`${LINE} text-ink-secondary`}>{deadline}</p> : null}
      <h2 ref={heading} id={ITEMS_HEADING_ID} tabIndex={-1} className="mt-4 text-headline text-ink focus:outline-none">
        {copy.itemsHeading}
      </h2>
      <ol className="mt-2">
        {test.items.map((item) => {
          const lines = itemLines(item);
          return (
            <li key={item.id} data-test-item={item.id} className="border-t border-hairline py-4">
              <h3 className="text-step-title font-semibold text-ink">
                {lines.heading}
                <span className="ml-3 text-body-phone font-normal text-ink-secondary lg:text-body">{lines.type}</span>
              </h3>
              <p className={`${LINE} mt-2 max-w-md text-ink`}>{item.title}</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
