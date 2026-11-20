"use client";

import { useEffect, useRef, useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { orderPreview } from "@/lib/preview";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH, rulesPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, type PlayEnvelope, playKey, useMyGame, usePlay, viewWeek } from "./api";
import { ChainBandView } from "./chain-band-view";
import { GameAction } from "./game-action";
import { OrderField } from "./order-field";
import { lastOrder, parseOrder } from "./order-input";
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
 * number of Weeks. Over the table the Seat's own link stands as the Kjedebånd (Story 6.9). In a
 * Veiledet uke the Ordrefelt shows the fixed Order read-only, and the page tells the api once that
 * the Student has the Week on screen, which counts as their Order there (Story 6.10). After them
 * the Student types the Order, previewed in the table and the Kjedebånd (Story 6.11); later
 * stories send it and add Setestatus. A game that has not started, or that this Student may
 * not play before the briefing and Starting task, shows its next action (briefing, «Start spillet» or the not-ready line); a finished one says so. The
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
  useGuidedView(game.id, envelope);
  const state = envelope.seat_state;
  // The typed Order belongs to its game and Uke: a new Uke starts empty (Story 6.12 keeps drafts).
  const [typed, setTyped] = useState({ game: game.id, week: state.week, text: "" });
  const text = typed.game === game.id && typed.week === state.week ? typed.text : "";
  const editable = !envelope.turn.guided && envelope.turn.order == null;
  const parsed = parseOrder(text, state.max_order);
  // The live preview (Story 6.11, AD-10): only for a valid value on an editable field.
  const preview = editable && parsed.kind === "valid" ? orderPreview(state.preview, parsed.value) : null;
  return (
    <div className="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12">
      <div className="min-w-0">
        {/* Reading and focus order: Topplinje, Kjedebånd, Graf over tabell, the rest (FR-73). */}
        <ChainBandView state={state} seatRoles={game.seats.map((seat) => seat.role)} typed={preview?.order} />
        {/* A placed Order (a Veiledet uke's fixed Order) stands in Din ordre at nå; a typed one
            there and at its arrival Uke. */}
        <WeekTable state={state} nowOrder={envelope.turn.order ?? undefined} typed={preview ?? undefined} />
      </div>
      <div>
        {/* The Ordrefelt follows the table on phone and tops the right column on laptop. */}
        <OrderField
          week={state.week}
          turn={envelope.turn}
          max={state.max_order}
          lastOrder={lastOrder(state.history)}
          text={text}
          onText={(next) => setTyped({ game: game.id, week: state.week, text: next })}
          preview={preview}
        />
        <PageLink href={rulesPath(game.id)}>{nb.games.briefing.title}</PageLink>
        <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
        <Seats game={game} />
      </div>
    </div>
  );
}

/**
 * A Guided Week on screen that the Student has not opened yet: tell the api once per Week (Story
 * 6.10, `viewWeek`). A refusal (409: the game moved on, or 403) is left to the next `game:` event,
 * which reads the envelope again; any other failure (offline, a dropped request, a 5xx) is sent
 * again after `VIEW_RETRY_MS`, since the Week waits for this view. Nothing is shown for either.
 */
function useGuidedView(gameId: string, envelope: PlayEnvelope) {
  const sent = useRef(new Set<number>());
  const [attempt, setAttempt] = useState(0);
  const week = envelope.seat_state.week;
  const due = envelope.turn.guided && !envelope.turn.viewed;
  useEffect(() => {
    if (!due || sent.current.has(week)) return;
    sent.current.add(week);
    let retry: ReturnType<typeof setTimeout> | undefined;
    let live = true;
    viewWeek(gameId, week).catch((error: unknown) => {
      const refused = error instanceof ApiRequestError && (error.status === 403 || error.status === 409);
      if (refused || !live) return;
      sent.current.delete(week);
      retry = setTimeout(() => setAttempt((n) => n + 1), VIEW_RETRY_MS);
    });
    return () => {
      live = false;
      if (retry !== undefined) clearTimeout(retry);
    };
  }, [gameId, week, due, attempt]);
}

/** How long a failed view waits before it is sent again. */
const VIEW_RETRY_MS = 5000;

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
