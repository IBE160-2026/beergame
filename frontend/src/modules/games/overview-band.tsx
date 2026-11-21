"use client";

import NextLink from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { Button, buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import { useThrottledAnnouncement } from "@/lib/announce";
import { roleName } from "@/modules/sessions/sessions";

import type { OverviewGame } from "./api";
import { bandMessagePath, bandSaid, bandText, type OverviewAlert } from "./overview";
import { consequenceText, resultText, TakeoverAction, type TakeoverResult } from "./spillstyring";
import { PauseResult, StaffPauseForm } from "./staff-pause";

/** Who put the AI player in the Seat, from the Oversikt read again (`mark_by`), never from the
 * refusal (Story 8.5). */
export function markBy(items: readonly OverviewGame[], gameId: string, role: string): string | null {
  return items.find((game) => game.game_id === gameId)?.seats.find((seat) => seat.role === role)?.mark_by ?? null;
}

/**
 * The Varselbånd (`attention-band`, Stories 7.11, 8.3 and 8.5, FR-39, FR-40, FR-37, UX-DR45,
 * DESIGN.md → Varselbånd): the Class game the api names as closest to Takeover (`alert`; the page
 * never picks it, AD-10) as a full-width `restordre-fill` band with `ink` text, «Spill 2 venter på
 * Noah (Grossist) i 23 t. KI overtar om 1 t.», counted on the server's clock (`now`, AD-20), the
 * consequence of a manual Takeover in caption text under it, the primary «Send Melding» to the
 * Meldingsskjema preset to the Student waited for and the secondary «Sett inn KI-spiller for Noah»
 * (Story 8.5), which Assistant lecturers have too. Below 1024 px the actions wrap under the text at
 * full width. Nothing is drawn when nothing waits, and nothing stands in its place. For a Lecturer
 * the secondary «Pause spillet» (Story 8.7) opens the Lecturer's pause form under the band; while it
 * is open «Send Melding» shows as secondary, so the screen keeps one primary. A paused game leaves
 * the band at once, and the result line («Pause til to. 19:00 er satt.») stands under it.
 *
 * After a press the band moves on to the next game, so the result line («KI-spiller satt inn for
 * Noah.», or who came first, named from the Oversikt read again) stands under the band and takes
 * focus. Its live region is always mounted: the band's game and Student are read out politely when
 * they appear or change, at most once a minute, never its ticking duration.
 */
export function OverviewBand({
  alert,
  sessionId,
  now,
  items = [],
  canPause = false,
  playDeadline = null,
}: {
  alert: OverviewAlert;
  sessionId: string;
  now: number;
  items?: readonly OverviewGame[];
  /** Story 8.7: the reader is a Lecturer of the Class, so the band offers «Pause spillet». */
  canPause?: boolean;
  playDeadline?: string | null;
}) {
  const id = useId();
  const said = useThrottledAnnouncement(bandSaid(alert));
  const [result, setResult] = useState<{ game: string; role: string; found: TakeoverResult } | null>(null);
  // Story 8.7: the game whose pause form is open under the band, and the Pause's result line.
  const [pauseFor, setPauseFor] = useState<string | null>(null);
  const [paused, setPaused] = useState({ text: "", n: 0 });
  const pauseRef = useRef<HTMLButtonElement>(null);
  const clock = useRef(now);
  clock.current = now;
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
  // The form belongs to the band's game: once the band moves on, it closes for good.
  const formOpen = canPause && alert !== null && pauseFor === alert.game_id;
  const bandGame = alert?.game_id ?? null;
  useEffect(() => {
    setPauseFor((open) => (open === bandGame ? open : null));
  }, [bandGame]);
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
              // While the pause form is open its button is the primary (UX-DR9).
              className={buttonClassName(formOpen ? "secondary" : "primary", "w-full shrink-0 lg:w-auto")}
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
              onPress={() => setPaused((prev) => ({ text: "", n: prev.n }))}
              onResult={(found) => {
                focusLine.current = true;
                setResult({ game: alert.game_id, role: alert.role, found });
              }}
            />
            {canPause ? (
              <Button
                ref={pauseRef}
                data-band-pause=""
                className="w-full shrink-0 lg:w-auto"
                aria-expanded={formOpen}
                onClick={() => {
                  setResult(null);
                  setPaused((prev) => ({ text: "", n: prev.n }));
                  setPauseFor(formOpen ? null : alert.game_id);
                }}
              >
                {nb.spillstyring.pause.open}
              </Button>
            ) : null}
          </div>
        </section>
      ) : null}
      {formOpen && alert ? (
        <StaffPauseForm
          key={alert.game_id}
          className="mt-3"
          gameId={alert.game_id}
          sessionId={sessionId}
          mode="pause"
          playDeadline={playDeadline}
          now={() => clock.current}
          onCancel={() => {
            setPauseFor(null);
            requestAnimationFrame(() => pauseRef.current?.focus());
          }}
          onDone={(text) => {
            setPauseFor(null);
            setPaused((prev) => ({ text, n: prev.n + 1 }));
          }}
        />
      ) : null}
      {paused.text ? <PauseResult className="mt-3" text={paused.text} n={paused.n} /> : null}
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
