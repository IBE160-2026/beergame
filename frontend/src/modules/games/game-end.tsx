"use client";

import NextLink from "next/link";
import { type ReactNode, useId } from "react";

import { buttonClassName } from "@/components/button";
import { ChainBill } from "@/components/chain-bill";
import { ChainCostChart } from "@/components/chain-cost-chart";
import { nb } from "@/copy/nb";
import { KRONER } from "@/lib/number-format";
import { DEBRIEF_PATH } from "@/modules/identity/homes";
import { roleName } from "@/modules/sessions/sessions";

import type { GameResult, MyGame } from "./api";
import { gameEnd } from "./result";

const copy = nb.games.play;
const LINE = "text-body-phone lg:text-body";

/** The hero total with a plain space before «kr», so at 200 % text on a phone «kr» wraps to the
 * next line instead of pushing the page sideways; the number itself never breaks. */
function heroTotal(total: string) {
  return total.endsWith(KRONER) ? `${total.slice(0, -KRONER.length)} kr` : total;
}

/** The page's heading: «Spillet er ferdig» over «Grossist, Spill 17», as the Topplinje stands. */
export function GameEndHeading({ game }: { game: MyGame }) {
  return (
    <div className="min-w-0">
      <h1 className="text-title-phone text-ink lg:text-title-page">{copy.end.title}</h1>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleGame(roleName(game.role), game.number)}</p>
    </div>
  );
}

/**
 * «Spillet er ferdig» (Story 6.18, FR-28, UX-DR30, EXPERIENCE.md, `06-spilldynamikk.png` F): under
 * `GameEndHeading`, then the chain's Total cost first («Kjedens totalkostnad», the
 * total in `figure-hero`, «Fire Roller, to kostnadsarter, hele spillet.»), then Kjedens regning per
 * Role, Kjedens kostnad over tid, the line that leads to the Debrief and the screen's one primary
 * button «Gå til Debrief». No ranking, praise or celebration (UX-DR72, UX-DR78). `note` is Epic 8's
 * slot for a game that ended at the Spillfrist; nothing renders there in Epic 6.
 */
export function GameEnd({ game, result, note }: { game: MyGame; result: GameResult; note?: ReactNode }) {
  const model = gameEnd(result, game.role);
  const id = useId();
  return (
    <div data-game-end="" className="max-w-md">
      {note ? <div data-game-end-note="">{note}</div> : null}
      <section aria-labelledby={`${id}-total`} className="mt-6">
        <h2 id={`${id}-total`} className="text-label text-ink-secondary">
          {copy.end.totalLabel}
        </h2>
        <p data-chain-total="" className="mt-1 text-figure-hero leading-tight text-ink">
          {heroTotal(model.total)}
        </p>
        <p className="mt-1 text-caption text-ink-secondary">{copy.end.totalNote}</p>
      </section>
      <ChainBill rows={model.rows} chain={model.chain} titleId={`${id}-bill`} className="mt-8" />
      <ChainCostChart points={model.points} rows={model.weeks} endLabels={model.endLabels} className="mt-8" />
      <p className={`${LINE} mt-8 text-ink`}>{copy.end.why}</p>
      <div className="mt-5">
        <NextLink href={DEBRIEF_PATH(game.id)} className={buttonClassName("primary")}>
          {copy.end.toDebrief}
        </NextLink>
      </div>
    </div>
  );
}
