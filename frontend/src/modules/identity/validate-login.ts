/**
 * Client-side check of the «Logg inn» form. It only mirrors what the server will check (AD-10),
 * so the server stays authoritative from Story 3.2 on. It returns error keys, and the form maps
 * them to the copy in `nb.ts`.
 */
export type EmailError =
  | "emailEmpty"
  | "emailSpace"
  | "emailNoAt"
  | "emailTwoAt"
  | "emailNoLocal"
  | "emailNoDomain";
export type PasswordError = "passwordEmpty";

export type LoginErrors = {
  email?: EmailError;
  password?: PasswordError;
};

export function validateEmail(raw: string): EmailError | undefined {
  const value = raw.trim();
  if (value === "") return "emailEmpty";
  if (/\s/.test(value)) return "emailSpace";
  const ats = value.split("@").length - 1;
  if (ats === 0) return "emailNoAt";
  if (ats > 1) return "emailTwoAt";
  const [local, domain] = value.split("@");
  if (local === "") return "emailNoLocal";
  const labels = domain.split(".");
  if (labels.length < 2 || labels.some((label) => label === "")) return "emailNoDomain";
  return undefined;
}

export function validatePassword(value: string): PasswordError | undefined {
  return value === "" ? "passwordEmpty" : undefined;
}

export function validateLogin(input: { email: string; password: string }): LoginErrors {
  const errors: LoginErrors = {};
  const email = validateEmail(input.email);
  const password = validatePassword(input.password);
  if (email) errors.email = email;
  if (password) errors.password = password;
  return errors;
}
