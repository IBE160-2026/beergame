"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiRequestError, toApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SessionUser = components["schemas"]["UserOut"];

/** The query key of the current session. `null` data means nobody is logged in. */
export const meKey = ["auth", "me"] as const;

async function fetchMe(): Promise<SessionUser | null> {
  const { data, error, response } = await api.GET("/api/auth/me");
  if (data) return data.user;
  if (response.status === 401) return null;
  throw toApiError(response.status, error);
}

export function useMe() {
  return useQuery({ queryKey: meKey, queryFn: fetchMe, retry: false });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string }) => {
      try {
        const { data, error, response } = await api.POST("/api/auth/login", { body });
        if (data) return data.user;
        throw toApiError(response.status, error);
      } catch (cause) {
        if (cause instanceof ApiRequestError) throw cause;
        throw new ApiRequestError(0, "network_error");
      }
    },
    onSuccess: (user) => queryClient.setQueryData(meKey, user),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.POST("/api/auth/logout");
      if (!response.ok) throw toApiError(response.status, error);
    },
    // Nothing of the old session stays in the cache.
    onSuccess: () => {
      queryClient.clear();
      queryClient.setQueryData(meKey, null);
    },
  });
}
