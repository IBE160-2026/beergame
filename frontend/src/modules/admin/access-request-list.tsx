"use client";

import { useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { errorCode } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";

import { type AccessRequest, accessRequestsKey, useAccessRequests, useDismissAccessRequest } from "./api";
import { formatDate } from "./invitations";
import { Cell, type RowLine, RowMessage } from "./user-list";

const copy = nb.admin.users.requests;

/**
 * «Forespørsler om lærertilgang» on «Brukere og roller» (Story 3.13, FR-1, FR-3): the open
 * requests from the Landing with name, address, Institution and date, newest first. Each row has
 * «Inviter … som Faglærer», which fills the invite form above (`onInvite`), and «Avvis
 * forespørselen fra …», which dismisses it at once with no dialog. Below laptop width every row is
 * one block with each field labelled, as the User list.
 */
export function AccessRequestList({ onInvite }: { onInvite: (request: AccessRequest) => void }) {
  const requests = useAccessRequests();
  const pageState = usePageState(requests, accessRequestsKey);
  const moreFailed = requests.isFetchNextPageError;
  const phase = moreFailed ? "ready" : pageState.phase;
  const dismiss = useDismissAccessRequest();
  // The line of the last dismissal stands under the list, since its row is gone.
  const [line, setLine] = useState<RowLine>();
  const items = requests.data?.pages.flatMap((page) => page.items) ?? [];

  function onDismiss(item: AccessRequest) {
    if (dismiss.isPending) return;
    setLine(undefined);
    dismiss.mutate(item, {
      onSuccess: () => setLine({ key: item.id, text: copy.dismissed(item.name), refused: false }),
      onError: (error) =>
        setLine(
          errorCode(error) === "not_found"
            ? { key: item.id, text: copy.alreadyAnswered(item.name), refused: false }
            : { key: item.id, text: copy.dismissFailed, refused: true },
        ),
    });
  }

  return (
    <div className="@container">
      {phase === "loading" || phase === "slow" ? (
        <div>
          <Skeleton heading={false} rows={2} columns={4} />
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
                  {[
                    copy.columns.name,
                    copy.columns.email,
                    copy.columns.institution,
                    copy.columns.received,
                    copy.columns.actions,
                  ].map((heading) => (
                    <th key={heading} scope="col" className="py-2 pr-6 align-bottom text-label font-semibold text-ink">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3">
                    <Cell label={copy.columns.name}>
                      <span className="font-semibold [overflow-wrap:anywhere]">{item.name}</span>
                    </Cell>
                    <Cell label={copy.columns.email}>
                      <span className="[overflow-wrap:anywhere]">{item.email}</span>
                    </Cell>
                    <Cell label={copy.columns.institution}>
                      <span className="[overflow-wrap:anywhere]">{item.institution}</span>
                    </Cell>
                    <Cell label={copy.columns.received}>
                      <span className="@min-[60em]:whitespace-nowrap">{formatDate(item.requested_at)}</span>
                    </Cell>
                    <td className="py-3 @max-[60em]:block @max-[60em]:pt-2 @max-[60em]:pb-0 @min-[60em]:w-[18em]">
                      <div className="flex flex-col gap-2">
                        <Button
                          className="[overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                          onClick={() => {
                            setLine(undefined);
                            onInvite(item);
                          }}
                        >
                          {copy.invite(item.name)}
                        </Button>
                        <Button
                          unavailable={dismiss.isPending}
                          className="[overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                          onClick={() => onDismiss(item)}
                        >
                          {copy.dismiss(item.name)}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <RowMessage line={line} />
          {moreFailed ? <ActionError message={copy.moreFailed} className="mt-4" /> : null}
          {requests.hasNextPage ? (
            <Button
              className="mt-4"
              unavailable={requests.isFetchingNextPage}
              onClick={() => void requests.fetchNextPage()}
            >
              {copy.more}
            </Button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
