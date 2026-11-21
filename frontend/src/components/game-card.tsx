import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Spillkort (`game-card`, DESIGN.md → Spillkort, EXPERIENCE.md → Spillkort, UX-DR28, Story 6.17):
 * Hjem's card for a game in play. It is a `paper` card with a 1 px `axis` border (decorative; the
 * content carries the meaning). The title (`label`) has the Uke right-aligned beside it. Under it
 * come the figure (a mini Graf over tabell), a screen-reader-only summary, then the Totalkostnad and
 * the action on one row that wraps. The figure's graph is `aria-hidden`, so the card's text plus
 * `summary` is its alternative, read straight after the table.
 *
 * The title is the variant: «Spillet venter på deg», the draft for a game that waits for others, or
 * Epic 13's «Oppfølgingsspill». The caller passes the words and the action; the card holds no rule
 * about the game.
 */
export function GameCard({
  title,
  titleId,
  week,
  figure,
  total,
  summary,
  action = null,
  className,
}: {
  title: string;
  titleId: string;
  /** «Uke 11», right of the title. */
  week: string;
  figure: ReactNode;
  /** «Totalkostnad 68,00 kr». */
  total: string;
  /** «Netto lager −13 i Uke 11.», read by screen readers only. */
  summary: string;
  /** The one primary button, a Lenke, or nothing. */
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section aria-labelledby={titleId} data-game-card="" className={cn("rounded-sm border border-axis bg-paper px-3 py-3", className)}>
      <h4 id={titleId} className="flex flex-wrap items-baseline justify-between gap-x-3 text-label font-semibold text-ink">
        <span>{title}</span>
        <span>
          <span className="sr-only">, </span>
          {week}
        </span>
      </h4>
      <div className="mt-2">{figure}</div>
      <p className="sr-only">{summary}</p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
        <p className="text-body-phone text-ink-secondary lg:text-body">{total}</p>
        {action}
      </div>
    </section>
  );
}
