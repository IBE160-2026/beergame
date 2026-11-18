import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

/**
 * The typed API client (AD-10). `schema.ts` is generated from the FastAPI OpenAPI schema
 * (`openapi.json`) by `npm run api:generate`; CI regenerates both and fails on any difference.
 *
 * Every request goes to the same origin through the proxy, with the session cookie. Every
 * mutation carries `X-Requested-With: olspillet`, the CSRF guard the API requires (AD-11).
 */
export const CSRF_HEADER = "X-Requested-With";
export const CSRF_VALUE = "olspillet";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method.toUpperCase())) {
      request.headers.set(CSRF_HEADER, CSRF_VALUE);
    }
    return request;
  },
};

export type ApiError = components["schemas"]["ErrorEnvelope"]["error"];

export function createApiClient(options: { baseUrl?: string; fetch?: typeof fetch } = {}) {
  const client = createClient<paths>({
    baseUrl: options.baseUrl ?? "",
    credentials: "same-origin",
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });
  client.use(csrfMiddleware);
  return client;
}

export const api = createApiClient();

/** An API answer that is not 2xx, carrying the AD-19 error code (or `network_error`). */
export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
  ) {
    super(code);
    this.name = "ApiRequestError";
  }
}

/** The session cookie was sent but the session has ended (401 `session_expired`, Story 3.4). */
export function isSessionExpired(error: unknown): boolean {
  return error instanceof ApiRequestError && error.code === "session_expired";
}

/** The error code of a failed openapi-fetch result; `unknown_error` when the body has none. */
export function toApiError(status: number, body: unknown): ApiRequestError {
  const code =
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof (body as { error?: { code?: unknown } }).error?.code === "string"
      ? (body as { error: { code: string } }).error.code
      : "unknown_error";
  return new ApiRequestError(status, code);
}
