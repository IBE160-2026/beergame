import type { ReactNode } from "react";

import { nb } from "@/copy/nb";

/**
 * The product header on every page (Story 3.3). The product name sits in a box as tall as a
 * button, so it stands at the same height whether or not the right side holds «Logg ut»
 * (Issue #68). No global navigation bar (UX-DR77): the right side holds only the session.
 */
export function AppHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 px-gutter-phone pt-6 lg:px-margin-laptop">
      <p className="flex min-h-control-height-phone items-center text-label text-ink">{nb.product.name}</p>
      {children}
    </header>
  );
}
