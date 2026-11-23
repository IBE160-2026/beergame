"use client";

import { usePathname } from "next/navigation";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";

export const STATEMENT_PATH = "/tilgjengelighet";

/** Pages without the footer: the print route (the Student report's PDF source) and the shared
 * projection screen, which fill the page or the wall by themselves. */
const WITHOUT_FOOTER = ["/print", "/delt-skjerm"];

/**
 * The footer under every page (Story 15.13, NFR-6): one Lenke to the accessibility statement, the
 * Landing's included. It stands below the page's own height, so it never moves a page's content.
 */
export function SiteFooter() {
  const path = usePathname() ?? "";
  if (WITHOUT_FOOTER.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))) return null;
  return (
    <footer className="px-gutter-phone pb-6 lg:px-margin-laptop">
      <div className="border-t border-hairline pt-2">
        {/* One long word: at 320 px with 200 % text it breaks rather than push the page sideways. */}
        <Link href={STATEMENT_PATH} standalone className="max-w-full [overflow-wrap:anywhere]">
          {nb.accessibility.footerLink}
        </Link>
      </div>
    </footer>
  );
}
