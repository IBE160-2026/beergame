"use client";

import { useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";

import { invitationsKey, type ListedInvitation, useInvitations, useResendInvitation } from "./api";
import {
  canResend,
  formatDate,
  resendLabel,
  resendRefusalLine,
  resentLine,
  roleText,
  rowKey,
  statusText,
} from "./invitations";
import { Cell, type RowLine, RowMessage } from "./user-list";

const copy = nb.admin.users.invitations;

/**
 * «Invitasjoner» on «Brukere og roller» (Story 3.10, FR-1, FR-3): the newest Invitation to each
 * address and role, newest first, with its role, status and expiry, and whether the recipient
 * asked for a new one. An open or expired Invitation has one button that sends it again, at once
 * and with no dialog; an accepted one has none. Below laptop width every row is one block with
 * each field labelled, as the User list.
 */
export function InvitationList() {
  const invitations = useInvitations();
  const pageState = usePageState(invitations, invitationsKey);
  const moreFailed = invitations.isFetchNextPageError;
  const phase = moreFailed ? "ready" : pageState.phase;
  const resend = useResendInvitation();
  const [line, setLine] = useState<RowLine>();
  const items = invitations.data?.pages.flatMap((page) => page.items) ?? [];

  function press(invitation: ListedInvitation) {
    if (resend.isPending) return;
    setLine(undefined);
    const key = rowKey(invitation);
    resend.mutate(invitation, {
      onSuccess: (sent) => setLine({ key, text: resentLine(sent), refused: false }),
      onError: (error) => setLine({ key, text: resendRefusalLine(error), refused: true }),
    });
  }

  return (
    <div className="@container">
      {phase === "loading" || phase === "slow" ? (
        <div>
          <Skeleton heading={false} rows={3} columns={4} />
          <LoadingNote visible={phase === "slow"} />
        </div>
      ) : null}
      {phase === "failed" ? (
        <div className="flex flex-col items-start gap-3">
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {nb.system.pageError}
          </p>
          <Button onClick={pageState.retry}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {phase === "ready" ? (
        <>
          {items.length === 0 ? <p className="text-body-phone text-ink lg:text-body">{copy.empty}</p> : null}
          {items.length > 0 ? (
            <table className="w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop">
              <thead className="@max-[60em]:hidden">
                <tr className="border-b border-axis">
                  {[copy.columns.email, copy.columns.role, copy.columns.status, copy.columns.expires, copy.columns.actions].map(
                    (heading) => (
                      <th key={heading} scope="col" className="py-2 pr-6 align-bottom text-label font-semibold text-ink">
                        {heading}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
                {items.map((invitation) => {
                  const key = rowKey(invitation);
                  return (
                    <tr key={key} className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3">
                      <Cell label={copy.columns.email}>
                        <span className="font-semibold [overflow-wrap:anywhere]">{invitation.email}</span>
                      </Cell>
                      <Cell label={copy.columns.role}>{roleText(invitation)}</Cell>
                      <Cell label={copy.columns.status}>
                        <span className={invitation.status === "open" ? undefined : "text-ink-secondary"}>
                          {statusText(invitation)}
                        </span>
                        {invitation.renewal_requested ? (
                          <span className="mt-1 block max-w-[16em] text-ink">{copy.renewalRequested}</span>
                        ) : null}
                      </Cell>
                      <Cell label={copy.columns.expires}>
                        <span className="@min-[60em]:whitespace-nowrap">{formatDate(invitation.expires_at)}</span>
                      </Cell>
                      <td className="py-3 @max-[60em]:block @max-[60em]:pt-2 @max-[60em]:pb-0">
                        {canResend(invitation) ? (
                          <Button
                            className="@max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                            unavailable={resend.isPending}
                            onClick={() => press(invitation)}
                          >
                            {resendLabel(invitation)}
                          </Button>
                        ) : null}
                        <RowMessage line={line?.key === key ? line : undefined} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : null}
          {moreFailed ? <ActionError message={copy.moreFailed} className="mt-4" /> : null}
          {invitations.hasNextPage ? (
            <Button
              className="mt-4"
              unavailable={invitations.isFetchingNextPage}
              onClick={() => void invitations.fetchNextPage()}
            >
              {copy.more}
            </Button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
