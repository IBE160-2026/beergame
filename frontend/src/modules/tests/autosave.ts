import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { osloDayAndTime } from "@/modules/sessions/dates";

/**
 * Autosave of one Individual test answer (Story 11.4, FR-51, AD-10, UX-DR65), as pure steps the
 * item's hook runs. Each change raises the answer's revision by one; the server keeps the highest
 * revision and answers with the one it stores. What is not yet stored is kept on this device in
 * `lib/drafts.ts` (`draftField`) and sent again until it is. No score and no right or wrong state
 * exist here (FR-54).
 */

const copy = nb.tests.individual;

/** A stored answer as the api gives it. */
export type Stored = { value: unknown; revision: number; saved_at: string };

/** A value not yet stored, kept on this device with its revision. */
export type Draft = { value: string; revision: number };

export type SaveStatus = "idle" | "saving" | "saved" | "failed" | "refused";

export type Entry = {
  /** The value shown: the latest change on this device, or the stored one. */
  value: string | null;
  /** The revision of `value` (0: never answered). */
  revision: number;
  /** The value and revision last known stored, and when. */
  storedValue: string | null;
  stored: number;
  savedAt: string | null;
  status: SaveStatus;
  /** Why the api refused the save (status `refused`). */
  refusal: string | null;
};

/** The draft field of an item: kept per User (by `lib/drafts.ts`) and per Class session and item. */
export function draftField(classSessionId: string, itemId: string): string {
  return `test:${classSessionId}:${itemId}`;
}

export function draftText(draft: Draft): string {
  return JSON.stringify(draft);
}

/** A kept draft, or null for none or one that cannot be read. */
export function parseDraft(text: string | null): Draft | null {
  if (!text) return null;
  try {
    const parsed: unknown = JSON.parse(text);
    if (typeof parsed !== "object" || parsed === null) return null;
    const { value, revision } = parsed as Record<string, unknown>;
    if (typeof value !== "string" || typeof revision !== "number" || !Number.isInteger(revision) || revision < 1) return null;
    return { value, revision };
  } catch {
    return null;
  }
}

const asChoice = (value: unknown): string | null => (typeof value === "string" ? value : null);

/** The entry an item starts with, and whether its draft is to be sent (`send`) or dropped
 * (`drop`, a draft the server already has or one that cannot be read). The stored answer from an
 * earlier visit says nothing in the status line. */
export function initial(stored: Stored | null, draftText: string | null): { entry: Entry; send: boolean; drop: boolean } {
  const storedValue = asChoice(stored?.value);
  const revision = stored?.revision ?? 0;
  const base: Entry = {
    value: storedValue,
    revision,
    storedValue,
    stored: revision,
    savedAt: stored?.saved_at ?? null,
    status: "idle",
    refusal: null,
  };
  const draft = parseDraft(draftText);
  if (draft && draft.revision > revision) {
    return { entry: { ...base, value: draft.value, revision: draft.revision, status: "saving" }, send: true, drop: false };
  }
  return { entry: base, send: false, drop: draftText !== null };
}

/** The Student picks `value`: one revision up, to be kept and sent. */
export function choose(entry: Entry, value: string): Entry {
  return { ...entry, value, revision: entry.revision + 1, status: "saving", refusal: null };
}

/** The api stored `saved` for a save of `entry`'s value: `done` when nothing newer waits on this
 * device (the draft is dropped); otherwise the newer value is sent next. An answer stored from a
 * higher revision (another device) replaces the one shown. */
export function applySaved(entry: Entry, saved: Stored): { entry: Entry; done: boolean } {
  const stored = {
    storedValue: asChoice(saved.value),
    stored: saved.revision,
    savedAt: saved.saved_at,
  };
  if (saved.revision >= entry.revision) {
    return {
      entry: { ...entry, ...stored, value: stored.storedValue, revision: saved.revision, status: "saved", refusal: null },
      done: true,
    };
  }
  return { entry: { ...entry, ...stored, status: "saving" }, done: false };
}

/** The save did not reach the api or it failed on its side: kept and tried again. */
export function applyFailed(entry: Entry): Entry {
  return { ...entry, status: "failed" };
}

/** The api refused the save for good: the stored value shows again, with why in words. */
export function applyRefused(entry: Entry, code: string): Entry {
  return {
    ...entry,
    value: entry.storedValue,
    revision: entry.stored,
    status: "refused",
    refusal: copy.saveErrors[code] ?? copy.saveRefused,
  };
}

/** The test was read again (another device, a live update): a stored answer from a higher
 * revision than this device's replaces it; otherwise this device's answer stands. */
export function merge(entry: Entry, stored: Stored | null): Entry {
  if (!stored || stored.revision <= entry.revision) return entry;
  const value = asChoice(stored.value);
  return {
    ...entry,
    value,
    revision: stored.revision,
    storedValue: value,
    stored: stored.revision,
    savedAt: stored.saved_at,
    status: entry.status === "idle" ? "idle" : "saved",
    refusal: null,
  };
}

/** Whether a failed save is refused for good, which the api says with 403 (no access), 409 (handed
 * in, past the deadline) or 422 (the item or value refused); every other failure (offline, a
 * server failure, an ended session, too many requests) keeps the draft and is tried again. */
export function refusedForGood(error: unknown): boolean {
  return error instanceof ApiRequestError && [403, 409, 422].includes(error.status);
}

/** The status line under the item: «Lagret 21:14» (Europe/Oslo), the failure line, the refusal,
 * or nothing. While a save runs the last line stands, so the line does not flicker. */
export function statusLine(entry: Entry, previous: string): string {
  switch (entry.status) {
    case "saved":
      return entry.savedAt ? copy.saved(osloDayAndTime(entry.savedAt).time) : "";
    case "failed":
      return copy.notSaved;
    case "refused":
      return entry.refusal ?? copy.saveRefused;
    case "saving":
      return previous;
    default:
      return "";
  }
}

/** How long a failed save waits before it is tried again (also at once when the device is back
 * online). */
export const RETRY_MS = 5_000;
