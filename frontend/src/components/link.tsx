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
