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
