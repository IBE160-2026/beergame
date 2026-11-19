"use client";

import { useMutation } from "@tanstack/react-query";

import { nb } from "@/copy/nb";

import { ApiRequestError, toApiError } from "./client";

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/**
 * Runs one openapi-fetch call and returns its data. A non-2xx answer throws `ApiRequestError`
 * with the AD-19 code; a request that never completed (offline, dropped) throws `network_error`.
 */
export async function request<T>(call: () => Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await call();
  } catch (cause) {
    // fetch rejects with a TypeError (or an AbortError) when the request never completed; any
    // other error is a bug and stays visible as itself.
    if (cause instanceof TypeError || (cause instanceof Error && cause.name === "AbortError")) {
      throw new ApiRequestError(0, "network_error");
    }
    throw cause;
  }
  if (!result.response.ok) throw toApiError(result.response.status, result.error);
  return result.data as T;
}

/** The error code of a failed action: the AD-19 code, or `unknown_error`. */
export function errorCode(error: unknown): string {
  return error instanceof ApiRequestError ? error.code : "unknown_error";
}

/** Codes worded the same for every action. `class_archived` (Story 4.10): the Class was archived
 * while its page was open; the query client then reads the Class again (`providers.tsx`). */
export const SHARED_MESSAGES: Readonly<Record<string, string>> = {
  class_archived: nb.classes.archive.refused,
};

/**
 * The line shown beside an action that failed (UX-DR59, UX-DR76). `messages` names the codes an
 * action words itself; then the shared codes; every other code, unknown ones included, reads
 * `fallback`, which is «Det ble ikke lagret. Prøv igjen.» unless the action says otherwise.
 */
export function actionErrorMessage(
  error: unknown,
  messages: Readonly<Record<string, string>> = {},
  fallback: string = nb.system.actionFailed,
): string {
  const code = errorCode(error);
  if (Object.hasOwn(messages, code)) return messages[code];
  return Object.hasOwn(SHARED_MESSAGES, code) ? SHARED_MESSAGES[code] : fallback;
}

/**
 * The shared mutation for an action (Story 3.4). It fails at once when the device is offline and
 * is never queued, so nothing is sent on its own when the connection returns. `errorMessage` is
 * the inline line for `ActionError`; it clears when the action runs again. The caller keeps the
 * button free of `unavailable` after a failure and never moves focus, so the User can press it
 * again with their input intact.
 */
export function useAction<TData, TVars = void>(options: {
  mutationFn: (vars: TVars) => Promise<TData>;
  messages?: Readonly<Record<string, string>>;
  fallback?: string;
  onSuccess?: (data: TData, vars: TVars) => unknown;
}) {
  const mutation = useMutation<TData, unknown, TVars>({
    mutationFn: options.mutationFn,
    onSuccess: options.onSuccess,
    networkMode: "always",
    retry: false,
  });
  const errorMessage = mutation.isError
    ? actionErrorMessage(mutation.error, options.messages, options.fallback)
    : undefined;
  return { ...mutation, errorMessage };
}
