"use client";

import NextLink from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import { useThrottledAnnouncement } from "@/lib/announce";
import { roleName } from "@/modules/sessions/sessions";

import type { OverviewGame } from "./api";
import { bandMessagePath, bandSaid, bandText, type OverviewAlert } from "./overview";
import { consequenceText, resultText, TakeoverAction, type TakeoverResult } from "./spillstyring";

/** Who put the AI player in the Seat, from the Oversikt read again (`mark_by`), never from the
 * refusal (Story 8.5). */
export function markBy(items: readonly OverviewGame[], gameId: string, role: string): string | null {
  return items.find((game) => game.game_id === gameId)?.seats.find((seat) => seat.role === role)?.mark_by ?? null;
}

/** The result line after the band moved to another game, or to none (follow-up of Story 8.5): the
 * press's own move keeps it (`moves` 0 → 1); any later move takes it away. */
export function afterBandMove<T extends { moves: number }>(was: T | null): T | null {
  return was === null || was.moves >= 1 ? null : { ...was, moves: was.moves + 1 };
}

/**
 * The Varselbånd (`attention-band`, Stories 7.11, 8.3 and 8.5, FR-39, FR-40, FR-37, UX-DR45,
 * DESIGN.md → Varselbånd): the Class game the api names as closest to Takeover (`alert`; the page
 * never picks it, AD-10) as a full-width `restordre-fill` band with `ink` text, «Spill 2 venter på
 * Noah (Grossist) i 23 t. KI overtar om 1 t.», counted on the server's clock (`now`, AD-20), the
 * consequence of a manual Takeover in caption text under it, the primary «Send Melding» to the
 * Meldingsskjema preset to the Student waited for and the secondary «Sett inn KI-spiller for Noah»
 * (Story 8.5), which Assistant lecturers have too. Below 1024 px the actions wrap under the text at
 * full width. Nothing is drawn when nothing waits, and nothing stands in its place. Stories 8.6–8.7
 * add «Pause spillet».
 *
 * After a press the band moves on to the next game, so the result line («KI-spiller satt inn for
 * Noah.», or who came first, named from the Oversikt read again) stands under the band and takes
 * focus; it goes when the band later moves to another game (or appears again after none waited).
 * A paused game is never the band's (Story 8.6: the api names only waiting games). Its live region is always mounted: the band's game and Student are read out politely when
 * they appear or change, at most once a minute, never its ticking duration.
 */
export function OverviewBand({
  alert,
  sessionId,
  now,
  items = [],
}: {
  alert: OverviewAlert;
  sessionId: string;
  now: number;
  items?: readonly OverviewGame[];
}) {
  const id = useId();
  const said = useThrottledAnnouncement(bandSaid(alert));
  const [result, setResult] = useState<{ game: string; role: string; found: TakeoverResult; moves: number } | null>(
    null,
  );
  // The band's game (or none). The press itself moves the band on once; the result line stays over
  // that move and goes when the band moves to another game after it (follow-up of Story 8.5).
  const shown = alert?.game_id ?? "";
  const lastShown = useRef(shown);
  useEffect(() => {
    if (lastShown.current === shown) return;
    lastShown.current = shown;
    setResult(afterBandMove);
  }, [shown]);
  const lineRef = useRef<HTMLParagraphElement>(null);
  const focusLine = useRef(false);
  useEffect(() => {
    if (focusLine.current && lineRef.current) {
      focusLine.current = false;
      lineRef.current.focus();
    }
  });
  const name = alert ? (alert.name ?? roleName(alert.role)) : "";
  const actedBy = result ? markBy(items, result.game, result.role) : null;
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
          <div className="min-w-0">
            <p
              className="text-body-phone font-semibold text-ink tabular-nums lining-nums [overflow-wrap:anywhere] lg:text-body"
              data-band-text=""
            >
              {bandText(alert, now)}
            </p>
            <p className="mt-1 text-caption text-ink [overflow-wrap:anywhere]" data-band-consequence="">
              {consequenceText("this_week", name)}
            </p>
          </div>
          <div className="flex w-full shrink-0 flex-col gap-3 lg:w-auto lg:flex-row lg:items-start">
            <NextLink
              href={bandMessagePath(sessionId, alert)}
              className={buttonClassName("primary", "w-full shrink-0 lg:w-auto")}
              data-band-message=""
            >
              {nb.messages.send}
            </NextLink>
            <TakeoverAction
              key={`${alert.game_id}:${alert.role}`}
              gameId={alert.game_id}
              sessionId={sessionId}
              role={alert.role}
              name={name}
              onResult={(found) => {
                focusLine.current = true;
                // A result set after the read again (someone came first) may find the band moved
                // already: that move was the press's own.
                const moved = lastShown.current !== alert.game_id;
                setResult({ game: alert.game_id, role: alert.role, found, moves: moved ? 1 : 0 });
              }}
            />
          </div>
        </section>
      ) : null}
      {result ? (
        <p
          ref={lineRef}
          tabIndex={-1}
          role="status"
          data-takeover-result={result.found.kind}
          className="mt-3 text-body-phone text-ink focus:outline-none lg:text-body"
        >
          {resultText(result.found, actedBy)}
        </p>
      ) : null}
    </>
  );
}
