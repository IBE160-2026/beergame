import NextLink from "next/link";

import { AppHeader } from "@/components/app-header";
import { buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import { CostPanel } from "@/modules/games/cost-panel-view";
import { GoHome } from "@/modules/identity/go-home";

import { DEMO_SEAT } from "./demo-seat";
import { SeatFigure } from "./seat-figure";
import { WallFigure } from "./wall-figure";

const copy = nb.landing;

export const ACCESS_REQUEST_PATH = "/laerertilgang";

/**
 * The Landing at `/` (Story 3.13, UX-DR61, UX-DR9, UX-DR75): the product name, the headline in
 * `display`, the lead and the two ways in, then one Demodata Seat as Graf over tabell (Story 6.8) with
 * its «Kostnad så langt», labelled «Demodata» (Story 6.16, UX-DR70). It renders without waiting for
 * the session; a User who is logged in is sent on to their own home. On laptop the headline stands
 * left of the lead and buttons, and the cost panel right of the Seat figure where the row has room
 * (`01-landing.png`), else under it; then «Alle spillene på én skjerm», the Matrisevegg with
 * Demodata (Story 7.2). On phone everything is one column in the order headline, lead,
 * buttons, Seat figure, «Kostnad så langt» (EXPERIENCE.md → Responsive & Platform → Landing).
 */
export function LandingPage() {
  return (
    <div className="min-h-dvh">
      <GoHome />
      <AppHeader />
      {/* The hairline sits directly under the header, as in 01-landing.png; the headline column is
          wide enough at 1280 px to break between the two sentences. */}
      <main className="px-gutter-phone pt-5 pb-16 lg:px-margin-laptop lg:pt-6">
        {/* One `minmax(0, 1fr)` column on phone, and the lead breaks a word that is wider than it
            («forsyningskjedeøvelsen» at 200 % text), so the page never scrolls sideways. */}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-x-12 gap-y-6 border-t border-hairline pt-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] lg:pt-12">
          <h1 className="text-title-phone text-ink lg:text-display">{copy.headline}</h1>
          <div className="flex flex-col gap-6">
            <p className="max-w-prose break-words hyphens-auto text-body-lead [hyphenate-limit-chars:8_4_3] text-ink-secondary">{copy.lead}</p>
            <div className="flex flex-wrap gap-3">
              <NextLink href={ACCESS_REQUEST_PATH} className={buttonClassName("primary")}>
                {copy.requestAccess}
              </NextLink>
              <NextLink href="/logg-inn" className={buttonClassName("secondary")}>
                {copy.login}
              </NextLink>
            </div>
          </div>
        </div>
        <section className="mt-12 lg:mt-16">
          <div className="flex flex-wrap items-start justify-between gap-x-12 gap-y-10">
            <SeatFigure />
            {/* Beside the figure, its title level with the first line under the caption, where `01-landing.png`
                draws the Kjedebånd (the Landing has no band). */}
            <CostPanel
              state={DEMO_SEAT}
              table="toggle"
              demoData={copy.seat.demoData}
              className="w-full min-w-0 lg:w-[20rem] xl:mt-10"
            />
          </div>
          <p className="mt-8 text-body-phone text-ink-secondary lg:text-body">{copy.seat.classCurves}</p>
        </section>
        <WallFigure />
      </main>
    </div>
  );
}
