import { nb } from "@/copy/nb";
import { WeekTable } from "@/modules/games/week-table-view";

import { DEMO_GUIDED_ORDER, DEMO_SEAT } from "./demo-seat";

const copy = nb.landing.seat;
const CAPTION_ID = "landing-seat-caption";

/**
 * The Landing's Seat figure (Stories 3.13 and 6.8, UX-DR70, UX-DR71, AD-18): one Seat in a
 * Veiledet uke as the same Graf over tabell Students play on, the play screen's `WeekTable` over
 * the Demodata Seat, with no chart code of its own. The caption names the table, which is the
 * graph's alternative; the note under it says the Student sees only their own numbers and where
 * the time axis ends, and «Demodata».
 */
export function SeatFigure() {
  return (
    <figure className="m-0 max-w-full lg:w-fit" aria-labelledby={CAPTION_ID}>
      <p id={CAPTION_ID} className="mb-3 text-label font-semibold text-ink">
        {copy.caption}
      </p>
      <WeekTable state={DEMO_SEAT} nowOrder={DEMO_GUIDED_ORDER} labelledBy={CAPTION_ID} wide />
      {/* Below 1024 px the figure is as wide as the page while its table is not, so «Demodata»
          stands under the note, by the table, rather than at the page's right edge. */}
      <figcaption className="mt-2 flex flex-col gap-x-4 text-caption text-ink-muted lg:flex-row lg:flex-wrap lg:justify-between">
        <span>{copy.ownNumbers}</span>
        <span>{copy.demoData}</span>
      </figcaption>
    </figure>
  );
}
