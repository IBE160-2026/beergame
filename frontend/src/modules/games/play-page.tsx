"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, useMyGame } from "./api";
import { GameAction } from "./game-action";
import { gameTitle, holderText } from "./home";

const copy = nb.games.play;
const LINE = "text-body-phone lg:text-body";

/**
 * The play route (Story 6.5, FR-22, mockup `05-spill.png`): while the game runs, the Topplinje's
 * «Uke 1» over «Grossist, Spill 17», then «Setene», each Seat's Role and who holds it in words
 * («KI-spiller» for every AI player). Never the number of Weeks. Later stories add the Kjedebånd,
 * Graf over tabell, Ordrefelt and Setestatus. A game that has not started, or that this Student
 * may not play before the briefing and Starting task, shows its next action (briefing, «Start
 * spillet» or the not-ready line); a finished one says so. The page follows the
 * game's `game:` events (`topics.ts`). Another Student's game shows the permission-denied page.
 */
export function PlayPage({ gameId }: { gameId: string }) {
  return (
    <GuardedPage page="home">{(user, updatedAt) => <PlayView gameId={gameId} user={user} updatedAt={updatedAt} />}</GuardedPage>
  );
}

function PlayView({ gameId, user, updatedAt }: { gameId: string; user: SessionUser; updatedAt: number }) {
  const found = useMyGame(gameId);
  const { phase, retry } = usePageState(found, myGameKey(gameId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const game = found.data;
  // The pre-play gate holds here too: a game another Student started shows «Les reglene» until
  // this Student has done the Starting task.
  const running = game?.status === "running" && game.week != null && !game.briefing_first;
  return (
    <PageShell
      user={user}
      title={game ? (running ? copy.week(game.week!) : gameTitle(game)) : undefined}
      updatedAt={updatedAt}
      phase={game ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {game ? running ? <Running game={game} /> : <NotRunning game={game} /> : null}
    </PageShell>
  );
}

function Running({ game }: { game: MyGame }) {
  return (
    <>
      <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleGame(roleName(game.role), game.number)}</p>
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      <Seats game={game} />
    </>
  );
}

function NotRunning({ game }: { game: MyGame }) {
  return (
    <>
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      {game.status === "finished" ? (
        <p className={`${LINE} mt-4 text-ink`}>{copy.finished}</p>
      ) : (
        <GameAction game={game} primary />
      )}
      <Seats game={game} />
    </>
  );
}

/** «Setene»: the four Seats, Fabrikk first, each holder in words (FR-34, UX-DR69). */
function Seats({ game }: { game: MyGame }) {
  const id = `seats-${game.id}`;
  return (
    <section aria-labelledby={id} className="mt-8 max-w-md">
      <h2 id={id} className="text-headline text-ink">
        {nb.homes.student.seats}
      </h2>
      <ul className="mt-2 flex flex-col border-t border-hairline">
        {game.seats.map((seat) => (
          <li key={seat.role} className={`${LINE} flex flex-wrap gap-x-4 border-b border-hairline py-2`}>
            <span className="min-w-[6.5rem] text-ink">{roleName(seat.role)}</span>
            <span className={seat.holder === "student" && seat.name ? "break-words text-ink" : "text-ink-secondary"}>
              {holderText(seat)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
