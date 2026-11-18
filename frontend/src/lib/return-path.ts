/** The login page, and its query parameters: where to go after login, and why the User is there. */
export const LOGIN_PATH = "/logg-inn";
export const NEXT_PARAM = "neste";
export const EXPIRED_PARAM = "utlopt";

const ORIGIN = "http://olspillet.invalid";

/**
 * `raw` as a path on this site, or `null` (UX-DR59, Story 3.4). Only a path that starts with one
 * `/`, holds no backslash or control character, stays on the same origin and is not «Logg inn»
 * itself is kept, so a crafted link can never send a User elsewhere after login.
 */
export function safeReturnPath(raw: unknown): string | null {
  if (typeof raw !== "string" || !raw.startsWith("/") || raw.startsWith("//")) return null;
  // eslint-disable-next-line no-control-regex
  if (/[\\\u0000-\u001f\u007f]/.test(raw)) return null;
  let url: URL;
  try {
    url = new URL(raw, ORIGIN);
  } catch {
    return null;
  }
  if (url.origin !== ORIGIN) return null;
  // Not «Logg inn» itself (with or without a trailing slash), and not an API address.
  const page = url.pathname.replace(/\/+$/, "") || "/";
  if (page === LOGIN_PATH || page === "/api" || page.startsWith("/api/")) return null;
  return `${url.pathname}${url.search}${url.hash}`;
}

/** «Logg inn» with the way back to `next`; `expired` adds «Du er logget ut. …». */
export function loginPath(next: string | null, expired = false): string {
  const params = new URLSearchParams();
  const path = safeReturnPath(next);
  if (path) params.set(NEXT_PARAM, path);
  if (expired) params.set(EXPIRED_PARAM, "1");
  const query = params.toString();
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH;
}
