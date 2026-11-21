"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/button";
import { Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { osloDateText } from "@/modules/sessions/dates";

import { type MyMessage, myMessagesKey, useMyMessages } from "./api";
import { arrivalText, senderName } from "./message-list";

const copy = nb.messages.mine;

/**
 * «Meldinger» on the Student's Hjem (Story 7.10, FR-40, FR-73, UX-DR46): the Messages written to
 * the Student, newest first, each with its sender, the time in Europe/Oslo and the full text as
 * plain text with its line breaks kept. One-way: no reply, reaction or forward, and no read state.
 * A Message's notice emits `user:<id>`, which refetches the list (`topics.ts`); a Message that
 * arrives while Hjem is open is said by a polite live region, and focus stays where it is. With no
 * Message the section is not drawn; its read failing never hides the rest of Hjem.
 */
export function MyMessages({ showClass }: { showClass: boolean }) {
  const found = useMyMessages();
  const { phase, retry } = usePageState(found, myMessagesKey);
  const items = found.data?.items;
  const said = useArrivals(found.isFetchedAfterMount ? items : undefined);
  let body: React.ReactNode = null;
  // A refetch that fails keeps the Messages already shown; only a first read that fails says so.
  if (phase === "failed" && items === undefined) {
    body = (
      <section aria-labelledby="my-messages-title" className="mt-8 flex max-w-md flex-col items-start gap-3">
        <h2 id="my-messages-title" className="text-headline text-ink">
          {copy.title}
        </h2>
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button onClick={retry}>{nb.system.retry}</Button>
      </section>
    );
  } else if (items === undefined) {
    body = (
      <div className="mt-8 max-w-md">
        <Skeleton heading rows={2} />
      </div>
    );
  } else if (items.length > 0) {
    body = (
      <section aria-labelledby="my-messages-title" className="mt-8 max-w-md" data-my-messages="">
        <h2 id="my-messages-title" className="text-headline text-ink">
          {copy.title}
        </h2>
        <ol className="mt-3 flex flex-col border-t border-hairline">
          {items.map((item) => (
            <MessageItem key={item.id} item={item} showClass={showClass} />
          ))}
        </ol>
      </section>
    );
  }
  return (
    <>
      {body}
      {/* Always in the page, so an arrival is heard even when it is the first Message. */}
      <p role="status" className="sr-only" data-my-messages-said="">
        {said}
      </p>
    </>
  );
}

function MessageItem({ item, showClass }: { item: MyMessage; showClass: boolean }) {
  return (
    <li className="border-b border-hairline py-4" data-message={item.id}>
      <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-body-phone font-semibold text-ink [overflow-wrap:anywhere] lg:text-body">
          {senderName(item)}
        </span>
        <time dateTime={item.sent_at} className="text-caption text-ink-secondary">
          {osloDateText(item.sent_at)}
        </time>
      </p>
      {showClass ? (
        <p className="mt-1 text-caption text-ink-secondary [overflow-wrap:anywhere]">{item.class_name}</p>
      ) : null}
      {/* Plain text: React escapes it, nothing is made a link, and line breaks are kept. */}
      <p className="mt-2 whitespace-pre-wrap text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">
        {item.text}
      </p>
    </li>
  );
}

/** The live region's text: what arrived since the previous answer; empty until something does.
 * `items` is undefined until a read made after the page opened, so Messages held in the cache from
 * an earlier visit are the first answer, never announced as new. */
function useArrivals(items: readonly MyMessage[] | undefined): string {
  const seen = useRef<ReadonlySet<string> | null>(null);
  const [said, setSaid] = useState("");
  useEffect(() => {
    if (items === undefined) return;
    const text = arrivalText(seen.current, items);
    seen.current = new Set([...(seen.current ?? []), ...items.map((item) => item.id)]);
    // The same words again (a second Message from the same sender) still change the region.
    if (text !== null) setSaid((was) => (was === text ? `${text} ` : text));
  }, [items]);
  return said;
}
