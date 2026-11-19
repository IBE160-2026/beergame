/**
 * Pure helpers of «Du er invitert» (Story 3.8), kept apart from the page so Vitest checks them
 * without a browser.
 */
import { nb } from "@/copy/nb";

import { type NewPasswordError, validateNewPassword } from "./password-reset";

/** The longest name the API takes (`identity.schemas.NAME_MAX_LENGTH`). */
export const NAME_MAX_LENGTH = 200;

export type NameError = "nameEmpty" | "nameLong";
export type InvitationErrors = { name?: NameError; password?: NewPasswordError };

/** The client check of a name; the API stays authoritative. Spaces are trimmed and collapsed as
 * the API does. */
export function validateName(value: string): NameError | undefined {
  const name = normaliseName(value);
  // A control character is refused by the API as no name at all.
  if (name === "" || /\p{Cc}/u.test(name)) return "nameEmpty";
  if ([...name].length > NAME_MAX_LENGTH) return "nameLong";
  return undefined;
}

export function normaliseName(value: string): string {
  return value.split(/\s+/).filter(Boolean).join(" ");
}

/** Both fields of a new account; the existing-account form checks only that a password is typed. */
export function validateInvitation(name: string, password: string): InvitationErrors {
  return { name: validateName(name), password: validateNewPassword(password) };
}

/** «Invitasjonen er gyldig i 14 dager.» with the real days left; a Student Invitation adds
 * «Du får Rolle og spill på startdatoen.» (Story 4.5). */
export function validityLine(days: number, student = false): string {
  const line = nb.auth.invitation.validity(days);
  return student ? `${line} ${nb.auth.invitation.student.startDate}` : line;
}

/** The role's name in the page's words. */
export function roleName(role: "lecturer" | "admin"): string {
  return nb.auth.invitation.roles[role];
}

/** What a checked link offers, in the page's words (Stories 3.8 and 4.5). */
export type InvitationOffer = {
  kind: "role" | "student" | "assistant";
  role?: "lecturer" | "admin" | null;
  class_name?: string | null;
  course_code?: string | null;
  invited_by?: string | null;
};

/** The lead under «Du er invitert»: the role, or the Class and its Lecturer; for an address that
 * has an account, what logging in adds. */
export function invitationLead(offer: InvitationOffer, existing: boolean): string {
  const copy = nb.auth.invitation;
  if (offer.kind === "assistant") {
    const label = nb.classes.home.label(offer.class_name ?? "", offer.course_code ?? null);
    return existing ? copy.assistant.existing.lead(label) : copy.assistant.lead(offer.invited_by ?? null, label);
  }
  if (offer.kind === "student") {
    const label = nb.classes.home.label(offer.class_name ?? "", offer.course_code ?? null);
    return existing ? copy.student.existing.lead(label) : copy.student.lead(offer.invited_by ?? null, label);
  }
  const role = roleName(offer.role ?? "lecturer");
  return existing ? copy.existing.lead(role) : copy.lead(role);
}
