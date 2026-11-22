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
 * sendt. Prøv igjen.», except the address of a deactivated User, which the form words beside the
 * field; the form checks the address before it sends. The Invitation list reads
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

/** Take the User's row out of every cached list. */
function dropUser(queryClient: ReturnType<typeof useQueryClient>, userId: string) {
  queryClient.setQueriesData<InfiniteData<UserPage>>({ queryKey: ["admin", "users"] }, (data) =>
    data
      ? {
          ...data,
          pages: data.pages.map((page) => ({ ...page, items: page.items.filter((item) => item.id !== userId) })),
        }
      : data,
  );
}

export type UserDeletion = { user: ListedUser; reference: string };

/** Delete a User on the Institution's instruction (Story 15.2, FR-76): one press, no dialog. The
 * row leaves every cached list at once, and the Invitation list reads again, since the User's
 * Invitations went with them; a refusal reads the User list again. The caller words the
 * refusals. */
export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation<unknown, unknown, UserDeletion>({
    mutationFn: ({ user, reference }) =>
      request(() =>
        api.POST("/api/admin/users/{user_id}/delete", {
          params: { path: { user_id: user.id } },
          body: { reference },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSuccess: (_, { user }) => {
      dropUser(queryClient, user.id);
      void queryClient.invalidateQueries({ queryKey: invitationsKey });
    },
    onError: () => void queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
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

export type EvaluationSession = components["schemas"]["EvaluationSessionOut"];
export type EvaluationExport = components["schemas"]["ExportOut"];
export type KeyState = components["schemas"]["KeyStateOut"];
export type AgreementInput = components["schemas"]["AgreementIn"];

/** The query keys of «Pseudonymisert eksport» (Story 15.4). */
export const evaluationKey = ["admin", "evaluation"] as const;
export const evaluationSessionsKey = [...evaluationKey, "class-sessions"] as const;
export const evaluationExportsKey = [...evaluationKey, "exports"] as const;
export const evaluationKeyStateKey = [...evaluationKey, "key"] as const;

/** Every saved Class session with its agreement and deletion date (Story 15.4). */
export function useEvaluationSessions() {
  return useQuery({
    queryKey: evaluationSessionsKey,
    queryFn: () => request(() => api.GET("/api/admin/evaluation/class-sessions")),
    retry: false,
  });
}

/** The newest export runs and refusals (Story 15.4). */
export function useEvaluationExports() {
  return useQuery({
    queryKey: evaluationExportsKey,
    queryFn: () => request(() => api.GET("/api/admin/evaluation/exports")),
    retry: false,
  });
}

/** The stored fingerprint of the pseudonym key (Story 15.4). */
export function useKeyState() {
  return useQuery({
    queryKey: evaluationKeyStateKey,
    queryFn: () => request(() => api.GET("/api/admin/evaluation/key")),
    retry: false,
  });
}

/** Record or replace a Class session's agreement (Story 15.4); the list reads again. */
export function useRecordAgreement() {
  const queryClient = useQueryClient();
  return useMutation<EvaluationSession, unknown, { id: string; body: AgreementInput }>({
    mutationFn: ({ id, body }) =>
      request(() =>
        api.PUT("/api/admin/evaluation/class-sessions/{class_session_id}/agreement", {
          params: { path: { class_session_id: id } },
          body,
        }),
      ),
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: evaluationSessionsKey }),
  });
}

/** Store a new key's fingerprint (Story 15.4); the key state reads again. */
export function useReplaceKey() {
  const queryClient = useQueryClient();
  return useMutation<KeyState, unknown, string>({
    mutationFn: (key) => request(() => api.POST("/api/admin/evaluation/key", { body: { key } })),
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: evaluationKey }),
  });
}

/** Run the export and hand back the ZIP with its file name (Story 15.4). The key goes in the
 * body only. The export list and the key state read again, run or refused. */
export function useRunExport() {
  const queryClient = useQueryClient();
  return useMutation<{ blob: Blob; name: string }, unknown, { ids: string[]; key: string }>({
    mutationFn: async ({ ids, key }) => {
      let name = "pseudonymisert-eksport.zip";
      const blob = await request(async () => {
        const result = await api.POST("/api/admin/evaluation/exports", {
          body: { class_session_ids: ids, key },
          parseAs: "blob",
        });
        const disposition = result.response.headers.get("content-disposition") ?? "";
        name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? name;
        return result;
      });
      return { blob: blob as unknown as Blob, name };
    },
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: evaluationKey }),
  });
}

export type ModelConfig = components["schemas"]["ModelConfigOut"];
export type ModelSession = components["schemas"]["ModelSessionOut"];
export type ModelFreezeState = components["schemas"]["FreezeStateOut"];

/** The query keys of «KI-kostnad» (Story 15.5). */
export const aiCostKey = ["admin", "ai-cost"] as const;
export const modelConfigsKey = [...aiCostKey, "model-configs"] as const;
export const modelSessionsKey = [...aiCostKey, "class-sessions"] as const;
export const modelFreezeKey = [...aiCostKey, "freeze"] as const;

/** Every model config with its measured Effort levels (Story 15.5). */
export function useModelConfigs() {
  return useQuery({
    queryKey: modelConfigsKey,
    queryFn: () => request(() => api.GET("/api/admin/ai/model-configs")),
    retry: false,
  });
}

/** Every saved Class session with its model setting (Story 15.5). */
export function useModelSessions() {
  return useQuery({
    queryKey: modelSessionsKey,
    queryFn: () => request(() => api.GET("/api/admin/ai/class-sessions")),
    retry: false,
  });
}

/** The study freeze in force, or null (Story 15.5). */
export function useModelFreeze() {
  return useQuery({
    queryKey: modelFreezeKey,
    queryFn: () => request(() => api.GET("/api/admin/ai/freeze")),
    retry: false,
  });
}

/** Pin a model config for one Class session (Story 15.5); the page reads again. */
export function usePinModel() {
  const queryClient = useQueryClient();
  return useMutation<ModelSession, unknown, { id: string; modelConfigId: string }>({
    mutationFn: ({ id, modelConfigId }) =>
      request(() =>
        api.PUT("/api/admin/ai/class-sessions/{class_session_id}/model-config", {
          params: { path: { class_session_id: id } },
          body: { model_config_id: modelConfigId },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: aiCostKey }),
  });
}

/** Freeze a model config for a learning study (Story 15.5); the page reads again. */
export function useFreezeModel() {
  const queryClient = useQueryClient();
  return useMutation<ModelFreezeState, unknown, { modelConfigId: string; ids: string[] }>({
    mutationFn: ({ modelConfigId, ids }) =>
      request(() =>
        api.POST("/api/admin/ai/freezes", {
          body: { model_config_id: modelConfigId, class_session_ids: ids },
        }),
      ),
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: aiCostKey }),
  });
}

/** Lift the study freeze (Story 15.5); the page reads again. */
export function useLiftFreeze() {
  const queryClient = useQueryClient();
  return useMutation<ModelFreezeState, unknown, string>({
    mutationFn: (id) =>
      request(() => api.POST("/api/admin/ai/freezes/{freeze_id}/lift", { params: { path: { freeze_id: id } } })),
    networkMode: "always",
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: aiCostKey }),
  });
}
