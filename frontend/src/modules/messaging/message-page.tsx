"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { Link } from "@/components/link";
import {
  classOverviewPath,
  classPath,
  classSessionPath,
  HOME_PATH,
  messagePath,
  sentMessagesPath,
  studentPagePath,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import {
  type MessageForm,
  messageFormKey,
  type MessageSent,
  type MessageTo,
  type NotMetStudent,
  sendMessage,
  useMessageForm,
} from "./api";
import { canSend, keyFor, messageTitle, notMetCells, recipientFrom, sendErrors } from "./message-form";

const copy = nb.messages;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Meldingsskjema (Story 7.9, FR-40, UX-DR46): its own page, with the recipient its query names
 * as the title — one Student, a Class game or the whole Class session — a multi-line Tekstfelt and
 * «Send Melding». One-way: no reply field and no way to add recipients. Browser Back returns to the
 * page it was opened from. Opened from the Oversikt header and Spillinnsikt; later epics open it
 * with `messagePath`. Story 13.6: written to the Students who have not met the requirement, a table
 * of them and their shares stands above the field. Anyone but the Class's staff sees the permission-denied page (FR-5).
 */
export function MessagePage({ sessionId }: { sessionId: string }) {
  const to = recipientFrom(useSearchParams());
  const named = ID.test(sessionId) && to !== null;
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <MessageView sessionId={sessionId.toLowerCase()} to={to} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function MessageView({
  sessionId,
  to,
  user,
  updatedAt,
}: {
  sessionId: string;
  to: MessageTo;
  user: SessionUser;
  updatedAt: number;
}) {
  const found = useMessageForm(sessionId, to);
  const { phase, retry } = usePageState(found, messageFormKey(sessionId, to));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  const title = data ? messageTitle(data) : undefined;
  const crumbs =
    data && title
      ? ([
          { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
          { label: data.class_name, href: classPath(data.class_id) },
          { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
          { label: nb.overview.crumb, href: classOverviewPath(sessionId) },
          { label: copy.crumb, href: messagePath(sessionId, to) },
        ] as const)
      : undefined;
  return (
    <PageShell
      user={user}
      title={title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 4, columns: 1 }}
    >
      {/* Keyed by the recipient: another recipient's page starts with an empty form and key. */}
      {data ? <Composer key={messageFormKey(sessionId, to).join("|")} sessionId={sessionId} to={to} form={data} /> : null}
    </PageShell>
  );
}

function makeKey(): string {
  return crypto.randomUUID();
}

/**
 * The form, then its result: «Meldingen er sendt til 4 studenter.» replaces the form and takes
 * focus. A failure shows «Det ble ikke lagret. Prøv igjen.» in place, keeps the text and leaves the
 * button active; a retry of the same text carries the same key, so it never sends twice.
 */
function Composer({ sessionId, to, form }: { sessionId: string; to: MessageTo; form: MessageForm }) {
  const fieldId = useId();
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [sent, setSent] = useState<MessageSent | null>(null);
  const key = useRef<{ key: string; text: string } | null>(null);
  const result = useRef<HTMLParagraphElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const writingAgain = useRef(false);
  const send = useAction({
    mutationFn: (vars: { text: string; key: string }) => sendMessage(sessionId, to, vars.text, vars.key),
    messages: sendErrors(form),
    onSuccess: (answer) => {
      key.current = null;
      setText("");
      setSent(answer);
      void queryClient.invalidateQueries({ queryKey: messageFormKey(sessionId, to) });
    },
  });
  useEffect(() => {
    if (sent) result.current?.focus();
    else if (writingAgain.current) {
      writingAgain.current = false;
      field.current?.focus();
    }
  }, [sent]);
  const ready = canSend(text, form, send.isPending);
  if (sent) {
    return (
      <div className="mt-6 flex max-w-[40rem] flex-col items-start gap-3" data-message-result="">
        <p
          ref={result}
          tabIndex={-1}
          role="status"
          className="self-stretch border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body"
        >
          {copy.sent(sent.students)}
        </p>
        <p className="text-caption text-ink-secondary">{copy.sentBefore(sent.sent_before)}</p>
        <SentLink sessionId={sessionId} />
        <Button
          onClick={() => {
            writingAgain.current = true;
            send.reset();
            setSent(null);
          }}
        >
          {copy.writeAnother}
        </Button>
      </div>
    );
  }
  return (
    <form
      className="mt-6 flex max-w-[40rem] flex-col gap-4"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready) return;
        key.current = keyFor(key.current, text, makeKey);
        send.mutate({ text, key: key.current.key });
      }}
    >
      <p className="text-body-phone text-ink-secondary lg:text-body">
        {form.students > 0 ? copy.reach(form.students) : copy.noStudents}
      </p>
      {form.kind === "requirement_not_met" && form.not_met.length > 0 ? (
        <NotMetTable sessionId={sessionId} rows={form.not_met} />
      ) : null}
      <TextAreaField
        ref={field}
        id={fieldId}
        label={copy.field}
        rows={8}
        value={text}
        onChange={(event) => setText(event.target.value)}
        hint={copy.hint(formatNumber(form.max_length))}
      />
      <div className="flex flex-col items-start gap-2">
        <Button type="submit" variant="primary" unavailable={!ready}>
          {send.isPending ? copy.sending : copy.send}
        </Button>
        <ActionError message={send.errorMessage} />
      </div>
      <p className="text-caption text-ink-secondary">{copy.sentBefore(form.sent_before)}</p>
      <SentLink sessionId={sessionId} />
    </form>
  );
}

