"use client";

import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { addDays, DATE_NAMES, type DateInputs, type DateName, TEST_AFTER_DEBRIEF_DAYS } from "./dates";

const copy = nb.sessions.dates;

/**
 * The four labelled date and time fields (Story 5.2, FR-18), in Europe/Oslo, one column below
 * 1024 px. They are the Datolinje's text alternative. Setting the Debrieffrist prefills the
 * Testfrist 7 days later until the Lecturer sets the Testfrist by hand. A date that has passed,
 * or every date for a User who may not change the session, is read-only.
 */
export function DateFields({
  inputs,
  testTouched,
  onChange,
  errors,
  passed,
  readOnly,
}: {
  inputs: DateInputs;
  testTouched: boolean;
  onChange: (inputs: DateInputs, testTouched: boolean) => void;
  errors: Partial<Record<DateName, string>>;
  passed: readonly DateName[];
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
          return (
            <TextField
              key={name}
              id={`date-${name}`}
              type="datetime-local"
              label={copy.names[name]}
              value={inputs[name]}
              readOnly={readOnly || isPassed}
              error={errors[name]}
              hint={isPassed ? copy.passed : name === "test_deadline" && prefilled ? copy.testPrefilled : undefined}
              onChange={(event) => change(name, event.target.value)}
            />
          );
        })}
      </div>
    </div>
  );
}
