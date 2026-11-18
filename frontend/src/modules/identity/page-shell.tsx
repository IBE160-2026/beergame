"use client";

import { type ReactNode, useEffect } from "react";

import { AppHeader } from "@/components/app-header";
import { Breadcrumb, type Crumb } from "@/components/breadcrumb";
import { ConnectionLine } from "@/components/connection-notice";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import type { PagePhase } from "@/lib/page-state";

import type { SessionUser } from "./api";
import { SessionHeader } from "./session-header";

/**
 * One page: the header, then the Tilkoblingslinje at the top of the content, then the h1 and
 * what follows it, in the layout «Logg inn» uses. While the page loads it shows the Skjelett;
 * a page that failed shows only the line «Siden kunne ikke lastes.» with «Prøv igjen» (Story 3.4).
 */
export function PageShell({
  user,
  title,
  phase = "ready",
  onRetry,
  updatedAt,
  crumbs,
  children,
}: {
  user?: SessionUser;
  /** The staff breadcrumb to this page (UX-DR77), shown above the heading. */
  crumbs?: readonly Crumb[];
  title?: string;
  phase?: PagePhase;
  onRetry?: () => void;
  updatedAt?: number;
  children?: ReactNode;
}) {
  const ready = phase === "ready";
  // The tab title follows the h1, so a refused page is not titled with the page it refuses.
  useEffect(() => {
    if (title && ready) document.title = `${title} – ${nb.product.name}`;
  }, [title, ready]);
  return (
    <div className="min-h-dvh">
      {user ? <SessionHeader user={user} /> : <AppHeader />}
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <ConnectionLine pageError={phase === "failed"} onRetry={onRetry} updatedAt={updatedAt} />
        {phase === "loading" || phase === "slow" ? (
          <>
            <Skeleton />
            <LoadingNote visible={phase === "slow"} />
          </>
        ) : null}
        {ready && crumbs ? (
          <div className="mb-4">
            <Breadcrumb items={crumbs} />
          </div>
        ) : null}
        {ready && title ? <h1 className="text-title-phone text-ink [overflow-wrap:anywhere] lg:text-title-page">{title}</h1> : null}
        {ready ? children : null}
      </main>
    </div>
  );
}

/** A Lenke on a line of its own under the heading. */
export function PageLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <p className="mt-4">
      <Link href={href} standalone>
        {children}
      </Link>
    </p>
  );
}
