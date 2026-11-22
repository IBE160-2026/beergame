"use client";

import { type ClipboardEvent, useState, useSyncExternalStore } from "react";

import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { MyTestItem } from "./api";
import { LONG_ANSWER_COUNT_FROM, LONG_ANSWER_MAX, pasteIsCut } from "./autosave";
import { itemLabel } from "./individual-test";
import { SaveLine, useAutosave } from "./use-autosave";

const copy = nb.tests.individual;

/**
 * A long-answer item (Story 11.6, FR-51, FR-52, FR-73, UX-DR11, UX-DR65): the question, as the
 * pinned question set words it, is the label above a multi-line Tekstfelt. On a phone the advice
 * to use a larger screen shows above it, read with the field; writing and saving work there all
 * the same. Each keystroke is kept on this device; the text is saved when typing pauses, when the
 * field loses focus or when the page is hidden, and «Lagret 21:14» is announced politely under it
 * without moving focus. Near the longest answer a count shows under the field, and a paste that
 * went past it says so instead of being cut silently. Nothing scores it here (FR-54). An Adapted
 * item whose wording an LLM chose (Story 11.8) is labelled «KI-generert, kan ta feil: «…»», marked
 * `data-ai-generated="true"` and read with the note that its numbers are the code's.
 */
export function LongItem({ classSessionId, userId, item }: { classSessionId: string; userId: string; item: MyTestItem }) {
  const { entry, line, write, flush } = useAutosave(classSessionId, userId, item);
  const { label, ai, note } = itemLabel(item);
  const [cut, setCut] = useState(false);
  const phone = usePhone();
  const text = typeof entry.value === "string" ? entry.value : "";
  const id = `test-${item.id}`;
  const max = formatNumber(LONG_ANSWER_MAX);
  const paste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const field = event.currentTarget;
    setCut(pasteIsCut(field.value.length, field.selectionEnd - field.selectionStart, event.clipboardData.getData("text").length));
  };
  return (
    <div className="mt-3 max-w-2xl" data-ai-generated={ai ? "true" : undefined}>
      <p id={`${id}-screen`} data-larger-screen className="mb-3 max-w-md text-body-phone text-ink-secondary md:hidden">
        {copy.long.largerScreen}
      </p>
      <TextAreaField
        id={id}
        label={label}
        hint={note ?? undefined}
        rows={10}
        maxLength={LONG_ANSWER_MAX}
        aria-describedby={phone ? `${id}-screen ${id}-count` : `${id}-count`}
        value={text}
        onChange={(event) => {
          if (cut && event.target.value.length < LONG_ANSWER_MAX) setCut(false);
          write(event.target.value);
        }}
        onPaste={paste}
        onBlur={flush}
      />
      <p id={`${id}-count`} data-long-count className="mt-1 text-label text-ink-secondary">
        {text.length >= LONG_ANSWER_COUNT_FROM ? copy.long.count(formatNumber(text.length), max) : null}
      </p>
      {/* Announced politely; the item's one status region stays the save line. */}
      <p aria-live="polite" data-long-cut className="text-label text-ink">
        {cut ? copy.long.cut(max) : null}
      </p>
      <SaveLine entry={entry} line={line} />
    </div>
  );
}

// Tailwind's `md` breakpoint: under it the advice to use a larger screen shows, and is read with
// the field (a hidden paragraph named in aria-describedby would still be read).
const PHONE = "(max-width: 47.99rem)";

function usePhone(): boolean {
  return useSyncExternalStore(
    (changed) => {
      const query = window.matchMedia(PHONE);
      query.addEventListener("change", changed);
      return () => query.removeEventListener("change", changed);
    },
    () => window.matchMedia(PHONE).matches,
    () => false,
  );
}
