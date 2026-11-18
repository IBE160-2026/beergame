"use client";

import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";

import { meKey, useMe } from "./api";
import { HOME_LINK, HOME_PATH, homeOf } from "./homes";
import { PageLink, PageShell } from "./page-shell";

/** «Fant ikke siden.» with a link home: the User's own home, or «Logg inn» (UX-DR59). While the
 * session loads it shows the Skjelett, and a failed load the page-error line (Story 3.4). */
export function NotFoundPage() {
  const me = useMe();
  const { phase, retry } = usePageState(me, meKey);
  const user = me.data ?? undefined;
  const home = user ? homeOf(user) : undefined;
  return (
    <PageShell user={user} title={nb.access.notFound} phase={phase} onRetry={retry} updatedAt={me.dataUpdatedAt}>
      {home ? <PageLink href={HOME_PATH[home]}>{HOME_LINK[home]}</PageLink> : null}
      {/* Not logged in: «Logg inn» is the way home. */}
      {me.data === null ? <PageLink href="/logg-inn">{nb.navigation.toLogin}</PageLink> : null}
    </PageShell>
  );
}
