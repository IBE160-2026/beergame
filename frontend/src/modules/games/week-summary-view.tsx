"use client";

import { nb } from "@/copy/nb";

import type { WeekSummary } from "./week-summary";

const copy = nb.games.play.summary;

/** A Lenke as a button: it skips the move and commits nothing (EXPERIENCE.md → Lenke). */
const LINK =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer shrink-0 items-center justify-end whitespace-nowrap text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

/**
 * The Uke-overgang (`week-summary`, Story 6.15, UX-DR23, `06-spilldynamikk.png` D): «Uke 11 er
 * ferdig regnet» with «Hopp over» at the right while the now-line moves, the rows of the Uke just
 * run («Restordre 13 blir 20») and the Uke's sum. It stands above the Ordrefelt and never takes
 * focus. The play screen's polite region reads it when the Uke moved on while the page was open,
 * not when the page loads. No celebration, no verdict (UX-DR78). The Lenke «Kostnad
 * så langt» comes with its target in Story 6.16.
 */
export function WeekSummaryView({
  summary,
  moving,
  onSkip,
}: {
  summary: WeekSummary;
  /** The now-line is moving: «Hopp over» ends the move at once. */
  moving: boolean;
  onSkip: () => void;
}) {
  return (
    <section aria-labelledby="week-summary-title" data-week-summary="" className="mt-8 max-w-md lg:mt-0 lg:mb-8">
      <div className="flex min-h-tap-target-min items-center justify-between gap-4">
        <h2 id="week-summary-title" className="text-label text-ink">
          {summary.title}
        </h2>
        {moving ? (
          <button type="button" className={LINK} onClick={onSkip}>
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
    </section>
  );
}
