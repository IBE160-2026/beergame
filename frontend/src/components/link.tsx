import NextLink from "next/link";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/**
 * Lenke (DESIGN.md → Components → Controls). A link navigates or opens a panel, and never commits.
 * It is `lager`, weight 600 and underlined. On a tinted row or band (`onTint`) it is `ink`.
 * `standalone` gives a link that stands on its own line the 44 px tap target.
 */
export type LinkProps = ComponentProps<typeof NextLink> & {
  onTint?: boolean;
  standalone?: boolean;
};

export function Link({ onTint = false, standalone = false, className, ...props }: LinkProps) {
  return (
    <NextLink
      className={cn(
        "text-label underline underline-offset-2 hover:decoration-2",
        onTint ? "text-ink" : "text-lager active:text-ink",
        standalone && "inline-flex min-h-tap-target-min items-center",
        className,
      )}
      {...props}
    />
  );
}

/**
 * A Lenke drawn as a `<button>`, for one that opens a panel or changes a view in place and goes
 * nowhere («Hopp over», «Alle rader og kostnad», «Vis som tabell», «Lukk»): `lager`, weight 600,
 * underlined, with the 44 px tap target. It commits nothing (EXPERIENCE.md → Lenke).
 */
export const LINK_BUTTON =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer shrink-0 items-center whitespace-nowrap text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";
