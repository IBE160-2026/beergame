"use client";

import {
  type InfiniteData,
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { nb } from "@/copy/nb";
import { api } from "@/lib/api/client";
import { request, useAction } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";
import { meKey } from "@/modules/identity/api";

export type AccountRole = components["schemas"]["AccountRole"];
export type SentInvitation = components["schemas"]["InvitationOut"];
export type ListedUser = components["schemas"]["UserListItem"];
export type UserPage = components["schemas"]["UserListOut"];
export type ListedInvitation = components["schemas"]["InvitationListItem"];
export type InvitationPage = components["schemas"]["InvitationListOut"];

/** The query key of the Invitation list (Story 3.10). */
export const invitationsKey = ["admin", "invitations"] as const;

/** Send an Invitation to an account role (Story 3.7). Any failure reads «Invitasjonen ble ikke
 * sendt. Prøv igjen.»; the form checks the address before it sends. The Invitation list reads
 * again, so the new one stands in it. */
export function useSendInvitation() {
  const queryClient = useQueryClient();
  return useAction<SentInvitation, { email: string; role: AccountRole }>({
    mutationFn: async (body) => await request(() => api.POST("/api/admin/invitations", { body })),
    fallback: nb.admin.users.invite.failed,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: invitationsKey }),
  });
}

/** The Invitation list (Story 3.10): the newest Invitation per address and role, newest first,
 * one page of the list envelope at a time. */
export function useInvitations() {
  return useInfiniteQuery({
    queryKey: invitationsKey,
    queryFn: ({ pageParam }) =>
      request(() =>
        api.GET("/api/admin/invitations", { params: { query: pageParam ? { cursor: pageParam } : {} } }),
      ),
    initialPageParam: "" as string,
    getNextPageParam: (last: InvitationPage) => last.next_cursor ?? undefined,
    retry: false,
  });
}

/** Send an open or expired Invitation again (Story 3.10). Either way the list reads again: the
 * new Invitation replaces the old in its row, and a refusal may mean the row was out of date. */
export function useResendInvitation() {
  const queryClient = useQueryClient();
  return useMutation<SentInvitation, unknown, ListedInvitation>({
    mutationFn: (invitation) =>
      request(() =>
        api.POST("/api/admin/invitations/{invitation_id}/resend", {
          params: { path: { invitation_id: invitation.id } },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: invitationsKey }),
  });
}

/** The query key of the User list for one search text (Story 3.9). */
export const usersKey = (search: string) => ["admin", "users", search] as const;

/** The User list, one page of the list envelope at a time, for the search text `search`. */
export function useUsers(search: string) {
  return useInfiniteQuery({
    queryKey: usersKey(search),
    queryFn: ({ pageParam }) =>
      request(() =>
        api.GET("/api/admin/users", {
          params: { query: { q: search, ...(pageParam ? { cursor: pageParam } : {}) } },
        }),
      ),
    initialPageParam: "" as string,
    getNextPageParam: (last: UserPage) => last.next_cursor ?? undefined,
    // A new search keeps the rows in view until its answer arrives: no Skjelett per key.
    placeholderData: keepPreviousData,
    retry: false,
  });
}

/** Put the answer's row in place of the User's row in every cached list. */
function replaceUser(queryClient: ReturnType<typeof useQueryClient>, updated: ListedUser) {
  queryClient.setQueriesData<InfiniteData<UserPage>>({ queryKey: ["admin", "users"] }, (data) =>
    data
      ? {
          ...data,
          pages: data.pages.map((page) => ({
            ...page,
            items: page.items.map((item) => (item.id === updated.id ? updated : item)),
          })),
        }
      : data,
  );
}

/** Deactivate or reactivate a User (Story 3.10). The answer replaces the User's row in place;
 * a refusal reads the list again. A deactivation voids the User's open Invitations, so the
 * Invitation list reads again too. The caller words the refusals. */
export function useChangeStatus() {
  const queryClient = useQueryClient();
  return useMutation<ListedUser, unknown, ListedUser>({
    mutationFn: (user) =>
      user.is_active
        ? request(() =>
            api.POST("/api/admin/users/{user_id}/deactivate", { params: { path: { user_id: user.id } } }),
          )
        : request(() =>
            api.POST("/api/admin/users/{user_id}/reactivate", { params: { path: { user_id: user.id } } }),
          ),
    networkMode: "always",
    retry: false,
    onSuccess: (updated) => {
      replaceUser(queryClient, updated);
      void queryClient.invalidateQueries({ queryKey: invitationsKey });
    },
    onError: () => void queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
}

export type RoleChange = { user: ListedUser; role: AccountRole; grant: boolean };

/** Grant or revoke one account role (Story 3.9). The answer replaces the User's row in every
 * cached list, so the row and its buttons update in place; revoking or granting one's own role
 * also reloads the session. The caller words the refusals. */
export function useChangeRole(selfId: string) {
  const queryClient = useQueryClient();
  return useMutation<ListedUser, unknown, RoleChange>({
    mutationFn: ({ user, role, grant }) =>
      grant
        ? request(() =>
            api.POST("/api/admin/users/{user_id}/roles", { params: { path: { user_id: user.id } }, body: { role } }),
          )
        : request(() =>
            api.DELETE("/api/admin/users/{user_id}/roles/{role}", { params: { path: { user_id: user.id, role } } }),
          ),
    networkMode: "always",
    retry: false,
    onSuccess: (updated) => {
      replaceUser(queryClient, updated);
      if (updated.id === selfId) void queryClient.invalidateQueries({ queryKey: meKey });
    },
    // A refusal may mean the row is out of date (another Admin changed it, or the User is gone):
    // read the list again, so the buttons match the server.
    onError: () => void queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
}
