"use client";

import NextLink from "next/link";
import { useId } from "react";

import { buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import type { GameResult, MyGame } from "@/modules/games/api";
import { heroTotal } from "@/modules/games/game-end";
import { walkthroughPath } from "@/modules/identity/homes";

import { replayEnd } from "./replay";

const copy = nb.games.play.replayEnd;

/**
 * «Replay er ferdig» (Story 10.5, FR-50, UX-DR64, EXPERIENCE.md → Replay, Finished), under
 * `GameEndHeading` («Replay er ferdig» over «Grossist, Replay»): the Student's own Totalkostnad in
 * `figure-hero`, the line under it, then the screen's one primary button «Gå til gjennomgangen».
 * No Kjedens regning and no Debrief line: the Replay has no Debrief, and the walkthrough (Story
 * 10.7) sets the run beside the Class game. No ranking, praise or celebration (UX-DR72, UX-DR78).
 * Every number is the api's (AD-10).
 */
export function ReplayEnd({ game, result }: { game: MyGame; result: GameResult }) {
  const id = useId();
  const model = replayEnd(result, game.role);
  return (
    <div data-replay-end="" className="max-w-md">
      {model ? (
        <section aria-labelledby={`${id}-total`} className="mt-6">
          <h2 id={`${id}-total`} className="text-label text-ink-secondary">
            {copy.totalLabel}
          </h2>
          <p data-replay-total="" className="mt-1 text-figure-hero leading-tight text-ink">
            {heroTotal(model.total)}
          </p>
          <p className="mt-1 text-caption text-ink-secondary">{model.note}</p>
        </section>
      ) : null}
      <div className="mt-8">
        <NextLink href={walkthroughPath(game.id)} className={buttonClassName("primary", "w-full lg:w-auto")}>
          {copy.toWalkthrough}
        </NextLink>
      </div>
    </div>
  );
}
