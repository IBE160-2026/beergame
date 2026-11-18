"use client";

import { nb } from "@/copy/nb";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_AUDIT_PATH, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { AuditLog } from "./audit-list";

const copy = nb.admin.audit;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_AUDIT_PATH },
] as const;

/** «Revisjonslogg» in the Admin-område (Story 3.12, FR-3): who did what and when, read only.
 * Only an Admin sees it; anyone else gets the permission-denied page. */
export function AuditPage() {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <p className="mt-2 mb-8 max-w-md text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <AuditLog />
        </PageShell>
      )}
    </GuardedPage>
  );
}
