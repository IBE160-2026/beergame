"use client";

import { Button } from "@/components/button";
import type { LiveLines } from "@/components/connection-notice";
import { Link } from "@/components/link";
import { Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { formatClock } from "@/lib/connection";
import { formatNumber } from "@/lib/number-format";
import { dayUsdText } from "@/modules/admin/daily-spend";
import { Cell } from "@/modules/admin/user-list";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_OPERATIONS_PATH, adminOperationsPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { type Operations, useOperationsSessions, useSessionOperations } from "./api";
import {
  ErrorHoursChart,
  ErrorHoursTable,
  FallbackChart,
  FallbackTable,
  ChartBlock,
  ResponseTimesChart,
  ResponseTimesTable,
} from "./ops-charts";
import { hourTotal, shareText } from "./operations";

const copy = nb.admin.operations;

const LIST_CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_OPERATIONS_PATH },
] as const;

const LEAD = "mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body";
const TEXT = "text-body-phone text-ink lg:text-body";
const TABLE =
  "w-full max-w-2xl border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop";
const HEAD = "py-2 pr-6 align-bottom text-label font-semibold text-ink";
const ROW = "border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3";
const BODY = "@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis";

/** The page's Tilkoblingslinje for figures read every 30 s: a read that failed keeps the last
 * figures, says when they are from and offers «Prøv igjen» (UX-DR58). The page reads by interval,
 * not from the event stream, so a quiet stream alone shows no line (an empty message is none). */
function liveLines(failed: boolean, updatedAt: number, retry: () => void): LiveLines {
  const action = { label: nb.system.retry, onPress: retry };
  const message = failed ? copy.failed(formatClock(updatedAt)) : "";
  return {
    stale: () => message,
    staleAction: action,
    failed: failed ? { message, action } : undefined,
  };
}

function Updated({ at }: { at: number }) {
  return (
    <p className="mt-1 text-label text-ink-secondary" data-updated-at={at}>
      {copy.refetch} {nb.system.lastUpdated(formatClock(at))}
    </p>
  );
}

function FirstLoad({
  pending,
  failed,
  retry,
  rows,
}: {
  pending: boolean;
  failed: boolean;
  retry: () => void;
  rows: number;
}) {
  if (pending) return <Skeleton heading={false} rows={rows} columns={3} />;
  if (!failed) return null;
  return (
    <div className="mt-6 flex flex-col items-start gap-3">
      <p role="alert" className="text-body-phone text-restordre lg:text-body">
        {nb.system.pageError}
      </p>
      <Button onClick={retry}>{nb.system.retry}</Button>
    </div>
  );
}

/**
 * «Drift» in the Admin-område (Story 15.8, NFR-8): every saved Class session, newest first, with
 * its errors of the last 24 hours, each a Lenke to its view. Read again every 30 s. Only an Admin
 * sees it; anyone else gets the permission-denied page.
 */
export function OperationsListPage() {
  return <GuardedPage page="adminArea">{(user) => <ListContent user={user} />}</GuardedPage>;
}

