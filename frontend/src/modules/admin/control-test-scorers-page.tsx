"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { scorerError } from "@/modules/assessment/scoring";
import { type Scorers, scorersKey, useNameScorer, useRemoveScorer, useScorers } from "@/modules/assessment/scoring-api";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_CONTROL_TESTS_PATH, controlTestScorersPath, HOME_PATH, scoringListPath } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

const copy = nb.scoring.scorers;
const LINE = "text-body-phone lg:text-body";

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: nb.admin.controlTests.title, href: ADMIN_CONTROL_TESTS_PATH },
] as const;

/**
 * Admin-område → «Kontrolltest» → «Sensorer» (Story 12.9, FR-82, AD-27): the Users named to
 * score one Control test's answers, each with how many they have scored and «Fjern»; a form that
 * names one more by e-mail address; and a Lenke to the answers, which the Admin reads (each read
 * is in the audit log). Only an Admin sees it.
 */
export function ControlTestScorersPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => <ScorersBody sessionId={sessionId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function ScorersBody({
  sessionId,
  user,
  updatedAt,
}: {
  sessionId: string;
  user: Parameters<typeof PageShell>[0]["user"];
  updatedAt: number;
}) {
  const found = useScorers(sessionId);
  const { phase, retry } = usePageState(found, scorersKey(sessionId));
  const notFound = found.error instanceof ApiRequestError && found.error.code === "not_found";
  const page = found.data;
  return (
    <PageShell
      user={user}
      title={page ? `${copy.title}: ${page.test.name}` : copy.title}
      updatedAt={updatedAt}
      phase={page || notFound ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      crumbs={[...CRUMBS, { label: copy.title, href: controlTestScorersPath(sessionId) }]}
    >
      {notFound ? <p className={`${LINE} mt-2 text-ink`}>{copy.notFound}</p> : null}
      {page ? <ScorersView page={page} sessionId={sessionId} /> : null}
    </PageShell>
  );
}

function ScorersView({ page, sessionId }: { page: Scorers; sessionId: string }) {
  const remove = useRemoveScorer(sessionId);
  const total = formatNumber(page.answers);
  return (
    <>
      <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.lead}</p>
      <p className={`${LINE} mt-3 text-ink tabular-nums`}>{copy.answers(total)}</p>
      <p className="mt-2">
        <Link href={scoringListPath(sessionId)} standalone>
          {copy.readAnswers}
        </Link>
      </p>
      <section aria-labelledby="scorers-title" className="mt-8 max-w-2xl">
        <h2 id="scorers-title" className="text-headline text-ink">
          {copy.listTitle}
        </h2>
        {page.scorers.length === 0 ? (
          <p className={`${LINE} mt-2 text-ink`}>{copy.empty}</p>
        ) : (
          <ul className="mt-3 flex flex-col border-t border-hairline">
            {page.scorers.map((scorer) => (
              <li
                key={scorer.user_id}
                data-scorer={scorer.email}
                className="flex flex-col gap-2 border-b border-hairline py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className={`${LINE} font-semibold text-ink [overflow-wrap:anywhere]`}>{scorer.name}</p>
                  <p className={`${LINE} text-ink-secondary [overflow-wrap:anywhere]`}>{scorer.email}</p>
                  <p className={`${LINE} text-ink tabular-nums`}>{copy.scored(formatNumber(scorer.scored), total)}</p>
                </div>
                <Button
                  unavailable={remove.isPending}
                  onClick={() => remove.mutate(scorer.user_id)}
                  aria-label={copy.remove(scorer.name || scorer.email)}
                >
                  {copy.removeButton}
                </Button>
              </li>
            ))}
          </ul>
        )}
        <ActionError className="mt-2" message={remove.isError ? copy.removeFailed : undefined} />
      </section>
      <AddScorer sessionId={sessionId} />
    </>
  );
}

/** «Utnevn sensor»: one address; a refused one says why under the field, a named one says so. */
function AddScorer({ sessionId }: { sessionId: string }) {
  const action = useNameScorer(sessionId);
  const fieldRef = useRef<HTMLInputElement>(null);
  const doneRef = useRef<HTMLParagraphElement>(null);
  const [error, setError] = useState<string>();
  const [added, setAdded] = useState<string>();

  useEffect(() => {
    if (added) doneRef.current?.focus();
  }, [added]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    setAdded(undefined);
    const email = (fieldRef.current?.value ?? "").trim();
    if (!email) {
      setError(copy.errors.empty);
      fieldRef.current?.focus();
      return;
    }
    setError(undefined);
    action.mutate(email, {
      onSuccess: () => {
        if (fieldRef.current) fieldRef.current.value = "";
        setAdded(email);
      },
      onError: (failure) => {
        setError(scorerError(failure));
        fieldRef.current?.focus();
      },
    });
  }

  return (
    <section aria-labelledby="add-scorer-title" className="mt-10 max-w-md">
      <h2 id="add-scorer-title" className="text-headline text-ink">
        {copy.addTitle}
      </h2>
      <form method="post" noValidate onSubmit={onSubmit} className="mt-3 flex flex-col gap-4">
        <TextField
          ref={fieldRef}
          id="scorer-email"
          name="email"
          type="email"
          autoComplete="off"
          label={copy.email}
          error={error}
          onChange={() => setAdded(undefined)}
        />
        <Button type="submit" variant="primary" unavailable={action.isPending} className="w-full">
          {copy.add}
        </Button>
        {added ? (
          <p
            ref={doneRef}
            tabIndex={-1}
            role="status"
            className={`${LINE} border-y border-ink-muted py-2 text-ink [overflow-wrap:anywhere]`}
          >
            {copy.added(added)}
          </p>
        ) : null}
      </form>
    </section>
  );
}
