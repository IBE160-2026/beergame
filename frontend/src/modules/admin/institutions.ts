import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

const copy = nb.admin.institutions;

/** The api's longest name (`INSTITUTION_NAME_MAX_LENGTH` in `identity/schemas.py`). */
export const NAME_MAX_LENGTH = 200;

type NameReason = keyof typeof copy.errors;

/** The name as the api stores it: trimmed, inner whitespace collapsed. */
export function cleanName(value: string): string {
  return value.split(/\s+/).filter(Boolean).join(" ");
}

/** The api's name rule (`institution_name` in `identity/schemas.py`), checked before sending: the
 * reason a name is refused, or undefined. Length counts characters, as Python does. The api has
 * the last word: at the edges of Unicode (format characters such as U+200B) it may still refuse a
 * name this passes, and its reason then stands under the field all the same. */
export function nameReason(value: string): NameReason | undefined {
  const name = cleanName(value);
  if (!name) return "name_empty";
  if ([...name].length > NAME_MAX_LENGTH) return "name_too_long";
  if (name.includes("@") || /[\u0000-\u001f\u007f-\u009f]/.test(name)) return "name_invalid";
  return undefined;
}

/** The line under the name field for a reason, or undefined. */
export function nameError(value: string): string | undefined {
  const reason = nameReason(value);
  return reason ? copy.errors[reason] : undefined;
}

/** A refusal that belongs beside the name field (a bad or taken name), or undefined for every
 * other failure, which reads as the action's general line. */
export function refusalForField(error: unknown): string | undefined {
  if (!(error instanceof ApiRequestError)) return undefined;
  if (error.code === "institution_name_taken") return copy.errors.institution_name_taken;
  const reason = error.fields.name;
  if (error.code === "invalid_request" && typeof reason === "string" && Object.hasOwn(copy.errors, reason)) {
    return copy.errors[reason as NameReason];
  }
  return undefined;
}

/** The api's longest «Signert av» (`PROCESSING_AGREEMENT_TEXT_MAX` in `identity/schemas.py`). */
export const SIGNED_BY_MAX_LENGTH = 200;

export type ProcessingAgreementValues = { signedBy: string; signedOn: string };
export type ProcessingAgreementErrors = Partial<Record<keyof ProcessingAgreementValues, string>>;

/** The api's rules for a data processing agreement (Story 15.12), checked before sending: who
 * signed is required and at most 200 characters without outer whitespace; the day is required and
 * not after `today` (Europe/Oslo, «2026-11-23»). */
export function processingAgreementErrors(values: ProcessingAgreementValues, today: string): ProcessingAgreementErrors {
  const form = copy.processingAgreement;
  const errors: ProcessingAgreementErrors = {};
  const by = values.signedBy.trim();
  if (!by) errors.signedBy = form.required;
  else if ([...by].length > SIGNED_BY_MAX_LENGTH) errors.signedBy = form.tooLong;
  if (!values.signedOn) errors.signedOn = form.required;
  else if (values.signedOn > today) errors.signedOn = form.inFuture;
  return errors;
}

/** The api's retention periods (`RETENTION_MONTHS_MIN`/`MAX` in `identity/schemas.py`). */
export const RETENTION_MONTHS_MIN = 1;
export const RETENTION_MONTHS_MAX = 120;

/** Story 15.3: the months typed in the retention field, as the api takes them: null for an empty
 * field (the placeholder), a whole number from 1 to 120, or undefined when the field holds
 * anything else. */
export function retentionMonths(value: string): number | null | undefined {
  const text = value.trim();
  if (!text) return null;
  if (!/^\d+$/.test(text)) return undefined;
  const months = Number(text);
  return months >= RETENTION_MONTHS_MIN && months <= RETENTION_MONTHS_MAX ? months : undefined;
}
