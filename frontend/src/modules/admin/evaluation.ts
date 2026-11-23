import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

const copy = nb.admin.evaluation;
const MONTHS = nb.admin.users.invitations.months;

/** The api's limits (`ops/schemas.py`, `ops/models.py`). */
export const KEY_MIN = 32;
export const KEY_MAX = 512;
export const AGREEMENT_TEXT_MAX = 200;
export const EXPORT_SESSIONS_MAX = 20;

/** «class-of-1994 · Klasseøkt 2». */
export function sessionLabel(item: { class_name: string; number: number }): string {
  return copy.sessions.label(item.class_name, item.number);
}

/** «17. mai 2027» for a calendar day («2027-05-17»), with no time zone shift. */
export function formatDay(day: string): string {
  const [year, month, date] = day.split("-").map(Number);
  return `${date}. ${MONTHS[month - 1]} ${year}`;
}

/** Today on the Oslo calendar, as «2026-11-22». */
export function todayInOslo(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Oslo" }).format(now);
}

export type AgreementValues = {
  agreedBy: string;
  agreedOn: string;
  controller: string;
};
export type AgreementErrors = Partial<Record<keyof AgreementValues, string>>;

function textError(value: string): string | undefined {
  const text = value.trim();
  if (!text) return copy.agreementForm.required;
  if ([...text].length > AGREEMENT_TEXT_MAX) return copy.agreementForm.tooLong;
  return undefined;
}

/** The api's agreement rules, checked before sending: the reason per field, or none. */
export function agreementErrors(values: AgreementValues, today: string): AgreementErrors {
  const errors: AgreementErrors = {};
  const by = textError(values.agreedBy);
  if (by) errors.agreedBy = by;
  if (!values.agreedOn) errors.agreedOn = copy.agreementForm.required;
  else if (values.agreedOn > today) errors.agreedOn = copy.agreementForm.inFuture;
  const controller = textError(values.controller);
  if (controller) errors.controller = controller;
  return errors;
}

/** The api's key rule, on the key without outer whitespace: the reason, or undefined. */
export function keyError(value: string): string | undefined {
  const key = value.trim();
  if ([...key].length < KEY_MIN) return copy.run.keyTooShort;
  if ([...key].length > KEY_MAX) return copy.run.keyTooLong;
  return undefined;
}

/** The line for a refused run: a changed key or a Class session without agreement, else the
 * general failure. */
export function runRefusal(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.code === "pseudonym_key_changed") return copy.run.keyChanged;
    if (error.code === "no_agreement") return copy.run.noAgreement;
    if (error.code === "invalid_request" && error.fields.key === "too_short") return copy.run.keyTooShort;
    if (error.code === "invalid_request" && error.fields.key === "too_long") return copy.run.keyTooLong;
  }
  return copy.run.failed;
}

/** The first 16 hex digits of a fingerprint, in groups of four: enough to compare by eye. */
export function shortFingerprint(fingerprint: string): string {
  return (
    fingerprint
      .slice(0, 16)
      .match(/.{1,4}/g)
      ?.join(" ") ?? ""
  );
}

/** «Eksportert», «Avvist: …», or the code of an outcome with no entry. */
export function outcomeText(outcome: string): string {
  return Object.hasOwn(copy.exports.outcomes, outcome) ? copy.exports.outcomes[outcome] : outcome;
}
