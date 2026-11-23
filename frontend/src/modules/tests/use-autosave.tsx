"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";

import { isSessionExpired } from "@/lib/api/client";
import { clearDraft, loadDraft, saveDraft } from "@/lib/drafts";

import { type MyTest, type MyTestItem, myTestKey, saveMyTestAnswer } from "./api";
import { draftField, draftText, type Entry, initial, statusLine } from "./autosave";
import { AnswerSaver } from "./saver";

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
 * The loop itself is `AnswerSaver` (`saver.ts`); while the page is hidden its saves go with
 * `keepalive`, so closing the tab does not cancel them.
 */
export function useAutosave(classSessionId: string, userId: string, item: MyTestItem) {
  const queryClient = useQueryClient();
  const field = draftField(classSessionId, item.id);
  const [start] = useState(() => initial(item.answer ?? null, loadDraft(userId, field)));
  // What shows: the entry and its status line (the last line stands while a save runs).
  const [shown, setShown] = useState(() => ({ entry: start.entry, line: statusLine(start.entry, "") }));
  // The save loop (`saver.ts`); made once per item, which keeps its Class session and id.
  const [saver] = useState(
    () =>
      new AnswerSaver(start.entry, {
        save: (draft, { keepalive }) => saveMyTestAnswer(classSessionId, item.id, draft, { keepalive }),
        keep: (draft) => saveDraft(userId, field, draftText(draft)),
        show: (next: Entry) => setShown((was) => ({ entry: next, line: statusLine(next, was.line) })),
        stored: (saved, done) => {
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
        },
        refused: () => {
          clearDraft(userId, field);
          void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) });
        },
        // Read the test again: an ended session takes the Student to «Logg inn»; the draft stays.
        failed: (error) => {
          if (isSessionExpired(error)) void queryClient.invalidateQueries({ queryKey: myTestKey(classSessionId) });
        },
      }),
  );

  // A draft the api does not have yet goes at once; one it has already is dropped.
  useEffect(() => {
    saver.start();
    if (start.drop) clearDraft(userId, field);
    if (start.send) saver.send();
    // The page hidden or left: what is typed goes now, not after the pause, and with keepalive,
    // so closing the tab or switching app does not cancel it.
    const visibility = () => {
      saver.hidden = document.visibilityState === "hidden";
      if (saver.hidden) saver.flush();
    };
    const leave = () => {
      saver.hidden = true;
      saver.flush();
    };
    const back = () => {
      saver.hidden = false;
    };
    window.addEventListener("online", saver.online);
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("pagehide", leave);
    window.addEventListener("pageshow", back);
    return () => {
      window.removeEventListener("online", saver.online);
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("pagehide", leave);
      window.removeEventListener("pageshow", back);
      saver.stop();
    };
  }, [field, saver, start, userId]);

  // The test read again (a live update, another device): a higher stored revision replaces this one.
  const answer = item.answer ?? null;
  useEffect(() => saver.received(answer), [answer, saver]);

  // Tell the review whether this item waits on a save; an item that leaves the page waits on none.
  const report = useContext(UnsentContext);
  const unsent = shown.entry.revision > shown.entry.stored;
  useEffect(() => {
    report?.(item.id, unsent);
  }, [report, item.id, unsent]);
  useEffect(() => () => report?.(item.id, false), [report, item.id]);

  return { ...shown, pick: saver.pick, write: saver.write, flush: saver.flush };
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
