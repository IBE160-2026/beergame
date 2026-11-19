import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { clean } from "./classes";

const copy = nb.classes.entries;
const reasons: Readonly<Record<string, string>> = nb.classes.roster.reasons;

export type EntryField = "email" | "name";
export type EntryErrors = Partial<Record<EntryField, string>>;

/** The line beside the address field for the api's reason (Story 4.8): the upload's own reasons
 * («Domene mangler»), a duplicate on the Roster, or an address already registered. */
export function emailReason(reason: string): string | undefined {
  if (Object.hasOwn(reasons, reason)) return reasons[reason];
  if (reason === "on_roster") return nb.classes.roster.onRoster;
  if (reason === "already_registered") return copy.alreadyRegistered;
  if (reason === "string_too_long") return copy.emailTooLong;
  return undefined;
}

function nameReason(reason: string): string | undefined {
  if (reason === "name_empty") return copy.nameEmpty;
  if (reason === "name_too_long") return copy.nameTooLong;
  return undefined;
}

/** The fields an api refusal names, worded; empty for every other failure, which reads as the
 * form's general line. */
export function entryRefusal(error: unknown): EntryErrors {
  if (!(error instanceof ApiRequestError) || error.code !== "invalid_request") return {};
  const out: EntryErrors = {};
  const email = error.fields.email;
  const name = error.fields.name;
  if (typeof email === "string") out.email = emailReason(email);
  if (typeof name === "string") out.name = nameReason(name);
  if (!out.email) delete out.email;
  if (!out.name) delete out.name;
  return out;
}

/** The api's name rule checked before sending: the name as stored (trimmed, collapsed), and its
 * line when refused. Length counts characters, as Python does. */
export function nameError(value: string): string | undefined {
  const name = clean(value);
  if (!name) return copy.nameEmpty;
  if ([...name].length > 200) return copy.nameTooLong;
  return undefined;
}

/** The first refused field, in form order, for focus. */
export function firstRefused(errors: EntryErrors): EntryField | undefined {
  return (["email", "name"] as const).find((field) => errors[field]);
}
