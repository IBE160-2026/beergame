"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nb } from "@/copy/nb";
import { api, toApiError } from "@/lib/api/client";
import { request, useAction } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

export type SessionUser = components["schemas"]["UserOut"];

/** The query key of the current session. `null` data means nobody is logged in. */
export const meKey = ["auth", "me"] as const;

/** The logged-in User, or `null` when the request carried no session. An ended session
 * (`session_expired`) is an error, which sends the User to «Logg inn» (Story 3.4). */
async function fetchMe(): Promise<SessionUser | null> {
  const { data, error, response } = await api.GET("/api/auth/me");
  if (data) return data.user;
  const failure = toApiError(response.status, error);
  if (response.status === 401 && failure.code !== "session_expired") return null;
  throw failure;
}

export function useMe() {
  return useQuery({ queryKey: meKey, queryFn: fetchMe, retry: false });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string }) =>
      (await request(() => api.POST("/api/auth/login", { body }))).user,
    onSuccess: (user) => queryClient.setQueryData(meKey, user),
  });
}

/** «Logg ut» through the shared action helper; a failure reads «Utloggingen gikk ikke. Prøv
 * igjen.», since nothing is saved. */
export function useLogout() {
  const queryClient = useQueryClient();
  return useAction<void>({
    mutationFn: async () => {
      await request(() => api.POST("/api/auth/logout"));
    },
    fallback: nb.auth.session.logoutFailed,
    // Nothing of the old session stays in the cache.
    onSuccess: () => {
      queryClient.clear();
      queryClient.setQueryData(meKey, null);
    },
  });
}

/** Ask for a reset link (Story 3.6). The answer is the same whether or not the address has an
 * account. */
export function useRequestPasswordReset() {
  return useAction<void, { email: string }>({
    mutationFn: async (body) => {
      await request(() => api.POST("/api/auth/password-reset", { body }));
    },
    messages: { rate_limited: nb.auth.forgot.rateLimited },
    fallback: nb.auth.forgot.failed,
  });
}

/** Whether a reset link still works: its account's e-mail, or `reset_link_invalid`. */
export async function checkPasswordReset(token: string): Promise<string> {
  return (await request(() => api.POST("/api/auth/password-reset/check", { body: { token } }))).email;
}

export type CheckedInvitation = components["schemas"]["InvitationCheckOut"];

/** What «Du er invitert» shows for a usable link, or `invitation_link_invalid` (Story 3.8). */
export async function checkInvitation(token: string): Promise<CheckedInvitation> {
  return request(() => api.POST("/api/auth/invitation/check", { body: { token } }));
}

/** Accept an Invitation: a new account, or the role added to the address's account. Either way
 * the User is logged in, and the session cache holds them. */
export function useAcceptInvitation(existing: boolean) {
  const queryClient = useQueryClient();
  const copy = nb.auth.invitation;
  return useAction<SessionUser, { token: string; name: string; password: string }>({
    mutationFn: async ({ token, name, password }) =>
      existing
        ? (await request(() => api.POST("/api/auth/invitation/accept-login", { body: { token, password } }))).user
        : (await request(() => api.POST("/api/auth/invitation/accept", { body: { token, name, password } }))).user,
    messages: {
      rate_limited: copy.rateLimited,
      invalid_credentials: nb.auth.login.invalidCredentials,
    },
    fallback: existing ? copy.existing.failed : copy.failed,
    onSuccess: (user) => queryClient.setQueryData(meKey, user),
  });
}

/** Ask for a new Invitation from a link that no longer works; the answer is the same for any link. */
export function useRequestInvitationRenewal() {
  return useAction<void, { token: string }>({
    mutationFn: async (body) => {
      await request(() => api.POST("/api/auth/invitation/renewal", { body }));
    },
    messages: { rate_limited: nb.auth.invitation.rateLimited },
    fallback: nb.auth.invitation.requestFailed,
  });
}

/** Set a new password through a reset link; resolves to the account's e-mail. */
export function useConfirmPasswordReset() {
  return useAction<string, { token: string; password: string }>({
    mutationFn: async (body) =>
      (await request(() => api.POST("/api/auth/password-reset/confirm", { body }))).email,
    fallback: nb.auth.reset.failed,
  });
}
