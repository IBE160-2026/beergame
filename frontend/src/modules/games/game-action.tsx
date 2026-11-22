"use client";

import { useQueryClient } from "@tanstack/react-query";
import NextLink from "next/link";
import { useRouter } from "next/navigation";

import { ActionError } from "@/components/action-error";
import { Button, buttonClassName } from "@/components/button";
import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { gamePath, HOME_LINK, HOME_PATH, rulesPath } from "@/modules/identity/homes";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { type MyGame, myGameKey, startGame } from "./api";
import { nextAction, toWeekText } from "./home";

const copy = nb.games.start;
const LINE = "text-body-phone text-ink lg:text-body";

/**
 * What the Student does next with their Class game (Story 6.5, FR-22, UX-DR78), on Hjem, on the
 * Startoppgave's done screen and on the play route alike: «Les reglene» until the Starting task is
 * done; then «Start spillet» with its consequence line above it and no second dialog; once the
 * game runs «Gå til Uke n»; before the game has its snapshot only the line that it is not ready;
 * once it has finished «Spillet er ferdig.» with a Lenke to the chain's Total cost (Story 6.18).
 * While the Play deadline playout plays the game out (Story 8.14) it says so, with a Lenke to the
 * game. `primary` makes it the screen's one primary control; otherwise it is a Lenke or a secondary
 * button. `homeWhenNotReady` adds «Til Hjem» to the not-ready line (the done screen).
 */
export function GameAction({
  game,
  primary,
  homeWhenNotReady = false,
}: {
  game: MyGame;
  primary: boolean;
  homeWhenNotReady?: boolean;
}) {
  if (game.status === "finished") {
    // Story 6.18: the game is over; «Spillet er ferdig» holds the chain's Total cost. A Lenke,
    // never the primary: the Debrief is Stegene's next step (Epic 9).
    return (
      <div className="mt-3 flex flex-col items-start gap-1">
        <p className={LINE}>{nb.homes.student.finished}</p>
        <Link href={gamePath(game.id)} standalone>
          {nb.homes.student.toResult}
        </Link>
      </div>
    );
  }
  if (game.status === "running" && game.played_out) {
    // Story 8.14: AI players play the game out; nothing is left for the Student to do in it.
    return (
      <div className="mt-3 flex flex-col items-start gap-1">
        <p className={LINE} data-playing-out="">
          {nb.homes.student.playingOut}
        </p>
        <Link href={gamePath(game.id)} standalone>
          {toWeekText(game)}
        </Link>
      </div>
    );
  }
  switch (nextAction(game)) {
    case "rules":
      return (
        <NavAction href={rulesPath(game.id)} primary={primary}>
          {nb.homes.student.readRules}
        </NavAction>
      );
    case "start":
      return <StartAction gameId={game.id} primary={primary} />;
    case "play":
      return (
        <NavAction href={gamePath(game.id)} primary={primary}>
          {toWeekText(game)}
        </NavAction>
      );
    case "notReady":
      return (
        <div className="mt-5 flex flex-col items-start gap-4">
          <p className={LINE}>{copy.notReady}</p>
          {homeWhenNotReady ? (
            <NextLink href={HOME_PATH.home} className={buttonClassName(primary ? "primary" : "secondary")}>
              {HOME_LINK.home}
            </NextLink>
          ) : null}
        </div>
      );
    default:
      return null;
  }
}

function NavAction({ href, primary, children }: { href: string; primary: boolean; children: string }) {
  if (primary) {
    return (
      <div className="mt-5">
        <NextLink href={href} className={buttonClassName("primary")}>
          {children}
        </NextLink>
      </div>
    );
  }
  return (
    <p className="mt-3">
      <Link href={href} standalone>
        {children}
      </Link>
    </p>
  );
}

/** «Start spillet» under its consequence line. The api starts the game, or finds it started by
 * another first, which counts as done; either way the Student lands on the play route. */
function StartAction({ gameId, primary }: { gameId: string; primary: boolean }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const starting = useAction({
    mutationFn: () => startGame(gameId),
    messages: copy.errors,
    fallback: copy.failed,
    onSuccess: (game) => {
      queryClient.setQueryData(myGameKey(gameId), game);
      void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
      router.push(gamePath(gameId));
    },
  });
  const done = starting.isSuccess;
  // A refused start means an earlier read was out of date: read the game and Hjem again.
  const press = () =>
    starting.mutate(undefined, {
      onError: () => {
        void queryClient.invalidateQueries({ queryKey: myGameKey(gameId) });
        void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
      },
    });
  return (
    <div className="mt-5 flex flex-col items-start gap-3">
      <p className={LINE}>{copy.consequence}</p>
      <Button
        variant={primary ? "primary" : "secondary"}
        unavailable={starting.isPending || done}
        onClick={press}
      >
        {copy.start}
      </Button>
      <ActionError message={starting.errorMessage} />
    </div>
  );
}
