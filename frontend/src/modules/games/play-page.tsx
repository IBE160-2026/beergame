"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { clearDraft, clearDrafts, loadDraft, saveDraft } from "@/lib/drafts";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { orderPreview } from "@/lib/preview";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH, rulesPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, placeOrder, type PlayEnvelope, playKey, useMyGame, usePlay, viewWeek } from "./api";
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
 * the Student types the Order, previewed in the table and the Kjedebånd (Story 6.11), kept as a
 * draft in this browser until it is sent, and sends it with «Bekreft ordre på 24» (Story 6.12);
 * later stories add Setestatus. A game that has not started, or that this Student may
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
      {game ? shown ? <Running game={game} envelope={shown} userId={user.id} /> : running ? null : <NotRunning game={game} /> : null}
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
        {/* Takes focus when the Student's own Order completed the Uke and the next one shows. */}
        <h1 id={WEEK_HEADING} tabIndex={-1} className="text-title-phone text-ink outline-none lg:text-title-page">
          {copy.week(state.week)}
        </h1>
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

const WEEK_HEADING = "play-week";

/** The draft field of the typed Order of `gameId` in Uke `week` (`lib/drafts.ts`). */
const orderDraftPrefix = (gameId: string) => `order:${gameId}:`;
const orderDraftField = (gameId: string, week: number) => `${orderDraftPrefix(gameId)}${week}`;

function Running({ game, envelope, userId }: { game: MyGame; envelope: PlayEnvelope; userId: string }) {
  useGuidedView(game.id, envelope);
  const state = envelope.seat_state;
  const turn = envelope.turn;
  const field = orderDraftField(game.id, state.week);
  // The typed Order belongs to its game and Uke: a new Uke starts empty, unless this browser
  // kept a draft of that very Uke for this User (a reload, a page left, an ended session).
  const [typed, setTyped] = useState<{ game: string; week: number; text: string } | null>(null);
  const text = typed?.game === game.id && typed.week === state.week ? typed.text : (loadDraft(userId, field) ?? "");
  const editable = !turn.guided && turn.order == null;
  // Drafts of the game's other Uker are of no use any more; nor is this Uke's once it is ordered.
  useEffect(() => {
    clearDrafts(userId, orderDraftPrefix(game.id), editable ? field : undefined);
  }, [userId, game.id, field, editable]);
  const send = useSendOrder(game.id, state.week, userId, field);
  const parsed = parseOrder(text, state.max_order);
  // The live preview (Story 6.11, AD-10): a valid value on an editable field, and the sent Order
  // after it, which the table and the Kjedebånd keep showing (Story 6.12, `06` C).
  const placed = !turn.guided && turn.order != null ? turn.order : null;
  const preview =
    placed !== null
      ? { ...orderPreview(state.preview, placed), confirmed: true }
      : editable && parsed.kind === "valid"
        ? orderPreview(state.preview, parsed.value)
        : null;
  return (
    <div className="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12">
      <div className="min-w-0">
        {/* Reading and focus order: Topplinje, Kjedebånd, Graf over tabell, the rest (FR-73). */}
        <ChainBandView state={state} seatRoles={game.seats.map((seat) => seat.role)} typed={preview?.order} />
        {/* A placed Order (a Veiledet uke's fixed Order) stands in Din ordre at nå; a typed one
            there and at its arrival Uke. */}
        <WeekTable state={state} nowOrder={turn.guided ? (turn.order ?? undefined) : undefined} typed={preview ?? undefined} />
      </div>
      <div>
        {/* The Ordrefelt follows the table on phone and tops the right column on laptop. */}
        <OrderField
          week={state.week}
          turn={turn}
          max={state.max_order}
          lastOrder={lastOrder(state.history)}
          text={text}
          onText={(next) => {
            setTyped({ game: game.id, week: state.week, text: next });
            saveDraft(userId, field, next);
          }}
          preview={editable ? preview : null}
          sending={send.sending === state.week}
          onConfirm={send.confirm}
        />
        <PageLink href={rulesPath(game.id)}>{nb.games.briefing.title}</PageLink>
        <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
        <Seats game={game} />
      </div>
    </div>
  );
}

/**
 * «Bekreft ordre på 24» (Story 6.12, AD-2, UX-DR60): sends the Order once (a press while it is on
 * its way does nothing), with no `version`. Either way the play envelope is read again, which
 * shows the Confirmed state (the Order is stored), the next Uke (it completed the Uke) or the
 * typed state again (it was refused or never arrived; Story 6.13 says so in words). After a
 * success the draft is dropped and focus moves to «Ordren på 24 er sendt.», or to the new Uke's
 * heading when the Uke moved on. Live updates never move focus: only this send does.
 */
function useSendOrder(gameId: string, week: number, userId: string, field: string) {
  const queryClient = useQueryClient();
  const inFlight = useRef(false);
  // The Uke whose Order is on its way: a new Uke shown meanwhile is not Submitting.
  const [sending, setSending] = useState<number | null>(null);
  const [sent, setSent] = useState<number | null>(null);
  useEffect(() => {
    if (sent === null) return;
    const target =
      sent === week ? document.querySelector<HTMLElement>("[data-order-sent]") : document.getElementById(WEEK_HEADING);
    target?.focus();
    setSent(null);
  }, [sent, week]);
  const confirm = (value: number) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setSending(week);
    const reread = () => queryClient.refetchQueries({ queryKey: playKey(gameId), exact: true });
    placeOrder(gameId, week, value)
      .then(
        async () => {
          clearDraft(userId, field);
          await reread();
          setSent(week);
        },
        () => reread(),
      )
      .finally(() => {
        inFlight.current = false;
        setSending(null);
      });
  };
  return { sending, confirm };
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
