import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

const errors = nb.classes.errors;

/** The api's longest name and course code (`CLASS_NAME_MAX_LENGTH`, `COURSE_CODE_MAX_LENGTH` in
 * `classes/schemas.py`). */
export const NAME_MAX_LENGTH = 200;
export const COURSE_CODE_MAX_LENGTH = 50;

export type ClassField = "name" | "institution_id" | "course_code";
export type ClassReason = keyof typeof errors;
export type ClassValues = { name: string; institution_id: string; course_code: string };
export type FieldErrors = Partial<Record<ClassField, string>>;

/** «Klassene dine» (Story 4.10, UX-DR56): the active Classes, then the archived ones under their
 * own heading, each group in the api's order (by name). */
export function splitArchived<T extends { archived: boolean }>(items: readonly T[]): { active: T[]; archived: T[] } {
  return { active: items.filter((i) => !i.archived), archived: items.filter((i) => i.archived) };
}

/** The value as the api stores it: trimmed, inner whitespace collapsed. Python's `str.split` also
 * splits on U+001C–U+001F and U+0085, so those count as whitespace here too. */
export function clean(value: string): string {
  return value.split(/[\s\u001c-\u001f\u0085]+/).filter(Boolean).join(" ");
}

// Control characters, as Python's `str.isprintable` refuses them (the api has the last word).
const CONTROL = /[\u0000-\u001f\u007f-\u009f]/;

/** The api's rules (`class_name`, `course_code` in `classes/schemas.py`), checked before sending:
 * the reason per refused field. Length counts characters, as Python does. */
export function classReasons(values: ClassValues): Partial<Record<ClassField, ClassReason>> {
  const reasons: Partial<Record<ClassField, ClassReason>> = {};
  const name = clean(values.name);
  if (!name) reasons.name = "name_empty";
  else if ([...name].length > NAME_MAX_LENGTH) reasons.name = "name_too_long";
  else if (CONTROL.test(name)) reasons.name = "name_invalid";
  if (!values.institution_id) reasons.institution_id = "institution_missing";
  const code = clean(values.course_code);
  if ([...code].length > COURSE_CODE_MAX_LENGTH) reasons.course_code = "course_code_too_long";
  else if (CONTROL.test(code)) reasons.course_code = "course_code_invalid";
  return reasons;
}

/** The line under each refused field. */
export function classErrors(values: ClassValues): FieldErrors {
  return wordReasons(classReasons(values));
}

function wordReasons(reasons: Partial<Record<ClassField, string>>): FieldErrors {
  const out: FieldErrors = {};
  for (const [field, reason] of Object.entries(reasons) as [ClassField, string][]) {
    if (Object.hasOwn(errors, reason)) out[field] = errors[reason as ClassReason];
  }
  return out;
}

/** The fields an api refusal names, worded; empty for every other failure, which reads as the
 * action's general line. */
export function refusalFields(error: unknown): FieldErrors {
  if (!(error instanceof ApiRequestError) || error.code !== "invalid_request") return {};
  const reasons: Partial<Record<ClassField, string>> = {};
  for (const field of ["name", "institution_id", "course_code"] as const) {
    const reason = error.fields[field];
    if (typeof reason === "string") reasons[field] = reason;
  }
  return wordReasons(reasons);
}

/** The first field with a reason, in form order, for focus. */
export function firstInvalid(found: FieldErrors): ClassField | undefined {
  return (["name", "institution_id", "course_code"] as const).find((field) => found[field]);
}
