"use client";

import {
  type InfiniteData,
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
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
  return useAction<SentInvitation, { email: string; role: AccountRole; access_request_id?: string }>({
    mutationFn: async (body) => await request(() => api.POST("/api/admin/invitations", { body })),
    fallback: nb.admin.users.invite.failed,
    onSuccess: (_, body) => {
      void queryClient.invalidateQueries({ queryKey: invitationsKey });
      // Sent from a request for lecturer access (Story 3.13): the request leaves the list.
      if (body.access_request_id) void queryClient.invalidateQueries({ queryKey: accessRequestsKey });
    },
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

export type Institution = components["schemas"]["InstitutionOut"];
export type InstitutionPage = components["schemas"]["InstitutionListOut"];

/** The query key of the Institution list (Story 3.11). */
export const institutionsKey = ["admin", "institutions"] as const;

/** The Institutions, newest first, one page of the list envelope at a time (Story 3.11). */
export function useInstitutions() {
  return useInfiniteQuery({
    queryKey: institutionsKey,
    queryFn: ({ pageParam }) =>
      request(() =>
        api.GET("/api/admin/institutions", { params: { query: pageParam ? { cursor: pageParam } : {} } }),
      ),
    initialPageParam: "" as string,
    getNextPageParam: (last: InstitutionPage) => last.next_cursor ?? undefined,
    retry: false,
  });
}

/** Create an Institution (Story 3.11). The list reads again, so the new one stands at its top. The
 * caller words the refusals: a bad or taken name goes beside the field. */
export function useCreateInstitution() {
  const queryClient = useQueryClient();
  return useMutation<Institution, unknown, string>({
    mutationFn: (name) => request(() => api.POST("/api/admin/institutions", { body: { name } })),
    networkMode: "always",
    retry: false,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: institutionsKey }),
  });
}

/** Rename an Institution (Story 3.11). The answer replaces its row in place; a refusal reads the
 * list again, since the row may be out of date. */
export function useRenameInstitution() {
  const queryClient = useQueryClient();
  return useMutation<Institution, unknown, { id: string; name: string }>({
    mutationFn: ({ id, name }) =>
      request(() =>
        api.PATCH("/api/admin/institutions/{institution_id}", {
          params: { path: { institution_id: id } },
          body: { name },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSuccess: (updated) =>
      queryClient.setQueryData<InfiniteData<InstitutionPage>>(institutionsKey, (data) =>
        data
          ? {
              ...data,
              pages: data.pages.map((page) => ({
                ...page,
                items: page.items.map((item) => (item.id === updated.id ? updated : item)),
              })),
            }
          : data,
      ),
    onError: () => void queryClient.invalidateQueries({ queryKey: institutionsKey }),
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

export type AuditEvent = components["schemas"]["AuditEventOut"];
export type AuditTarget = components["schemas"]["AuditTarget"];
export type AuditActor = components["schemas"]["AuditActor"];
export type AuditPage = components["schemas"]["AuditListOut"];

/** The audit log's filters (Story 3.12): an actor id or `system`, an action, and inclusive
 * Europe/Oslo days as ISO dates. An empty string means no filter. */
export type AuditFilters = { actor: string; action: string; since: string; until: string };

/** The query key of the audit log for one set of filters (Story 3.12). */
export const auditKey = (filters: AuditFilters) => ["admin", "audit", filters] as const;

/** The audit log, newest first, one page of the list envelope at a time (Story 3.12). */
export function useAuditEvents(filters: AuditFilters) {
  return useInfiniteQuery({
    queryKey: auditKey(filters),
    queryFn: ({ pageParam }) => {
      const query: Record<string, string> = {};
      for (const [key, value] of Object.entries(filters)) if (value) query[key] = value;
      if (pageParam) query.cursor = pageParam;
      return request(() => api.GET("/api/admin/audit", { params: { query } }));
    },
    initialPageParam: "" as string,
    getNextPageParam: (last: AuditPage) => last.next_cursor ?? undefined,
    // A new filter keeps the rows in view until its answer arrives: no Skjelett per filter.
    placeholderData: keepPreviousData,
    retry: false,
  });
}

/** Everyone who appears as actor in the log, for the «Utført av» filter (Story 3.12). */
export function useAuditActors() {
  return useQuery({
    queryKey: ["admin", "audit-actors"] as const,
    queryFn: () => request(() => api.GET("/api/admin/audit/actors")),
    retry: false,
  });
}

export type AccessRequest = components["schemas"]["AccessRequestOut"];
export type AccessRequestPage = components["schemas"]["AccessRequestListOut"];

/** The query key of the open requests for lecturer access (Story 3.13). */
export const accessRequestsKey = ["admin", "access-requests"] as const;

/** The open requests for lecturer access, newest first, one page of the list envelope at a time
 * (Story 3.13). */
export function useAccessRequests() {
  return useInfiniteQuery({
    queryKey: accessRequestsKey,
    queryFn: ({ pageParam }) =>
      request(() =>
        api.GET("/api/admin/access-requests", { params: { query: pageParam ? { cursor: pageParam } : {} } }),
      ),
    initialPageParam: "" as string,
    getNextPageParam: (last: AccessRequestPage) => last.next_cursor ?? undefined,
    retry: false,
  });
}

/** Dismiss an open request (Story 3.13). Either way the list reads again: the request leaves it,
 * and a refusal means it was already answered. The caller words the refusal. */
export function useDismissAccessRequest() {
  const queryClient = useQueryClient();
  return useMutation<void, unknown, AccessRequest>({
    mutationFn: async (item) => {
      await request(() =>
        api.POST("/api/admin/access-requests/{access_request_id}/dismiss", {
          params: { path: { access_request_id: item.id } },
        }),
      );
    },
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: accessRequestsKey }),
  });
}
