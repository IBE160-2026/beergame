"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { nb } from "@/copy/nb";
import { api, toApiError } from "@/lib/api/client";
import { request, useAction } from "@/lib/api/mutation";
import { clearAllDrafts } from "@/lib/drafts";
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
    // Nothing of the old session stays in the cache, nor any unsent input (Story 6.12).
    onSuccess: () => {
      clearAllDrafts();
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

export type CheckedReset = components["schemas"]["ResetCheckOut"];

/** Whether a reset link still works: its account's e-mail and whether the account has no password
 * yet (a manually registered Student, Story 4.8), or `reset_link_invalid`. */
export async function checkPasswordReset(token: string): Promise<CheckedReset> {
  return request(() => api.POST("/api/auth/password-reset/check", { body: { token } }));
}

export type CheckedInvitation = components["schemas"]["InvitationCheckOut"];

/** What «Du er invitert» shows for a usable link, or `invitation_link_invalid` (Story 3.8). */
export async function checkInvitation(token: string): Promise<CheckedInvitation> {
  return request(() => api.POST("/api/auth/invitation/check", { body: { token } }));
}

/** Accept an Invitation: a new account, or the role (or, for a Student Invitation, the Class)
 * added to the address's account. Either way the User is logged in, and the session cache holds
 * them. */
export function useAcceptInvitation(existing: boolean, student = false) {
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
    fallback: existing ? (student ? copy.student.existing.failed : copy.existing.failed) : copy.failed,
    onSuccess: (user) => {
      queryClient.setQueryData(meKey, user);
      // The account may hold a new role or Class: every other read is fetched again (Hjem's
      // Classes among them), not served from a cache younger than its stale time.
      void queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
    },
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

export type Consent = components["schemas"]["ConsentOut"];
export type ConsentDecision = NonNullable<Consent["decision"]>;

/** The query key of a test student's consent (Story 12.8). */
export const consentKey = ["me", "test-student-consent"] as const;

/** A test student's decision on the current consent text; only read for a test student. */
export function useConsent(enabled: boolean) {
  return useQuery({
    queryKey: consentKey,
    queryFn: () => request(() => api.GET("/api/me/test-student-consent")),
    enabled,
  });
}

/** «Jeg samtykker» or «Nei takk» on the text Hjem shows (`nb.homes.consent.version`). */
export function useDecideConsent() {
  const queryClient = useQueryClient();
  const copy = nb.homes.consent;
  return useAction<Consent, ConsentDecision>({
    mutationFn: async (decision) => {
      try {
        return await request(() =>
          api.PUT("/api/me/test-student-consent", { body: { decision, text_version: copy.version } }),
        );
      } catch (error) {
        // Consent given in another tab: read it again, so the page shows what is stored.
        void queryClient.invalidateQueries({ queryKey: consentKey, exact: true });
        throw error;
      }
    },
    messages: { consent_text_changed: copy.changed, consent_given: copy.alreadyGiven },
    fallback: copy.failed,
    onSuccess: (data) => queryClient.setQueryData(consentKey, data),
  });
}