/**
 * The Students who have not met the requirement (Story 13.6, FR-17, UX-DR54): each name a Lenke
 * to their Studentside, the share of Weeks they ordered against the share required of them, and
 * the share the Play deadline's playout played, so a shortfall the playout or the group's pace
 * caused can be told from one the Student caused. Every number is the api's.
 */
function NotMetTable({ sessionId, rows }: { sessionId: string; rows: readonly NotMetStudent[] }) {
  const table = copy.notMet;
  return (
    <div className="flex flex-col gap-2">
      <table className="w-full border-collapse text-caption text-ink tabular-nums lining-nums lg:text-body" data-not-met="">
        <caption className="text-left text-label text-ink">{table.caption}</caption>
        <thead>
          <tr className="border-b border-axis text-ink-secondary">
            <th scope="col" className="py-1 pr-3 text-left align-bottom font-normal">
              {table.student}
            </th>
            <th scope="col" className="py-1 pr-3 text-right align-bottom font-normal">
              {table.ordered}
            </th>
            <th scope="col" className="py-1 pr-3 text-right align-bottom font-normal">
              {table.required}
            </th>
            <th scope="col" className="py-1 text-right align-bottom font-normal">
              {table.playout}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const cells = notMetCells(row);
            return (
              <tr key={row.user_id} className="border-b border-hairline" data-not-met-row={row.user_id}>
                <th scope="row" className="py-1 pr-3 text-left align-top font-normal [overflow-wrap:anywhere]">
                  {row.name === null ? (
                    copy.unknownStudent
                  ) : (
                    // A 44 px tap target, as every control on a phone.
                    <Link href={studentPagePath(sessionId, row.user_id)} standalone className="min-w-tap-target-min">
                      {row.name}
                    </Link>
                  )}
                </th>
                <td className="py-1 pr-3 text-right align-top">{cells.ordered}</td>
                <td className="py-1 pr-3 text-right align-top">{cells.required}</td>
                <td className="py-1 text-right align-top">{cells.playout}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="text-caption text-ink-secondary">{table.note}</p>
    </div>
  );
}

/** «Se sendte meldinger»: the Class session's «Meldinger» (Story 7.10). */
function SentLink({ sessionId }: { sessionId: string }) {
  return (
    <p>
      <Link href={sentMessagesPath(sessionId)} standalone>
        {copy.sentList.fromForm}
      </Link>
    </p>
  );
}
