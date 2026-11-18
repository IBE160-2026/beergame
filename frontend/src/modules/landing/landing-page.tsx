import NextLink from "next/link";

import { AppHeader } from "@/components/app-header";
import { buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import { GoHome } from "@/modules/identity/go-home";

import { SeatTable } from "./seat-table";

const copy = nb.landing;

export const ACCESS_REQUEST_PATH = "/laerertilgang";

/**
 * The Landing at `/` (Story 3.13, UX-DR61, UX-DR9, UX-DR75): the product name, the headline in
 * `display`, the lead and the two ways in, then one Demodata Seat as a week table. It renders
 * without waiting for the session; a User who is logged in is sent on to their own home.
 * On laptop the headline stands left of the lead and buttons; on phone everything is one column
 * in the order headline, lead, buttons, Seat table.
 */
export function LandingPage() {
  return (
    <div className="min-h-dvh">
      <GoHome />
      <AppHeader />
      {/* The hairline sits directly under the header, as in 01-landing.png; the headline column is
          wide enough at 1280 px to break between the two sentences. */}
      <main className="px-gutter-phone pt-5 pb-16 lg:px-margin-laptop lg:pt-6">
        <div className="grid gap-x-12 gap-y-6 border-t border-hairline pt-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] lg:pt-12">
          <h1 className="text-title-phone text-ink lg:text-display">{copy.headline}</h1>
          <div className="flex flex-col gap-6">
            <p className="max-w-prose text-body-lead text-ink-secondary">{copy.lead}</p>
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
          <SeatTable />
          <p className="mt-8 text-body-phone text-ink-secondary lg:text-body">{copy.seat.classCurves}</p>
        </section>
      </main>
    </div>
  );
}
