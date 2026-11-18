"use client";

import { nb } from "@/copy/nb";

import { useMe } from "./api";
import { LogoutButton } from "./logout-button";

/**
 * `/` for a logged-in User: the product header with «Logg ut», and the User's name. A placeholder
 * until Story 3.3 sends each Role to its own home. Anonymous visitors see nothing here until the
 * Landing (Story 3.13).
 */
export function SignedIn() {
  const me = useMe();
  if (!me.data) return <main />;
  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between gap-4 px-gutter-phone pt-6 lg:px-margin-laptop">
        <p className="text-label text-ink">{nb.product.name}</p>
        <LogoutButton />
      </header>
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <h1 className="text-title-phone text-ink lg:text-title-page">{me.data.name}</h1>
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{nb.auth.session.signedIn}</p>
      </main>
    </div>
  );
}
