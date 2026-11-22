"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { isSessionExpired } from "@/lib/api/client";
import { errorCode } from "@/lib/api/mutation";
import { clearDraft, loadDraft, saveDraft } from "@/lib/drafts";

import { type MyTest, type MyTestItem, myTestKey, saveMyTestAnswer } from "./api";
import {
  type AnswerValue,
  applyFailed,
  applyRefused,
  applySaved,
  choose,
  draftField,
  draftText,
  type Entry,
  initial,
  LONG_ANSWER_PAUSE_MS,
  merge,
  RETRY_MS,
  refusedForGood,
  statusLine,
} from "./autosave";

/** Where each item's autosave says whether it holds a change not yet stored (Story 11.10): the
 * review holds «Lever testen» back until every answer typed on this device is stored, so nothing
 * typed is left out of what is handed in. */
export const UnsentContext = createContext<((itemId: string, unsent: boolean) => void) | null>(null);

/**
 * The autosave of one item's answer (Story 11.4, AD-10; every item type from Story 11.5): the
 * entry to show, and `pick` for a change. A change is kept on this device first
 * (`lib/drafts.ts`), then sent; one save runs at a time, and the latest change goes after it. A
 * failure is tried again every `RETRY_MS` and at once when the device is back online, until the
 * api stores it; a refusal for good (handed in, past the deadline) drops the draft, shows why and
 * reads the test again. An ended session keeps the draft and reads the test again, which takes
 * the Student to «Logg inn»; back on the page the draft goes with its higher revision.
 *
 * Typing in a long answer (Story 11.6) uses `write`: each keystroke is kept on the device at once
 * and saved when typing pauses for `LONG_ANSWER_PAUSE_MS`; `flush` saves at once, which the field
 * does when it loses focus, and the hook does when the page is hidden or the item leaves the page.
 */
export function useAutosave(classSessionId: string, userId: string, item: MyTestItem) {
  const queryClient = useQueryClient();
  const field = draftField(classSessionId, item.id);
  const [start] = useState(() => initial(item.answer ?? null, loadDraft(userId, field)));
  // What shows: the entry and its status line (the last line stands while a save runs).
  const [shown, setShown] = useState(() => ({ entry: start.entry, line: statusLine(start.entry, "") }));
  const current = useRef(start.entry);
  const sending = useRef(false);
  const timer = useRef<number | null>(null);
  // A pending save after a pause in typing (`write`).
  const pause = useRef<number | null>(null);
  const live = useRef(true);

  const update = useCallback((next: Entry) => {
    current.current = next;
    if (live.current) setShown((was) => ({ entry: next, line: statusLine(next, was.line) }));
  }, []);

  const send = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    const sent = current.current;
    // Nothing newer than the stored answer (a cleared number is sent as null, too).
    if (sending.current || sent.revision <= sent.stored) return;
    sending.current = true;
    saveMyTestAnswer(classSessionId, item.id, { value: sent.value, revision: sent.revision })
      .then((saved) => {
        sending.current = false;
        const { entry: next, done } = applySaved(current.current, saved);
        update(next);
        // The cached test holds the stored answer, so the page shows it again on return.
        queryClient.setQueryData<MyTest>(myTestKey(classSessionId), (test) =>
          test
            ? {
                ...test,
                items: test.items.map((i) =>
                  i.id === item.id ? { ...i, answer: { value: saved.value, revision: saved.revision, saved_at: saved.saved_at } } : i,
                ),
              }
            : test,
        );
        if (done) clearDraft(userId, field);
        // Still typing: the newer text goes when the pause ends, not at once. Also after the item
        // has left the page, so text typed during the last save is not left on the device only.
        else if (pause.current === null) send();
      })
      .catch((error: unknown) => {
        sending.current = false;
        if (refusedForGood(error)) {
          clearDraft(userId, field);
          update(applyRefused(current.current, errorCode(error)));
          void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) });
          return;
        }
        update(applyFailed(current.current));
        // Read the test again: an ended session takes the Student to «Logg inn»; the draft stays.
        if (isSessionExpired(error)) void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) });
        if (live.current) timer.current = window.setTimeout(send, RETRY_MS);
      });
  }, [classSessionId, field, item.id, queryClient, update, userId]);

  const pick = useCallback(
    (value: AnswerValue) => {
      const next = choose(current.current, value);
      saveDraft(userId, field, draftText({ value, revision: next.revision }));
      update(next);
      send();
    },
    [field, send, update, userId],
  );

  const flush = useCallback(() => {
    if (pause.current !== null) {
      window.clearTimeout(pause.current);
      pause.current = null;
    }
    send();
  }, [send]);

  const write = useCallback(
    (value: AnswerValue) => {
      const next = choose(current.current, value);
      saveDraft(userId, field, draftText({ value, revision: next.revision }));
      update(next);
      if (pause.current !== null) window.clearTimeout(pause.current);
      pause.current = window.setTimeout(() => {
        pause.current = null;
        send();
      }, LONG_ANSWER_PAUSE_MS);
    },
    [field, send, update, userId],
  );

  // A draft the api does not have yet goes at once; one it has already is dropped.
  useEffect(() => {
    live.current = true;
    if (start.drop) clearDraft(userId, field);
    if (start.send) send();
    const online = () => {
      if (current.current.status === "failed") send();
    };
    // The page hidden or left: what is typed goes now, not after the pause.
    const hidden = () => {
      if (document.visibilityState === "hidden") flush();
    };
    window.addEventListener("online", online);
    document.addEventListener("visibilitychange", hidden);
    window.addEventListener("pagehide", flush);
    return () => {
      window.removeEventListener("online", online);
      document.removeEventListener("visibilitychange", hidden);
      window.removeEventListener("pagehide", flush);
      if (pause.current !== null) flush();
      live.current = false;
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
  }, [field, flush, send, start, userId]);

  // The test read again (a live update, another device): a higher stored revision replaces this one.
  const answer = item.answer ?? null;
  useEffect(() => {
    const next = merge(current.current, answer);
    if (next !== current.current) update(next);
  }, [answer, update]);

  // Tell the review whether this item waits on a save; an item that leaves the page waits on none.
  const report = useContext(UnsentContext);
  const unsent = shown.entry.revision > shown.entry.stored;
  useEffect(() => {
    report?.(item.id, unsent);
  }, [report, item.id, unsent]);
  useEffect(() => () => report?.(item.id, false), [report, item.id]);

  return { ...shown, pick, write, flush };
}

/** The autosave line under an item: «Lagret 21:14», the failure line or a refusal, in a polite
 * status region, so it is announced without moving focus (UX-DR65). */
export function SaveLine({ entry, line }: { entry: Entry; line: string }) {
  return (
    <p role="status" data-save-status={entry.status} className="mt-2 min-h-6 text-label text-ink-secondary">
      {line}
    </p>
  );
}
