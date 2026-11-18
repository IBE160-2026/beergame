"use client";

import { useState } from "react";

import { nb } from "@/copy/nb";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_INSTITUTIONS_PATH, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { InstitutionForm } from "./institution-form";
import { InstitutionList } from "./institution-list";

const copy = nb.admin.institutions;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_INSTITUTIONS_PATH },
] as const;

/** Which part of the page started an action last, counted per start. */
export type ActionStart = { by: "create" | "rename"; n: number };

/** «Institusjoner» in the Admin-område (Story 3.11, FR-3): the create form, then every
 * Institution with its creation date and a rename button. Only an Admin sees it; anyone else gets
 * the permission-denied page and no form. A new action in one part ends the result line of the
 * other, as on «Brukere og roller», so an old line never stands beside a new action. */
export function InstitutionsPage() {
  const [started, setStarted] = useState<ActionStart>();
  const start = (by: ActionStart["by"]) => setStarted((prev) => ({ by, n: (prev?.n ?? 0) + 1 }));
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <section aria-labelledby="create-title" className="mt-8">
            <h2 id="create-title" className="text-headline text-ink">
              {copy.create.title}
            </h2>
            <p className="mt-2 mb-5 max-w-md text-body-phone text-ink-secondary lg:text-body">{copy.create.lead}</p>
            <InstitutionForm onStart={() => start("create")} otherStarted={started?.by === "rename" ? started.n : 0} />
          </section>
          <section aria-labelledby="institutions-title" className="mt-12">
            <h2 id="institutions-title" className="mb-4 text-headline text-ink">
              {copy.list.title}
            </h2>
            <InstitutionList onStart={() => start("rename")} otherStarted={started?.by === "create" ? started.n : 0} />
          </section>
        </PageShell>
      )}
    </GuardedPage>
  );
}
