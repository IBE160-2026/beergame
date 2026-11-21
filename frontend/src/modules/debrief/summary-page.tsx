"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classSessionPath, HOME_PATH, studentDebriefPath } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { osloDateText } from "@/modules/sessions/dates";
import { roleName } from "@/modules/sessions/sessions";

import { type StaffSummary, staffSummaryKey, type Summary, useStaffSummary } from "./api";

const copy = nb.debrief.staffSummary;
const LINE = "text-body-phone lg:text-body";
const SECTION = "mt-8 max-w-2xl border-t border-axis pt-4";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * A Student's Explanation and Debrief summary for the Class's owners and Assistant lecturers
 * (Story 9.8, FR-47, AD-12), where Spillinnsikt's links lead: the Explanation as sent, then the
 * finished Debrief, its time (and whether it was after the Debrief deadline), the key moments as
 * the Student read them and the reflection answers. Each part says when it is missing. An Admin
 * outside the Class and every Student get the permission-denied page (the api refuses them).
 * Ids and Roles only; the page names no Student (AD-14).
 */
export function SummaryPage({ classSessionId, studentId }: { classSessionId: string; studentId: string }) {
  const named = UUID.test(classSessionId) && UUID.test(studentId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <SummaryView classSessionId={classSessionId} studentId={studentId} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function SummaryView({
  classSessionId,
  studentId,
  user,
  updatedAt,
}: {
  classSessionId: string;
  studentId: string;
  user: SessionUser;
  updatedAt: number;
}) {
  const found = useStaffSummary(classSessionId, studentId);
  const { phase, retry } = usePageState(found, staffSummaryKey(classSessionId, studentId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const item = found.data;
  const crumbs = item
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: nb.sessions.crumb, href: classSessionPath(classSessionId) },
        { label: copy.crumb, href: studentDebriefPath(classSessionId, studentId) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={item ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {item ? <SummaryBody item={item} /> : null}
    </PageShell>
  );
}

function SummaryBody({ item }: { item: StaffSummary }) {
  return (
    <>
      <p className={`${LINE} mt-1 text-ink-secondary`}>
        {item.role ? nb.debriefEntry.roleGame(roleName(item.role), item.game_number ?? null) : copy.noStudent}
      </p>
      <section id="forklaring" aria-labelledby="summary-explanation" data-summary-explanation="" className={SECTION}>
        <h2 id="summary-explanation" className="text-headline text-ink">
          {copy.explanation}
        </h2>
        {item.explanation ? (
          <>
            <p className="mt-1 text-caption text-ink-secondary">{copy.sentAt(osloDateText(item.explanation.saved_at))}</p>
            <p className={`${LINE} mt-3 border-l-2 border-axis pl-3 whitespace-pre-wrap text-ink`}>{item.explanation.text}</p>
          </>
        ) : (
          <p className={`${LINE} mt-3 text-ink`}>{copy.noExplanation}</p>
        )}
      </section>
      <section aria-labelledby="summary-debrief" data-summary-debrief={item.summary ? "" : "missing"} className={SECTION}>
        <h2 id="summary-debrief" className="text-headline text-ink">
          {copy.summary}
        </h2>
        {item.summary ? <Finished summary={item.summary} /> : <p className={`${LINE} mt-3 text-ink`}>{copy.notFinished}</p>}
      </section>
    </>
  );
}

function Finished({ summary }: { summary: Summary }) {
  return (
    <>
      <p data-summary-finished="" className={`${LINE} mt-3 text-ink`}>
        {copy.finishedAt(osloDateText(summary.finished_at))} {summary.late ? copy.late : null}
      </p>
      <h3 className="mt-6 text-label text-ink">{copy.moments}</h3>
      {summary.moments.length === 0 ? (
        <p className={`${LINE} mt-1 text-ink`}>{copy.noMoments}</p>
      ) : (
        <ol className="mt-2 flex flex-col gap-4">
          {summary.moments.map((moment) => (
            <li key={moment.id} data-summary-moment={moment.id} className={`${LINE} text-ink`}>
              <p className="font-semibold">{moment.heading.text}</p>
              <p className="mt-1">{moment.reckoning.text}</p>
              <p className="mt-1">{moment.later.text}</p>
              {moment.patterns.map((pattern, i) => (
                <p key={i} className="mt-1 text-ink-secondary">
                  {pattern.text}
                </p>
              ))}
            </li>
          ))}
        </ol>
      )}
      <h3 className="mt-6 text-label text-ink">{copy.reflection}</h3>
      <ol className="mt-2 flex flex-col gap-4">
        {summary.reflection.map((answer) => (
          <li key={answer.question_id} data-summary-answer={answer.question_id}>
            <p className={`${LINE} text-ink`}>{answer.prompt}</p>
            <p className={`${LINE} mt-1 border-l-2 border-axis pl-3 whitespace-pre-wrap text-ink`}>{answer.text}</p>
          </li>
        ))}
      </ol>
    </>
  );
}
