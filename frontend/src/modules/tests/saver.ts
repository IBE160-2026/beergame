import { errorCode } from "@/lib/api/mutation";

import {
  type AnswerValue,
  applyFailed,
  applyRefused,
  applySaved,
  choose,
  type Draft,
  type Entry,
  LONG_ANSWER_PAUSE_MS,
  merge,
  RETRY_MS,
  refusedForGood,
  type Stored,
} from "./autosave";

/**
 * The save loop of one item's answer (Story 11.4, AD-10; long answers from Story 11.6), without
 * React, so it runs the same in the hook (`use-autosave.tsx`) and in its unit test. A change is
 * kept on this device first (`keep`), then sent; one save runs at a time, and the latest change
 * goes after it. A failure is tried again every `RETRY_MS` (and at once when `online` is called),
 * until the api stores it; a refusal for good drops the draft and shows why.
 *
 * While the page is hidden or being left (`hidden`), a save goes with `keepalive`, so the browser
 * finishes it after the tab is closed or the app is switched away. The browser allows a keepalive
 * body of at most 64 kB; a longer one goes as a plain request, and if the browser cancels it the
 * draft kept on this device goes on the next visit.
 */

/** The largest body sent with `keepalive` (bytes of UTF-8 JSON), under the browser's 64 kB. */
export const KEEPALIVE_MAX_BYTES = 60_000;

/** Whether a save of `draft` fits in one keepalive request. */
export function fitsKeepalive(draft: Draft): boolean {
  return new TextEncoder().encode(JSON.stringify(draft)).length <= KEEPALIVE_MAX_BYTES;
}

export type SaverHooks = {
  /** Store `draft` on the api; `keepalive` asks the browser to finish it after the page goes. */
  save(draft: Draft, options: { keepalive: boolean }): Promise<Stored>;
  /** Keep `draft` on this device until the api has it. */
  keep(draft: Draft): void;
  /** The entry to show changed. */
  show(entry: Entry): void;
  /** The api stored `saved`; `done` when nothing newer waits on this device (drop the draft). */
  stored(saved: Stored, done: boolean): void;
  /** The api refused the save for good (drop the draft, read the test again). */
  refused(error: unknown): void;
  /** The save failed and is tried again (an ended session reads the test again). */
  failed(error: unknown): void;
};

export class AnswerSaver {
  /** The page is hidden or being left: saves go with `keepalive`. */
  hidden = false;
  private sending = false;
  private retry: ReturnType<typeof setTimeout> | null = null;
  private pause: ReturnType<typeof setTimeout> | null = null;
  private live = true;

  constructor(
    public entry: Entry,
    private readonly hooks: SaverHooks,
  ) {}

  private set(next: Entry) {
    this.entry = next;
    if (this.live) this.hooks.show(next);
  }

  /** Send the latest change, unless one save runs already (the change goes after it) or the api
   * has it. */
  send = () => {
    if (this.retry !== null) {
      clearTimeout(this.retry);
      this.retry = null;
    }
    const sent = this.entry;
    // Nothing newer than the stored answer (a cleared number is sent as null, too).
    if (this.sending || sent.revision <= sent.stored) return;
    this.sending = true;
    const draft: Draft = { value: sent.value, revision: sent.revision };
    this.hooks
      .save(draft, { keepalive: this.hidden && fitsKeepalive(draft) })
      .then((saved) => {
        this.sending = false;
        const { entry: next, done } = applySaved(this.entry, saved);
        this.set(next);
        this.hooks.stored(saved, done);
        // Still typing: the newer text goes when the pause ends, not at once. Also after the item
        // has left the page, so text typed during the last save is not left on the device only.
        if (!done && this.pause === null) this.send();
      })
      .catch((error: unknown) => {
        this.sending = false;
        if (refusedForGood(error)) {
          this.set(applyRefused(this.entry, errorCode(error)));
          this.hooks.refused(error);
          return;
        }
        this.set(applyFailed(this.entry));
        this.hooks.failed(error);
        if (this.live) this.retry = setTimeout(this.send, RETRY_MS);
      });
  };

  /** A choice, a number or a table cell: kept and sent at once. */
  pick = (value: AnswerValue) => {
    const next = choose(this.entry, value);
    this.hooks.keep({ value, revision: next.revision });
    this.set(next);
    this.send();
  };

  /** Typing in a long answer: kept at once, sent when typing pauses for `LONG_ANSWER_PAUSE_MS`. */
  write = (value: AnswerValue) => {
    const next = choose(this.entry, value);
    this.hooks.keep({ value, revision: next.revision });
    this.set(next);
    if (this.pause !== null) clearTimeout(this.pause);
    this.pause = setTimeout(() => {
      this.pause = null;
      this.send();
    }, LONG_ANSWER_PAUSE_MS);
  };

  /** Send what is typed now, not after the pause (the field left, the page hidden). */
  flush = () => {
    if (this.pause !== null) {
      clearTimeout(this.pause);
      this.pause = null;
    }
    this.send();
  };

  /** Back online: a failed save is tried at once. */
  online = () => {
    if (this.entry.status === "failed") this.send();
  };

  /** The test was read again: a stored answer from a higher revision replaces this one. */
  received = (stored: Stored | null) => {
    const next = merge(this.entry, stored);
    if (next !== this.entry) this.set(next);
  };

  start() {
    this.live = true;
  }

  /** The item leaves the page: what is typed goes now; no retry is planned after. */
  stop() {
    if (this.pause !== null) this.flush();
    this.live = false;
    if (this.retry !== null) {
      clearTimeout(this.retry);
      this.retry = null;
    }
  }
}
