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
  if (name === "") return "nameEmpty";
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

/** «Invitasjonen er gyldig i 14 dager.» with the real days left. */
export function validityLine(days: number): string {
  return nb.auth.invitation.validity(days);
}

/** The role's name in the page's words. */
export function roleName(role: "lecturer" | "admin"): string {
  return nb.auth.invitation.roles[role];
}
