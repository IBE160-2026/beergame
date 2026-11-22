"use client";

import { useEffect, useId, useRef, useState } from "react";

import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import { ActionError } from "./action-error";
import { Button } from "./button";
import { SegmentedChoice, type SegmentedOption } from "./segmented-choice";

const copy = nb.believability;

type Scale = "1" | "2" | "3" | "4" | "5";
const SCALE: readonly Scale[] = ["1", "2", "3", "4", "5"];

/**
 * The believability question (Story 10.8, FR-70, UX-DR76): «Hvor troverdige var KI-spillernes
 * ordrer?» on a five-point scale, shared by «Spillet er ferdig» and the Replay-gjennomgang. The
 * scale is Valgknapper (`SegmentedChoice`): native radios in a `fieldset` whose legend is the
 * question, so the arrow keys move the choice; five segments of at least 44 px. Under them the end
 * points in words, «1: ikke troverdige» left and «5: svært troverdige» right, each the description
 * of its own option. The Student chooses, then sends with «Send svar» (a secondary button: the
 * screen keeps its one primary), so a stray tap is not the answer. Optional: nothing waits on it.
 * Once answered (`rating`), one line says what they answered, and the question is not asked
 * again; it is the Student's own answer, never anyone else's.
 */
export function BelievabilityQuestion({
  rating,
  onSend,
  sending = false,
  errorMessage,
  className,
}: {
  /** The Student's stored answer; null until they answer. */
  rating: number | null;
  onSend: (rating: number) => void;
  sending?: boolean;
  /** The inline line of a failed send (`useAction`). */
  errorMessage?: string;
  className?: string;
}) {
  const id = useId();
  const [chosen, setChosen] = useState<Scale | null>(null);
  const saved = useRef<HTMLParagraphElement>(null);
  const sent = useRef(false);
  // Focus follows the answer to the line that replaced the question, so it is not lost.
  useEffect(() => {
    if (rating !== null && sent.current) saved.current?.focus();
  }, [rating]);
  if (rating !== null) {
    return (
      <p ref={saved} tabIndex={-1} role="status" data-believability-saved="" className={cn("text-body-phone text-ink lg:text-body", className)}>
        {copy.saved(rating)}
      </p>
    );
  }
  const options: SegmentedOption<Scale>[] = SCALE.map((value) => ({
    value,
    label: value,
    describedBy: value === "1" ? `${id}-low` : value === "5" ? `${id}-high` : undefined,
  }));
  return (
    <div data-believability="" className={cn("max-w-sm", className)}>
      <SegmentedChoice
        name={`${id}-scale`}
        legend={copy.legend}
        options={options}
        // No choice yet: no segment matches.
        value={(chosen ?? "") as Scale}
        onChange={setChosen}
        describedBy={`${id}-note`}
      />
      <div aria-hidden="true" className="mt-1 flex justify-between gap-4 text-caption text-ink-secondary">
        <span>{copy.low}</span>
        <span className="text-right">{copy.high}</span>
      </div>
      {/* The end points' words for screen readers, as the descriptions of options 1 and 5. */}
      <span id={`${id}-low`} hidden>
        {copy.low}
      </span>
      <span id={`${id}-high`} hidden>
        {copy.high}
      </span>
      <p id={`${id}-note`} className="mt-3 text-caption text-ink-secondary">
        {copy.note}
      </p>
      <Button
        className="mt-3"
        aria-label={copy.sendName}
        unavailable={chosen === null || sending}
        onClick={() => {
          if (chosen === null) return;
          sent.current = true;
          onSend(Number(chosen));
        }}
      >
        {copy.send}
      </Button>
      <ActionError message={errorMessage} className="mt-2" />
    </div>
  );
}
