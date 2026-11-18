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
            <li key={`${i}:${crumb.href}`} className="flex items-center gap-x-2">
              {i > 0 ? (
                <span aria-hidden="true" className="text-ink-muted">
                  /
                </span>
              ) : null}
              {current ? (
                <span aria-current="page" className="text-ink">
                  {crumb.label}
                </span>
              ) : (
                <Link href={crumb.href} standalone>
                  {crumb.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
