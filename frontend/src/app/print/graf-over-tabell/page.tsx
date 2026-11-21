import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import type { SeatState } from "@/modules/games/api";
import week11 from "@/modules/games/fixtures/play-week-11.json";
import { WeekTable } from "@/modules/games/week-table-view";

/**
 * The AD-18 spike's print page (Story 6.7): Graf over tabell for the Demodata Grossist in Uke 11,
 * rendered on the server with every width fixed and no script needed, the way the Student report
 * page (Epic 13) will render it. `worker-batch` converts it with WeasyPrint (`pdf/ua-1`) in CI
 * (`app.platform.chart_print_check`) and fails if the chart is missing, clipped or off its
 * columns, or a font comes from outside the app. `/print/*` is internal only: the proxy answers
 * 404 (AD-11, AD-18). It holds no real data.
 */
export const dynamic = "force-static";

export const metadata: Metadata = { title: nb.terms.demoData };

/** Px widths that hold every number of the window at 13 px. */
const FIXED = { labelWidth: 96, columnWidth: 28, fontSize: 13 };

export default function GraphPrintPage() {
  return (
    <main className="bg-paper p-4 text-ink">
      <h1 className="text-headline">{nb.games.play.week(week11.seat_state.week)}</h1>
      <p className="mb-4 text-caption text-ink-secondary">{nb.terms.demoData}</p>
      <WeekTable state={week11.seat_state as SeatState} fixed={FIXED} />
    </main>
  );
}
