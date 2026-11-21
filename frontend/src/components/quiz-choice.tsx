import type { ReactNode } from "react";

import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

export type QuizOption = { id: string; text: string };

/** A scored question: the Student's choice and the right one. */
export type QuizMarks = { chosen: string; right: string };

/**
 * Quizvalg (DESIGN.md → Components → `quiz-option`, UX-DR37): one single-choice question as
 * full-width rows, reused by the Debrief quiz (Story 9.9) and the Individual test. Native radios
 * in a `fieldset`, so the legend (the question) names the group, the arrow keys move the choice
 * and a screen reader reads «1 av 3». Each radio covers its whole row, so the row is the tap
 * target (44 px at least), with a dot that draws the state: idle `ink-muted` border, chosen 1.4 px
 * `ink` with a filled dot (the selected state before submit, accessibility review M7).
 *
 * With `marks` the question is scored and reads only: the Student's wrong choice has a 1.4 px
 * `restordre` border and «Ditt svar, ikke riktig», the right one a 1.4 px `ink` border and
 * «Riktig», in text inside the row (so in its accessible name) and never by colour alone. The
 * explanation follows under the rows (`children`).
 */
export function QuizChoice({
  name,
  legend,
  options,
  value,
  onChange,
  marks,
  children,
  className,
}: {
  name: string;
  legend: ReactNode;
  options: readonly QuizOption[];
  value: string | null;
  onChange?: (id: string) => void;
  marks?: QuizMarks;
  /** Under the rows: the explanation of a scored question. */
  children?: ReactNode;
  className?: string;
}) {
  const scored = marks !== undefined;
  return (
    <fieldset className={cn("m-0 min-w-0 border-0 p-0", className)} disabled={scored}>
      <legend className="mb-field-gap text-body-phone text-ink lg:text-body">{legend}</legend>
      <div className="flex flex-col gap-2">
        {options.map((option) => {
          const chosen = scored ? marks.chosen === option.id : value === option.id;
          const right = scored && marks.right === option.id;
          const wrong = scored && chosen && !right;
          return (
            <label
              key={option.id}
              data-quiz-option={option.id}
              data-quiz-mark={right ? "right" : wrong ? "wrong" : undefined}
              className={cn(
                "group relative flex min-h-tap-target-min w-full items-center gap-3 rounded-sm border border-ink-muted bg-paper px-4 py-2.5 text-body-phone text-ink lg:text-body",
                !scored && "cursor-pointer hover:border-ink active:bg-hairline",
                !scored && "has-checked:border-[1.4px] has-checked:border-ink",
                "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink",
                right && "border-[1.4px] border-ink",
                wrong && "border-[1.4px] border-restordre",
              )}
            >
              {/* The radio covers its whole row and border (transparent), so the tap target is the row; the
                  dot beside the text draws its state. */}
              <input
                type="radio"
                name={name}
                value={option.id}
                checked={chosen}
                onChange={() => onChange?.(option.id)}
                className={cn(
                  "peer absolute -inset-[1.5px] m-0 cursor-pointer appearance-none rounded-sm opacity-0 focus-visible:outline-none",
                  scored && "cursor-default",
                )}
              />
              <span
                aria-hidden="true"
                className={cn(
                  "grid size-5 shrink-0 place-content-center rounded-full border border-ink-muted bg-paper peer-checked:border-ink",
                  wrong && "peer-checked:border-restordre",
                )}
              >
                <span className="size-2.5 scale-0 rounded-full bg-ink text-paper group-has-checked:scale-100" />
              </span>
              <span className="min-w-0 flex-1 break-words">{option.text}</span>
              {right ? <span className="shrink-0 text-label text-ink">{nb.quizChoice.right}</span> : null}
              {wrong ? <span className="shrink-0 text-label text-restordre">{nb.quizChoice.wrong}</span> : null}
            </label>
          );
        })}
      </div>
      {children}
    </fieldset>
  );
}
