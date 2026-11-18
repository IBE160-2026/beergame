"use client";

import { nb } from "@/copy/nb";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_USERS_PATH, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { InviteForm } from "./invite-form";
import { UserList } from "./user-list";

const copy = nb.admin.users;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_USERS_PATH },
] as const;

/** «Brukere og roller» in the Admin-område: the invite form (Story 3.7), then the User list with
 * its role buttons (Story 3.9). Only an Admin sees it; anyone else gets the permission-denied page
 * and no form. */
export function UsersPage() {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <section aria-labelledby="invite-title" className="mt-8">
            <h2 id="invite-title" className="text-headline text-ink">
              {copy.invite.title}
            </h2>
            <p className="mt-2 mb-5 max-w-md text-body-phone text-ink-secondary lg:text-body">{copy.invite.lead}</p>
            <InviteForm />
          </section>
          <section aria-labelledby="users-title" className="mt-12">
            <h2 id="users-title" className="mb-4 text-headline text-ink">
              {copy.list.title}
            </h2>
            <UserList selfId={user.id} />
          </section>
        </PageShell>
      )}
    </GuardedPage>
  );
}
