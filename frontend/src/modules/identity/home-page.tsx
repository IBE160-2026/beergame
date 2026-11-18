"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { loginPath } from "@/lib/return-path";

import { meKey, type SessionUser, useMe } from "./api";
import { canView, HOME_LINK, HOME_PATH, type Home, homeOf } from "./homes";
import { PageLink, PageShell } from "./page-shell";

const TITLE: Record<Home, string> = {
  adminArea: nb.homes.adminArea,
  lecturerHome: nb.homes.lecturerHome,
  home: nb.homes.home,
};

/** The link a home carries to the other home its User may open (FR-2: Admin and Lecturer). */
const CROSS_LINK: Partial<Record<Home, Home>> = { lecturerHome: "adminArea", adminArea: "lecturerHome" };

/**
 * One of the three homes (Story 3.3). A User whose roles do not allow it sees the permission-
 * denied page at the same address; a visitor who is not logged in goes to «Logg inn» and comes
 * back after it. While `/me` loads the page shows the Skjelett, and a failed load the page-error
 * line (Story 3.4). The
 * Lærerhjem and Hjem hold a heading only until Epics 4 and 6 fill them; the Admin-område's
 * sections come with Stories 3.9–3.12.
 */
export function HomePage({ page }: { page: Home }) {
  const router = useRouter();
  const pathname = usePathname();
  const me = useMe();
  const { phase, retry } = usePageState(me, meKey);
  const user = me.data;

  // Not logged in: «Logg inn», and back here after it (Story 3.4).
  useEffect(() => {
    if (user === null) router.replace(loginPath(`${pathname}${window.location.search}${window.location.hash}`));
  }, [user, router, pathname]);

  if (!user) return <PageShell phase={phase === "ready" ? "loading" : phase} onRetry={retry} />;
  if (!canView(page, user)) return <AccessDenied user={user} updatedAt={me.dataUpdatedAt} />;
  const other = CROSS_LINK[page];
  return (
    <PageShell user={user} title={TITLE[page]} updatedAt={me.dataUpdatedAt}>
      {other && canView(other, user) ? <PageLink href={HOME_PATH[other]}>{HOME_LINK[other]}</PageLink> : null}
    </PageShell>
  );
}

/** «Du har ikke tilgang til denne siden.» with a link to the User's own home (UX-DR59). It never
 * says whether the page or item exists. */
export function AccessDenied({ user, updatedAt }: { user: SessionUser; updatedAt?: number }) {
  const home = homeOf(user);
  return (
    <PageShell user={user} title={nb.access.denied} updatedAt={updatedAt}>
      <PageLink href={HOME_PATH[home]}>{HOME_LINK[home]}</PageLink>
    </PageShell>
  );
}
