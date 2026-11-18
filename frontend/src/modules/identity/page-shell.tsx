"use client";

import { type ReactNode, useEffect } from "react";

import { AppHeader } from "@/components/app-header";
import { Link } from "@/components/link";
import { nb } from "@/copy/nb";

import type { SessionUser } from "./api";
import { SessionHeader } from "./session-header";

/** One page: the header, then the h1 and what follows it, in the layout «Logg inn» uses. */
export function PageShell({ user, title, children }: { user?: SessionUser; title?: string; children?: ReactNode }) {
  // The tab title follows the h1, so a refused page is not titled with the page it refuses.
  useEffect(() => {
    if (title) document.title = `${title} – ${nb.product.name}`;
  }, [title]);
  return (
    <div className="min-h-dvh">
      {user ? <SessionHeader user={user} /> : <AppHeader />}
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        {title ? <h1 className="text-title-phone text-ink lg:text-title-page">{title}</h1> : null}
        {children}
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
