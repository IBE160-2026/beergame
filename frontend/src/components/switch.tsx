import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Bryter (DESIGN.md → Components → `switch`, UX-DR12): a native button with `role="switch"` and
 * `aria-checked`, so Space and Enter toggle it and a screen reader says «på» or «av». On, the
 * track is filled `ink` with a `paper` knob at the right; off, it is `paper` with an `ink-muted`
 * border and an `ink-secondary` knob at the left, so the knob's place carries the state, never the
 * colour alone. The state text (`children`) sits beside the track, inside the 44 px target, and is
 * read with the name: the accessible name is `labelledBy` (the setting's heading) and the text.
 * The shared focus ring is drawn around the whole target. In the Klasseøkt it follows the
 * Valgknapper rules: it changes a draft that takes effect on «Lagre Klasseøkt».
 */
export function Switch({
  id,
  checked,
  onChange,
  labelledBy,
  describedBy,
  children,
  className,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** The id of the setting's visible name, such as its heading. */
  labelledBy: string;
  describedBy?: string;
  /** The state in words beside the track («Ja, står i emneplanen» / «Nei»). */
  children: ReactNode;
  className?: string;
}) {
  const textId = `${id}-text`;
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={`${labelledBy} ${textId}`}
      aria-describedby={describedBy}
      onClick={() => onChange(!checked)}
      className={cn(
        "group inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center gap-3 rounded-sm py-2 pr-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "relative inline-block h-7 w-13 shrink-0 rounded-full border transition-colors motion-reduce:transition-none",
          checked ? "border-ink bg-ink text-paper" : "border-ink-muted bg-paper group-hover:border-ink",
        )}
      >
        <span
          className={cn(
            "absolute top-1/2 size-5 -translate-y-1/2 rounded-full transition-[left] motion-reduce:transition-none",
            checked ? "left-[calc(100%-1.5rem)] bg-paper" : "left-1 bg-ink-secondary text-paper",
          )}
        />
      </span>
      <span id={textId} className="text-body-phone text-ink lg:text-body">
        {children}
      </span>
    </button>
  );
}
