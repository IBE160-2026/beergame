"use client";

import { QuizChoice } from "@/components/quiz-choice";
import { nb } from "@/copy/nb";

import type { MyTestItem } from "./api";
import { SaveLine, useAutosave } from "./use-autosave";

const copy = nb.tests.individual;

/**
 * A multiple-choice item (Story 11.4, FR-52, UX-DR37): Quizvalg reused, single choice, the item's
 * text as its legend, never a right or wrong mark (FR-54). Under it the autosave line, «Lagret
 * 21:14» or the failure line, in a polite status region, so it is announced without moving focus
 * (UX-DR65).
 */
export function ChoiceItem({ classSessionId, userId, item }: { classSessionId: string; userId: string; item: MyTestItem }) {
  const { entry, line, pick } = useAutosave(classSessionId, userId, item);
  return (
    <div className="mt-3 max-w-md">
      <QuizChoice
        name={`test-${item.id}`}
        legend={item.title}
        options={item.options.map((id) => ({ id, text: copy.option(id) }))}
        value={typeof entry.value === "string" ? entry.value : null}
        onChange={pick}
      />
      <SaveLine entry={entry} line={line} />
    </div>
  );
}
