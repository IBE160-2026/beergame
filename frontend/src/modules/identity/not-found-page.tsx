"use client";

import { nb } from "@/copy/nb";

import { useMe } from "./api";
import { HOME_LINK, HOME_PATH, homeOf } from "./homes";
import { PageLink, PageShell } from "./page-shell";

/** «Fant ikke siden.» with a link home: the User's own home, or «Logg inn» (UX-DR59). */
export function NotFoundPage() {
  const me = useMe();
  const user = me.data ?? undefined;
  const home = user ? homeOf(user) : undefined;
  return (
    <PageShell user={user} title={nb.access.notFound}>
      {home ? <PageLink href={HOME_PATH[home]}>{HOME_LINK[home]}</PageLink> : null}
      {/* Not logged in, or the session could not be read: «Logg inn» is the way home. */}
      {!user && !me.isPending ? <PageLink href="/logg-inn">{nb.navigation.toLogin}</PageLink> : null}
    </PageShell>
  );
}
