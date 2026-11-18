"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { nb } from "@/copy/nb";

import { type SessionUser, useMe } from "./api";
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
 * denied page at the same address; a visitor who is not logged in goes to «Logg inn». The
 * Lærerhjem and Hjem hold a heading only until Epics 4 and 6 fill them; the Admin-område's
 * sections come with Stories 3.9–3.12.
 */
export function HomePage({ page }: { page: Home }) {
  const router = useRouter();
  const me = useMe();
  const user = me.data;

  useEffect(() => {
    if (user === null) router.replace("/logg-inn");
  }, [user, router]);

  if (!user) return <PageShell />;
  if (!canView(page, user)) return <AccessDenied user={user} />;
  const other = CROSS_LINK[page];
  return (
    <PageShell user={user} title={TITLE[page]}>
      {other && canView(other, user) ? <PageLink href={HOME_PATH[other]}>{HOME_LINK[other]}</PageLink> : null}
    </PageShell>
  );
}

/** «Du har ikke tilgang til denne siden.» with a link to the User's own home (UX-DR59). It never
 * says whether the page or item exists. */
export function AccessDenied({ user }: { user: SessionUser }) {
  const home = homeOf(user);
  return (
    <PageShell user={user} title={nb.access.denied}>
      <PageLink href={HOME_PATH[home]}>{HOME_LINK[home]}</PageLink>
    </PageShell>
  );
}
