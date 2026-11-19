"use client";

import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { GuardedPage } from "@/modules/identity/home-page";
import { HOME_PATH, NEW_CLASS_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { classInstitutionsKey, useClassInstitutions } from "./api";
import { ClassForm } from "./class-form";

const copy = nb.classes.create;

const CRUMBS = [
  { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
  { label: copy.title, href: NEW_CLASS_PATH },
] as const;

/** «Lag Klasse» (Story 4.1): only a Lecturer sees it; anyone else gets the permission-denied page
 * and no form. The page waits for the Institutions the select offers. */
export function NewClassPage() {
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) => <NewClass user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function NewClass({ user, updatedAt }: { user: Parameters<typeof PageShell>[0]["user"]; updatedAt: number }) {
  const institutions = useClassInstitutions();
  const { phase, retry } = usePageState(institutions, classInstitutionsKey);
  return (
    <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS} phase={phase} onRetry={retry}>
      <p className="mt-2 max-w-md text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
      <ClassForm institutions={institutions.data?.items ?? []} />
    </PageShell>
  );
}
