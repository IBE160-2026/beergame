import { nb } from "@/copy/nb";

const copy = nb.auth.login;

/**
 * The Norwegian line for a failed login, from the API's stable error code (AD-19, FR-72).
 * The copy never says whether an account exists (UX-DR61).
 */
export function loginErrorMessage(code: string): string {
  switch (code) {
    case "invalid_credentials":
      return copy.invalidCredentials;
    case "account_deactivated":
      return copy.deactivated;
    case "rate_limited":
      return copy.rateLimited;
    default:
      return copy.failed;
  }
}
