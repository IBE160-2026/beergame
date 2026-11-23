"use client";

import { useId } from "react";

import { SegmentedChoice } from "@/components/segmented-choice";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import type { ClassSession } from "@/modules/sessions/api";

import { BOUNDED, type BoundsDraft, boundsText, type LetterChoice, offendingBounds } from "./letter";

const copy = nb.assessment.letterBlock;
const LINE = "text-body-phone lg:text-body";
const CHOICES: readonly LetterChoice[] = ["all", "student_choice", "unavailable"];

/**
 * «Veiledende bokstav» in the Klasseøkt's «KI-vurdering» (Story 12.6, FR-56, UX-DR12): Valgknapper
 * for who sees the letter (shown to everyone, each Student for themselves, unavailable), with the
 * chosen setting's scope in help text, and the lower bound of A to E in whole percent. Both are
 * drafts that take effect on «Lagre Klasseøkt», while the «KI-vurdering» switch can change; the
 * bounds stand as text once a Student has opened the test. Where the Institution forbids the
 * letter only «Ikke tilgjengelig» can be chosen, and the block says why. An Assistant lecturer
 * reads it as text (AD-12).
 */
export function LetterBlock({
  item,
  setting,
  onSetting,
  bounds,
  onBounds,
  boundsError,
  onBoundsLeave,
}: {
  item: ClassSession;
  setting: LetterChoice;
  onSetting: (setting: LetterChoice) => void;
  bounds: BoundsDraft;
  onBounds: (bounds: BoundsDraft) => void;
  boundsError?: string;
  onBoundsLeave: () => void;
}) {
  const ids = useId();
  const titleId = `${ids}-title`;
  const scopeId = `${ids}-scope`;
  const forcedId = `${ids}-forced`;
  const boundsTitleId = `${ids}-bounds`;
  const boundsErrorId = `${ids}-bounds-error`;
  const offending = boundsError ? offendingBounds(bounds) : new Set<string>();
  const letter = item.ai_assessment.letter;
  const shown = letter.can_change ? setting : letter.setting;
  return (
    <section aria-labelledby={titleId} className="mt-8" data-letter-block="">
      <h3 id={titleId} className="text-step-title font-semibold text-ink">
        {copy.title}
      </h3>
      {letter.forced ? (
        <p id={forcedId} className={`${LINE} mt-2 font-semibold text-ink`} data-letter-forced="">
          {copy.forced}
        </p>
      ) : null}
      {letter.can_change ? (
        <SegmentedChoice
          className="mt-3"
          name={`${ids}-setting`}
          legend={copy.legend}
          value={shown}
          onChange={onSetting}
          describedBy={scopeId}
          options={CHOICES.map((value) => ({
            value,
            label: copy.options[value],
            unavailable: letter.forced && value !== "unavailable",
            describedBy: letter.forced && value !== "unavailable" ? forcedId : undefined,
          }))}
        />
      ) : (
        <p className={`${LINE} mt-3 font-semibold text-ink`} data-letter-setting={shown}>
          {copy.options[shown]}
        </p>
      )}
      <p id={scopeId} className={`${LINE} mt-2 text-ink-secondary`}>
        {copy.scope[shown]}
      </p>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.note}</p>
      <h4 id={boundsTitleId} className={`${LINE} mt-6 font-semibold text-ink`}>
        {copy.thresholdsTitle}
      </h4>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.thresholdsLead}</p>
      {letter.thresholds_open ? (
        <fieldset aria-labelledby={boundsTitleId} className="m-0 mt-3 min-w-0 border-0 p-0" data-letter-bounds="">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {BOUNDED.map((key) => (
              <TextField
                key={key}
                id={`${ids}-bound-${key}`}
                label={copy.bound(key)}
                inputMode="numeric"
                autoComplete="off"
                value={bounds[key]}
                onChange={(event) => onBounds({ ...bounds, [key]: event.target.value })}
                onBlur={onBoundsLeave}
                inputClassName="tabular-nums"
                // The fields the rule is broken in (all of them when none can be named alone).
                errorFor={boundsError && (offending.size === 0 || offending.has(key)) ? boundsErrorId : undefined}
              />
            ))}
          </div>
          {boundsError ? (
            <p id={boundsErrorId} role="alert" className="mt-2 text-body-phone text-restordre" data-letter-bounds-error="">
              {boundsError}
            </p>
          ) : null}
          <p className={`${LINE} mt-2 text-ink-secondary`}>{copy.rest}</p>
        </fieldset>
      ) : (
        <>
          <p className={`${LINE} mt-2 text-ink tabular-nums`} data-letter-bounds-text="">
            {boundsText(letter.thresholds)}. {copy.rest}.
          </p>
          {letter.can_change ? <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.thresholdsLocked}</p> : null}
        </>
      )}
    </section>
  );
}
