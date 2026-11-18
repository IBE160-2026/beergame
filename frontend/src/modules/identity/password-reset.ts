/**
 * Pure helpers of «Glemt passord» and «Nytt passord» (Story 3.6), kept apart from the forms so
 * Vitest checks them without a browser.
 */

/** The shortest password the API takes (`identity.schemas.PASSWORD_MIN_LENGTH`). */
export const PASSWORD_MIN_LENGTH = 8;

export type NewPasswordError = "passwordEmpty" | "passwordShort";

/** The client check of a new password; the API stays authoritative. Length counts characters as
 * the API does (code points), so an emoji is one. */
export function validateNewPassword(value: string): NewPasswordError | undefined {
  if (value === "") return "passwordEmpty";
  if ([...value].length < PASSWORD_MIN_LENGTH) return "passwordShort";
  return undefined;
}

/** The token of a reset link, from the URL fragment (`/nytt-passord#<token>`). A fragment never
 * reaches a server log or a `Referer` header. Empty when the link carries none. */
export function tokenFromHash(hash: string): string {
  const token = hash.startsWith("#") ? hash.slice(1) : hash;
  return /^[A-Za-z0-9_-]{1,128}$/.test(token) ? token : "";
}
