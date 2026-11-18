import type { ButtonHTMLAttributes, MouseEvent, MouseEventHandler } from "react";

import { cn } from "@/lib/utils";

/**
 * Knapper (DESIGN.md → Components → Controls). One primary button per screen.
 *
 * A button that cannot act takes `unavailable`. It renders `aria-disabled="true"`, keeps its focus
 * and ignores presses. It never gets the native `disabled`, which would drop focus (UX-DR8).
 */
export type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "disabled" | "aria-disabled"> & {
  variant?: "primary" | "secondary";
  unavailable?: boolean;
};

const base =
  "inline-flex min-h-control-height-phone items-center justify-center rounded-sm border px-5 py-2 text-button cursor-pointer aria-disabled:cursor-not-allowed";

const variants = {
  primary:
    "border-transparent bg-ink text-paper hover:not-aria-disabled:underline active:not-aria-disabled:bg-ink-secondary aria-disabled:border-axis aria-disabled:bg-future-tint aria-disabled:text-ink-muted",
  secondary:
    "border-ink-muted bg-paper text-ink hover:not-aria-disabled:border-ink active:not-aria-disabled:bg-hairline aria-disabled:border-axis aria-disabled:bg-future-tint aria-disabled:text-ink-muted",
} as const;

/** Wraps a click handler so presses are ignored while the control is unavailable. */
export function guardUnavailable(
  unavailable: boolean,
  handler?: MouseEventHandler<HTMLButtonElement>,
): MouseEventHandler<HTMLButtonElement> {
  return (event: MouseEvent<HTMLButtonElement>) => {
    if (unavailable) {
      event.preventDefault();
      return;
    }
    handler?.(event);
  };
}

export function Button({
  variant = "secondary",
  unavailable = false,
  className,
  onClick,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      aria-disabled={unavailable ? true : undefined}
      onClick={guardUnavailable(unavailable, onClick)}
      className={cn(base, variants[variant], className)}
      {...props}
    />
  );
}
