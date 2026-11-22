"use client";

import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";

import type { MyTestItem } from "./api";
import { LONG_ANSWER_MAX } from "./autosave";
import { SaveLine, useAutosave } from "./use-autosave";

const copy = nb.tests.individual;

/**
 * A long-answer item (Story 11.6, FR-51, FR-52, FR-73, UX-DR11, UX-DR65): the question, as the
 * pinned question set words it, is the label above a multi-line Tekstfelt. On a phone the advice
 * to use a larger screen shows above it; writing and saving work there all the same. Each
 * keystroke is kept on this device; the text is saved when typing pauses, when the field loses
 * focus or when the page is hidden, and «Lagret 21:14» is announced politely under it without
 * moving focus. Nothing scores it here (FR-54).
 */
export function LongItem({ classSessionId, userId, item }: { classSessionId: string; userId: string; item: MyTestItem }) {
  const { entry, line, write, flush } = useAutosave(classSessionId, userId, item);
  return (
    <div className="mt-3 max-w-2xl">
      <p data-larger-screen className="mb-3 max-w-md text-body-phone text-ink-secondary md:hidden">
        {copy.long.largerScreen}
      </p>
      <TextAreaField
        id={`test-${item.id}`}
        label={item.title}
        rows={10}
        maxLength={LONG_ANSWER_MAX}
        value={typeof entry.value === "string" ? entry.value : ""}
        onChange={(event) => write(event.target.value)}
        onBlur={flush}
      />
      <SaveLine entry={entry} line={line} />
    </div>
  );
}
