"use client";

import { AppHeader } from "@/components/app-header";

import type { SessionUser } from "./api";
import { LogoutButton } from "./logout-button";

/**
 * The product header for a logged-in User: their name and «Logg ut» (UX-DR77). The session side
 * takes the room the product name leaves and the name wraps inside it, so a long name keeps the
 * header on one line on a phone; only when even «Logg ut» does not fit (200 % text on a phone)
 * does the side move under the product name.
 */
export function SessionHeader({ user }: { user: SessionUser }) {
  return (
    <AppHeader>
      <div className="flex min-w-min flex-1 items-start justify-end gap-x-4">
        <p className="flex min-h-control-height-phone min-w-0 items-center text-right text-body-phone text-ink-secondary [overflow-wrap:anywhere] lg:text-body">
          {user.name}
        </p>
        <div className="shrink-0">
          <LogoutButton />
        </div>
      </div>
    </AppHeader>
  );
}
