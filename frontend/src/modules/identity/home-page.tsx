"use client";

import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { loginPath } from "@/lib/return-path";

import { meKey, type SessionUser, useMe } from "./api";
import {
  ADMIN_AI_COST_PATH,
  ADMIN_AUDIT_PATH,
  ADMIN_EVALUATION_PATH,
  ADMIN_INSTITUTIONS_PATH,
  ADMIN_USERS_PATH,
  canView,
  HOME_LINK,
  HOME_PATH,
  type Home,
  homeOf,
} from "./homes";
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
 * line (Story 3.4). The Lærerhjem's content comes from `classes` as `children` (Story 4.1), and so
 * does Hjem's: the Student's Classes (Story 4.5) until Epic 6 fills it. The Admin-område lists its
 * pages, «Brukere og
 * roller» first (Story 3.7).
 */
export function HomePage({ page, children }: { page: Home; children?: ReactNode }) {
  return (
    <GuardedPage page={page}>
      {(user, updatedAt) => {
        const other = CROSS_LINK[page];
        return (
          <PageShell user={user} title={TITLE[page]} updatedAt={updatedAt}>
            {other && canView(other, user) ? <PageLink href={HOME_PATH[other]}>{HOME_LINK[other]}</PageLink> : null}
            {page === "adminArea" ? <AdminSections /> : null}
            {children}
          </PageShell>
        );
      }}
    </GuardedPage>
  );
}

/** The pages of the Admin-område (Story 3.7 on; `09-alle-sider.png`): one Lenke per page, in a
 * list under the heading. Later stories add theirs. */
function AdminSections() {
  return (
    <ul className="mt-6 flex max-w-md flex-col border-t border-hairline">
      <li className="border-b border-hairline">
        <Link href={ADMIN_USERS_PATH} standalone>
          {nb.admin.sections.users}
        </Link>
      </li>
      <li className="border-b border-hairline">
        <Link href={ADMIN_INSTITUTIONS_PATH} standalone>
          {nb.admin.sections.institutions}
        </Link>
      </li>
      <li className="border-b border-hairline">
        <Link href={ADMIN_AUDIT_PATH} standalone>
          {nb.admin.sections.audit}
        </Link>
      </li>
      <li className="border-b border-hairline">
        <Link href={ADMIN_EVALUATION_PATH} standalone>
          {nb.admin.sections.evaluation}
        </Link>
      </li>
      <li className="border-b border-hairline">
        <Link href={ADMIN_AI_COST_PATH} standalone>
          {nb.admin.sections.aiCost}
        </Link>
      </li>
    </ul>
  );
}

/**
 * A page only some Users may open (Story 3.3), as the homes and the Admin pages are. While `/me`
 * loads it shows the Skjelett, and a failed load the page-error line (Story 3.4); a visitor who
 * is not logged in goes to «Logg inn» and comes back after it; a User whose roles do not allow
 * `page` sees the permission-denied page at the same address. Otherwise it renders `children`
 * with the User. The API enforces access on every request; this decides what is shown. `any`
 * opens to every logged-in User and leaves it to the api alone: the play route, where a Student
 * plays their Class game and a Lecturer their test Game through the same scope (Story 6.20).
 */
export function GuardedPage({
  page,
  children,
}: {
  page: Home | "any";
  children: (user: SessionUser, updatedAt: number) => ReactNode;
}) {
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
  if (page !== "any" && !canView(page, user)) return <AccessDenied user={user} updatedAt={me.dataUpdatedAt} />;
  return <>{children(user, me.dataUpdatedAt)}</>;
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
