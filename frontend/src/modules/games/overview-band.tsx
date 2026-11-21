"use client";

import NextLink from "next/link";
import { useId } from "react";

import { buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import { useThrottledAnnouncement } from "@/lib/announce";

import { bandMessagePath, bandSaid, bandText, type OverviewAlert } from "./overview";

/**
 * The Varselbånd (`attention-band`, Stories 7.11 and 8.3, FR-39, FR-40, UX-DR45, DESIGN.md →
 * Varselbånd): the Class game the api names as closest to Takeover (`alert`; the page never picks
 * it, AD-10) as a full-width `restordre-fill` band with `ink` text, «Spill 2 venter på Noah
 * (Grossist) i 23 t. KI overtar om 1 t.», counted on the server's clock (`now`, AD-20), and the
 * primary «Send Melding» to the Meldingsskjema preset to the Student waited for. Below 1024 px the
 * action wraps under the text at full width. Nothing is drawn when nothing waits, and nothing
 * stands in its place. Stories 8.5–8.7 add «Pause spillet» and «Sett inn KI-spiller».
 *
 * Its live region is always mounted: the band's game and Student are read out politely when they
 * appear or change, at most once a minute, never its ticking duration; focus never moves.
 */
export function OverviewBand({ alert, sessionId, now }: { alert: OverviewAlert; sessionId: string; now: number }) {
  const id = useId();
  const said = useThrottledAnnouncement(bandSaid(alert));
  return (
    <>
      <p role="status" className="sr-only" data-attention-announcement="">
        {said}
      </p>
      {alert ? (
        <section
          aria-labelledby={id}
          className="mt-6 flex flex-col gap-3 bg-restordre-fill px-4 py-3 lg:flex-row lg:items-center lg:justify-between lg:gap-6"
          data-attention-band={alert.game_id}
        >
          <h2 id={id} className="sr-only">
            {nb.overview.band.label}
          </h2>
          <p className="min-w-0 text-body-phone font-semibold text-ink tabular-nums lining-nums [overflow-wrap:anywhere] lg:text-body">
            {bandText(alert, now)}
          </p>
          <NextLink
            href={bandMessagePath(sessionId, alert)}
            className={buttonClassName("primary", "w-full shrink-0 lg:w-auto")}
            data-band-message=""
          >
            {nb.messages.send}
          </NextLink>
        </section>
      ) : null}
    </>
  );
}
