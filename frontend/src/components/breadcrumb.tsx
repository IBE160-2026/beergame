import { nb } from "@/copy/nb";

import { Link } from "./link";

export type Crumb = { label: string; href: string };

/**
 * The staff breadcrumb, Lærerhjem → Klasse → Klasseøkt / Oversikt (UX-DR77). Later epics pass the
 * path to the current page; the last crumb is the page itself and is not a link. A single crumb
 * is the home itself, so nothing is shown.
 */
export function Breadcrumb({ items }: { items: readonly Crumb[] }) {
  if (items.length < 2) return null;
  return (
    <nav aria-label={nb.navigation.breadcrumb}>
      <ol className="flex flex-wrap items-center gap-x-2 text-body-phone lg:text-body">
        {items.map((crumb, i) => {
          const current = i === items.length - 1;
          return (
            // The separator ends its crumb rather than starting the next, so a wrapped line at
            // 390 px begins with a crumb, never with a lone «/».
            <li key={`${i}:${crumb.href}`} className="flex min-w-0 items-center gap-x-2">
              {current ? (
                <span aria-current="page" className="text-ink [overflow-wrap:anywhere]">
                  {crumb.label}
                </span>
              ) : (
                // A short crumb («Hjem», Story 12.9) still makes a 44 px tap target.
                <Link href={crumb.href} standalone className="min-w-tap-target-min [overflow-wrap:anywhere]">
                  {crumb.label}
                </Link>
              )}
              {current ? null : (
                <span aria-hidden="true" className="text-ink-muted">
                  /
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
