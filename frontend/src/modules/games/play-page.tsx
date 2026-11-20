"use client";

import { useEffect } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH, rulesPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, type PlayEnvelope, playKey, useMyGame, usePlay } from "./api";
import { GameAction } from "./game-action";
import { gameTitle, holderText } from "./home";
import { ROWS } from "./week-table";
import { WeekTable } from "./week-table-view";

const copy = nb.games.play;
const LINE = "text-body-phone lg:text-body";

/**
 * The play route (Stories 6.5 and 6.6, FR-22, FR-23, FR-73, mockup `05-spill.png`): while the game
 * runs, the Topplinje («Uke 11» over «Grossist, Spill 17», «Totalkostnad» over the amount at the
 * right), the week table from the play envelope (`/api/me/games/{id}/play`), a Lenke to «Regler
 * før første ordre» and «Setene», each Seat's Role and who holds it in words («KI-spiller» for
 * every AI player). From 1024 px the table stands left and the rest in a right column. Never the
 * number of Weeks. Later stories add the graph, Kjedebånd, Ordrefelt and Setestatus. A game that
 * has not started, or that this Student may not play before the briefing and Starting task, shows
 * its next action (briefing, «Start spillet» or the not-ready line); a finished one says so. The
 * page follows the game's `game:` events (`topics.ts`). Another Student's game shows the
 * permission-denied page.
 */
export function PlayPage({ gameId }: { gameId: string }) {
  return (
    <GuardedPage page="home">{(user, updatedAt) => <PlayView gameId={gameId} user={user} updatedAt={updatedAt} />}</GuardedPage>
  );
}

function PlayView({ gameId, user, updatedAt }: { gameId: string; user: SessionUser; updatedAt: number }) {
  const found = useMyGame(gameId);
  const { phase, retry } = usePageState(found, myGameKey(gameId));
  const game = found.data;
  // The pre-play gate holds here too: a game another Student started shows «Les reglene» until
  // this Student has done the Starting task.
  const running = game?.status === "running" && game.week != null && !game.briefing_first;
  // The envelope is asked for only while the game runs; its wait follows the game's.
  const envelope = usePlay(gameId, running);
  const play = usePageState(envelope, playKey(gameId));
  // A game that stopped running between the two reads: read the game again, which then shows
  // where it stands (finished, or its next action).
  const stopped = envelope.error instanceof ApiRequestError && envelope.error.code === "game_not_running";
  const refetchGame = found.refetch;
  useEffect(() => {
    if (stopped) void refetchGame();
  }, [stopped, refetchGame]);
  const denied = [found.error, envelope.error].some((e) => e instanceof ApiRequestError && e.code === "forbidden");
  if (denied) return <AccessDenied user={user} updatedAt={updatedAt} />;
  const shown = running && envelope.data ? envelope.data : null;
  const pagePhase = !game
    ? phase === "ready"
      ? "loading"
      : phase
    : running && !shown
      ? play.phase === "ready"
        ? "loading"
        : play.phase
      : "ready";
  return (
    <PageShell
      user={user}
      title={game ? (running ? copy.week(shown?.seat_state.week ?? game.week!) : gameTitle(game)) : undefined}
      header={game && shown ? <Topplinje game={game} envelope={shown} /> : undefined}
      updatedAt={updatedAt}
      phase={pagePhase}
      onRetry={() => {
        retry();
        if (running) play.retry();
      }}
      skeleton={SKELETON}
    >
      {game ? shown ? <Running game={game} envelope={shown} /> : running ? null : <NotRunning game={game} /> : null}
    </PageShell>
  );
}

/** The Skjelett in the week table's real rows («Uke» and the phone's rows) and 12 columns. */
const SKELETON = { rows: 1 + ROWS.filter((row) => !row.laptopOnly).length, columns: 12 };

/** The Topplinje (DESIGN.md → Topplinje, UX-DR13): «Uke 11» over «Grossist, Spill 17», and
 * «Totalkostnad» over the amount at the right. Never the number of Uker (FR-14). */
function Topplinje({ game, envelope }: { game: MyGame; envelope: PlayEnvelope }) {
  const state = envelope.seat_state;
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div className="min-w-0">
        <h1 className="text-title-phone text-ink lg:text-title-page">{copy.week(state.week)}</h1>
        <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleGame(roleName(game.role), game.number)}</p>
      </div>
      <p className="text-right">
        <span className="block text-caption text-ink-secondary">{nb.terms.totalCost}</span>
        <span className="block text-figure-total text-ink tabular-nums lining-nums">
          {formatNumber(state.total_cost, { kroner: true })}
        </span>
      </p>
    </div>
  );
}

function Running({ game, envelope }: { game: MyGame; envelope: PlayEnvelope }) {
  return (
    <div className="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12">
      <div className="min-w-0">
        <WeekTable state={envelope.seat_state} />
      </div>
      <div>
        <PageLink href={rulesPath(game.id)}>{nb.games.briefing.title}</PageLink>
        <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
        <Seats game={game} />
      </div>
    </div>
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
