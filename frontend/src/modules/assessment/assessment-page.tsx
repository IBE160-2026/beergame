"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { itemLabel, itemLines } from "@/modules/tests/individual-test";

import { type AssessedItem, type ItemFeedback, type MyAssessment, myAssessmentKey, useMyAssessment } from "./api";
import { flagCountText, pointsText, scoreText, stateLine, totalText, type Viewer } from "./assessment";
import { FlagControl } from "./flag-control";

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
 *
 * Story 12.3 (FR-34, FR-54, FR-81, UX-DR66, UX-DR69): under an AI item's score its written
 * feedback, «KI-generert, kan ta feil:» first, each quote of the Student's own answer set apart as a
 * quotation; where the feedback was left out, a note in its place; and while the Scoring guide is
 * not checked by a Control test, «Ikke kontrollert med en Kontrolltest.» under the disclosure.
 *
 * Story 12.5 (FR-55, UX-DR39): under each piece of feedback the Student's «Marker som feil».
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
      {assessment ? <AssessmentView assessment={assessment} viewer="student" classSessionId={classSessionId} /> : null}
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
    </PageShell>
  );
}

type HeadingLevel = 2 | 3;

/**
 * The «KI-vurdering» itself, for the Student on their page and, Story 12.5 (FR-55, UX-DR66), for
 * the staff of their Class in the Studentside's block: the same disclosure, unchecked notice,
 * scores, feedback and dropped-feedback notes. The Student flags feedback (`classSessionId`); the
 * staff read which pieces the Student flagged, in words. `level` is the heading level of
 * «Oppgavene»; each item's heading is one below it.
 */
export function AssessmentView({
  assessment,
  viewer,
  classSessionId,
  level = 2,
}: {
  assessment: MyAssessment;
  viewer: Viewer;
  classSessionId?: string;
  level?: HeadingLevel;
}) {
  const line = stateLine(assessment, viewer);
  const total = totalText(assessment);
  const flags = viewer === "staff" ? flagCountText(assessment) : null;
  const ListHeading = level === 2 ? "h2" : "h3";
  const itemsId = `${ITEMS_HEADING_ID}-${viewer}`;
  return (
    <div data-assessment-state={assessment.state} data-viewer={viewer} className="mt-4 max-w-2xl">
      <p data-disclosure className={`${LINE} font-semibold text-ink`}>
        {copy.disclosure}
      </p>
      {assessment.items.length > 0 && !assessment.checked ? (
        <p data-unchecked className={`${LINE} mt-1 text-ink-secondary`}>
          {copy.unchecked}
        </p>
      ) : null}
      {line ? <p className={`${LINE} mt-3 text-ink`}>{line}</p> : null}
      {flags ? (
        <p data-flag-count className={`${LINE} mt-3 font-semibold text-ink`}>
          {flags}
        </p>
      ) : null}
      {assessment.items.length > 0 ? (
        <section aria-labelledby={itemsId} className="mt-6 border-t border-axis pt-4">
          <ListHeading id={itemsId} className="text-headline text-ink">
            {copy.itemsTitle}
          </ListHeading>
          <ol className="mt-2 flex flex-col">
            {assessment.items.map((item) => (
              <Item key={item.id} item={item} viewer={viewer} classSessionId={classSessionId} level={level} />
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
function Item({
  item,
  viewer,
  classSessionId,
  level,
}: {
  item: AssessedItem;
  viewer: Viewer;
  classSessionId?: string;
  level: HeadingLevel;
}) {
  const { heading, type } = itemLines(item);
  const { label, ai, note } = itemLabel(item);
  const criteria = item.computed?.criteria ?? [];
  const Heading = level === 2 ? "h3" : "h4";
  const feedback = item.ai?.feedback;
  const headingId = `assessment-item-${viewer}-${item.id}`;
  return (
    <li data-item={item.id} className="border-b border-hairline py-4 last:border-b-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <Heading id={headingId} className="text-step-title font-semibold text-ink">
          {heading} <span className="font-normal text-ink-secondary">· {type}</span>
        </Heading>
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
      {feedback ? <Feedback feedback={feedback} /> : null}
      {feedback && viewer === "student" && classSessionId ? (
        <FlagControl
          classSessionId={classSessionId}
          itemId={item.id}
          flagged={Boolean(item.ai?.flagged)}
          itemHeadingId={headingId}
        />
      ) : null}
      {feedback && viewer === "staff" && item.ai?.flagged ? (
        <p data-flagged className={`${LINE} mt-2 font-semibold text-ink`}>
          {nb.assessment.staff.flagged}
        </p>
      ) : null}
      {item.ai?.feedback_dropped ? (
        <p data-feedback-dropped className={`${LINE} mt-2 text-ink-secondary`}>
          {viewer === "staff" ? nb.assessment.staff.feedbackDropped : copy.feedbackDropped}
        </p>
      ) : null}
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

/** An item's written feedback (Story 12.3): the AI prefix, then code-rendered text with each quote
 * of the Student's own answer as a quotation, cut from their original text by the api. */
function Feedback({ feedback }: { feedback: ItemFeedback }) {
  return (
    <div
      data-feedback
      data-ai-generated={feedback.ai_generated ? "true" : undefined}
      className="mt-2 border-l-2 border-axis pl-3"
    >
      <p className={`${LINE} text-ink [overflow-wrap:anywhere]`}>
        {feedback.ai_generated ? <span className="font-semibold">{copy.feedbackPrefix} </span> : null}
        {feedback.parts.map((part, index) =>
          part.kind === "quote" ? (
            <q key={index} data-quote className="italic [quotes:'«'_'»']">
              {part.text}
            </q>
          ) : (
            <span key={index}>{part.text}</span>
          ),
        )}
      </p>
    </div>
  );
}
