import { nb } from "@/copy/nb";
import { cleanName, NAME_MAX_LENGTH, nameReason } from "@/modules/admin/institutions";
import { validateEmail } from "@/modules/identity/validate-login";

const errors = nb.accessRequest.errors;

export type AccessRequestFields = { name: string; email: string; institution: string };
export type AccessRequestErrors = Partial<Record<keyof AccessRequestFields, string>>;

/**
 * The api's checks of «Be om lærertilgang» (`AccessRequestIn` in `identity/schemas.py`), before
 * sending: the reason under each field that the api would refuse. Names are trimmed with inner
 * whitespace collapsed, and length counts characters, as Python does. The Institution follows the
 * Institution name rule (Story 3.11).
 */
export function validateAccessRequest(fields: AccessRequestFields): AccessRequestErrors {
  const out: AccessRequestErrors = {};
  const name = cleanName(fields.name);
  if (!name || /[\u0000-\u001f\u007f-\u009f]/.test(name)) out.name = errors.nameEmpty;
  else if ([...name].length > NAME_MAX_LENGTH) out.name = errors.nameLong;
  const email = validateEmail(fields.email);
  if (email) out.email = email === "emailEmpty" ? errors.emailEmpty : nb.auth.login.errors[email];
  const institution = nameReason(fields.institution);
  if (institution === "name_empty") out.institution = errors.institutionEmpty;
  else if (institution === "name_too_long") out.institution = errors.institutionLong;
  else if (institution === "name_invalid") out.institution = errors.institutionInvalid;
  return out;
}

/** What the form sends: the names cleaned, the address trimmed. */
export function cleanAccessRequest(fields: AccessRequestFields): AccessRequestFields {
  return { name: cleanName(fields.name), email: fields.email.trim(), institution: cleanName(fields.institution) };
}
