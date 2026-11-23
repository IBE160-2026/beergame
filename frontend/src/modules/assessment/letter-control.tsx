"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId } from "react";

import { ActionError } from "@/components/action-error";
import { Switch } from "@/components/switch";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { type MyAssessment, myAssessmentKey, setLetterChoice } from "./api";

const copy = nb.assessment.letter;
const LINE = "text-body-phone lg:text-body";

type Letter = NonNullable<MyAssessment["letter"]>["value"];

/**
 * The Indicative letter beside the total (Story 12.6, FR-56, UX-DR66): «Veiledende bokstav: B»
 * with the label «KI-generert indikasjon. Teller ikke. Ingen karakter.» under it, the same for the
 * Student and the staff. Text only; nothing but words carries the meaning.
 */
export function LetterLine({ value }: { value: NonNullable<Letter> }) {
  return (
    <div data-letter={value} className="mt-3">
      <p className="text-step-title font-semibold text-ink">{copy.value(value)}</p>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.label}</p>
    </div>
  );
}

/**
 * The Student's «Veiledende bokstav» (Story 12.6, FR-56, UX-DR66) where the Lecturer leaves it to
 * each Student: a Bryter that turns the letter on for their own view only, stored at once, and off
 * again; its help says the staff never see it. Shown to everyone, there is no Bryter, only the
 * letter. The api's answer replaces the page's copy; a 409 (the setting changed meanwhile) reads
 * the view again. A failed request says «Det ble ikke lagret. Prøv igjen.» beside it.
 */
export function LetterControl({
  classSessionId,
  letter,
}: {
  classSessionId: string;
  letter: NonNullable<MyAssessment["letter"]>;
}) {
  const ids = useId();
  const nameId = `${ids}-name`;
  const helpId = `${ids}-help`;
  const queryClient = useQueryClient();
  const toggle = useMutation({
    mutationFn: (on: boolean) => setLetterChoice(classSessionId, on),
    onSuccess: (view) => queryClient.setQueryData(myAssessmentKey(classSessionId), view),
    onError: (error) => {
      if (error instanceof ApiRequestError && error.status === 409) {
        void queryClient.invalidateQueries({ queryKey: myAssessmentKey(classSessionId) });
      }
    },
  });
  const chosen = toggle.isPending && toggle.variables !== undefined ? toggle.variables : letter.chosen;
  return (
    <div data-letter-control={letter.setting} className="mt-4">
      {letter.setting === "student_choice" ? (
        <>
          <p id={nameId} className={`${LINE} font-semibold text-ink`}>
            {copy.control}
          </p>
          <Switch
            id={`${ids}-switch`}
            checked={chosen}
            labelledBy={nameId}
            describedBy={helpId}
            onChange={(on) => {
              if (!toggle.isPending) toggle.mutate(on);
            }}
          >
            {chosen ? copy.on : copy.off}
          </Switch>
          <p id={helpId} className={`${LINE} text-ink-secondary`}>
            {copy.help}
          </p>
          <ActionError message={toggle.isError ? copy.failed : undefined} />
        </>
      ) : null}
      {/* Announced as it appears or goes; while a change is under way it follows the Bryter. */}
      <div aria-live="polite">
        {letter.value && (letter.setting === "all" || chosen) ? <LetterLine value={letter.value} /> : null}
      </div>
    </div>
  );
}
