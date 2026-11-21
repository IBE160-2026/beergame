"use client";

import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import type { WeekSummary } from "./week-summary";

const copy = nb.games.play.summary;

/**
 * The Uke-overgang (`week-summary`, Story 6.15, UX-DR23, `06-spilldynamikk.png` D): «Uke 11 er
 * ferdig regnet» with «Hopp over» at the right while the now-line moves, the rows of the Uke just
 * run («Restordre 13 blir 20») and the Uke's sum. It stands above the Ordrefelt and never takes
 * focus. The play screen's polite region reads it when the Uke moved on while the page was open,
 * not when the page loads. No celebration, no verdict (UX-DR78). Below 1024 px the Lenke
 * «Kostnad så langt» under the Uke's sum opens «Alle rader og kostnad» at that panel (Story 6.16);
 * from 1024 px the panel is pinned under the Ordrefelt, so the Lenke is not shown.
 */
export function WeekSummaryView({
  summary,
  moving,
  onSkip,
  onCost,
}: {
  summary: WeekSummary;
  /** The now-line is moving: «Hopp over» ends the move at once. */
  moving: boolean;
  onSkip: () => void;
  /** Opens «Alle rader og kostnad» at «Kostnad så langt» (phone only). */
  onCost?: (opener: HTMLElement) => void;
}) {
  return (
    <section aria-labelledby="week-summary-title" data-week-summary="" className="mt-8 max-w-md lg:mt-0 lg:mb-8">
      <div className="flex min-h-tap-target-min items-center justify-between gap-4">
        <h2 id="week-summary-title" className="text-label text-ink">
          {summary.title}
        </h2>
        {moving ? (
          <button type="button" className={cn(LINK_BUTTON, "justify-end")} onClick={onSkip}>
            {copy.skip}
          </button>
        ) : null}
      </div>
      <dl className="text-body-phone text-ink tabular-nums lining-nums lg:text-body">
        {summary.rows.map((row) => (
          <div key={row.label} className="flex justify-between gap-4 border-b border-hairline py-1">
            <dt>{row.label}</dt>
            <dd className="text-right">{row.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-caption font-semibold text-ink">{summary.cost}</p>
      {onCost ? (
        <button
          type="button"
          data-cost-link=""
          className={cn(LINK_BUTTON, "lg:hidden")}
          onClick={(event) => onCost(event.currentTarget)}
        >
          {copy.costLink}
        </button>
      ) : null}
    </section>
  );
}
