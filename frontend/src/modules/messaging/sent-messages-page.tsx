"use client";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import {
  classOverviewPath,
  classPath,
  classSessionPath,
  HOME_PATH,
  messagePath,
  sentMessagesPath,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { osloDateText } from "@/modules/sessions/dates";

import { type SentMessage, sentMessagesKey, useSentMessages } from "./api";
import { againTo, recipientLine, senderName } from "./message-list";

const copy = nb.messages.sentList;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * «Meldinger» (Story 7.10, FR-40): every Message a Class session was sent, newest first, with its
 * recipient, sender, time in Europe/Oslo, the number of Students it went to and its text as plain
 * text, each with a Lenke back to the Meldingsskjema for the same recipient. For the Class's staff;
 * anyone else sees the permission-denied page (FR-5). A send emits `session:<id>`, which refetches
 * the list (`topics.ts`).
 */
export function SentMessagesPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        ID.test(sessionId) ? (
          <SentView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function SentView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useSentMessages(sessionId);
  const { phase, retry } = usePageState(found, sentMessagesKey(sessionId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  const crumbs = data
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: data.class_name, href: classPath(data.class_id) },
        { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
        { label: nb.overview.crumb, href: classOverviewPath(sessionId) },
        { label: copy.crumb, href: sentMessagesPath(sessionId) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={data ? copy.title : undefined}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 4, columns: 1 }}
    >
      {data ? (
        <div className="mt-2 flex max-w-[40rem] flex-col">
          <p className="text-body-phone text-ink-secondary [overflow-wrap:anywhere] lg:text-body">
            {copy.session(data.session_number, data.class_name)}
          </p>
          <p>
            <Link href={messagePath(sessionId)} standalone data-message-session="">
              {nb.messages.toSession}
            </Link>
          </p>
          {data.items.length === 0 ? (
            <p className="mt-4 text-body-phone text-ink-secondary lg:text-body">{copy.empty}</p>
          ) : (
            <ol className="mt-4 flex flex-col border-t border-hairline" data-sent-messages="">
              {data.items.map((item) => (
                <SentItem key={item.id} item={item} sessionId={sessionId} sessionNumber={data.session_number} />
              ))}
            </ol>
          )}
        </div>
      ) : null}
    </PageShell>
  );
}

function SentItem({ item, sessionId, sessionNumber }: { item: SentMessage; sessionId: string; sessionNumber: number }) {
  const recipient = recipientLine(item, sessionNumber);
  const to = againTo(item);
  return (
    <li className="border-b border-hairline py-4" data-message={item.id}>
      <h2 className="text-body-phone font-semibold text-ink [overflow-wrap:anywhere] lg:text-body">{recipient}</h2>
      <p className="mt-1 text-caption text-ink-secondary [overflow-wrap:anywhere]">
        {copy.from(senderName(item))} · <time dateTime={item.sent_at}>{osloDateText(item.sent_at)}</time> ·{" "}
        {copy.reach(item.students)}
      </p>
      {/* Plain text: React escapes it, nothing is made a link, and line breaks are kept. */}
      <p className="mt-2 whitespace-pre-wrap text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">
        {item.text}
      </p>
      {to ? (
        <p>
          <Link href={messagePath(sessionId, to)} standalone aria-label={copy.writeAgainLabel(recipient)}>
            {copy.writeAgain}
          </Link>
        </p>
      ) : null}
    </li>
  );
}
