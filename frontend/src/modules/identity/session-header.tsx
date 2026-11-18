"use client";

import { AppHeader } from "@/components/app-header";

import type { SessionUser } from "./api";
import { LogoutButton } from "./logout-button";

/** The product header for a logged-in User: their name and «Logg ut» (UX-DR77). */
export function SessionHeader({ user }: { user: SessionUser }) {
  return (
    <AppHeader>
      <div className="flex flex-wrap items-start justify-end gap-x-4 gap-y-2">
        <p className="flex min-h-control-height-phone items-center text-body-phone text-ink-secondary lg:text-body">
          {user.name}
        </p>
        <LogoutButton />
      </div>
    </AppHeader>
  );
}
