"use client";

import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { addDays, DATE_NAMES, type DateInputs, type DateName, osloDateText, TEST_AFTER_DEBRIEF_DAYS } from "./dates";

const copy = nb.sessions.dates;

/**
 * The four labelled date and time fields (Story 5.2, FR-18), in Europe/Oslo, one column below
 * 1024 px. They are the Datolinje's text alternative. Setting the Debrieffrist prefills the
 * Testfrist 7 days later until the Lecturer sets the Testfrist by hand. A date that cannot change
 * (it has passed, or the User may not change the session) stands as text, not as a field
 * (Story 5.11, GitHub issue 103), each a group named by its label.
 */
export function DateFields({
  inputs,
  values,
  testTouched,
  onChange,
  errors,
  passed,
  frozen,
  readOnly,
}: {
  inputs: DateInputs;
  /** The stored dates (ISO, UTC), shown as text where a date cannot change. */
  values: Record<DateName, string | null | undefined>;
  testTouched: boolean;
  onChange: (inputs: DateInputs, testTouched: boolean) => void;
  errors: Partial<Record<DateName, string>>;
  passed: readonly DateName[];
  /** The dates that no longer move (`frozenDates`): passed ones and an early lock's Startdato. */
  frozen: readonly DateName[];
  readOnly: boolean;
}) {
  const change = (name: DateName, value: string) => {
    if (name === "test_deadline") {
      onChange({ ...inputs, test_deadline: value }, true);
      return;
    }
    const next = { ...inputs, [name]: value };
    if (name === "debrief_deadline" && !testTouched) {
      next.test_deadline = value ? addDays(value, TEST_AFTER_DEBRIEF_DAYS) : "";
    }
    onChange(next, testTouched);
  };
  const prefilled = !testTouched && inputs.test_deadline !== "";
  return (
    <div className="mt-6">
      <p className="text-body-phone text-ink-secondary">{copy.timeZone}</p>
      <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {DATE_NAMES.map((name) => {
          const isPassed = passed.includes(name);
          const isFrozen = frozen.includes(name);
          if (readOnly || isPassed || isFrozen) {
            const value = values[name];
            const note = isPassed ? copy.passed : isFrozen ? copy.lockedStart : null;
            return (
              <div key={name} role="group" aria-labelledby={`date-${name}-label`} className="flex flex-col gap-field-gap">
                <span id={`date-${name}-label`} className="text-label text-ink">
                  {copy.names[name]}
                </span>
                <span className="text-body-phone text-ink lg:text-body">{value ? osloDateText(value) : copy.notSet}</span>
                {note ? <span className="text-body-phone text-ink-secondary">{note}</span> : null}
              </div>
            );
          }
          return (
            <TextField
              key={name}
              id={`date-${name}`}
              type="datetime-local"
              label={copy.names[name]}
              value={inputs[name]}
              error={errors[name]}
              hint={name === "test_deadline" && prefilled ? copy.testPrefilled : undefined}
              onChange={(event) => change(name, event.target.value)}
            />
          );
        })}
      </div>
    </div>
  );
}
