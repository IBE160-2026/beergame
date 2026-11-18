"use client";

import { nb } from "@/copy/nb";
import { api } from "@/lib/api/client";
import { request, useAction } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

export type AccountRole = components["schemas"]["AccountRole"];
export type SentInvitation = components["schemas"]["InvitationOut"];

/** Send an Invitation to an account role (Story 3.7). Any failure reads «Invitasjonen ble ikke
 * sendt. Prøv igjen.»; the form checks the address before it sends. */
export function useSendInvitation() {
  return useAction<SentInvitation, { email: string; role: AccountRole }>({
    mutationFn: async (body) => await request(() => api.POST("/api/admin/invitations", { body })),
    fallback: nb.admin.users.invite.failed,
  });
}
