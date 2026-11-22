"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { itemLabel, itemLines } from "@/modules/tests/individual-test";

import { type AssessedItem, type MyAssessment, myAssessmentKey, useMyAssessment } from "./api";
import { pointsText, scoreText, stateLine, totalText } from "./assessment";

const copy = nb.assessment.student;
const LINE = "text-body-phone lg:text-body";
const ITEMS_HEADING_ID = "assessment-items";

/**
 * The Student's «KI-vurdering» of their Individual test (Story 12.2, FR-54, FR-55, FR-61, FR-80,
 * UX-DR66), reached from Hjem once the test is handed in. Every view starts with «KI-generert, kan
 * ta feil. Teller ikke. Ingen karakter.»; then one line for a state with nothing to show (not
 * ready, switched off, no test, failed), or each item in the test's order with its score in words
 * and its points of its weight, and, when every item has a score, the weighted total. There is no
 * pass or fail and no letter. Every number is the api's (AD-10), through the number formatter.
 * Another Student's or an unknown session shows the permission-denied page.
 */
export function AssessmentPage({ classSessionId }: { classSessionId: string }) {
  return (
    <GuardedPage page="home">
      {(user, updatedAt) => <Assessment classSessionId={classSessionId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function Assessment({ classSessionId, user, updatedAt }: { classSessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useMyAssessment(classSessionId);
  const { phase, retry } = usePageState(found, myAssessmentKey(classSessionId));
  const code = found.error instanceof ApiRequestError ? found.error.code : null;
  if (code === "forbidden") return <AccessDenied user={user} updatedAt={updatedAt} />;
  const assessment = found.data;
  return (
    <PageShell user={user} title={copy.title} updatedAt={updatedAt} phase={assessment ? "ready" : phase === "ready" ? "loading" : phase} onRetry={retry}>
      {assessment ? <Body assessment={assessment} /> : null}
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
    </PageShell>
  );
}

function Body({ assessment }: { assessment: MyAssessment }) {
  const line = stateLine(assessment);
  const total = totalText(assessment);
  return (
    <div data-assessment-state={assessment.state} className="mt-4 max-w-2xl">
      <p data-disclosure className={`${LINE} font-semibold text-ink`}>
        {copy.disclosure}
      </p>
      {line ? <p className={`${LINE} mt-3 text-ink`}>{line}</p> : null}
      {assessment.items.length > 0 ? (
        <section aria-labelledby={ITEMS_HEADING_ID} className="mt-6 border-t border-axis pt-4">
          <h2 id={ITEMS_HEADING_ID} className="text-headline text-ink">
            {copy.itemsTitle}
          </h2>
          <ol className="mt-2 flex flex-col">
            {assessment.items.map((item) => (
              <Item key={item.id} item={item} />
            ))}
          </ol>
        </section>
      ) : null}
      {total ? (
        <div data-total className="mt-6 border-t border-axis pt-4">
          <p className="text-step-title font-semibold text-ink tabular-nums">{total}</p>
          <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.totalNote}</p>
        </div>
      ) : null}
    </div>
  );
}

/** One item: «Oppgave 3», its type, the question, the score in words, any computed criteria, and
 * its points of its Item weight. Text only: no colour carries a meaning. */
function Item({ item }: { item: AssessedItem }) {
  const { heading, type } = itemLines(item);
  const { label, ai, note } = itemLabel(item);
  const criteria = item.computed?.criteria ?? [];
  return (
    <li data-item={item.id} className="border-b border-hairline py-4 last:border-b-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="text-step-title font-semibold text-ink">
          {heading} <span className="font-normal text-ink-secondary">· {type}</span>
        </h3>
        <p data-points className={`${LINE} text-ink tabular-nums`}>
          {pointsText(item)}
        </p>
      </div>
      <p data-ai-text={ai ? "" : undefined} className={`${LINE} mt-1 text-ink-secondary [overflow-wrap:anywhere]`}>
        {label}
      </p>
      {note ? <p className="mt-1 text-caption text-ink-secondary">{note}</p> : null}
      <p data-score className={`${LINE} mt-2 text-ink`}>
        {scoreText(item)}
      </p>
      {criteria.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-1">
          {criteria.map((criterion) => (
            <li key={criterion.code} className={`${LINE} text-ink`}>
              <span className="font-semibold">{criterion.met ? copy.criterionMet : copy.criterionNotMet}:</span>{" "}
              {criterion.explanation}
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}
