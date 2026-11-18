"use client";

import { useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";

import { type AuditEvent, type AuditFilters, auditKey, useAuditEvents } from "./api";
import { actionLabel, actorText, changeLines, formatTime, rangeError, targetText } from "./audit";
import { AuditFiltersForm } from "./audit-filters";
import { Cell } from "./user-list";

const copy = nb.admin.audit;

const NO_FILTERS: AuditFilters = {
  actor: "",
  action: "",
  since: "",
  until: "",
};

/**
 * The audit log (Story 3.12, FR-3, UX-DR75): the filters, then every event newest first with
 * time, actor, action, what it concerns and the change, one page of the list envelope at a time.
 * Names are the api's, read when the page is. Below laptop width every row is one block with
 * each field labelled, as the User list.
 */
export function AuditLog() {
  const [typed, setTyped] = useState<AuditFilters>(NO_FILTERS);
  // A reversed range is not asked for: the list keeps the last filters that make sense.
  const [applied, setApplied] = useState<AuditFilters>(NO_FILTERS);
  const events = useAuditEvents(applied);
  const pageState = usePageState(events, auditKey(applied));
  const moreFailed = events.isFetchNextPageError;
  const phase = moreFailed ? "ready" : pageState.phase;
  const items = events.data?.pages.flatMap((page) => page.items) ?? [];
  const filtered = Object.values(applied).some(Boolean);

  function change(next: AuditFilters) {
    setTyped(next);
    // A reversed range keeps the last valid dates; the actor and action still apply.
    setApplied((last) =>
      rangeError(next.since, next.until) ? { ...next, since: last.since, until: last.until } : next,
    );
  }

  return (
    <div className="@container">
      <AuditFiltersForm value={typed} onChange={change} />
      {phase === "loading" || phase === "slow" ? (
        <div className="mt-6">
          <Skeleton heading={false} rows={4} columns={5} />
          <LoadingNote visible={phase === "slow"} />
        </div>
      ) : null}
      {phase === "failed" ? (
        <div className="mt-6 flex flex-col items-start gap-3">
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {nb.system.pageError}
          </p>
          <Button onClick={pageState.retry}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {phase === "ready" ? (
        <>
          <p role="status" className="mt-6 text-body-phone text-ink lg:text-body">
            {items.length === 0 ? (filtered ? copy.list.noMatches : copy.list.empty) : null}
          </p>
          {items.length > 0 ? (
            <table className="w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop">
              <caption className="sr-only">{copy.list.title}</caption>
              <thead className="@max-[60em]:hidden">
                <tr className="border-b border-axis">
                  {Object.values(copy.list.columns).map((heading) => (
                    <th key={heading} scope="col" className="py-2 pr-6 align-bottom text-label font-semibold text-ink">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
                {items.map((event) => (
                  <EventRow key={event.id} event={event} />
                ))}
              </tbody>
            </table>
          ) : null}
          {moreFailed ? <ActionError message={copy.list.moreFailed} className="mt-4" /> : null}
          {events.hasNextPage ? (
            <Button
              className="mt-4"
              unavailable={events.isFetchingNextPage}
              onClick={() => void events.fetchNextPage()}
            >
              {copy.list.more}
            </Button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function EventRow({ event }: { event: AuditEvent }) {
  const columns = copy.list.columns;
  const lines = changeLines(event.change);
  return (
    <tr className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3">
      <Cell label={columns.time}>
        <time dateTime={event.occurred_at} className="@min-[60em]:whitespace-nowrap">
          {formatTime(event.occurred_at)}
        </time>
      </Cell>
      <Cell label={columns.actor}>
        <span className={event.actor_id === null ? "text-ink-secondary" : undefined}>{actorText(event)}</span>
      </Cell>
      <Cell label={columns.action}>
        <span className="font-semibold [overflow-wrap:anywhere]">{actionLabel(event.action)}</span>
      </Cell>
      <Cell label={columns.target}>
        <span className="[overflow-wrap:anywhere]">
          {event.targets.length ? event.targets.map(targetText).join(" · ") : copy.noChange}
        </span>
      </Cell>
      <Cell label={columns.change}>
        {lines.length ? (
          <span className="flex flex-col [overflow-wrap:anywhere]">
            {lines.map((line) => (
              <span key={line.label}>
                <span className="text-ink-secondary">{line.label}:</span> {line.value}
              </span>
            ))}
          </span>
        ) : (
          copy.noChange
        )}
      </Cell>
    </tr>
  );
}
