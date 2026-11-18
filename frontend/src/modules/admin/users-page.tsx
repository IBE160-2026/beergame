"use client";

import { useState } from "react";

import { nb } from "@/copy/nb";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_USERS_PATH, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { AccessRequestList } from "./access-request-list";
import { InvitationList } from "./invitation-list";
import { type InvitePrefill, InviteForm } from "./invite-form";
import { UserList } from "./user-list";

const copy = nb.admin.users;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_USERS_PATH },
] as const;

/** «Brukere og roller» in the Admin-område: the invite form (Story 3.7), the open requests for
 * lecturer access that fill it (Story 3.13), the User list with its role and status buttons
 * (Stories 3.9, 3.10), then the Invitations sent (Story 3.10). Only an Admin sees it; anyone else
 * gets the permission-denied page and no form. */
export function UsersPage() {
  const [prefill, setPrefill] = useState<InvitePrefill>();
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <section aria-labelledby="invite-title" className="mt-8">
            <h2 id="invite-title" className="text-headline text-ink">
              {copy.invite.title}
            </h2>
            <p className="mt-2 mb-5 max-w-md text-body-phone text-ink-secondary lg:text-body">{copy.invite.lead}</p>
            <InviteForm prefill={prefill} />
          </section>
          <section aria-labelledby="requests-title" className="mt-12">
            <h2 id="requests-title" className="text-headline text-ink">
              {copy.requests.title}
            </h2>
            <p className="mt-2 mb-5 max-w-md text-body-phone text-ink-secondary lg:text-body">{copy.requests.lead}</p>
            <AccessRequestList
              onInvite={(request) => setPrefill((prev) => ({ request, n: (prev?.n ?? 0) + 1 }))}
            />
          </section>
          <section aria-labelledby="users-title" className="mt-12">
            <h2 id="users-title" className="mb-4 text-headline text-ink">
              {copy.list.title}
            </h2>
            <UserList selfId={user.id} />
          </section>
          <section aria-labelledby="invitations-title" className="mt-12">
            <h2 id="invitations-title" className="mb-4 text-headline text-ink">
              {copy.invitations.title}
            </h2>
            <InvitationList />
          </section>
        </PageShell>
      )}
    </GuardedPage>
  );
}