function ListContent({ user }: { user: Parameters<typeof PageShell>[0]["user"] }) {
  const sessions = useOperationsSessions();
  const found = sessions.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      crumbs={LIST_CRUMBS}
      updatedAt={sessions.dataUpdatedAt || undefined}
      liveLines={found ? liveLines(sessions.isError, sessions.dataUpdatedAt, () => void sessions.refetch()) : undefined}
    >
      <p className={LEAD}>{copy.lead}</p>
      <p className={LEAD}>{copy.listLead}</p>
      {found ? <Updated at={sessions.dataUpdatedAt} /> : null}
      <FirstLoad
        pending={sessions.isPending}
        failed={sessions.isError && !found}
        retry={() => void sessions.refetch()}
        rows={4}
      />
      {found && found.items.length === 0 ? <p className={`${TEXT} mt-6`}>{copy.empty}</p> : null}
      {found && found.items.length > 0 ? (
        <div className="mt-6 @container">
          <table className={TABLE}>
            <thead className="@max-[60em]:hidden">
              <tr className="border-b border-axis">
                <th scope="col" className={HEAD}>
                  {copy.columns.session}
                </th>
                <th scope="col" className={`${HEAD} text-right`}>
                  {copy.columns.errors}
                </th>
              </tr>
            </thead>
            <tbody className={BODY}>
              {found.items.map((item) => (
                <tr key={item.id} className={ROW}>
                  <Cell label={copy.columns.session}>
                    <Link href={adminOperationsPath(item.id)} standalone className="[overflow-wrap:anywhere]">
                      {item.label}
                    </Link>
                    {item.institution_name ? (
                      <span className="block text-ink-secondary [overflow-wrap:anywhere]">{item.institution_name}</span>
                    ) : null}
                  </Cell>
                  <td className="py-3 pr-6 text-right @max-[60em]:flex @max-[60em]:gap-3 @max-[60em]:py-1 @max-[60em]:pr-0 @max-[60em]:text-left">
                    <span className="w-20 shrink-0 text-ink-secondary @min-[60em]:hidden">{copy.columns.errors}</span>
                    <span className={item.errors_24h > 0 ? "font-semibold" : undefined}>
                      {formatNumber(item.errors_24h)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </PageShell>
  );
}

/**
 * One Class session's «Drift» view (Story 15.8, NFR-8, FR-79, UX-DR58): its errors by source and
 * hour, the share of its LLM players' Orders each fallback kind replaced, their response times per
 * Effort level, the share of LLM Seats the Play guard switched and its AI cost; each chart with
 * «Vis som tabell». Counts and timings only. Read again every 30 s; a failed read keeps the last
 * figures and says so in the Tilkoblingslinje.
 */
export function OperationsPage({ sessionId }: { sessionId: string }) {
  return <GuardedPage page="adminArea">{(user) => <ViewContent user={user} sessionId={sessionId} />}</GuardedPage>;
}

function ViewContent({ user, sessionId }: { user: Parameters<typeof PageShell>[0]["user"]; sessionId: string }) {
  const figures = useSessionOperations(sessionId);
  const found = figures.data;
  const retry = () => void figures.refetch();
  const title = found?.label ?? copy.title;
  return (
    <PageShell
      user={user}
      title={title}
      crumbs={[...LIST_CRUMBS, { label: title, href: adminOperationsPath(sessionId) }]}
      updatedAt={figures.dataUpdatedAt || undefined}
      liveLines={found ? liveLines(figures.isError, figures.dataUpdatedAt, retry) : undefined}
    >
      {found?.institution_name ? (
        <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{found.institution_name}</p>
      ) : null}
      {found ? <Updated at={figures.dataUpdatedAt} /> : null}
      <FirstLoad pending={figures.isPending} failed={figures.isError && !found} retry={retry} rows={6} />
      {found ? <Figures found={found} /> : null}
    </PageShell>
  );
}

export function Figures({ found }: { found: Operations }) {
  const last24 = found.hours.reduce((sum, hour) => sum + hourTotal(hour), 0);
  const allTime = found.totals.conservation_check + found.totals.job_failed + found.totals.api_error;
  return (
    <>
      <dl className="mt-6 grid max-w-2xl grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-3">
        <div>
          <dt className="text-label text-ink-secondary">{copy.columns.errors}</dt>
          <dd className="text-step-title font-semibold text-ink tabular-nums lining-nums">{formatNumber(last24)}</dd>
        </div>
        <div>
          <dt className="text-label text-ink-secondary">{copy.guard.title}</dt>
          <dd className="text-step-title font-semibold text-ink tabular-nums lining-nums">
            {found.llm_seats === 0
              ? copy.guard.none
              : copy.guard.value(
                  shareText(found.switched_share),
                  formatNumber(found.switched_seats),
                  formatNumber(found.llm_seats),
                )}
          </dd>
        </div>
        <div>
          <dt className="text-label text-ink-secondary">{copy.cost.title}</dt>
          <dd className="text-step-title font-semibold text-ink tabular-nums lining-nums">
            {copy.cost.value(dayUsdText(found.cost_usd), formatNumber(found.ai_calls))}
          </dd>
        </div>
      </dl>
      <ChartBlock
        kind="errors"
        title={copy.errors.title}
        lead={
          <>
            <p>{copy.errors.lead}</p>
            <p className="tabular-nums lining-nums">
              {copy.errors.last24(formatNumber(last24))} {copy.errors.allTime(formatNumber(allTime))}
            </p>
          </>
        }
        chart={<ErrorHoursChart hours={found.hours} />}
        table={<ErrorHoursTable hours={found.hours} />}
      />
      <ChartBlock
        kind="fallbacks"
        title={copy.fallback.title}
        lead={
          <>
            <p>{copy.fallback.lead}</p>
            <p className="tabular-nums lining-nums">
              {found.llm_orders === 0 ? copy.fallback.none : copy.fallback.base(formatNumber(found.llm_orders))}
            </p>
          </>
        }
        chart={<FallbackChart found={found} />}
        table={<FallbackTable found={found} />}
      />
      {found.response_times.length === 0 ? (
        <section aria-labelledby="times-title" className="mt-10">
          <h2 id="times-title" className="text-headline text-ink">
            {copy.times.title}
          </h2>
          <p className={LEAD}>{copy.times.none}</p>
        </section>
      ) : (
        <ChartBlock
          kind="response-times"
          title={copy.times.title}
          lead={copy.times.lead}
          chart={<ResponseTimesChart found={found} />}
          table={<ResponseTimesTable found={found} />}
        />
      )}
    </>
  );
}
